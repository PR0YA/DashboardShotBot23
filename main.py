import asyncio
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
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
        """Отправляет стартовое сообщение с меню"""
        # Создаем inline-клавиатуру
        keyboard = [
            [
                InlineKeyboardButton("📸 PNG", callback_data="png"),
                InlineKeyboardButton("🖼 JPEG", callback_data="jpeg"),
                InlineKeyboardButton("🌅 WebP", callback_data="webp")
            ],
            [
                InlineKeyboardButton("✨ PNG с улучшением", callback_data="png_enhance"),
                InlineKeyboardButton("✨ JPEG с улучшением", callback_data="jpeg_enhance"),
                InlineKeyboardButton("✨ WebP с улучшением", callback_data="webp_enhance")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_text = """
🤖 *Добро пожаловать в DashboardSJ Bot\!*

Этот бот поможет вам создавать качественные скриншоты Google Sheets\.

*Доступные форматы:*
• PNG \- для максимального качества
• JPEG \- для оптимального размера
• WebP \- современный формат

*Варианты улучшения:*
• Обычный скриншот \- точная копия
• С улучшением \- оптимизированное качество

Выберите нужный формат из меню ниже 👇
"""

        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()

        # Разбираем callback_data
        format_data = query.data.split('_')
        format_type = format_data[0]
        enhance = len(format_data) > 1 and format_data[1] == 'enhance'

        # Отправляем статусное сообщение
        enhancement_text = " с улучшением" if enhance else ""
        status_message = await query.message.reply_text(
            f"📸 Создаю скриншот в формате {format_type.upper()}{enhancement_text}...\n"
            "Пожалуйста, подождите."
        )

        try:
            # Получаем скриншот
            screenshot_data = await self.screenshot_service.get_screenshot(format_type, enhance)

            # Формируем подпись
            enhancement_caption = "✨ С улучшением качества" if enhance else "📸 Стандартное качество"
            caption = f"Формат: {format_type.upper()}\n{enhancement_caption}"

            # Отправляем скриншот
            await query.message.reply_photo(
                photo=io.BytesIO(screenshot_data),
                caption=caption
            )

            # Удаляем статусное сообщение
            await status_message.delete()

        except Exception as e:
            error_message = f"❌ Произошла ошибка: {str(e)}"
            logger.error(error_message)
            await status_message.edit_text(error_message)

    def run(self):
        try:
            # Создаем приложение
            application = Application.builder().token(TELEGRAM_TOKEN).build()

            # Добавляем обработчики
            application.add_handler(CommandHandler("start", self.start))
            application.add_handler(CallbackQueryHandler(self.button_handler))

            # Запускаем бота
            logger.info("Запуск бота...")
            application.run_polling()

        except Exception as e:
            logger.error(f"Ошибка инициализации бота: {str(e)}")
            raise

if __name__ == '__main__':
    bot = DashboardBot()
    bot.run()