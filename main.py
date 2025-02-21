import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackContext
)
from services.screenshot import ScreenshotService
from services.error_handler import ErrorHandler
from services.bot_metrics import BotMetrics
from config import TELEGRAM_TOKEN
from services.process_manager import ProcessManager

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация сервисов
screenshot_service = ScreenshotService()
bot_metrics = BotMetrics()
error_handler = ErrorHandler(bot_metrics)

async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start"""
    try:
        await update.message.reply_text(
            "👋 Добро пожаловать в DashboardSJ Bot!\n\n"
            "Я помогу вам создавать качественные скриншоты ваших Google Sheets таблиц "
            "с расширенными возможностями настройки.\n\n"
            "🔹 /screenshot - создать скриншот с настройками\n"
            "🔹 /help - подробная информация о командах"
        )
        logger.info(f"Start command handled for user {update.effective_user.id}")
    except Exception as e:
        error_message = error_handler.handle_error(e, {'update': update, 'command': 'start'})
        await update.message.reply_text(error_message)

async def help(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /help"""
    try:
        await update.message.reply_text(
            "📋 Команды бота:\n\n"
            "🔹 /start - Начать работу с ботом\n"
            "🔹 /help - Показать это сообщение\n"
            "🔹 /screenshot - Создать скриншот с настройками:\n"
            "   • Выбор области таблицы\n"
            "   • Улучшение качества изображения\n"
            "   • Настройка масштаба\n"
            "   • Выбор пресетов обработки"
        )
        logger.info(f"Help command handled for user {update.effective_user.id}")
    except Exception as e:
        error_message = error_handler.handle_error(e, {'update': update, 'command': 'help'})
        await update.message.reply_text(error_message)

async def screenshot(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /screenshot"""
    start_time = bot_metrics.start_command_tracking("screenshot")
    try:
        await update.message.reply_text(
            "🔄 Создаю скриншот таблицы...\n"
            "⏳ Пожалуйста, подождите"
        )

        screenshot_data = screenshot_service.get_screenshot(
            format='png',
            enhance=True,
            preset='high_contrast'
        )

        await update.message.reply_document(
            document=screenshot_data,
            filename='screenshot.png',
            caption=(
                '✅ Скриншот готов!\n\n'
                '📝 Параметры:\n'
                '• Формат: PNG\n'
                '• Улучшение качества: Включено\n'
                '• Пресет: Высокий контраст\n\n'
                'Используйте /help для информации о дополнительных настройках'
            )
        )

        bot_metrics.end_command_tracking("screenshot", start_time, success=True)
        logger.info(f"Screenshot created for user {update.effective_user.id}")

    except Exception as e:
        bot_metrics.end_command_tracking("screenshot", start_time, success=False)
        error_message = error_handler.handle_error(e, {
            'user_id': update.effective_user.id,
            'command': 'screenshot'
        })
        await update.message.reply_text(error_message)

def main() -> None:
    """Запуск бота"""
    try:
        # Очищаем старые процессы
        ProcessManager.cleanup_old_processes()
        ProcessManager.remove_pid()

        # Создаем апдейтер
        updater = Updater(TELEGRAM_TOKEN)
        dispatcher = updater.dispatcher

        # Добавляем обработчики команд
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("help", help))
        dispatcher.add_handler(CommandHandler("screenshot", screenshot))

        # Запускаем бота
        logger.info("Starting bot...")
        updater.start_polling()
        updater.idle()

    except Exception as e:
        logger.error(f"Critical error in main: {e}")
        raise
    finally:
        ProcessManager.remove_pid()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
    finally:
        ProcessManager.remove_pid()