import logging
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
from services.screenshot import ScreenshotService
from services.error_handler import ErrorHandler
from services.bot_metrics import BotMetrics
from config import TELEGRAM_TOKEN

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    try:
        await update.message.reply_text(
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
        await update.message.reply_text(error_message)

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    try:
        await update.message.reply_text(
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
        await update.message.reply_text(error_message)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        await update.message.reply_text(status_message)
        logger.info(f"Status command handled for user {update.effective_user.id}")
    except Exception as e:
        error_message = error_handler.handle_error(e, {'update': update, 'command': 'status'})
        await update.message.reply_text(error_message)

async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /screenshot"""
    start_time = bot_metrics.start_command_tracking("screenshot")
    try:
        await update.message.reply_text("🔄 Создаю скриншот таблицы...")

        # Получаем скриншот
        screenshot_data = screenshot_service.get_screenshot(
            format='png',
            enhance=True,
            preset='high_contrast'
        )

        # Отправляем файл
        await update.message.reply_document(
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
        await update.message.reply_text(error_message)

async def main() -> None:
    """Запуск бота"""
    try:
        # Создаем приложение
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help))
        application.add_handler(CommandHandler("status", status))
        application.add_handler(CommandHandler("screenshot", screenshot))

        # Запускаем бота
        logger.info("Starting bot...")
        await application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Critical error in main: {e}")
        raise

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())