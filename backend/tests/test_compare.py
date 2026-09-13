from database import (
    create_database,
    add_test_apartments,
    get_complexes_by_ids
)


create_database()
add_test_apartments()


selected_ids = [1, 5, 7]


complexes = get_complexes_by_ids(selected_ids)


print("Выбранные ЖК:\n")


for complex_item in complexes:

    (
        complex_id,
        name,
        district,
        housing_class,
        completion_year,
        description,
        infrastructure,
        parking
    ) = complex_item

    print(f"ЖК: {name}")
    print(f"Район: {district}")
    print(f"Класс: {housing_class}")
    print(f"Сдача: {completion_year}")
    print(f"Описание: {description}")
    print(f"Инфраструктура: {infrastructure}")
    print(f"Парковка: {parking}")
    print()