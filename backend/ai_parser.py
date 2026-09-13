import os
import json
import re

from dotenv import load_dotenv
from gigachat import GigaChat


load_dotenv()

GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")


def ask_gigachat(prompt):
    """Отправляет запрос в GigaChat и возвращает текст ответа."""

    if not GIGACHAT_CREDENTIALS:
        return None

    try:
        giga = GigaChat(
            credentials=GIGACHAT_CREDENTIALS,
            model="GigaChat-2",
            # Отключено для совместимости с окружением хакатона.
            # В production необходимо использовать проверку сертификатов.
            verify_ssl_certs=False
        )

        response = giga.chat(prompt)

        return response.choices[0].message.content

    except Exception as error:
        print(f"[GigaChat error] {error}")
        return None


def extract_number(text):
    """Извлекает число из строки."""

    match = re.search(r"\d+(?:[.,]\d+)?", text)

    if not match:
        return None

    return float(match.group(0).replace(",", "."))


def parse_user_request(user_text, current_filters=None):
    """
    Извлекает параметры поиска из сообщения пользователя.

    Возвращает:

    {
        "updates": {...},
        "clear_fields": [...]
    }
    """

    if current_filters is None:
        current_filters = {}

    text = user_text.lower().strip()

    updates = {}
    clear_fields = []

    # ==========================================================
    # КОМНАТЫ
    # ==========================================================

    room_patterns = [
        (1, r"\bоднушк\w*\b"),
        (1, r"\bоднокомнатн\w*\b"),
        (1, r"\b1[- ]?комнатн\w*\b"),
        (2, r"\bдвушк\w*\b"),
        (2, r"\bдвухкомнатн\w*\b"),
        (2, r"\b2[- ]?комнатн\w*\b"),
        (3, r"\bтрешк\w*\b"),
        (3, r"\bтрёшк\w*\b"),
        (3, r"\bтрехкомнатн\w*\b"),
        (3, r"\bтрёхкомнатн\w*\b"),
        (3, r"\b3[- ]?комнатн\w*\b"),
        (4, r"\bчетырехкомнатн\w*\b"),
        (4, r"\bчетырёхкомнатн\w*\b"),
        (4, r"\b4[- ]?комнатн\w*\b")
    ]

    for room_value, pattern in room_patterns:
        if re.search(pattern, text):
            updates["rooms"] = room_value
            break

    # ==========================================================
    # ОЧИСТКА ПАРАМЕТРОВ
    # ==========================================================

    # Площадь
    if re.search(
        r"(без ограничен\w* по площад|"
        r"не важна площад|"
        r"площадь не важна|"
        r"убери ограничен\w* по площад|"
        r"убрать ограничен\w* по площад|"
        r"сними ограничен\w* по площад|"
        r"снять ограничен\w* по площад|"
        r"без ограничений.*площад)",
        text
    ):
        clear_fields.append("min_area")
        clear_fields.append("max_area")

    # Цена
    if re.search(
        r"(без ограничен\w* по цен|"
        r"цена не важна|"
        r"бюджет не важен|"
        r"убери ограничен\w* по цен|"
        r"убрать ограничен\w* по цен|"
        r"сними ограничен\w* по цен|"
        r"снять ограничен\w* по цен|"
        r"бюджет можно не учитывать)",
        text
    ):
        clear_fields.append("max_price")

    # Этаж
    if re.search(
        r"(этаж не важен|"
        r"без ограничен\w* по этаж|"
        r"убери ограничен\w* по этаж|"
        r"убрать ограничен\w* по этаж|"
        r"сними ограничен\w* по этаж|"
        r"снять ограничен\w* по этаж)",
        text
    ):
        clear_fields.append("max_floor")

    # ==========================================================
    # ЦЕНА
    # ==========================================================

    price_match = re.search(
        r"(?:до|не дороже|максимум|бюджет(?:ом)? до)\s*"
        r"(\d+(?:[.,]\d+)?)\s*(?:млн|миллион(?:а|ов)?)",
        text
    )

    if price_match:
        value = float(price_match.group(1).replace(",", "."))
        updates["max_price"] = value * 1_000_000

    else:
        price_match = re.search(
            r"(\d+(?:[.,]\d+)?)\s*(?:млн|миллион(?:а|ов)?)",
            text
        )

        if price_match and re.search(
            r"(цен|стоим|бюджет|миллион|млн)",
            text
        ):
            value = float(price_match.group(1).replace(",", "."))
            updates["max_price"] = value * 1_000_000

    # Полная цена в рублях
    if "max_price" not in updates:
        price_rubles_match = re.search(
            r"(?:до|не дороже|максимум|бюджет(?:ом)? до)\s*"
            r"(\d{6,})\s*(?:руб|₽|р)?",
            text
        )

        if price_rubles_match:
            updates["max_price"] = float(price_rubles_match.group(1))

    # ==========================================================
    # ПЛОЩАДЬ
    # ==========================================================

    # Диапазон: 50-60 м²
    area_range = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(?:-|–|до)\s*"
        r"(\d+(?:[.,]\d+)?)\s*(?:м2|м²|кв\.?\s*м|квадрат)",
        text
    )

    if area_range:
        first = float(area_range.group(1).replace(",", "."))
        second = float(area_range.group(2).replace(",", "."))

        updates["min_area"] = min(first, second)
        updates["max_area"] = max(first, second)

    # Минимальная площадь
    min_area_match = re.search(
        r"(?:от|минимум|не меньше)\s*"
        r"(\d+(?:[.,]\d+)?)\s*"
        r"(?:м2|м²|кв\.?\s*м|квадрат)",
        text
    )

    if min_area_match:
        updates["min_area"] = float(
            min_area_match.group(1).replace(",", ".")
        )

    # Максимальная площадь
    max_area_match = re.search(
        r"(?:площад\w*\s*)?(?:до|не больше|максимум)\s*"
        r"(\d+(?:[.,]\d+)?)\s*"
        r"(?:м2|м²|кв\.?\s*м|квадрат)",
        text
    )

    if max_area_match:
        updates["max_area"] = float(
            max_area_match.group(1).replace(",", ".")
        )

    # ==========================================================
    # ЭТАЖ
    # ==========================================================

    floor_match = re.search(
        r"(?:до|не выше|не выше чем|максимум)\s*"
        r"(\d+)\s*(?:этаж\w*)",
        text
    )

    if floor_match:
        updates["max_floor"] = int(floor_match.group(1))

    # ==========================================================
    # ЕСЛИ ЧТО-ТО НАШЛИ — НЕ НУЖНО СПРАШИВАТЬ GIGACHAT
    # ==========================================================

    if updates or clear_fields:
        return {
            "updates": updates,
            "clear_fields": clear_fields
        }

    # ==========================================================
    # FALLBACK ЧЕРЕЗ GIGACHAT
    # ==========================================================

    prompt = f"""
Ты извлекаешь параметры поиска квартиры из сообщения пользователя.

Текущие параметры:
{json.dumps(current_filters, ensure_ascii=False)}

Сообщение:
{text}

Верни ТОЛЬКО JSON следующего формата:

{{
    "updates": {{
        "rooms": null,
        "min_area": null,
        "max_area": null,
        "max_price": null,
        "max_floor": null
    }},
    "clear_fields": []
}}

Правила:

rooms:
1, 2, 3 или 4.

min_area:
минимальная площадь в квадратных метрах.

max_area:
максимальная площадь в квадратных метрах.

max_price:
максимальная цена в рублях.

max_floor:
максимальный этаж.

Если параметр не упоминается — ставь null.

clear_fields:
если пользователь явно хочет убрать ранее заданное ограничение,
добавь название поля:
rooms
min_area
max_area
max_price
max_floor

Не добавляй пояснения.
"""

    answer = ask_gigachat(prompt)

    if not answer:
        return {
            "updates": {},
            "clear_fields": []
        }

    try:
        answer = answer.strip()

        answer = re.sub(r"^```json", "", answer)
        answer = re.sub(r"^```", "", answer)
        answer = re.sub(r"```$", "", answer)

        data = json.loads(answer)

        updates_from_ai = data.get("updates", {})
        clear_from_ai = data.get("clear_fields", [])

        updates = {
            key: value
            for key, value in updates_from_ai.items()
            if value is not None
        }

        return {
            "updates": updates,
            "clear_fields": clear_from_ai
        }

    except Exception:
        return {
            "updates": {},
            "clear_fields": []
        }


def generate_clarifying_question(filters):
    """Формирует уточняющий вопрос."""

    if filters.get("rooms") is None:
        return "Подскажите, пожалуйста, сколько комнат вам нужно?"

    return "Какие ещё параметры важны для вас?"


def should_ask_more(filters):
    """Проверяет, достаточно ли данных для поиска."""

    return filters.get("rooms") is None


def parse_apartment_selection(user_text, apartments):
    """Определяет, какие квартиры выбрал пользователь."""

    if not apartments:
        return []

    text = user_text.lower().strip()

    ordinal_words = {
        "первый": 1,
        "первая": 1,
        "первое": 1,
        "первую": 1,

        "второй": 2,
        "вторая": 2,
        "второе": 2,
        "вторую": 2,

        "третий": 3,
        "третья": 3,
        "третье": 3,
        "третью": 3,

        "четвертый": 4,
        "четвёртый": 4,
        "четвертая": 4,
        "четвёртая": 4,
        "четвертое": 4,
        "четвёртое": 4,
        "четвертую": 4,
        "четвёртую": 4,

        "пятый": 5,
        "пятая": 5,
        "пятое": 5,
        "пятую": 5,

        "шестой": 6,
        "шестая": 6,
        "шестое": 6,
        "шестую": 6,

        "седьмой": 7,
        "седьмая": 7,
        "седьмое": 7,
        "седьмую": 7,

        "восьмой": 8,
        "восьмая": 8,
        "восьмое": 8,
        "восьмую": 8,

        "девятый": 9,
        "девятая": 9,
        "девятое": 9,
        "девятую": 9,

        "десятый": 10,
        "десятая": 10,
        "десятое": 10,
        "десятую": 10
    }

    selected = []

    # --------------------------------------------------
    # 1. Выбор по порядковому номеру
    # --------------------------------------------------

    for word, number in ordinal_words.items():

        if word in text:

            index = number - 1

            if 0 <= index < len(apartments):

                apartment = apartments[index]

                if apartment not in selected:
                    selected.append(apartment)

    # --------------------------------------------------
    # 2. Выбор по номеру варианта
    # --------------------------------------------------

    variant_matches = re.findall(
        r"\b(?:вариант|варианта|варианту)\s*(?:№|#)?\s*(\d+)",
        text
    )

    for number_text in variant_matches:

        number = int(number_text)
        index = number - 1

        if 0 <= index < len(apartments):

            apartment = apartments[index]

            if apartment not in selected:
                selected.append(apartment)

    # --------------------------------------------------
    # 3. Выбор квартиры по ID
    # --------------------------------------------------

    id_matches = re.findall(
        r"\bid\s*(?:№|#)?\s*(\d+)",
        text
    )

    for apartment_id_text in id_matches:

        apartment_id = int(apartment_id_text)

        for apartment in apartments:

            if apartment[0] == apartment_id:

                if apartment not in selected:
                    selected.append(apartment)

                break

    # --------------------------------------------------
    # 4. Фраза "квартира 13" означает ID квартиры
    # --------------------------------------------------

    apartment_matches = re.findall(
        r"\bквартир(?:а|у|е|ой)?\s*(?:№|#)?\s*(\d+)",
        text
    )

    for number_text in apartment_matches:

        apartment_id = int(number_text)

        for apartment in apartments:

            if apartment[0] == apartment_id:

                if apartment not in selected:
                    selected.append(apartment)

                break

    return selected


def parse_complex_selection(user_text, complexes):
    """
    Определяет, какие ЖК выбрал пользователь.

    complexes — список кортежей из базы.
    """

    if not complexes:
        return []

    # Если пользователь явно указал номера ЖК, обрабатываем их без GigaChat.
    numeric_matches = re.findall(
        r"\bжк\s*№?\s*(\d+)\b",
        user_text.lower()
    )

    if numeric_matches:
        result = []

        for number_text in numeric_matches:
            number = int(number_text)

            # Здесь number — это именно ID ЖК из базы
            for complex_data in complexes:
                if complex_data[0] == number:
                    if complex_data[0] not in result:
                        result.append(complex_data[0])

        if result:
            return result

    # Если пользователь явно указал название ЖК, определяем его напрямую, без GigaChat.
    lower_text = user_text.lower()

    exact_name_matches = []

    for complex_data in complexes:
        complex_id = complex_data[0]
        name = complex_data[1]

        if name.lower() in lower_text:
            exact_name_matches.append(complex_id)

    if exact_name_matches:
        return exact_name_matches

    complex_names = [complex_data[1] for complex_data in complexes]

    prompt = f"""
Пользователь выбирает жилые комплексы из списка.

Доступные ЖК:

{chr(10).join(
    f"{index + 1}. {name}"
    for index, name in enumerate(complex_names)
)}

Сообщение пользователя:
"{user_text}"

Определи номера выбранных ЖК.

Например:

"первый, пятый и седьмой"
-> [1, 5, 7]

"первый и третий"
-> [1, 3]

"ЖК Парковый и ЖК Лесной"
-> соответствующие номера.

Верни ТОЛЬКО JSON:

{{
    "selected": [1, 5, 7]
}}
"""

    answer = ask_gigachat(prompt)

    if answer:
        try:

            answer = answer.strip()
            answer = re.sub(r"^```json", "", answer)
            answer = re.sub(r"^```", "", answer)
            answer = re.sub(r"```$", "", answer)

            data = json.loads(answer)

            selected = data.get("selected", [])

            result = []

            for number in selected:
                if isinstance(number, int):
                    index = number - 1

                    if 0 <= index < len(complexes):
                        result.append(complexes[index][0])

            if result:
                return result

        except Exception:
            pass

    # ==========================================================
    # FALLBACK БЕЗ GIGACHAT
    # ==========================================================

    ordinal_map = {
        "первый": 1,
        "первого": 1,
        "первая": 1,
        "второй": 2,
        "второго": 2,
        "вторая": 2,
        "третий": 3,
        "третьего": 3,
        "третья": 3,
        "четвертый": 4,
        "четвертого": 4,
        "четвёртый": 4,
        "четвёртого": 4,
        "пятый": 5,
        "пятого": 5,
        "шестой": 6,
        "шестого": 6,
        "седьмой": 7,
        "седьмого": 7
    }

    selected_numbers = []

    for word, number in ordinal_map.items():
        if re.search(rf"\b{word}\b", user_text.lower()):
            selected_numbers.append(number)

    # Убираем дубликаты и сортируем
    selected_numbers = sorted(set(selected_numbers))

    result = []

    for number in selected_numbers:
        index = number - 1

        if 0 <= index < len(complexes):
            result.append(complexes[index][0])

    # Дополнительно проверяем названия ЖК
    lower_text = user_text.lower()

    for complex_data in complexes:
        complex_id = complex_data[0]
        name = complex_data[1]

        if name.lower() in lower_text:
            if complex_id not in result:
                result.append(complex_id)

    return result


def is_comparison_request(user_text):
    """Определяет запрос пользователя на сравнение объектов."""

    text = user_text.lower().strip()

    if "парковк" in text:
        return True

    phrases = [
        # Общее сравнение
        "сравни",
        "сравнить",
        "сравнение",
        "сравни их",
        "сравни эти",
        "чем они отличаются",
        "чем отличаются",
        "в чем отличие",
        "в чем разница",
        "какая разница",

        # Инфраструктура
        "где лучше инфраструктура",
        "у кого лучше инфраструктура",
        "где инфраструктура лучше",
        "какая инфраструктура лучше",
        "где больше инфраструктуры",

        # Парковка
        "в каком из них есть подземная парковка",
        "у кого есть подземная парковка",
        "где есть подземная парковка",
        "в каком жк есть подземная парковка",
        "у какого жк есть подземная парковка",

        # Срок сдачи
        "какой раньше сдастся",
        "какой раньше сдается",
        "какой раньше сдаётся",
        "кто раньше сдастся",
        "кто раньше сдается",
        "кто раньше сдаётся",
        "какой из них раньше сдастся",
        "какой из них раньше сдается",
        "какой из них раньше сдаётся",
        "какой из них сдастся раньше",
        "какой из них сдается раньше",
        "какой из них сдаётся раньше",

        # Класс
        "какой класс выше",
        "у кого класс выше",
        "какой жк выше классом",

        # Район
        "какой район лучше",
        "где район лучше",
        "где лучше расположен",
        "какой расположен лучше",

        # Цена
        "какой дешевле",
        "какая дешевле",
        "у кого дешевле",
        "где дешевле",
        "какой из них дешевле",

        "какой дороже",
        "какая дороже",
        "у кого дороже",
        "где дороже",
        "какой из них дороже",

        # Площадь
        "у кого больше площадь",
        "у кого площадь больше",
        "у какой площадь больше",
        "у какой из них площадь больше",
        "какая площадь больше",
        "какая квартира больше",
        "какая из них больше",
        "кто больше по площади",
        "какая больше",

        "у кого меньше площадь",
        "у кого площадь меньше",
        "у какой площадь меньше",
        "у какой из них площадь меньше",
        "какая площадь меньше",
        "какая квартира меньше",
        "какая из них меньше",
        "кто меньше по площади",
        "какая меньше",
        "у кого площадь меньше",
        "какая площадь меньше",
        "какая квартира меньше",
        "кто меньше по площади",
        "какая меньше",

        # Этаж
        "какой этаж выше",
        "у кого этаж выше",
        "какая квартира выше",
        "кто выше",

        "какой этаж ниже",
        "у кого этаж ниже",
        "какая квартира ниже",
        "кто ниже",

        # Общие вопросы выбора
        "где лучше",
        "у кого лучше",
        "какой лучше",
        "какой из них лучше",
        "в каком лучше",
        "где больше",
        "у кого больше",
        "какой раньше",
        "какой позже"
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


def compare_apartments_by_criterion(
    user_text,
    apartments
):
    """Определяет конкретный критерий сравнения квартир."""

    if not apartments or len(apartments) < 2:
        return None

    text = user_text.lower().strip()

    # Цена — дешевле
    if any(
        phrase in text
        for phrase in [
            "какой дешевле",
            "какая дешевле",
            "у кого дешевле",
            "где дешевле",
            "какая квартира дешевле",
            "какой из них дешевле",
            "какая из них дешевле",
            "кто из них дешевле",
            "что дешевле",
            "что из них дешевле"
        ]
    ):
        return "cheapest"

    # Цена — дороже
    if any(
        phrase in text
        for phrase in [
            "какой дороже",
            "какая дороже",
            "у кого дороже",
            "где дороже",
            "какая квартира дороже",
            "какой из них дороже"
        ]
    ):
        return "most_expensive"

    # Площадь — больше
    if any(
        phrase in text
        for phrase in [
            "у кого больше площадь",
            "у кого площадь больше",
            "у какой площадь больше",
            "у какой из них площадь больше",
            "какая площадь больше",
            "какая квартира больше",
            "какая из них больше",
            "кто больше по площади",
            "какая больше"
        ]
    ):
        return "largest_area"

    # Площадь — меньше
    if any(
        phrase in text
        for phrase in [
            "у кого меньше площадь",
            "у кого площадь меньше",
            "у какой площадь меньше",
            "у какой из них площадь меньше",
            "какая площадь меньше",
            "какая квартира меньше",
            "какая из них меньше",
            "кто меньше по площади",
            "какая меньше"
        ]
    ):
        return "smallest_area"

    # Этаж — выше
    if any(
        phrase in text
        for phrase in [
            "какой этаж выше",
            "у кого этаж выше",
            "какая квартира выше",
            "какая из них выше",
            "кто выше"
        ]
    ):
        return "highest_floor"

    # Этаж — ниже
    if any(
        phrase in text
        for phrase in [
            "какой этаж ниже",
            "у кого этаж ниже",
            "какая квартира ниже",
            "кто ниже"
        ]
    ):
        return "lowest_floor"

    return None


def is_information_request(user_text):
    """Проверяет, спрашивает ли пользователь информацию о ЖК."""

    text = user_text.lower().strip()

    information_phrases = [
        "расскажи про",
        "расскажи о",
        "расскажи подробнее про",
        "расскажи подробнее о",
        "подробнее про",
        "подробнее о",
        "что можешь рассказать про",
        "что можешь рассказать о",
        "какая инфраструктура",
        "где инфраструктура лучше",
        "где лучше инфраструктура",
        "что есть рядом",
        "что есть в жк",
        "что находится рядом",
        "где есть подземная парковка",
        "в каком жк есть подземная парковка",
        "у какого жк есть подземная парковка",
        "какая парковка",
        "какая парковка в жк",
        "какой район",
        "какой класс",
        "какой жилой комплекс",
        "какой жк",
        "когда сдача",
        "когда сдается",
        "когда сдаётся",
        "когда будет сдан",
        "что за жк",
        "что это за жк",
        "расскажи подробнее"
    ]

    return any(
        phrase in text
        for phrase in information_phrases
    )


def is_filter_change_request(user_text):
    """
    Определяет тип запроса через GigaChat,
    если базовые правила не смогли его определить.
    """

    text = user_text.lower().strip()

    prompt = f"""
Определи тип запроса пользователя.

Сообщение:
"{text}"

Возможные типы:

filter
Пользователь задаёт или меняет параметры квартиры.

complex
Пользователь выбирает один или несколько ЖК.

comparison
Пользователь хочет сравнить выбранные ЖК.

information
Пользователь хочет получить информацию о ЖК:
описание, инфраструктура, район, класс,
парковка, срок сдачи и т.д.

other
Другой запрос.

Верни ТОЛЬКО одно слово:
filter
complex
comparison
information
other
"""

    answer = ask_gigachat(prompt)

    if not answer:
        return "other"

    answer = answer.lower().strip()

    for intent in [
        "comparison",
        "information",
        "complex",
        "filter",
        "other"
    ]:
        if intent in answer:
            return intent

    return "other"


def is_alternative_request(user_text):
    """Определяет запрос пользователя на другие/похожие варианты."""

    text = user_text.lower().strip()

    phrases = [
        "подбери другие варианты",
        "подбери другие",
        "покажи другие варианты",
        "покажи другие",
        "есть еще варианты",
        "есть ещё варианты",
        "что еще есть",
        "что ещё есть",
        "а что еще есть",
        "а что ещё есть",
        "покажи похожие",
        "покажи похожие варианты",
        "есть что-нибудь похожее",
        "есть что нибудь похожее",
        "предложи похожие варианты",
        "предложи другие варианты",
        "можешь предложить другие",
        "можешь предложить что-нибудь",
        "можешь подобрать другие",
        "а есть что-нибудь еще",
        "а есть что-нибудь ещё",
        "а есть что нибудь еще",
        "а есть что нибудь ещё"
    ]

    return any(
        phrase in text
        for phrase in phrases
    )


def is_apartment_selection_request(user_text):
    """Определяет выбор квартиры из последнего списка."""

    text = user_text.lower().strip()

    phrases = [
        "первый вариант",
        "второй вариант",
        "третий вариант",
        "четвертый вариант",
        "четвёртый вариант",
        "пятый вариант",
        "шестой вариант",
        "седьмой вариант",
        "восьмой вариант",
        "девятый вариант",
        "десятый вариант",

        "первая квартира",
        "вторая квартира",
        "третья квартира",
        "четвертая квартира",
        "четвёртая квартира",
        "пятая квартира",

        "первую квартиру",
        "вторую квартиру",
        "третью квартиру",
        "четвертую квартиру",
        "четвёртую квартиру",
        "пятую квартиру",

        "квартира id",
        "квартиру id",
        "квартира номер",
        "квартиру номер",

        "id ",
        "id:",
        "id#",
        "id №",

        "квартира №",
        "квартиру №",
        "квартира #",
        "квартиру #"
    ]

    return any(
        phrase in text
        for phrase in phrases
    )

def detect_basic_intent(user_text, complexes=None):
    """
    Быстро определяет тип запроса без обращения к GigaChat.
    """
    if is_apartment_selection_request(user_text):
        return "apartment"

    text = user_text.lower().strip()

    # Сравнение проверяем первым
    if is_comparison_request(text):
        return "comparison"

    # Запрос других / похожих вариантов
    if is_alternative_request(text):
        return "alternative"

    if is_apartment_selection_request(text):
        return "apartment"


    # Запрос списка жилых комплексов
    complex_list_phrases = [
        "покажи жк",
        "показать жк",
        "какие жк",
        "какие есть жк",
        "какие жилые комплексы",
        "покажи жилые комплексы",
        "показать жилые комплексы",
        "список жк",
        "список жилых комплексов"
    ]

    if any(phrase in text for phrase in complex_list_phrases):
        return "complex"
    

    # Явные фильтры и изменение уже заданных параметров
    filter_words = [
        "этаж",
        "площад",
        "млн",
        "миллион",
        "бюджет",
        "комнат",
        "однуш",
        "двуш",
        "треш",
        "трёш",
        "трехкомнат",
        "трёхкомнат",
        "четырехкомнат",
        "четырёхкомнат"
    ]

    if any(word in text for word in filter_words):
        return "filter"

    # Явное изменение или сброс уже заданного параметра
    filter_change_phrases = [
        "убери ограничение",
        "убрать ограничение",
        "сними ограничение",
        "снять ограничение",
        "без ограничения",
        "без ограничений",
        "ограничение не нужно",
        "ограничение больше не нужно",
        "не учитывай",
        "не учитывать",
        "цена не важна",
        "бюджет не важен",
        "площадь не важна",
        "этаж не важен"
    ]

    if any(phrase in text for phrase in filter_change_phrases):
        return "filter"

    # Выбор ЖК по номеру
    ordinal_words = [
        "первый",
        "первого",
        "первая",
        "второй",
        "второго",
        "вторая",
        "третий",
        "третьего",
        "третья",
        "четвертый",
        "четвертого",
        "четвёртый",
        "четвёртого",
        "пятый",
        "пятого",
        "шестой",
        "шестого",
        "седьмой",
        "седьмого"
    ]

    if any(word in text for word in ordinal_words):
        return "complex"

    # Выбор по названию ЖК
    if complexes:
        for complex_data in complexes:
            name = complex_data[1].lower()

            if name in text:
                return "complex"

    # Общие конструкции изменения фильтров
    filter_phrases = [
        "от ",
        "до ",
        "не выше",
        "не больше",
        "не меньше",
        "не дороже",
        "хочу",
        "нужна",
        "нужен",
        "ищу",
        "подбери"
    ]

    if any(phrase in text for phrase in filter_phrases):
        return "filter"

    return "unknown"


def detect_intent(user_text, complexes=None):
    """
    Основная функция определения намерения пользователя.

    Возможные значения:

    manager
    comparison
    information
    alternative
    complex
    filter
    other
    """

    if is_manager_request(user_text):
        return "manager"

    basic_intent = detect_basic_intent(
        user_text,
        complexes
    )

    if basic_intent != "unknown":
        return basic_intent

    return is_filter_change_request(user_text)


def is_manager_request(user_text):
    """Проверяет, хочет ли пользователь обратиться к менеджеру."""

    text = user_text.lower()

    manager_phrases = [
        "менеджер",
        "связаться с менеджером",
        "позови менеджера",
        "хочу менеджера",
        "нужен менеджер",
        "связаться с человеком",
        "связаться с сотрудником",
        "человек"
    ]

    return any(
        phrase in text
        for phrase in manager_phrases
    )


def find_information_target(user_text, complexes):
    """
    Определяет, про какой ЖК говорит пользователь.

    Возвращает ID ЖК или None.
    """

    if not complexes:
        return None

    text = user_text.lower()

    # Сначала ищем точное название
    for complex_data in complexes:
        complex_id = complex_data[0]
        name = complex_data[1]

        if name.lower() in text:
            return complex_id

    # Затем название без "ЖК"
    for complex_data in complexes:
        complex_id = complex_data[0]
        name = complex_data[1].lower()

        short_name = name.replace("жк ", "").strip()

        if short_name and short_name in text:
            return complex_id

    # Если пользователь написал "про него",
    # используем единственный выбранный ЖК
    if len(complexes) == 1:
        return complexes[0][0]

    return None


def detect_information_topic(user_text):
    """
    Определяет, какая именно информация интересует пользователя.

    Возвращает:

    description
    infrastructure
    parking
    district
    housing_class
    completion_year
    general
    """

    text = user_text.lower()

    if "инфраструктур" in text or "что есть рядом" in text:
        return "infrastructure"

    if "парковк" in text:
        return "parking"

    if "район" in text:
        return "district"

    if (
        "класс" in text
        or "комфорт+" in text
        or "бизнес" in text
    ):
        return "housing_class"

    if (
        "сдач" in text
        or "сдается" in text
        or "сдаётся" in text
        or "будет сдан" in text
    ):
        return "completion_year"

    if (
        "описани" in text
        or "расскажи про" in text
        or "расскажи о" in text
        or "подробнее" in text
        or "что за жк" in text
    ):
        return "description"

    return "general"



def detect_comparison_topic(user_text):
    """
    Определяет, по какому критерию пользователь хочет сравнить ЖК.

    Возвращает:
    - infrastructure
    - parking
    - completion_year
    - housing_class
    - district
    - None
    """

    text = user_text.lower().replace("ё", "е")

    # Инфраструктура
    infrastructure_phrases = [
        "инфраструктур",
        "где лучше инфраструктура",
        "у кого лучше инфраструктура",
        "где инфраструктура лучше",
        "какая инфраструктура лучше",
        "где больше инфраструктуры",
    ]

    if any(phrase in text for phrase in infrastructure_phrases):
        return "infrastructure"

    # Парковка
    parking_phrases = [
        "парковк",
        "подземн",
        "где есть подземная парковка",
        "у кого есть подземная парковка",
        "в каком жк есть подземная парковка",
        "где парковка лучше",
        "у кого парковка лучше",
        "какая парковка лучше",
        "где лучше по парковке",
        "у кого лучше по парковке",
        "а парковка",
    ]

    if any(phrase in text for phrase in parking_phrases):
        return "parking"

    # Срок сдачи
    completion_phrases = [
        "сдач",
        "сдается",
        "сдаётся",
        "раньше сда",
        "позже сда",
        "когда будет сдан",
        "когда сдадут",
        "сдастся раньше",
        "сдается раньше",
        "сдаётся раньше",
        "сдастся раньше",
        "сдается раньше",
        "сдаётся раньше",
    ]

    if any(phrase in text for phrase in completion_phrases):
        return "completion_year"

    # Класс жилья
    class_phrases = [
        "класс",
        "какой класс",
        "класс жилья",
        "класс жк",
    ]

    if any(phrase in text for phrase in class_phrases):
        return "housing_class"

    # Район
    district_phrases = [
        "район",
        "где находится",
        "где расположен",
        "расположение",
    ]

    if any(phrase in text for phrase in district_phrases):
        return "district"

    return None


def compare_complexes_by_criterion(user_text, complex_data):
    """
    Формирует сравнение нескольких ЖК по одному конкретному критерию.

    complex_data:
        список кортежей из get_complex_by_id():
        (id, name, district, housing_class, completion_year,
         description, infrastructure, parking)

    Возвращает готовый текст ответа.
    """

    topic = detect_comparison_topic(user_text)

    if not topic:
        return None

    if not complex_data:
        return "Не удалось найти ЖК для сравнения."

    # ---------------------------------------------------------
    # ИНФРАСТРУКТУРА
    # ---------------------------------------------------------

    if topic == "infrastructure":
        result = ["Сравнение по критерию «Инфраструктура»:\n"]

        infrastructure_counts = []

        for complex_item in complex_data:
            (
                complex_id,
                name,
                district,
                housing_class,
                completion_year,
                description,
                infrastructure,
                parking,
                *extra
            ) = complex_item

            items = [
                item.strip()
                for item in infrastructure.split(",")
                if item.strip()
            ]

            infrastructure_counts.append((name, len(items)))

            result.append(f"{name}:")
            result.append(f"• {infrastructure}")
            result.append("")

        max_count = max(
            count for name, count in infrastructure_counts
        )

        leaders = [
            name
            for name, count in infrastructure_counts
            if count == max_count
        ]

        result.append(
            "По количеству указанных в базе объектов инфраструктуры:"
        )

        for name, count in infrastructure_counts:
            result.append(f"• {name} — {count}")

        if len(leaders) == 1:
            result.append(
                f"\nУ {leaders[0]} указано больше всего объектов "
                f"инфраструктуры — {max_count}."
            )
        else:
            result.append(
                f"\nУ {', '.join(leaders)} указано больше всего "
                f"объектов инфраструктуры — по {max_count}."
            )

        result.append(
            "\nВажно: количество объектов само по себе не означает, "
            "что инфраструктура лучше — набор объектов у ЖК может отличаться."
        )

        return "\n".join(result)

    # ---------------------------------------------------------
    # ПАРКОВКА
    # ---------------------------------------------------------

    if topic == "parking":
        result = [
            "Сравнение по критерию «Парковка»:\n"
        ]

        underground = []

        for complex_item in complex_data:
            (
                complex_id,
                name,
                district,
                housing_class,
                completion_year,
                description,
                infrastructure,
                parking,
                *extra
            ) = complex_item

            result.append(
                f"{name} — {parking}"
            )

            if "подзем" in parking.lower():
                underground.append(name)

        if underground:
            result.append(
                f"\nПодземная парковка есть у: "
                f"{', '.join(underground)}."
            )
        else:
            result.append(
                "\nСреди выбранных ЖК подземная парковка "
                "в базе не указана."
            )

        return "\n".join(result)

    # ---------------------------------------------------------
    # СРОК СДАЧИ
    # ---------------------------------------------------------

    if topic == "completion_year":
        result = [
            "Сравнение по критерию «Срок сдачи»:\n"
        ]

        years = []

        for complex_item in complex_data:
            (
                complex_id,
                name,
                district,
                housing_class,
                completion_year,
                description,
                infrastructure,
                parking,
                *extra
            ) = complex_item

            result.append(
                f"{name} — {completion_year}"
            )

            years.append((name, completion_year))

        earliest_year = min(
            year for name, year in years
        )

        leaders = [
            name
            for name, year in years
            if year == earliest_year
        ]

        if len(leaders) == 1:
            result.append(
                f"\nРаньше всего планируется сдача "
                f"{leaders[0]} — в {earliest_year} году."
            )
        else:
            result.append(
                f"\nОба ЖК планируется сдать "
                f"в {earliest_year} году."
            )

        return "\n".join(result)


    # ---------------------------------------------------------
    # КЛАСС
    # ---------------------------------------------------------

    if topic == "housing_class":
        result = [
            "Сравнение по критерию «Класс жилья»:\n"
        ]

        class_order = {
            "эконом": 1,
            "комфорт": 2,
            "комфорт+": 3,
            "бизнес": 4,
            "премиум": 5
        }

        classes = []

        for complex_item in complex_data:
            (
                complex_id,
                name,
                district,
                housing_class,
                completion_year,
                description,
                infrastructure,
                parking,
                *extra
            ) = complex_item

            result.append(
                f"{name} — {housing_class}"
            )

            classes.append((name, housing_class))

        # Определяем уровень класса
        ranked_classes = []

        for name, housing_class in classes:
            normalized_class = housing_class.lower().strip()

            if normalized_class in class_order:
                ranked_classes.append(
                    (
                        name,
                        housing_class,
                        class_order[normalized_class]
                    )
                )

        if ranked_classes:
            max_level = max(
                level
                for name, housing_class, level in ranked_classes
            )

            leaders = [
                name
                for name, housing_class, level in ranked_classes
                if level == max_level
            ]

            if len(leaders) == len(ranked_classes):
                result.append(
                    f"\nВсе выбранные ЖК относятся к классу "
                    f"«{ranked_classes[0][1]}»."
                )
            elif len(leaders) == 1:
                winner_class = next(
                    housing_class
                    for name, housing_class, level in ranked_classes
                    if name == leaders[0]
                )

                result.append(
                    f"\nВыше классом — {leaders[0]} "
                    f"({winner_class})."
                )
            else:
                result.append(
                    f"\nСамый высокий класс среди выбранных ЖК: "
                    f"{', '.join(leaders)}."
                )

        return "\n".join(result)

    # ---------------------------------------------------------
    # РАЙОН
    # ---------------------------------------------------------

    if topic == "district":
        result = [
            "Сравнение по критерию «Район»:\n"
        ]

        for complex_item in complex_data:
            (
                complex_id,
                name,
                district,
                housing_class,
                completion_year,
                description,
                infrastructure,
                parking,
                *extra
            ) = complex_item

            result.append(
                f"{name} — {district}"
            )

        return "\n".join(result)

    return None



def generate_information_answer(user_text, complex_data):
    """
    Формирует ответ о ЖК через GigaChat,
    используя только данные из базы.

    complex_data:

    (
        id,
        name,
        district,
        housing_class,
        completion_year,
        description,
        infrastructure,
        parking
    )
    """

    if not complex_data:
        return "Не удалось найти информацию об этом жилом комплексе."

    (
        complex_id,
        name,
        district,
        housing_class,
        completion_year,
        description,
        infrastructure,
        parking,
        *extra
    ) = complex_data

    topic = detect_information_topic(user_text)

    # ==========================================================
    # Для конкретных вопросов отвечаем напрямую из БД.
    # GigaChat здесь вообще не нужен.
    # ==========================================================

    if topic == "infrastructure":
        return (
            f"У {name} в инфраструктуру входят: "
            f"{infrastructure}."
        )

    if topic == "parking":
        return (
            f"В {name} предусмотрена {parking.lower()} парковка."
        )

    if topic == "district":
        return (
            f"{name} находится в районе «{district}»."
        )

    if topic == "housing_class":
        return (
            f"{name} относится к классу «{housing_class}»."
        )

    if topic == "completion_year":
        return (
            f"Сдача {name} запланирована на {completion_year} год."
        )

    # ==========================================================
    # Данные из БД, которые разрешено использовать GigaChat
    # ==========================================================

    facts = f"""
Жилой комплекс: {name}
Район: {district}
Класс: {housing_class}
Сдача: {completion_year}
Описание: {description}
Инфраструктура: {infrastructure}
Парковка: {parking}
"""

    # ==========================================================
    # Промпт для GigaChat
    # ==========================================================

    prompt = f"""
Ты — консультант по жилым комплексам.

Пользователь спрашивает:
"{user_text}"

Вот единственные достоверные данные, которые тебе разрешено
использовать для ответа:

{facts}

Твоя задача — дать понятный краткий ответ на русском языке.

СТРОГИЕ ПРАВИЛА:

1. Используй ТОЛЬКО факты, которые буквально присутствуют
   в предоставленных данных.

2. НИЧЕГО НЕ ДОБАВЛЯЙ ОТ СЕБЯ.

3. Не делай предположений, выводов или оценок, которых нет
   в данных.

4. Не превращай один факт в другой.
   Например:
   - "магазины" нельзя заменять на "продуктовые магазины";
   - "школа" нельзя заменять на "школа рядом с домом";
   - "подземная парковка" нельзя дополнять словами
     о безопасности, защите от погоды или удобстве;
   - "тихий жилой комплекс" нельзя превращать в утверждение
     о "тихой атмосфере района".

5. Не добавляй информацию о:
   - метро;
   - транспорте;
   - расстояниях;
   - ценах;
   - площади квартир;
   - количестве квартир;
   - магазинах, если их нет в данных;
   - больницах;
   - детских учреждениях, если их нет в данных;
   - преимуществах ЖК;
   - недостатках ЖК;
   - безопасности;
   - экологии;
   - инвестиционной привлекательности;
   - комфорте проживания;
   - будущей инфраструктуре;
   - любых других характеристиках, которых нет в данных.

6. Если в вопросе пользователя запрашивается информация,
   которой нет в предоставленных данных, прямо скажи,
   что таких данных нет.

7. Можно переформулировать предложения, чтобы ответ звучал
   естественно, но смысл фактов менять нельзя.

8. Не используй слова "согласно базе данных" или
   "в базе данных указано", если это не требуется.

9. Не используй JSON.

10. Не выдумывай рекомендации вроде "подойдёт тем, кто..."
    или "это отличный вариант", если такие выводы
    непосредственно не следуют из предоставленных данных.

11. Если пользователь просит рассказать подробнее,
    используй несколько коротких абзацев или маркированный список.

12. Отвечай только на вопрос пользователя и не добавляй
    лишние сведения без необходимости.
"""

    answer = ask_gigachat(prompt)

    if answer:
        return answer.strip()

    # ==========================================================
    # Безопасный fallback, если GigaChat недоступен
    # ==========================================================

    return (
        f"{name} — жилой комплекс в районе {district}, "
        f"класса {housing_class}. "
        f"Сдача запланирована на {completion_year} год.\n\n"
        f"{description}\n\n"
        f"Инфраструктура: {infrastructure}.\n"
        f"Парковка: {parking}."
    )


def is_context_reference_request(user_text):
    """Определяет запрос со ссылкой на уже показанный объект."""

    text = user_text.lower().strip()

    phrases = [
        "первый",
        "первая",
        "первую",
        "второй",
        "вторая",
        "вторую",
        "третий",
        "третья",
        "третью",
        "четвертый",
        "четвёртый",
        "четвертая",
        "четвёртая",
        "четвертую",
        "четвёртую",
        "пятый",
        "пятая",
        "пятую",
        "шестой",
        "шестая",
        "шестую",
        "седьмой",
        "седьмая",
        "седьмую",
        "восьмой",
        "восьмая",
        "восьмую",
        "девятый",
        "девятая",
        "девятую",
        "десятый",
        "десятая",
        "десятую",
        "этот",
        "эта",
        "это",
        "эту",
        "данный",
        "данная",
        "данное",
        "данную",
        "из них",
        "из этих",
        "из выбранных"
    ]

    return any(
        re.search(
            rf"\b{re.escape(phrase)}\b",
            text
        )
        for phrase in phrases
    )


def parse_context_selection(user_text, items):
    """Выбирает элементы из последнего списка по порядковому номеру."""

    if not items:
        return []

    text = user_text.lower().strip()

    ordinal_words = {
        "первый": 1,
        "первая": 1,
        "первую": 1,

        "второй": 2,
        "вторая": 2,
        "вторую": 2,

        "третий": 3,
        "третья": 3,
        "третью": 3,

        "четвертый": 4,
        "четвёртый": 4,
        "четвертая": 4,
        "четвёртая": 4,
        "четвертую": 4,
        "четвёртую": 4,

        "пятый": 5,
        "пятая": 5,
        "пятую": 5,

        "шестой": 6,
        "шестая": 6,
        "шестую": 6,

        "седьмой": 7,
        "седьмая": 7,
        "седьмую": 7,

        "восьмой": 8,
        "восьмая": 8,
        "восьмую": 8,

        "девятый": 9,
        "девятая": 9,
        "девятую": 9,

        "десятый": 10,
        "десятая": 10,
        "десятую": 10
    }

    selected = []

    for word, number in ordinal_words.items():

        if word in text:

            index = number - 1

            if 0 <= index < len(items):

                item = items[index]

                if item not in selected:
                    selected.append(item)

    return selected


def is_complex_reference_request(user_text):
    text = user_text.lower().strip()

    # Выбор ЖК по номеру:
    # "ЖК 1", "ЖК №1", "жк 1 и жк 5"
    if re.search(r"\bжк\s*№?\s*\d+\b", text):
        return True

    phrases = [
        "первый жк", "второй жк", "третий жк", "четвертый жк", "четвёртый жк",
        "пятый жк", "шестой жк", "седьмой жк", "восьмой жк", "девятый жк", "десятый жк",

        "первый жилой комплекс", "второй жилой комплекс",
        "третий жилой комплекс", "четвертый жилой комплекс",
        "четвёртый жилой комплекс", "пятый жилой комплекс",
        "шестой жилой комплекс", "седьмой жилой комплекс",
        "восьмой жилой комплекс", "девятый жилой комплекс",
        "десятый жилой комплекс"
    ]

    if any(phrase in text for phrase in phrases):
        return True

    # Обращение к ЖК по его названию.
    # Например: "ЖК Лесной", "посмотрим ЖК Солнечный"
    if re.search(r"\bжк\s+[а-яёa-z0-9][а-яёa-z0-9\s-]*", text):
        return True

    return False


def is_last_object_reference(user_text):
    """Определяет ссылку на последний выбранный объект."""

    text = user_text.lower().strip()

    phrases = [
        "этот вариант",
        "эта квартира",
        "эту квартиру",
        "этот объект",
        "данный вариант",
        "данная квартира",
        "данный объект",
        "этот",
        "эта",
        "эту",
        "данный",
        "данная",
        "данную"
    ]

    return any(
        re.search(
            rf"\b{re.escape(phrase)}\b",
            text
        )
        for phrase in phrases
    )