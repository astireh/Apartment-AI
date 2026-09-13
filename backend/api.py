from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import ApartmentAgent
from database import create_database
from import_excel import import_excel_to_database


app = FastAPI(
    title="AI-агент по подбору квартир",
    description="API для поиска и сравнения квартир",
    version="1.0.0"
)


# Разрешаем frontend обращаться к backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Делаем изображения доступными для frontend.
app.mount(
    "/images",
    StaticFiles(directory="images"),
    name="images"
)


# Создаём базу данных и загружаем актуальные данные из Excel.
create_database()
import_excel_to_database()


# Отдельный агент для каждой пользовательской сессии.
agents = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str


def get_agent(session_id: str) -> ApartmentAgent:
    """Возвращает агента для текущей сессии."""

    if session_id not in agents:
        agents[session_id] = ApartmentAgent()

    return agents[session_id]


@app.get("/health")
def health_check():
    """Проверка работоспособности API."""

    return {
        "status": "ok"
    }


@app.post("/chat")
def chat(request: ChatRequest):
    """Обрабатывает сообщение пользователя."""

    agent = get_agent(request.session_id)

    result = agent.process_message(
        request.message
    )

    return result