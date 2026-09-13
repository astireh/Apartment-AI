from agent import ApartmentAgent


agent = ApartmentAgent()


print()
print("AI-агент по подбору квартир")
print("Введите запрос или напишите «выход» для завершения.")
print()


while True:

    user_text = input("Вы: ").strip()

    if not user_text:
        continue

    if user_text.lower() in [
        "выход",
        "exit",
        "quit"
    ]:
        print()
        print("Агент: До свидания!")
        break

    result = agent.process_message(
        user_text
    )

    print()
    print("Ответ агента:")
    print(result)
    print()