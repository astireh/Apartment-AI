import os

from database import (
    create_database,
    add_test_apartments,
    update_complex_images,
    get_all_complexes
)


create_database()
add_test_apartments()
update_complex_images()

complexes = get_all_complexes()

print("Проверка фотографий ЖК:")
print()

for complex_data in complexes:
    name = complex_data[1]
    image = complex_data[8]

    print(f"ЖК: {name}")
    print(f"Фото: {image}")
    print(f"Файл существует: {os.path.exists(image)}")
    print()