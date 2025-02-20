import asyncio
from telegram.ext import Application, CommandHandler, CallbackContext
from telegram import Update, ReplyKeyboardMarkup
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
        keyboard = [
            ['/screen jpeg', '/screen png', '/screen webp']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "Добро пожаловать в DashboardSJ Bot!\n"
            "Используйте команду /screen с указанием формата:\n"
            "/screen jpeg - для JPEG формата\n"
            "/screen png - для PNG формата\n"
            "/screen webp - для WebP формата",
            reply_markup=reply_markup
        )

    async def screen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            # Получаем формат из аргументов команды
            format_arg = context.args[0].lower() if context.args else 'jpeg'

            # Проверяем валидность формата
            if format_arg not in ['jpeg', 'png', 'webp']:
                await update.message.reply_text(
                    "Неверный формат. Используйте один из следующих: jpeg, png, webp"
                )
                return

            # Отправляем начальное сообщение
            status_message = await update.message.reply_text(
                f"Получаю скриншот в формате {format_arg.upper()}... Пожалуйста, подождите."
            )

            # Получаем скриншот в указанном формате
            screenshot_data = await self.screenshot_service.get_screenshot(format_arg)

            # Отправляем скриншот
            await update.message.reply_photo(
                photo=io.BytesIO(screenshot_data),
                caption=f"Скриншот диаграмм в формате {format_arg.upper()}"
            )

            # Удаляем статусное сообщение
            await status_message.delete()

        except IndexError:
            await update.message.reply_text(
                "Пожалуйста, укажите формат: /screen [jpeg|png|webp]"
            )
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