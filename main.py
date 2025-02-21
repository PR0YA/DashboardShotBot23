import logging
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
from services.screenshot import ScreenshotService
from services.error_handler import ErrorHandler
from services.bot_metrics import BotMetrics

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен из конфигурации
TELEGRAM_TOKEN = "7770923655:AAHcyQiCKWSYKRB9JfxsD9wMSAutdyCz9NQ"

# Инициализация сервисов
screenshot_service = ScreenshotService()
bot_metrics = BotMetrics()
error_handler = ErrorHandler(bot_metrics)

def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start"""
    try:
        update.message.reply_text(
            "👋 Добро пожаловать в DashboardSJ Bot!\n\n"
            "Я помогу вам создавать качественные скриншоты ваших Google Sheets таблиц "
            "с возможностью настройки и улучшения изображения.\n\n"
            "🔹 Используйте /screenshot для создания скриншота\n"
            "🔹 /help - список всех команд\n"
            "🔹 /status - проверка состояния бота"
        )
        logger.info(f"Start command handled for user {update.effective_user.id}")
    except Exception as e:
        error_message = error_handler.handle_error(e, {'update': update, 'command': 'start'})
        update.message.reply_text(error_message)

def help(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /help"""
    try:
        update.message.reply_text(
            "Доступные команды:\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать это сообщение\n"
            "/status - Проверить статус бота\n"
            "/screenshot - Сделать скриншот таблицы\n"
            "\nДля создания скриншота используйте команду /screenshot"
        )
        logger.info(f"Help command handled for user {update.effective_user.id}")
    except Exception as e:
        error_message = error_handler.handle_error(e, {'update': update, 'command': 'help'})
        update.message.reply_text(error_message)

def status(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /status"""
    try:
        stats = bot_metrics.get_performance_stats()
        status_message = (
            "✅ Бот работает нормально\n\n"
            f"📊 Статистика:\n"
            f"• Выполнено команд: {stats.get('commands', {}).get('total_executed', 0)}\n"
            f"• Успешность: {stats.get('commands', {}).get('success_rate', 100)}%\n"
            f"• Среднее время ответа: {stats.get('commands', {}).get('average_time', 0)}с"
        )
        update.message.reply_text(status_message)
        logger.info(f"Status command handled for user {update.effective_user.id}")
    except Exception as e:
        error_message = error_handler.handle_error(e, {'update': update, 'command': 'status'})
        update.message.reply_text(error_message)

def screenshot(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /screenshot"""
    start_time = bot_metrics.start_command_tracking("screenshot")
    try:
        update.message.reply_text("🔄 Создаю скриншот таблицы...")

        # Получаем скриншот
        screenshot_data = screenshot_service.get_screenshot(
            format='png',
            enhance=True,
            preset='high_contrast'
        )

        # Отправляем файл
        update.message.reply_document(
            document=screenshot_data,
            filename='screenshot.png',
            caption='📊 Скриншот таблицы готов!'
        )

        # Завершаем отслеживание
        bot_metrics.end_command_tracking("screenshot", start_time, success=True)
        logger.info(f"Screenshot created for user {update.effective_user.id}")

    except Exception as e:
        bot_metrics.end_command_tracking("screenshot", start_time, success=False)
        error_message = error_handler.handle_error(e, {
            'user_id': update.effective_user.id,
            'command': 'screenshot'
        })
        update.message.reply_text(error_message)

def error_callback(update: Update, context: CallbackContext) -> None:
    """Глобальный обработчик ошибок"""
    try:
        if update and update.effective_message:
            error_message = error_handler.handle_error(context.error, {
                'update': update,
                'context': context
            })
            update.effective_message.reply_text(error_message)
        else:
            logger.error(f"Error occurred: {context.error}")
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

def main() -> None:
    """Запуск бота"""
    try:
        # Создаем Updater
        updater = Updater(TELEGRAM_TOKEN)

        # Получаем диспетчер
        dp = updater.dispatcher

        # Добавляем обработчики команд
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("help", help))
        dp.add_handler(CommandHandler("status", status))
        dp.add_handler(CommandHandler("screenshot", screenshot))

        # Добавляем обработчик ошибок
        dp.add_error_handler(error_callback)

        # Запускаем бота
        logger.info("Starting bot...")
        updater.start_polling()
        updater.idle()

    except Exception as e:
        logger.error(f"Critical error in main: {e}")
        raise

if __name__ == '__main__':
    main()