import os
import sys
import logging
from telegram.ext import Updater, CommandHandler

# Расширенная настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Токен из конфигурации
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "7770923655:AAHcyQiCKWSYKRB9JfxsD9wMSAutdyCz9NQ")

def start_command(update, context):
    """Обработчик команды /start"""
    try:
        update.message.reply_text(
            "👋 Привет! Я бот для создания скриншотов.\n"
            "Сейчас я работаю в режиме отладки.\n"
            "Используйте /help для получения списка команд."
        )
        logger.info("Successfully sent start message")
    except Exception as e:
        logger.error(f"Error sending start message: {e}")
        raise

def help_command(update, context):
    """Обработчик команды /help"""
    try:
        help_text = """
*Доступные команды:*
/start \- Начать работу с ботом
/help \- Показать это сообщение
/status \- Проверить статус бота
"""
        update.message.reply_text(help_text, parse_mode='MarkdownV2')
        logger.info("Successfully sent help message")
    except Exception as e:
        logger.error(f"Error sending help message: {e}")
        raise

def status_command(update, context):
    """Обработчик команды /status"""
    try:
        update.message.reply_text("✅ Бот работает нормально\n")
        logger.info("Successfully sent status message")
    except Exception as e:
        logger.error(f"Error sending status message: {e}")
        raise

def error_handler(update, context):
    """Обработчик ошибок"""
    logger.error(f"Exception while handling an update: {context.error}")
    try:
        if update and hasattr(update, 'effective_message'):
            update.effective_message.reply_text(
                "Произошла ошибка при обработке команды. Попробуйте позже."
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

def main():
    """Основная функция запуска бота"""
    try:
        logger.info("Starting bot initialization...")

        # Создаем апдейтер
        updater = Updater(TELEGRAM_TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        logger.info("Updater created successfully")

        # Регистрация обработчиков команд
        dispatcher.add_handler(CommandHandler("start", start_command))
        dispatcher.add_handler(CommandHandler("help", help_command))
        dispatcher.add_handler(CommandHandler("status", status_command))
        logger.info("Command handlers registered")

        # Регистрация обработчика ошибок
        dispatcher.add_error_handler(error_handler)
        logger.info("Error handler registered")

        logger.info("Starting polling...")
        updater.start_polling()
        updater.idle()

    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()