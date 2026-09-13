import sqlite3
from openpyxl import load_workbook


EXCEL_FILE = "apartments.xlsx"
DATABASE_FILE = "apartments.db"


def import_excel_to_database():
    """Импортирует данные из Excel в SQLite."""

    print()
    print("Начинаю импорт данных из Excel...")
    print()

    # Загружаем Excel
    workbook = load_workbook(
        EXCEL_FILE,
        data_only=True
    )

    sheet_complexes = workbook["ЖК"]
    sheet_apartments = workbook["Квартиры"]

    # Подключаемся к SQLite
    connection = sqlite3.connect(
        DATABASE_FILE
    )

    cursor = connection.cursor()

    # -------------------------------------------------
    # Создание таблиц
    # -------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS residential_complexes (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            district TEXT,
            housing_class TEXT,
            completion_year INTEGER,
            description TEXT,
            infrastructure TEXT,
            parking TEXT
        )
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
            FOREIGN KEY (complex_id)
                REFERENCES residential_complexes(id)
        )
    """)

    # -------------------------------------------------
    # Очищаем старые данные
    # -------------------------------------------------

    cursor.execute(
        "DELETE FROM apartments"
    )

    cursor.execute(
        "DELETE FROM residential_complexes"
    )

    # -------------------------------------------------
    # Импорт ЖК
    # -------------------------------------------------

    complex_count = 0

    for row in sheet_complexes.iter_rows(
        min_row=2,
        values_only=True
    ):

        if not row[0]:
            continue

        (
            complex_id,
            name,
            district,
            housing_class,
            completion_year,
            description,
            infrastructure,
            parking
        ) = row

        cursor.execute("""
            INSERT INTO residential_complexes (
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
        """, (
            complex_id,
            name,
            district,
            housing_class,
            completion_year,
            description,
            infrastructure,
            parking
        ))

        complex_count += 1

    # -------------------------------------------------
    # Импорт квартир
    # -------------------------------------------------

    apartment_count = 0

    for row in sheet_apartments.iter_rows(
        min_row=2,
        values_only=True
    ):

        if not row[0]:
            continue

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
        ) = row

        cursor.execute("""
            INSERT INTO apartments (
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
        """, (
            apartment_id,
            complex_id,
            rooms,
            area,
            price,
            floor,
            finishing,
            balcony,
            image
        ))

        apartment_count += 1

    # Сохраняем изменения
    connection.commit()

    # Закрываем соединение
    connection.close()

    print(
        f"Импортировано ЖК: {complex_count}"
    )

    print(
        f"Импортировано квартир: {apartment_count}"
    )

    print()
    print(
        "Импорт Excel → SQLite завершён успешно."
    )
    print()


if __name__ == "__main__":
    import_excel_to_database()