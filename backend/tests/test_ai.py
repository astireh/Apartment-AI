import os
import json

from dotenv import load_dotenv
from gigachat import GigaChat

load_dotenv()

credentials = os.getenv("GIGACHAT_CREDENTIALS")

user_text = input("Что вы ищете? ")

with GigaChat(
    credentials=credentials,
    model="GigaChat-2",
    ca_bundle_file="russian_trusted_root_ca_pem.crt"
) as client:

    response = client.chat.create(
        f"""
        Ты помогаешь подбирать квартиры.

        Пользователь написал:
        {user_text}

        Извлеки из этого запроса параметры квартиры.

        Ответь только JSON-объектом.
        Не добавляй пояснений до или после JSON.

        Числа в JSON записывай без разделителей тысяч.
        Например: 15000000, а не 15_000_000.

        Правила для площади:

        - "от X м²" означает min_area = X, max_area = null
        - "не меньше X м²" означает min_area = X, max_area = null
        - "до X м²" означает min_area = null, max_area = X
        - "не больше X м²" означает min_area = null, max_area = X
        - "от X до Y м²" означает min_area = X, max_area = Y
        - "X–Y м²" означает min_area = X, max_area = Y
        - "ровно X м²" означает min_area = X, max_area = X

        Если пользователь не указал ограничение, используй null.

        Используй следующие поля:
        rooms
        min_area
        max_area
        max_price
        max_floor
        """
    )

    answer = response.messages[0].content[0].text

    print("Ответ GigaChat:")
    print(answer)

    json_text = answer.replace("```json", "").replace("```", "").strip()

    print("Чистый JSON:")
    print(json_text)

    data = json.loads(json_text)

    print("Данные Python:")
    print(data)

    print("Тип данных:")
    print(type(data))

    print("Количество комнат:", data["rooms"])
    print("Минимальная площадь:", data["min_area"])
    print("Максимальная площадь:", data["max_area"])
    print("Максимальная цена:", data["max_price"])
    print("Максимальный этаж:", data["max_floor"])