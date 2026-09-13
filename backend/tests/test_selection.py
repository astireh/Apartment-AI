from ai_parser import parse_complex_selection
from database import (
    create_database,
    add_test_apartments,
    get_complexes_for_filters
)


create_database()
add_test_apartments()


filters = {
    "rooms": 1,
    "max_price": None,
    "min_area": None,
    "max_area": None,
    "max_floor": None
}


complexes = get_complexes_for_filters(filters)


print("Список ЖК:\n")

for index, complex_item in enumerate(complexes, start=1):
    print(
        f"{index}. {complex_item[1]}"
    )


user_text = input(
    "\nКакие ЖК выбираете?\nВы: "
)


selection = parse_complex_selection(
    user_text,
    complexes
)


print("\nРезультат:")
print(selection)