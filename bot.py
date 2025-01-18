import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
import os

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# API MEXC для получения фьючерсных пар
MEXC_FUTURES_API_URL = 'https://contract.mexc.com/api/v1/contract/detail'

# Хранилище уже известных пар
known_pairs = set()
registered_chats = set()

async def fetch_futures_pairs():
    """Запрос списка фьючерсных пар с MEXC."""
    try:
        response = requests.get(MEXC_FUTURES_API_URL)
        response.raise_for_status()
        data = response.json()
        if 'data' in data:
            data = data['data']
        pairs = [item['symbol'] for item in data]
        logger.info(f"Найдено пар: {len(pairs)}")
        return pairs
    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе данных из MEXC: {e}")
        return []
    except KeyError as e:
        logger.error(f"Ошибка обработки данных: отсутствует ключ {e}")
        return []

async def check_new_listings():
    """Проверка на новые листинги и отправка уведомлений."""
    global known_pairs
    pairs = await fetch_futures_pairs()
    if not pairs:
        logger.warning("Не удалось получить список пар для проверки новых листингов.")
        return

    new_pairs = set(pairs) - known_pairs
    if new_pairs:
        for pair in new_pairs:
            message = f"🚀 Новая фьючерсная пара на MEXC: {pair}"
            logger.info(message)
            for chat_id in registered_chats:
                await application.bot.send_message(chat_id=chat_id, text=message)
        known_pairs.update(new_pairs)

async def periodic_check():
    """Периодическая проверка листингов."""
    while True:
        await check_new_listings()
        await asyncio.sleep(60)  # Проверяем раз в минуту

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    global known_pairs
    logger.info(f"Получена команда /start от чата {update.effective_chat.id}")
    registered_chats.add(update.effective_chat.id)  # Регистрируем чат
    await update.message.reply_text("Бот запущен и отслеживает листинги новых фьючерсов на MEXC!")
    known_pairs = set(await fetch_futures_pairs())  # Сохраняем текущий список пар

def main():
    """Основной метод для запуска бота."""
    global application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))

    # Запускаем периодическую проверку
    loop = asyncio.get_event_loop()
    loop.create_task(periodic_check())

    logger.info("Bot is running...")
    application.run_polling()  # Используем long polling

# Запуск бота
if __name__ == "__main__":
    main()
