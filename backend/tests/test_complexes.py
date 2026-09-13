from database import (
    create_database,
    add_test_apartments,
    get_complexes_for_filters
)


create_database()
add_test_apartments()


filters = {
    "rooms": 2,
    "max_price": 15000000,
    "min_area": 55,
    "max_area": None,
    "max_floor": None
}


complexes = get_complexes_for_filters(filters)


print("Подходящие ЖК:\n")


for complex_item in complexes:
    (
        complex_id,
        name,
        district,
        housing_class,
        completion_year,
        description,
        infrastructure,
        parking,
        apartment_count
    ) = complex_item

    print(
        f"ID: {complex_id} | "
        f"{name} | "
        f"{district} | "
        f"{housing_class} | "
        f"подходящих квартир: {apartment_count}"
    )