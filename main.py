import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен из конфигурации
TELEGRAM_TOKEN = "7770923655:AAHcyQiCKWSYKRB9JfxsD9wMSAutdyCz9NQ"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    try:
        await update.message.reply_text(
            "👋 Привет! Я бот для создания скриншотов.\n"
            "Используйте /help для получения списка команд."
        )
        logger.info(f"Start command handled for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    try:
        await update.message.reply_text(
            "Доступные команды:\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать это сообщение\n"
            "/status - Проверить статус бота"
        )
        logger.info(f"Help command handled for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /status"""
    try:
        await update.message.reply_text("✅ Бот работает нормально")
        logger.info(f"Status command handled for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальный обработчик ошибок"""
    logger.error(f"Exception while handling an update: {context.error}")

async def main() -> None:
    """Запуск бота"""
    try:
        # Создаем приложение
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help))
        application.add_handler(CommandHandler("status", status))

        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)

        # Запускаем бота
        logger.info("Starting bot...")
        await application.run_polling()

    except Exception as e:
        logger.error(f"Critical error in main: {e}")
        raise

if __name__ == '__main__':
    asyncio.run(main())