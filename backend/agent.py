from ai_parser import (
    parse_user_request,
    parse_complex_selection,
    parse_apartment_selection,
    detect_intent,
    find_information_target,
    generate_information_answer,
    compare_complexes_by_criterion,
    compare_apartments_by_criterion,
    is_context_reference_request,
    parse_context_selection,
    is_complex_reference_request,
    is_last_object_reference
)

from database import (
    search_apartments,
    search_nearest_apartments,
    get_complexes_for_filters,
    get_complexes_by_ids,
    get_complex_by_id,
    get_all_complexes,
    get_apartment_by_id,
    book_apartment
)


ERROR_MESSAGES = {
    "EMPTY_MESSAGE": "Пустой запрос.",
    "INVALID_REQUEST": "Не удалось обработать запрос.",
    "APARTMENT_NOT_FOUND": "Не удалось найти указанную квартиру.",
    "COMPLEX_NOT_FOUND": "Не удалось найти указанный жилой комплекс.",
    "BOOKING_UNAVAILABLE": "Эта квартира сейчас недоступна для бронирования.",
    "INVALID_BOOKING_TYPE": "Не удалось определить тип бронирования.",
    "INTERNAL_ERROR": "Произошла внутренняя ошибка. Попробуйте ещё раз."
}


def make_error(error_code, message=None):
    """Создаёт единый ответ об ошибке для API."""

    return {
        "type": "error",
        "error_code": error_code,
        "message": message or ERROR_MESSAGES[error_code]
    }


class ApartmentAgent:
    """Основное ядро агента по подбору квартир."""

    def __init__(self):
        self.current_filters = {
            "rooms": None,
            "max_price": None,
            "min_area": None,
            "max_area": None,
            "max_floor": None
        }

        self.last_user_request = ""

        # Последние показанные ЖК
        self.last_complexes = []

        # Выбранные ЖК
        self.selected_complex_ids = []

        # Последние показанные квартиры
        self.last_apartments = []

        # Все квартиры, показанные в рамках поиска
        self.shown_apartment_ids = set()

        # Выбранные квартиры
        self.selected_apartments = []

        # Последняя выбранная квартира
        self.last_selected_apartment = None

        # Последний выбранный ЖК
        self.last_selected_complex_id = None

        # Тип последнего списка: "apartment" или "complex"
        self.last_context_type = None

        # Квартира, для которой пользователь начал бронирование
        self.pending_booking_apartment = None

        # Шаг бронирования:
        # "type" — выбор типа брони;
        # "payment" — подтверждение оплаты.
        self.booking_step = None

    # --------------------------------------------------
    # Служебные функции
    # --------------------------------------------------

    def _apartment_to_dict(self, apartment):
        """Преобразует квартиру из tuple в JSON-совместимый словарь."""

        if not apartment:
            return None

        (
            apartment_id,
            complex_id,
            rooms,
            area,
            price,
            floor,
            finishing,
            balcony,
            image,
            booking_status,
            booking_type,
            booking_until
        ) = apartment

        complex_data = get_complex_by_id(complex_id)

        complex_name = None

        if complex_data:
            complex_name = complex_data[1]

        return {
            "id": apartment_id,
            "complex_id": complex_id,
            "complex": complex_name,
            "rooms": rooms,
            "area": area,
            "price": price,
            "floor": floor,
            "finishing": finishing,
            "balcony": balcony,
            "image": image,
            "booking_status": booking_status,
            "booking_type": booking_type,
            "booking_until": booking_until
        }


    def _build_recommendation(self, apartments, filters):
        """Определяет наиболее подходящую квартиру среди найденных."""

        if not apartments:
            return None

        # Сначала предпочитаем более дешёвые варианты. При одинаковой цене — большую площадь.
        best_apartment = min(
            apartments,
            key=lambda apartment: (
                apartment[4],
                -apartment[3]
            )
        )

        apartment_id = best_apartment[0]
        price = best_apartment[4]
        area = best_apartment[3]

        reasons = []

        if filters.get("rooms") is not None:
            reasons.append(
                f"{filters['rooms']}-комнатная квартира"
            )

        if filters.get("min_area") is not None:
            reasons.append(
                f"площадь {area:g} м² соответствует "
                f"минимуму {filters['min_area']:g} м²"
            )
    
        if filters.get("max_area") is not None:
            reasons.append(
                f"площадь {area:g} м² не превышает "
                f"максимум {filters['max_area']:g} м²"
            )

        if filters.get("max_price") is not None:
            reasons.append(
                f"цена {price:,.0f} ₽".replace(",", " ")
                + " укладывается в бюджет"
            )

        if filters.get("max_floor") is not None:
            reasons.append(
                f"{best_apartment[5]} этаж "
                f"соответствует ограничению"
            )

        if not reasons:
            reasons.append(
                "один из наиболее доступных вариантов"
            )

        return {
            "apartment_id": apartment_id,
            "reason": (
                "Рекомендую этот вариант: "
                + "; ".join(reasons)
                + "."
            )
        }


    def _explain_recommendation(self):
        """Объясняет, почему была выбрана рекомендованная квартира."""

        if not self.last_apartments:
            return {
                "type": "clarification",
                "message": (
                    "Сначала нужно подобрать квартиры, "
                    "и я объясню, почему рекомендую один из вариантов."
                )
            }

        recommendation = self._build_recommendation(
            self.last_apartments,
            self.current_filters
        )

        if not recommendation:
            return make_error(
                "INTERNAL_ERROR",
                "Не удалось определить рекомендуемый вариант."
            )

        apartment_id = recommendation["apartment_id"]

        apartment = next(
            (
                apartment
                for apartment in self.last_apartments
                if apartment[0] == apartment_id
            ),
            None
        )

        if not apartment:
            return make_error(
                "APARTMENT_NOT_FOUND",
                "Не удалось найти рекомендуемую квартиру."
            )

        price = apartment[4]
        area = apartment[3]
        rooms = apartment[2]
        floor = apartment[5]
        finishing = apartment[6]

        price_formatted = f"{price:,.0f}".replace(",", " ")

        message = (
            f"Я рекомендую квартиру №{apartment_id}, потому что "
            f"она полностью соответствует вашим требованиям: "
            f"{rooms}-комнатная, площадь {area:g} м², "
            f"цена {price_formatted} ₽. "
            f"Она находится на {floor} этаже, "
            f"отделка — {finishing.lower()}. "
            f"Среди найденных вариантов это самый доступный "
            f"вариант, который подходит под ваши условия."
        )

        return {
            "type": "information",
            "message": message,
            "apartment": self._apartment_to_dict(apartment),
            "recommendation": recommendation
        }
    

    def _complex_to_dict(self, complex_data):
        """Преобразует ЖК из tuple в JSON-совместимый словарь."""

        if not complex_data:
            return None

        complex_id = complex_data[0]
        name = complex_data[1]
        district = complex_data[2]
        housing_class = complex_data[3]
        completion_year = complex_data[4]
        description = complex_data[5]
        infrastructure = complex_data[6]
        parking = complex_data[7]

        result = {
            "id": complex_id,
            "name": name,
            "district": district,
            "housing_class": housing_class,
            "completion_year": completion_year,
            "description": description,
            "infrastructure": infrastructure,
            "parking": parking
        }

        # Если get_complexes_for_filters() дополнительно возвращает изображение и количество квартир
        if len(complex_data) > 8:
            result["image"] = complex_data[8]

        if len(complex_data) > 9:
            result["apartments_count"] = complex_data[9]

        return result

    def _apartments_to_dict(self, apartments):
        """Преобразует список квартир."""

        return [
            self._apartment_to_dict(apartment)
            for apartment in apartments
        ]

    def _complexes_to_dict(self, complexes):
        """Преобразует список ЖК."""

        return [
            self._complex_to_dict(complex_data)
            for complex_data in complexes
        ]

    def _is_request_complete(self):
        """Проверяет, указано ли обязательное количество комнат."""

        return self.current_filters.get("rooms") is not None

    def _reset_search_context(self):
        """Сбрасывает контекст предыдущего поиска."""

        self.shown_apartment_ids = set()

        self.selected_apartments = []

        self.last_selected_apartment = None

        self.selected_complex_ids = []

        self.last_selected_complex_id = None

    # --------------------------------------------------
    # Поиск квартир
    # --------------------------------------------------

    def _search(self):
        """Выполняет новый поиск квартир."""

        self._reset_search_context()

        apartments = search_apartments(
            self.current_filters
        )

        if not apartments:
            alternatives = search_nearest_apartments(
                self.current_filters,
                limit=5,
                exclude_ids=set()
            )

            self.last_apartments = alternatives
            self.last_context_type = "apartment"

            for apartment in alternatives:
                self.shown_apartment_ids.add(
                    apartment[0]
                )

            return {
                "type": "alternative",
                "message": (
                    "Точных совпадений не найдено. "
                    "Но я подобрал наиболее близкие варианты."
                ),
                "filters": self.current_filters.copy(),
                "complexes": [],
                "apartments": self._apartments_to_dict(
                    alternatives
                ),
                "selected_complex_ids": [],
                "selected_apartment_ids": []
            }

        self.last_apartments = apartments

        self.last_context_type = "apartment"

        for apartment in apartments:
            self.shown_apartment_ids.add(
                apartment[0]
            )

        complexes = get_complexes_for_filters(
            self.current_filters
        )

        self.last_complexes = complexes

        return {
            "type": "search",
            "message": "Найдены подходящие варианты.",
            "filters": self.current_filters.copy(),
            "complexes": self._complexes_to_dict(
                complexes
            ),
            "apartments": self._apartments_to_dict(
                apartments
            ),
            "selected_complex_ids": [],
            "selected_apartment_ids": [],
            "recommendation": self._build_recommendation(
                apartments,
                self.current_filters
            )
        }

    # --------------------------------------------------
    # Выбор квартир
    # --------------------------------------------------

    def _select_apartments(self, user_text):
        """Обрабатывает выбор квартир."""

        if not self.last_apartments:
            return make_error(
                "INVALID_REQUEST",
                "Сначала нужно выполнить поиск квартир."
            )

        selected = parse_apartment_selection(
            user_text,
            self.last_apartments
        )

        if not selected:
            return make_error(
                "INVALID_REQUEST",
                "Не удалось определить, какие квартиры вы выбрали."
            )

        
        for apartment in selected:
            if apartment not in self.selected_apartments:
                self.selected_apartments.append(apartment)

        self.last_selected_apartment = (
            self.selected_apartments[-1]
        )

        return {
            "type": "selection",
            "message": "Квартиры выбраны.",
            "filters": self.current_filters.copy(),
            "complexes": [],
            "apartments": self._apartments_to_dict(
                selected
            ),
            "selected_complex_ids": [],
            "selected_apartment_ids": [
                apartment[0]
                for apartment in selected
            ]
        }

    # --------------------------------------------------
    # Выбор ЖК
    # --------------------------------------------------

    def _select_complexes(self, user_text):
        """Обрабатывает выбор ЖК."""

        if not self.last_complexes:
            return make_error(
                "INVALID_REQUEST",
                "Сначала нужно получить список ЖК."
            )

        selected_ids = parse_complex_selection(
            user_text,
            self.last_complexes
        )

        if not selected_ids:
            return make_error(
                "INVALID_REQUEST",
                "Не удалось определить, какие ЖК вы выбрали."
            )

        selected = [
            complex_data
            for complex_data in self.last_complexes
            if complex_data[0] in selected_ids
        ]

        if not selected:
            return make_error(
                "COMPLEX_NOT_FOUND"
            )

        self.selected_complex_ids = [
            complex_data[0]
            for complex_data in selected
        ]

        self.last_selected_complex_id = selected[-1][0]

        self.last_context_type = "complex"

        return {
            "type": "selection",
            "message": "Жилые комплексы выбраны.",
            "filters": self.current_filters.copy(),
            "complexes": self._complexes_to_dict(
                selected
            ),
            "apartments": [],
            "selected_complex_ids": (
                self.selected_complex_ids.copy()
            ),
            "selected_apartment_ids": []
        }

    # --------------------------------------------------
    # Сравнение квартир
    # --------------------------------------------------

    def _compare_apartments(self, user_text):
        """Сравнивает выбранные квартиры."""

        if len(self.selected_apartments) < 2:
            return {
                "type": "comparison",
                "message": (
                    "Для сравнения нужно выбрать "
                    "как минимум две квартиры."
                ),
                "filters": self.current_filters.copy(),
                "complexes": [],
                "apartments": self._apartments_to_dict(
                    self.selected_apartments
                ),
                "selected_complex_ids": (
                    self.selected_complex_ids.copy()
                ),
                "selected_apartment_ids": [
                    apartment[0]
                    for apartment in self.selected_apartments
                ]
            }

        criterion = compare_apartments_by_criterion(
            user_text,
            self.selected_apartments
        )

        apartments = self._apartments_to_dict(
            self.selected_apartments
        )

        result = {
            "type": "comparison",
            "message": "Сравнение выбранных квартир.",
            "criterion": criterion,
            "apartments": apartments,
            "selected_apartment_ids": [
                apartment["id"]
                for apartment in apartments
            ]
        }

        if criterion:

            if criterion == "cheapest":

                best_apartment = min(
                    self.selected_apartments,
                    key=lambda apartment: apartment[4]
                )

                result["message"] = (
                    "Самый дешёвый вариант "
                    "среди выбранных квартир."
                )

            elif criterion == "most_expensive":

                best_apartment = max(
                    self.selected_apartments,
                    key=lambda apartment: apartment[4]
                )

                result["message"] = (
                    "Самый дорогой вариант "
                    "среди выбранных квартир."
                )

            elif criterion == "largest_area":

                best_apartment = max(
                    self.selected_apartments,
                    key=lambda apartment: apartment[3]
                )

                result["message"] = (
                    "Вариант с наибольшей площадью."
                )

            elif criterion == "smallest_area":

                best_apartment = min(
                    self.selected_apartments,
                    key=lambda apartment: apartment[3]
                )

                result["message"] = (
                    "Вариант с наименьшей площадью."
                )

            elif criterion == "highest_floor":

                best_apartment = max(
                    self.selected_apartments,
                    key=lambda apartment: apartment[5]
                )

                result["message"] = (
                    "Вариант на самом высоком этаже."
                )

            elif criterion == "lowest_floor":

                best_apartment = min(
                    self.selected_apartments,
                    key=lambda apartment: apartment[5]
                )

                result["message"] = (
                    "Вариант на самом низком этаже."
                )
    
            result["best_apartment_id"] = best_apartment[0]

        return result

    # --------------------------------------------------
    # Сравнение ЖК
    # --------------------------------------------------

    def _compare_complexes(self, user_text):
        """Сравнивает выбранные ЖК."""

        if len(self.selected_complex_ids) < 2:
            return {
                "type": "clarification",
                "message": (
                    "Для сравнения нужно выбрать "
                    "как минимум два ЖК."
                )
            }

        complexes = get_complexes_by_ids(
            self.selected_complex_ids
        )

        if not complexes:
            return make_error(
                "COMPLEX_NOT_FOUND",
                "Не удалось найти выбранные ЖК."
            )

        criterion = compare_complexes_by_criterion(
            user_text,
            complexes
        )

        return {
            "type": "comparison",
            "message": "Сравнение выбранных ЖК.",
            "criterion": criterion,
            "complexes": self._complexes_to_dict(
                complexes
            )
        }


    # --------------------------------------------------
    # Бронирование
    # --------------------------------------------------

    def _start_booking(self):
        """Начинает процесс бронирования выбранной квартиры."""

        if not self.last_selected_apartment:
            return make_error(
                "INVALID_REQUEST",
                "Сначала выберите квартиру."
            )

        apartment_id = self.last_selected_apartment[0]

        # Получаем актуальное состояние квартиры из базы.
        apartment = get_apartment_by_id(apartment_id)

        if apartment is None:
            return make_error(
                "APARTMENT_NOT_FOUND",
                "Квартира не найдена."
            )

        # Обновляем квартиру в памяти агента.
        self.last_selected_apartment = apartment

        # Если квартира уже забронирована,
        # не предлагаем повторно выбрать тип брони.
        if apartment[9] == "booked":
            return {
                "type": "booking",
                "message": "Эта квартира уже забронирована.",
                "apartment": self._apartment_to_dict(apartment)
            }

        self.pending_booking_apartment = apartment
        self.booking_step = "type"

        price_formatted = f"{apartment[4]:,.0f}".replace(",", " ")

        return {
            "type": "booking",
            "message": (
                f"Вы хотите забронировать квартиру №{apartment[0]} "
                f"стоимостью {price_formatted} ₽.\n\n"
                "Выберите тип бронирования:\n"
                "1. Бесплатная бронь — 3 часа, 0 ₽.\n"
                "2. Длительная бронь — 1 месяц, 20 000 ₽."
            ),
            "apartment": self._apartment_to_dict(apartment),
            "booking_options": [
                {
                    "type": "free",
                    "duration": "3 часа",
                    "price": 0
                },
                {
                    "type": "paid",
                    "duration": "1 месяц",
                    "price": 20000
                }
            ]
        }


    def _process_booking(self, user_text):
        """Обрабатывает выбор типа бронирования и оплату."""

        if not self.pending_booking_apartment:
            self.booking_step = None

            return make_error(
                "INVALID_REQUEST",
                "Сначала выберите квартиру, которую хотите забронировать."
            )

        text_lower = user_text.lower()

        # Отмена бронирования
        cancel_phrases = (
            "отмена",
            "отменить",
            "передумал",
            "передумала",
            "не хочу бронировать",
            "не хочу оплачивать",
            "не хочу платить"
        )

        if any(phrase in text_lower for phrase in cancel_phrases):
            self.booking_step = None
            self.pending_booking_apartment = None

            return {
                "type": "booking_cancelled",
                "message": "Хорошо, бронирование отменено."
            }


        # Выбор типа бронирования
        if self.booking_step == "type":

            # Бесплатная бронь
            if (
                "бесплат" in text_lower
                or "3 часа" in text_lower
                or text_lower in ["1", "первый", "первый вариант"]
            ):

                apartment_id = (
                    self.pending_booking_apartment[0]
                )

                result = book_apartment(
                    apartment_id,
                    "free"
                )

                if result["success"]:

                    updated_apartment = get_apartment_by_id(
                        apartment_id
                    )

                    self.last_selected_apartment = (
                        updated_apartment
                    )

                    self.booking_step = None
                    self.pending_booking_apartment = None

                    return {
                        "type": "booking",
                        "message": result["message"],
                        "booking": result,
                        "apartment": self._apartment_to_dict(
                            self.last_selected_apartment
                        )
                    }

                return make_error(
                    "BOOKING_UNAVAILABLE",
                    result["message"]
                )

            # Платная бронь
            if (
                "месяц" in text_lower
                or "платн" in text_lower
                or "длитель" in text_lower
                or "20" in text_lower
                or text_lower in ["2", "второй", "второй вариант"]
            ):

                self.booking_step = "payment"

                return {
                    "type": "payment",
                    "message": (
                        "Для бронирования на 1 месяц "
                        "необходимо оплатить 20 000 ₽.\n\n"
                        "Это демонстрационная оплата — "
                        "реальные деньги не списываются.\n\n"
                        "Подтвердить оплату?"
                    ),
                    "amount": 20000,
                    "apartment": self._apartment_to_dict(
                        self.pending_booking_apartment
                    ),
                    "payment_status": "pending"
                }

            return {
                "type": "clarification",
                "message": (
                    "Выберите тип бронирования:\n"
                    "1. Бесплатная бронь — 3 часа, 0 ₽.\n"
                    "2. Длительная бронь — 1 месяц, 20 000 ₽."
                )
            }

        # --------------------------------------------------
        # Подтверждение демонстрационной оплаты
        # --------------------------------------------------

        if self.booking_step == "payment":

            if (
                "да" in text_lower
                or "оплат" in text_lower
                or "подтвержда" in text_lower
                or "готов" in text_lower
                or text_lower in ["1", "подтвердить"]
            ):

                apartment_id = (
                    self.pending_booking_apartment[0]
                )

                result = book_apartment(
                    apartment_id,
                    "paid"
                )

                if result["success"]:

                    updated_apartment = get_apartment_by_id(
                        apartment_id
                    )

                    self.last_selected_apartment = (
                        updated_apartment
                    )

                    self.booking_step = None
                    self.pending_booking_apartment = None

                    return {
                        "type": "booking",
                        "message": (
                            "Оплата прошла успешно.\n\n"
                            + result["message"]
                        ),
                        "booking": result,
                        "payment_status": "success",
                        "apartment": self._apartment_to_dict(
                            self.last_selected_apartment
                        )
                    }

                self.booking_step = None
                self.pending_booking_apartment = None

                return make_error(
                    "BOOKING_UNAVAILABLE",
                    result["message"]
                )
            
            if (
                "нет" in text_lower
                or "отмен" in text_lower
                or "не хочу" in text_lower
            ):

                self.booking_step = None
                self.pending_booking_apartment = None

                return {
                    "type": "booking",
                    "message": "Бронирование отменено.",
                    "payment_status": "cancelled"
                }

            return {
                "type": "payment",
                "message": (
                    "Подтвердить демонстрационную оплату "
                    "20 000 ₽?\n"
                    "Реальные деньги не списываются."
                ),
                "amount": 20000,
                "payment_status": "pending"
            }


    # --------------------------------------------------
    # Информация о квартире
    # --------------------------------------------------

    def _apartment_information(self):
        """Возвращает подробную информацию о квартире."""

        if not self.last_selected_apartment:
            return make_error(
                "INVALID_REQUEST",
                "Сначала выберите квартиру."
            )

        apartment = self.last_selected_apartment

        return {
            "type": "information",
            "message": (
                "Подробная информация "
                "по выбранной квартире."
            ),
            "apartment": self._apartment_to_dict(
                apartment
            )
        }


    def _apartment_complex_information(self, user_text):
        """Возвращает информацию о ЖК выбранной квартиры."""

        if not self.last_selected_apartment:
            return make_error(
                "INVALID_REQUEST",
                "Сначала выберите квартиру."
            )

        apartment = self.last_selected_apartment

        complex_id = apartment[1]

        complex_data = get_complex_by_id(complex_id)

        if not complex_data:
            return make_error(
                "INTERNAL_ERROR",
                "Не удалось найти ЖК этой квартиры."
            )

        answer = generate_information_answer(
            user_text,
            complex_data
        )

        return {
            "type": "information",
            "message": answer,
            "complex": self._complex_to_dict(
                complex_data
            ),
            "apartment": self._apartment_to_dict(
                apartment
            )
        }

    # --------------------------------------------------
    # Информация о ЖК
    # --------------------------------------------------

    def _complex_information(self, user_text):
        """Возвращает информацию о ЖК."""

        complexes_for_search = self.last_complexes

        # Если список ЖК ещё не получен,
        # ищем среди всех ЖК из базы.
        if not complexes_for_search:
            complexes_for_search = get_all_complexes()

        target_id = find_information_target(
            user_text,
            complexes_for_search
        )

        if target_id is None:

            if self.last_selected_complex_id:

                target_id = (
                    self.last_selected_complex_id
                )

        if target_id is None:
            return make_error(
                "INVALID_REQUEST",
                "Не удалось определить, "
                "о каком ЖК идёт речь."
            )

        complex_data = get_complex_by_id(
            target_id
        )

        if not complex_data:
            return make_error(
                "COMPLEX_NOT_FOUND",
                "Не удалось найти этот ЖК."
            )

        answer = generate_information_answer(
            user_text,
            complex_data
        )

        return {
            "type": "information",
            "message": answer,
            "complex": self._complex_to_dict(
                complex_data
            )
        }

    # --------------------------------------------------
    # Другие варианты
    # --------------------------------------------------

    def _alternatives(self):
        """Возвращает следующие варианты."""

        if not self._is_request_complete():
            return {
                "type": "clarification",
                "message": (
                    "Сначала давайте определимся, "
                    "сколько комнат вам нужно."
                )
            }

        alternatives = search_nearest_apartments(
            self.current_filters,
            limit=5,
            exclude_ids=self.shown_apartment_ids
        )

        if not alternatives:
            return {
                "type": "alternative",
                "message": (
                    "Я показал все доступные "
                    "подходящие или наиболее близкие варианты."
                )
            }

        self.last_apartments = alternatives

        self.last_context_type = "apartment"

        for apartment in alternatives:
            self.shown_apartment_ids.add(
                apartment[0]
            )

        return {
            "type": "alternative",
            "message": "Вот другие варианты.",
            "filters": self.current_filters.copy(),
            "complexes": [],
            "apartments": self._apartments_to_dict(
                alternatives
            ),
            "selected_complex_ids": (
                self.selected_complex_ids.copy()
            ),
            "selected_apartment_ids": []
        }

    # --------------------------------------------------
    # Основная функция
    # --------------------------------------------------

    def process_message(self, user_text):
        """Обрабатывает одно сообщение пользователя."""

        user_text = user_text.strip()

        if not user_text:
            return make_error("EMPTY_MESSAGE")

        self.last_user_request = user_text

        text_lower = user_text.lower()

        # --------------------------------------------------
        # Бронирование
        # --------------------------------------------------

        if self.booking_step is not None:
            return self._process_booking(user_text)

        if (
            "забронировать" in text_lower
            or "бронь" in text_lower
            or "бронировать" in text_lower
        ):
            return self._start_booking()

        # --------------------------------------------------
        # Явный выбор квартиры
        # --------------------------------------------------

        if self.last_apartments:
            apartment_selection = parse_apartment_selection(
                user_text,
                self.last_apartments
            )

            if apartment_selection:

                self.selected_apartments = apartment_selection

                self.last_selected_apartment = (
                    apartment_selection[-1]
                )

                self.last_context_type = "apartment"

                wants_details = (
                    "расскажи" in text_lower
                    or "подробнее" in text_lower
                    or "информац" in text_lower
                    or "характеристик" in text_lower
                    or "что за квартира" in text_lower
                )

                if wants_details:
                    return self._apartment_information()

                return {
                    "type": "selection",
                    "message": "Квартира выбрана.",
                    "filters": self.current_filters.copy(),
                    "complexes": [],
                    "apartments": (
                        self._apartments_to_dict(
                            apartment_selection
                        )
                    ),
                    "selected_complex_ids": [],
                    "selected_apartment_ids": [
                        apartment[0]
                        for apartment in apartment_selection
                    ]
                }

        intent = detect_intent(
            user_text,
            self.last_complexes
        )

        # --------------------------------------------------
        # Менеджер
        # --------------------------------------------------

        if intent == "manager":

            return {
                "type": "manager",
                "message": (
                    "Конечно. Передаю ваш запрос менеджеру."
                ),
                "filters": self.current_filters.copy(),
                "last_request": self.last_user_request,
                "selected_complex_ids": (
                    self.selected_complex_ids.copy()
                )
            }

        # --------------------------------------------------
        # Другие варианты
        # --------------------------------------------------

        if intent == "alternative":

            parsed = parse_user_request(
                user_text,
                self.current_filters
            )

            updates = parsed.get(
                "updates",
                {}
            )

            clear_fields = parsed.get(
                "clear_fields",
                []
            )

            # Если пользователь одновременно изменил фильтры — сначала обновляем их
            if updates or clear_fields:

                for field, value in updates.items():

                    if field in self.current_filters:
                        self.current_filters[field] = value

                for field in clear_fields:

                    if field in self.current_filters:
                        self.current_filters[field] = None

                # Если после изменения фильтров не хватает количества комнат, просим его указать
                if not self._is_request_complete():

                    return {
                        "type": "clarification",
                        "message": (
                            "Скажите, сколько комнат "
                            "вам нужно."
                        ),
                        "filters": (
                            self.current_filters.copy()
                        )
                    }

                return self._search()

            # Если новых фильтров нет, действительно нужны просто альтернативы.
            return self._alternatives()


        # --------------------------------------------------
        # ЖК
        # --------------------------------------------------

        if intent == "complex":

            # Если список ЖК ещё не показывали,
            # загружаем все ЖК из базы.
            if not self.last_complexes:

                self.last_complexes = get_all_complexes()

                return {
                    "type": "selection",
                    "message": "Доступные жилые комплексы:",
                    "filters": self.current_filters.copy(),
                    "complexes": self._complexes_to_dict(
                        self.last_complexes
                    ),
                    "apartments": [],
                    "selected_complex_ids": [],
                    "selected_apartment_ids": []
                }

            return self._select_complexes(
                user_text
            )


        # --------------------------------------------------
        # Объяснение рекомендации
        # --------------------------------------------------

        if (
            "почему" in text_lower
            and (
                "рекоменд" in text_lower
                or "выбрал" in text_lower
                or "выбра" in text_lower
                or "лучший" in text_lower
                or "этот вариант" in text_lower
                or "этот" in text_lower
            )
        ):

            return self._explain_recommendation()

        # --------------------------------------------------
        # Явный выбор ЖК
        # --------------------------------------------------

        if is_complex_reference_request(user_text):

            selected_ids = parse_complex_selection(
                user_text,
                self.last_complexes
            )

            if selected_ids:

                selected = [
                    complex_data
                    for complex_data in self.last_complexes
                    if complex_data[0] in selected_ids
                ]

                if selected:

                    self.selected_complex_ids = [
                        complex_data[0]
                        for complex_data in selected
                    ]

                    self.last_selected_complex_id = (
                        selected[-1][0]
                    )

                    self.last_context_type = "complex"

                    return {
                        "type": "selection",
                        "message": (
                            "Жилые комплексы выбраны."
                        ),
                        "filters": self.current_filters.copy(),
                        "complexes": (
                            self._complexes_to_dict(
                                selected
                            )
                        ),
                        "apartments": [],
                        "selected_complex_ids": (
                            self.selected_complex_ids.copy()
                        ),
                        "selected_apartment_ids": []
                    }

        # --------------------------------------------------
        # Ссылка на последний контекст
        # --------------------------------------------------

        if (
            is_context_reference_request(user_text)
            and intent not in [
                "information",
                "comparison"
            ]
        ):

            if self.last_context_type == "apartment":

                selected = parse_context_selection(
                    user_text,
                    self.last_apartments
                )

                if selected:

                    for apartment in selected:
                        if apartment not in self.selected_apartments:
                            self.selected_apartments.append(
                                apartment
                            )

                    self.last_selected_apartment = (
                        self.selected_apartments[-1]
                    )

                    # Если пользователь одновременно
                    # выбрал квартиру и попросил рассказать о ней
                    wants_details = (
                        "расскажи" in text_lower
                        or "подробнее" in text_lower
                        or "информац" in text_lower
                        or "характеристик" in text_lower
                        or "что за квартира" in text_lower
                    )

                    if wants_details:
                        return self._apartment_information()

                    return {
                        "type": "selection",
                        "message": "Квартиры выбраны.",
                        "apartments": (
                            self._apartments_to_dict(
                                selected
                            )
                        ),
                        "selected_apartment_ids": [
                            apartment[0]
                            for apartment in selected
                        ]
                    }

            if self.last_context_type == "complex":

                selected = parse_context_selection(
                    user_text,
                    self.last_complexes
                )

                if selected:

                    self.selected_complex_ids = [
                        complex_data[0]
                        for complex_data in selected
                    ]

                    self.last_selected_complex_id = (
                        selected[-1][0]
                    )

                    return {
                        "type": "selection",
                        "message": (
                            "Жилые комплексы выбраны."
                        ),
                        "complexes": (
                            self._complexes_to_dict(
                                selected
                            )
                        ),
                        "selected_complex_ids": (
                            self.selected_complex_ids.copy()
                        )
                    }

        # --------------------------------------------------
        # Информация
        # --------------------------------------------------

        if intent == "information":

            # Если пользователь явно спрашивает про ЖК
            # выбранной квартиры
            if (
                self.last_selected_apartment
                and (
                    "что это за жк" in text_lower
                    or "какой жк" in text_lower
                    or "что за жк" in text_lower
                    or "жилой комплекс" in text_lower
                )
            ):

                return self._apartment_complex_information(
                    user_text
                )

            # Если уже выбрана квартира и пользователь
            # говорит о ней через контекст
            if (
                self.last_selected_apartment
                and (
                    is_last_object_reference(user_text)
                    or "квартир" in text_lower
                    or "вариант" in text_lower
                )
            ):

                return self._apartment_information()

            return self._complex_information(
                user_text
            )

        # --------------------------------------------------
        # Выбор квартиры
        # --------------------------------------------------

        if intent == "apartment":

            selected_result = self._select_apartments(
                user_text
            )

            wants_details = (
                "расскажи" in text_lower
                or "подробнее" in text_lower
                or "информац" in text_lower
                or "характеристик" in text_lower
                or "что за квартира" in text_lower
            )

            if (
                selected_result.get("type") == "selection"
                and wants_details
            ):

                return self._apartment_information()

            return selected_result

        # --------------------------------------------------
        # Сравнение
        # --------------------------------------------------

        if intent == "comparison":

            if (
                self.selected_apartments
                and len(self.selected_apartments) >= 2
            ):
                
                return self._compare_apartments(
                    user_text
                )

            # Если ЖК ещё не были выбраны, попробуем определить их прямо из сообщения.
            if not self.selected_complex_ids:

                complexes_for_selection = self.last_complexes

                # Если до этого список ЖК не был получен,
                # берём все ЖК из базы.
                if not complexes_for_selection:
                    complexes_for_selection = get_all_complexes()

                selected_ids = parse_complex_selection(
                    user_text,
                    complexes_for_selection
                )

                if len(selected_ids) >= 2:

                    self.selected_complex_ids = selected_ids

                    self.last_selected_complex_id = selected_ids[-1]

                    self.last_context_type = "complex"

            if self.selected_complex_ids:

                return self._compare_complexes(
                    user_text
                )

            return {
                "type": "clarification",
                "message": (
                    "Сначала выберите ЖК или квартиры, "
                    "которые хотите сравнить."
                )
            }

        # --------------------------------------------------
        # Изменение фильтров / поиск
        # --------------------------------------------------

        if intent == "filter":

            parsed = parse_user_request(
                user_text,
                self.current_filters
            )

            updates = parsed.get(
                "updates",
                {}
            )

            clear_fields = parsed.get(
                "clear_fields",
                []
            )

            # Применяем найденные изменения
            for field, value in updates.items():

                if field in self.current_filters:
                    self.current_filters[field] = value

            for field in clear_fields:

                if field in self.current_filters:
                    self.current_filters[field] = None

            # Если параметров недостаточно,
            # просим пользователя уточнить количество комнат
            if not self._is_request_complete():

                return {
                    "type": "clarification",
                    "message": (
                        "Скажите, сколько комнат "
                        "вам нужно."
                    ),
                    "filters": (
                        self.current_filters.copy()
                    )
                }

            # Если параметры уже полные,
            # выполняем поиск
            return self._search()

        # --------------------------------------------------
        # Неизвестный запрос
        # --------------------------------------------------

        return {
            "type": "clarification",
            "message": (
                "Я могу подобрать квартиру, "
                "сравнить варианты, рассказать о ЖК "
                "или передать запрос менеджеру."
            )
        }

if __name__ == "__main__":
    agent = ApartmentAgent()

    print("Агент запущен. Напишите сообщение.")
    print("Для выхода введите: выход")

    while True:
        user_text = input("\nВы: ")

        if user_text.lower() == "выход":
            print("Агент завершил работу.")
            break

        result = agent.process_message(user_text)

        print("\nАгент:")
        print(result)
