import sqlite3


DB_NAME = "apartments.db"

FREE_BOOKING_HOURS = 3
PAID_BOOKING_MONTHS = 1
PAID_BOOKING_PRICE = 20_000

def get_connection():
    """Создаёт подключение к базе данных."""
    connection = sqlite3.connect(DB_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def create_database():
    """Создаёт таблицы базы данных."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS residential_complexes (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            district TEXT,
            housing_class TEXT,
            completion_year INTEGER,
            description TEXT,
            infrastructure TEXT,
            parking TEXT,
            image TEXT
        )
    """)

    # Если таблица уже существовала без image, добавляем колонку безопасно
    cursor.execute("PRAGMA table_info(residential_complexes)")
    columns = [row[1] for row in cursor.fetchall()]

    if "image" not in columns:
        cursor.execute("""
            ALTER TABLE residential_complexes
            ADD COLUMN image TEXT
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apartments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complex_id INTEGER NOT NULL,
            rooms INTEGER NOT NULL,
            area REAL NOT NULL,
            price INTEGER NOT NULL,
            floor INTEGER NOT NULL,
            finishing TEXT,
            balcony TEXT,
            image TEXT,
            booking_status TEXT NOT NULL DEFAULT 'available',
            booking_type TEXT,
            booking_until TEXT,
            FOREIGN KEY (complex_id) REFERENCES residential_complexes(id)
        )
    """)

    connection.commit()
    connection.close()

    update_complex_images()


def update_complex_images():
    connection = get_connection()
    cursor = connection.cursor()

    complex_images = {
        1: "images/complexes/complex_1_ЖК_Солнечный.jpg",
        2: "images/complexes/complex_2_ЖК_Речной.jpg",
        3: "images/complexes/complex_3_ЖК_Северный.jpg",
        4: "images/complexes/complex_4_ЖК_Центральный.jpg",
        5: "images/complexes/complex_5_ЖК_Парковый.jpg",
        6: "images/complexes/complex_7_ЖК_Новый_город.jpg",
        7: "images/complexes/complex_6_ЖК_Лесной.jpg"
    }
    for complex_id, image_path in complex_images.items():
        cursor.execute("""
            UPDATE residential_complexes
            SET image = ?
            WHERE id = ?
        """, (image_path, complex_id))

    connection.commit()
    connection.close()


def add_test_apartments():
    """
    Заполняет базу тестовыми данными только в том случае,
    если база ещё пустая.

    Если данные уже были загружены из Excel,
    существующая база не изменяется.
    """

    connection = get_connection()
    cursor = connection.cursor()

    # Проверяем, есть ли уже данные в базе
    cursor.execute("""
        SELECT COUNT(*)
        FROM residential_complexes
    """)

    complexes_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM apartments
    """)

    apartments_count = cursor.fetchone()[0]

    # Если база уже заполнена, ничего не перезаписываем
    if complexes_count > 0 or apartments_count > 0:
        connection.close()
        return

    complexes = [
        (
            1,
            "ЖК Солнечный",
            "Северный",
            "Комфорт",
            2027,
            "Современный жилой комплекс рядом с большим парком.",
            "Парк, школа, детский сад, детские площадки",
            "Наземная"
        ),
        (
            2,
            "ЖК Речной",
            "Набережный",
            "Комфорт+",
            2026,
            "Жилой комплекс рядом с набережной и прогулочной зоной.",
            "Набережная, магазины, кафе, спортивная площадка",
            "Подземная"
        ),
        (
            3,
            "ЖК Северный",
            "Северный",
            "Комфорт",
            2028,
            "Новый жилой комплекс с развитой инфраструктурой.",
            "Школа, детский сад, супермаркеты, спортивная площадка",
            "Наземная"
        ),
        (
            4,
            "ЖК Центральный",
            "Центральный",
            "Бизнес",
            2027,
            "Жилой комплекс в центральной части города.",
            "Кафе, рестораны, магазины, фитнес-центр",
            "Подземная"
        ),
        (
            5,
            "ЖК Парковый",
            "Западный",
            "Комфорт+",
            2026,
            "Тихий жилой комплекс рядом с зелёной зоной.",
            "Парк, школа, детский сад, магазины",
            "Подземная"
        ),
        (
            6,
            "ЖК Новый город",
            "Восточный",
            "Комфорт",
            2028,
            "Большой семейный жилой комплекс.",
            "Школа, детский сад, магазины, детские площадки",
            "Наземная"
        ),
        (
            7,
            "ЖК Лесной",
            "Пригород",
            "Комфорт+",
            2027,
            "Тихий жилой комплекс рядом с лесопарковой зоной.",
            "Лесопарк, прогулочные зоны, детская площадка",
            "Наземная"
        )
    ]

    cursor.executemany("""
        INSERT INTO residential_complexes
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, complexes)

    apartments = [
        # ЖК Солнечный
        (1, 1, 38.5, 7_000_000, 4, "Предчистовая"),
        (1, 1, 42.0, 8_500_000, 7, "Чистовая"),
        (1, 2, 55.0, 11_000_000, 3, "Чистовая"),
        (1, 2, 68.0, 13_500_000, 8, "Предчистовая"),
        (1, 3, 85.0, 19_000_000, 10, "Чистовая"),

        # ЖК Речной
        (2, 1, 40.0, 9_000_000, 5, "Чистовая"),
        (2, 2, 58.5, 12_000_000, 7, "Чистовая"),
        (2, 2, 72.0, 14_500_000, 12, "Предчистовая"),
        (2, 3, 95.5, 23_000_000, 8, "Чистовая"),
        (2, 4, 120.0, 30_000_000, 15, "Чистовая"),

        # ЖК Северный
        (3, 1, 37.0, 6_800_000, 2, "Предчистовая"),
        (3, 1, 45.0, 8_800_000, 9, "Чистовая"),
        (3, 2, 54.0, 10_000_000, 2, "Чистовая"),
        (3, 2, 62.0, 12_500_000, 6, "Предчистовая"),
        (3, 3, 88.0, 18_500_000, 11, "Чистовая"),

        # ЖК Центральный
        (4, 1, 43.0, 12_500_000, 6, "Чистовая"),
        (4, 2, 60.0, 18_000_000, 5, "Чистовая"),
        (4, 2, 74.0, 22_000_000, 10, "Чистовая"),
        (4, 3, 92.0, 28_000_000, 12, "Чистовая"),
        (4, 4, 125.0, 38_000_000, 14, "Чистовая"),

        # ЖК Парковый
        (5, 1, 39.0, 7_800_000, 3, "Предчистовая"),
        (5, 1, 46.0, 9_200_000, 7, "Чистовая"),
        (5, 2, 56.0, 11_500_000, 4, "Чистовая"),
        (5, 2, 69.0, 14_000_000, 9, "Чистовая"),
        (5, 3, 86.0, 19_500_000, 10, "Предчистовая"),

        # ЖК Новый город
        (6, 1, 38.0, 7_200_000, 4, "Чистовая"),
        (6, 2, 55.0, 10_500_000, 5, "Предчистовая"),
        (6, 2, 65.0, 12_500_000, 8, "Чистовая"),
        (6, 3, 82.0, 17_500_000, 12, "Чистовая"),
        (6, 3, 96.0, 21_000_000, 15, "Предчистовая"),

        # ЖК Лесной
        (7, 1, 41.0, 8_000_000, 2, "Предчистовая"),
        (7, 2, 57.0, 11_000_000, 3, "Чистовая"),
        (7, 2, 70.0, 13_500_000, 6, "Чистовая"),
        (7, 3, 90.0, 18_500_000, 8, "Чистовая"),
        (7, 4, 118.0, 29_000_000, 10, "Предчистовая")
    ]

    apartment_rows = []

    balcony_options = [
        "Балкон",
        "Лоджия",
        "Балкон + лоджия",
        "Нет",
        "Балкон"
    ]

    apartment_id = 1

    for complex_id, rooms, area, price, floor, finishing in apartments:

        balcony = balcony_options[
            (apartment_id - 1) % len(balcony_options)
        ]

        image = f"images/apartment_{apartment_id}.jpg"

        apartment_rows.append(
            (
                apartment_id,
                complex_id,
                rooms,
                area,
                price,
                floor,
                finishing,
                balcony,
                image
            )
        )

        apartment_id += 1

    cursor.executemany("""
        INSERT INTO apartments
        (
            id,
            complex_id,
            rooms,
            area,
            price,
            floor,
            finishing,
            balcony,
            image
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, apartment_rows)

    connection.commit()
    connection.close()


def release_expired_bookings():
    """
    Освобождает квартиры, у которых закончился срок бронирования.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE apartments
        SET
            booking_status = 'available',
            booking_type = NULL,
            booking_until = NULL
        WHERE
            booking_status = 'booked'
            AND booking_until IS NOT NULL
            AND datetime(booking_until) <= datetime('now')
    """)

    released_count = cursor.rowcount

    connection.commit()
    connection.close()

    return released_count


def get_apartment_by_id(apartment_id):
    """Возвращает квартиру по ID."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
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
        FROM apartments
        WHERE id = ?
    """, (apartment_id,))

    apartment = cursor.fetchone()

    connection.close()

    if apartment is None:
        return None

    return tuple(apartment)


def get_all_apartments():
    """Возвращает все доступные квартиры."""

    release_expired_bookings()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
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
        FROM apartments
        WHERE booking_status = 'available'
        ORDER BY price ASC
    """)

    apartments = cursor.fetchall()

    connection.close()

    return [tuple(row) for row in apartments]


def search_apartments(filters):
    """
    Ищет квартиры по заданным фильтрам.

    Поддерживаемые фильтры:
    rooms
    min_area
    max_area
    max_price
    max_floor
    """

    release_expired_bookings()

    query = """
        SELECT
            id,
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
        FROM apartments
        WHERE booking_status = 'available'
    """

    parameters = []

    rooms = filters.get("rooms")
    min_area = filters.get("min_area")
    max_area = filters.get("max_area")
    max_price = filters.get("max_price")
    max_floor = filters.get("max_floor")

    if rooms is not None:
        query += " AND rooms = ?"
        parameters.append(rooms)

    if min_area is not None:
        query += " AND area >= ?"
        parameters.append(min_area)

    if max_area is not None:
        query += " AND area <= ?"
        parameters.append(max_area)

    if max_price is not None:
        query += " AND price <= ?"
        parameters.append(max_price)

    if max_floor is not None:
        query += " AND floor <= ?"
        parameters.append(max_floor)

    query += " ORDER BY price ASC"

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(query, parameters)

    apartments = cursor.fetchall()

    connection.close()

    return [tuple(row) for row in apartments]


def search_nearest_apartments(
    filters,
    limit=5,
    exclude_ids=None
):
    """Ищет ближайшие варианты с возможностью исключить уже показанные квартиры."""

    if exclude_ids is None:
        exclude_ids = []

    apartments = get_all_apartments()

    scored_apartments = []

    for apartment in apartments:

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

        # Не показываем уже показанные квартиры
        if apartment_id in exclude_ids:
            continue

        score = 0

        # Комнаты
        if filters.get("rooms") is not None:
            score += abs(
                rooms - filters["rooms"]
            ) * 10000

        # Площадь
        if filters.get("min_area") is not None:
            if area < filters["min_area"]:
                score += (
                    filters["min_area"] - area
                ) * 100

        if filters.get("max_area") is not None:
            if area > filters["max_area"]:
                score += (
                    area - filters["max_area"]
                ) * 100

        # Цена
        if filters.get("max_price") is not None:
            if price > filters["max_price"]:
                score += (
                    price - filters["max_price"]
                ) / 1000

        # Этаж
        if filters.get("max_floor") is not None:
            if floor > filters["max_floor"]:
                score += (
                    floor - filters["max_floor"]
                ) * 500

        scored_apartments.append(
            (
                score,
                apartment
            )
        )

    scored_apartments.sort(
        key=lambda item: item[0]
    )

    return [
        apartment
        for score, apartment
        in scored_apartments[:limit]
    ]


def get_complex_names_by_apartments(apartments):
    """Возвращает словарь complex_id -> название ЖК."""

    complex_ids = list(set(apartment[1] for apartment in apartments))

    if not complex_ids:
        return {}

    placeholders = ",".join("?" for _ in complex_ids)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        f"""
        SELECT id, name
        FROM residential_complexes
        WHERE id IN ({placeholders})
        """,
        complex_ids
    )

    rows = cursor.fetchall()

    connection.close()

    return {
        row["id"]: row["name"]
        for row in rows
    }


def get_complexes_for_filters(filters):
    """
    Возвращает ЖК, в которых есть квартиры,
    соответствующие фильтрам.
    """

    release_expired_bookings()

    query = """
        SELECT
            rc.id,
            rc.name,
            rc.district,
            rc.housing_class,
            rc.completion_year,
            rc.description,
            rc.infrastructure,
            rc.parking,
            rc.image,
            COUNT(a.id) AS apartment_count
        FROM residential_complexes rc
        JOIN apartments a
            ON a.complex_id = rc.id
        WHERE a.booking_status = 'available'
    """

    parameters = []

    rooms = filters.get("rooms")
    min_area = filters.get("min_area")
    max_area = filters.get("max_area")
    max_price = filters.get("max_price")
    max_floor = filters.get("max_floor")

    if rooms is not None:
        query += " AND a.rooms = ?"
        parameters.append(rooms)

    if min_area is not None:
        query += " AND a.area >= ?"
        parameters.append(min_area)

    if max_area is not None:
        query += " AND a.area <= ?"
        parameters.append(max_area)

    if max_price is not None:
        query += " AND a.price <= ?"
        parameters.append(max_price)

    if max_floor is not None:
        query += " AND a.floor <= ?"
        parameters.append(max_floor)

    query += """
        GROUP BY
            rc.id,
            rc.name,
            rc.district,
            rc.housing_class,
            rc.completion_year,
            rc.description,
            rc.infrastructure,
            rc.parking,
            rc.image
        ORDER BY rc.id
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(query, parameters)

    complexes = cursor.fetchall()

    connection.close()

    return [tuple(row) for row in complexes]


def get_complexes_by_ids(complex_ids):
    """Возвращает информацию о конкретных ЖК."""

    if not complex_ids:
        return []

    placeholders = ",".join("?" for _ in complex_ids)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        f"""
        SELECT
            id,
            name,
            district,
            housing_class,
            completion_year,
            description,
            infrastructure,
            parking,
            image
        FROM residential_complexes
        WHERE id IN ({placeholders})
        ORDER BY id
        """,
        complex_ids
    )

    complexes = cursor.fetchall()

    connection.close()

    return [tuple(row) for row in complexes]


def get_complex_by_name(name):
    """
    Ищет ЖК по названию.

    Поддерживает частичное совпадение.
    Например:
    "Парковый" -> ЖК Парковый
    "ЖК Парковый" -> ЖК Парковый
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            district,
            housing_class,
            completion_year,
            description,
            infrastructure,
            parking,
            image
        FROM residential_complexes
        WHERE LOWER(name) = LOWER(?)
           OR LOWER(name) LIKE LOWER(?)
        LIMIT 1
    """, (name, f"%{name}%"))

    row = cursor.fetchone()

    connection.close()

    if row is None:
        return None

    return tuple(row)


def get_complex_by_id(complex_id):
    """Возвращает один ЖК по ID."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            district,
            housing_class,
            completion_year,
            description,
            infrastructure,
            parking,
            image
        FROM residential_complexes
        WHERE id = ?
    """, (complex_id,))

    row = cursor.fetchone()

    connection.close()

    if row is None:
        return None

    return tuple(row)


def get_all_complexes():
    """Возвращает все ЖК."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            district,
            housing_class,
            completion_year,
            description,
            infrastructure,
            parking,
            image
        FROM residential_complexes
        ORDER BY id
    """)

    complexes = cursor.fetchall()

    connection.close()

    return [tuple(row) for row in complexes]


def book_apartment(apartment_id, booking_type):
    """
    Бронирует квартиру, если она свободна.

    free — бесплатная бронь на 3 часа.
    paid — платная бронь на 1 месяц.
    """

    if booking_type not in ("free", "paid"):
        return {
            "success": False,
            "message": "Неизвестный тип бронирования."
        }

    connection = get_connection()
    cursor = connection.cursor()

    # Сначала освобождаем квартиры,
    # у которых закончился срок бронирования.
    cursor.execute("""
        UPDATE apartments
        SET
            booking_status = 'available',
            booking_type = NULL,
            booking_until = NULL
        WHERE
            booking_status = 'booked'
            AND booking_until IS NOT NULL
            AND datetime(booking_until) <= datetime('now')
    """)

    # Проверяем квартиру
    cursor.execute("""
        SELECT
            id,
            booking_status
        FROM apartments
        WHERE id = ?
    """, (apartment_id,))

    apartment = cursor.fetchone()

    if apartment is None:
        connection.close()

        return {
            "success": False,
            "message": "Квартира не найдена."
        }

    if apartment["booking_status"] != "available":
        connection.close()

        return {
            "success": False,
            "message": "Эта квартира уже забронирована."
        }

    # Выбираем срок бронирования
    if booking_type == "free":
        booking_until_sql = "datetime('now', '+3 hours')"
    else:
        booking_until_sql = "datetime('now', '+1 month')"

    cursor.execute(f"""
        UPDATE apartments
        SET
            booking_status = 'booked',
            booking_type = ?,
            booking_until = {booking_until_sql}
        WHERE id = ?
    """, (booking_type, apartment_id))

    connection.commit()

    # Получаем установленный срок бронирования
    cursor.execute("""
        SELECT
            booking_status,
            booking_type,
            booking_until
        FROM apartments
        WHERE id = ?
    """, (apartment_id,))

    booking = cursor.fetchone()

    connection.close()

    return {
        "success": True,
        "apartment_id": apartment_id,
        "booking_type": booking["booking_type"],
        "booking_until": booking["booking_until"],
        "price": (
            0
            if booking_type == "free"
            else PAID_BOOKING_PRICE
        ),
        "message": (
            "Квартира забронирована бесплатно на 3 часа."
            if booking_type == "free"
            else "Квартира забронирована на 1 месяц."
        )
    }


if __name__ == "__main__":
    create_database()
    add_test_apartments()
    update_complex_images()
    print("База данных успешно создана и заполнена.")