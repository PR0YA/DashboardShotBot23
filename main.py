import asyncio
from telegram.ext import Application, CommandHandler
from telegram import Update
from telegram.ext import ContextTypes
from config import TELEGRAM_TOKEN
from services.google_sheets import GoogleSheetsService
from services.screenshot import ScreenshotService
from utils.logger import logger
import io

class DashboardBot:
    def __init__(self):
        self.google_sheets_service = GoogleSheetsService()
        self.screenshot_service = ScreenshotService()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Добро пожаловать в DashboardSJ Bot!\n"
            "Используйте /screen чтобы получить скриншот диаграмм."
        )

    async def screen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            # Отправляем начальное сообщение
            status_message = await update.message.reply_text("Получаю скриншот... Пожалуйста, подождите.")

            # Получаем скриншот
            screenshot_data = await self.screenshot_service.get_screenshot()

            # Отправляем скриншот
            await update.message.reply_photo(
                photo=io.BytesIO(screenshot_data),
                caption="Скриншот диаграмм"
            )

            # Удаляем статусное сообщение
            await status_message.delete()

        except Exception as e:
            error_message = f"Произошла ошибка: {str(e)}"
            logger.error(error_message)
            await update.message.reply_text(f"Извините, произошла ошибка: {str(e)}")

    def run(self):
        try:
            # Создаем приложение
            application = Application.builder().token(TELEGRAM_TOKEN).build()

            # Добавляем обработчики команд
            application.add_handler(CommandHandler("start", self.start))
            application.add_handler(CommandHandler("screen", self.screen))

            # Запускаем бота
            logger.info("Запуск бота...")
            application.run_polling()

        except Exception as e:
            logger.error(f"Ошибка инициализации бота: {str(e)}")
            raise

if __name__ == '__main__':
    bot = DashboardBot()
    bot.run()