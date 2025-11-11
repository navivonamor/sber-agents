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

# Dialog Manager (in-memory)
dialog_history: dict[int, list[dict]] = {}

async def get_llm_response(user_message: str, chat_id: int) -> str:
    """Получить ответ от LLM с учетом истории"""
    if client is None:
        raise RuntimeError("LLM client не инициализирован")
    try:
        # Формируем историю для передачи в LLM
        history = dialog_history.get(chat_id, [])
        messages = ([{"role": "system", "content": SYSTEM_PROMPT}] +
                    history + [{"role": "user", "content": user_message}])
        # Оставляем system prompt + последние 10 пользовательских сообщений
        messages = [messages[0]] + messages[1:][-10:]
        logger.info(f"Запрос к LLM (модель: {LLM_MODEL}, история: {len(messages)-1} сообщений)")
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=LLM_MODEL,
            messages=messages,
            temperature=LLM_TEMPERATURE,
        )
        response_text = response.choices[0].message.content
        logger.info(f"Получен ответ от LLM (длина: {len(response_text)} символов)")
        return response_text
    except Exception as e:
        logger.error(
            f"Ошибка при запросе к LLM: {e}\nmessages: {messages}",
            exc_info=True
        )
        raise

# Telegram Handler
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    try:
        await message.answer(
            "Привет! Я кулинарный помощник. "
            "Задавай мне вопросы о приготовлении пищи, рецептах и кулинарных техниках!"
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке /start: {e}", exc_info=True)
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")

async def cmd_reset(message: Message):
    """Обработка команды /reset (очистка истории для пользователя)"""
    try:
        chat_id = message.chat.id
        dialog_history.pop(chat_id, None)
        await message.answer("История диалога очищена. Начнем заново!")
    except Exception as e:
        logger.error(f"Ошибка при обработке /reset: {e}", exc_info=True)
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")

async def handle_text_message(message: Message):
    """Обработчик текстовых сообщений"""
    logger.info(f"Получено сообщение из чата {message.chat.id}")
    chat_id = message.chat.id
    text = (message.text or "").strip()
    if not text:
        await message.answer("Сообщение не должно быть пустым.")
        logger.info(f"Пустое сообщение из чата {chat_id}, не отправлено в LLM")
        return
    try:
        # Добавляем сообщение пользователя в историю
        dialog_history.setdefault(chat_id, []).append({"role": "user", "content": text})
        # Обрезаем историю до 10 последних сообщений (не считая system)
        if len(dialog_history[chat_id]) > 10:
            dialog_history[chat_id] = dialog_history[chat_id][-10:]
        response_text = await get_llm_response(text, chat_id)
        await message.answer(response_text)
        logger.info(f"Отправлен ответ в чат {chat_id}")
        # Сохраняем ответ ассистента в историю
        dialog_history[chat_id].append({"role": "assistant", "content": response_text})
        if len(dialog_history[chat_id]) > 10:
            dialog_history[chat_id] = dialog_history[chat_id][-10:]
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
    dp.message.register(cmd_reset, Command("reset"))
    dp.message.register(handle_text_message, F.text)
    
    logger.info("Бот запущен")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Фатальная ошибка polling: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())

