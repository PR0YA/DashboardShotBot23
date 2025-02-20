import asyncio
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import TELEGRAM_TOKEN
from services.google_sheets import GoogleSheetsService
from services.screenshot import ScreenshotService
from utils.logger import logger
import io
import json

# Состояния разговора
CHOOSING_FORMAT, SELECTING_AREA, CHOOSING_ZOOM, CHOOSING_PRESET, CONFIRMING = range(5)

class DashboardBot:
    def __init__(self):
        self.google_sheets_service = GoogleSheetsService()
        self.screenshot_service = ScreenshotService()
        self.user_data = {}

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет стартовое сообщение с меню выбора формата"""
        keyboard = [
            [
                InlineKeyboardButton("📸 PNG", callback_data="format_png"),
                InlineKeyboardButton("🖼 JPEG", callback_data="format_jpeg"),
                InlineKeyboardButton("🌅 WebP", callback_data="format_webp")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_text = """
🤖 *Добро пожаловать в DashboardSJ Bot\!*

Этот бот поможет вам создавать качественные скриншоты Google Sheets\.

*Процесс создания скриншота:*
1\. Выберите формат
2\. Укажите масштаб \(50\-200%\)
3\. Выберите область \(или весь лист\)
4\. Выберите пресет улучшения
5\. Просмотрите результат

Выберите формат для начала 👇
"""
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
        return CHOOSING_FORMAT

    async def format_chosen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик выбора формата"""
        query = update.callback_query
        await query.answer()

        format_type = query.data.split('_')[1]
        context.user_data['format'] = format_type

        # Клавиатура для выбора масштаба
        keyboard = [
            [
                InlineKeyboardButton("50%", callback_data="zoom_50"),
                InlineKeyboardButton("100%", callback_data="zoom_100"),
                InlineKeyboardButton("150%", callback_data="zoom_150"),
                InlineKeyboardButton("200%", callback_data="zoom_200")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"Формат {format_type.upper()} выбран.\nТеперь выберите масштаб изображения:",
            reply_markup=reply_markup
        )
        return CHOOSING_ZOOM

    async def zoom_chosen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик выбора масштаба"""
        query = update.callback_query
        await query.answer()

        zoom = int(query.data.split('_')[1])
        context.user_data['zoom'] = zoom

        # Клавиатура для выбора области
        keyboard = [
            [
                InlineKeyboardButton("📊 Весь dashboard", callback_data="area_full"),
                InlineKeyboardButton("📈 Только метрики", callback_data="area_metrics"),
                InlineKeyboardButton("📉 Только графики", callback_data="area_charts")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"Масштаб {zoom}% выбран.\nТеперь выберите область скриншота:",
            reply_markup=reply_markup
        )
        return SELECTING_AREA

    async def area_chosen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик выбора области"""
        query = update.callback_query
        await query.answer()

        area_type = query.data.split('_')[1]
        # Предустановленные области (координаты можно настроить)
        areas = {
            'full': None,  # Весь лист
            'metrics': {'x': 0, 'y': 0, 'width': 2440, 'height': 500},  # Только метрики
            'charts': {'x': 0, 'y': 500, 'width': 2440, 'height': 1500}  # Только графики
        }
        context.user_data['area'] = areas[area_type]

        # Клавиатура для выбора пресета улучшения
        presets = self.screenshot_service.get_available_presets()
        keyboard = [[InlineKeyboardButton(preset.replace('_', ' ').title(), 
                                        callback_data=f"preset_{preset}")]
                   for preset in presets]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "Область выбрана.\nВыберите пресет улучшения изображения:",
            reply_markup=reply_markup
        )
        return CHOOSING_PRESET

    async def preset_chosen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик выбора пресета и создание превью"""
        query = update.callback_query
        await query.answer()

        preset = query.data.split('_')[1]
        context.user_data['preset'] = preset

        # Создаем превью с текущими настройками
        status_message = await query.edit_message_text("🔄 Создаю превью...")

        try:
            screenshot_data = await self.screenshot_service.get_screenshot(
                format=context.user_data['format'],
                enhance=True,
                zoom=context.user_data['zoom'],
                area=context.user_data['area'],
                preset=preset
            )

            # Клавиатура для подтверждения
            keyboard = [
                [
                    InlineKeyboardButton("✅ Сохранить", callback_data="confirm_save"),
                    InlineKeyboardButton("🔄 Изменить настройки", callback_data="confirm_restart")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Отправляем превью
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=io.BytesIO(screenshot_data),
                caption=f"Превью скриншота:\nФормат: {context.user_data['format'].upper()}\n"
                        f"Масштаб: {context.user_data['zoom']}%\n"
                        f"Пресет: {preset}",
                reply_markup=reply_markup
            )
            await status_message.delete()
            return CONFIRMING

        except Exception as e:
            error_message = f"❌ Ошибка создания превью: {str(e)}"
            logger.error(error_message)
            await status_message.edit_text(error_message)
            return ConversationHandler.END

    async def handle_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик подтверждения сохранения"""
        query = update.callback_query
        await query.answer()

        action = query.data.split('_')[1]
        if action == 'restart':
            # Начинаем процесс заново
            await self.start(update, context)
            return CHOOSING_FORMAT
        else:
            # Сохраняем финальную версию
            try:
                screenshot_data = await self.screenshot_service.get_screenshot(
                    format=context.user_data['format'],
                    enhance=True,
                    zoom=context.user_data['zoom'],
                    area=context.user_data['area'],
                    preset=context.user_data['preset']
                )

                # Отправляем финальный скриншот
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=io.BytesIO(screenshot_data),
                    filename=f"dashboard_{context.user_data['format']}.{context.user_data['format']}",
                    caption="✅ Готово! Используйте /start для создания нового скриншота."
                )
                return ConversationHandler.END

            except Exception as e:
                error_message = f"❌ Ошибка сохранения: {str(e)}"
                logger.error(error_message)
                await query.edit_message_text(error_message)
                return ConversationHandler.END

    def run(self):
        try:
            # Создаем приложение
            application = Application.builder().token(TELEGRAM_TOKEN).build()

            # Создаем обработчик разговора
            conv_handler = ConversationHandler(
                entry_points=[CommandHandler("start", self.start)],
                states={
                    CHOOSING_FORMAT: [CallbackQueryHandler(self.format_chosen, pattern=r"^format_")],
                    CHOOSING_ZOOM: [CallbackQueryHandler(self.zoom_chosen, pattern=r"^zoom_")],
                    SELECTING_AREA: [CallbackQueryHandler(self.area_chosen, pattern=r"^area_")],
                    CHOOSING_PRESET: [CallbackQueryHandler(self.preset_chosen, pattern=r"^preset_")],
                    CONFIRMING: [CallbackQueryHandler(self.handle_confirmation, pattern=r"^confirm_")]
                },
                fallbacks=[CommandHandler("start", self.start)]
            )

            # Добавляем обработчик
            application.add_handler(conv_handler)

            # Запускаем бота
            logger.info("Запуск бота...")
            application.run_polling()

        except Exception as e:
            logger.error(f"Ошибка инициализации бота: {str(e)}")
            raise

if __name__ == '__main__':
    bot = DashboardBot()
    bot.run()