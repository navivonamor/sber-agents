import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from openai import OpenAI

# Загрузка переменных окружения
load_dotenv()

# Константы
SYSTEM_PROMPT = "Ты — кулинарный помощник. Помогаешь пользователям с вопросами о приготовлении пищи, рецептах, кулинарных техниках и всем, что связано с кулинарией."
LLM_TEMPERATURE = 0.7

# Конфигурация
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "anthropic/claude-3-haiku")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# LLM Client (инициализируется в main())
client: OpenAI | None = None

async def get_llm_response(user_message: str) -> str:
    """Получить ответ от LLM"""
    if client is None:
        raise RuntimeError("LLM client не инициализирован")
    try:
        logger.info(f"Запрос к LLM (модель: {LLM_MODEL})")
        # Используем asyncio.to_thread для неблокирующего вызова синхронной функции
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=LLM_TEMPERATURE,
        )
        response_text = response.choices[0].message.content
        logger.info(f"Получен ответ от LLM (длина: {len(response_text)} символов)")
        return response_text
    except Exception as e:
        logger.error(f"Ошибка при запросе к LLM: {e}", exc_info=True)
        raise

# Telegram Handler
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "Привет! Я кулинарный помощник. "
        "Задавай мне вопросы о приготовлении пищи, рецептах и кулинарных техниках!"
    )

async def handle_text_message(message: Message):
    """Обработчик текстовых сообщений"""
    logger.info(f"Получено сообщение из чата {message.chat.id}")
    try:
        response_text = await get_llm_response(message.text)
        await message.answer(response_text)
        logger.info(f"Отправлен ответ в чат {message.chat.id}")
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}", exc_info=True)
        await message.answer("Извините, произошла ошибка. Попробуйте еще раз.")

async def main():
    """Главная функция запуска бота"""
    global client
    
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY не найден в переменных окружения")
    
    # Инициализация LLM клиента
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
    
    # Инициализация бота и диспетчера
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрация обработчиков (команды первыми для приоритета)
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(handle_text_message, F.text)
    
    logger.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

