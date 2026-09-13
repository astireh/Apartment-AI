from database import (
    create_database,
    add_test_apartments,
    get_complexes_by_ids
)


create_database()
add_test_apartments()


selected_ids = [1, 5, 7]

complexes = get_complexes_by_ids(selected_ids)


print("\nСравнение жилых комплексов:\n")


# Заголовок таблицы

print(
    f"{'Характеристика':<20} | "
    f"{complexes[0][1]:<20} | "
    f"{complexes[1][1]:<20} | "
    f"{complexes[2][1]:<20}"
)

print("-" * 90)


# Район

print(
    f"{'Район':<20} | "
    f"{complexes[0][2]:<20} | "
    f"{complexes[1][2]:<20} | "
    f"{complexes[2][2]:<20}"
)


# Класс

print(
    f"{'Класс':<20} | "
    f"{complexes[0][3]:<20} | "
    f"{complexes[1][3]:<20} | "
    f"{complexes[2][3]:<20}"
)


# Срок сдачи

print(
    f"{'Сдача':<20} | "
    f"{complexes[0][4]:<20} | "
    f"{complexes[1][4]:<20} | "
    f"{complexes[2][4]:<20}"
)


# Инфраструктура

print(
    f"{'Инфраструктура':<20} | "
    f"{complexes[0][6]:<20} | "
    f"{complexes[1][6]:<20} | "
    f"{complexes[2][6]:<20}"
)


# Парковка

print(
    f"{'Парковка':<20} | "
    f"{complexes[0][7]:<20} | "
    f"{complexes[1][7]:<20} | "
    f"{complexes[2][7]:<20}"
)


print()