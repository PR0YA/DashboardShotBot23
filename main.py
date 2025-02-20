import asyncio
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import TELEGRAM_TOKEN
from services.screenshot import ScreenshotService
from utils.logger import logger
import io

# Состояния разговора
CHOOSING_FORMAT, CHOOSING_ZOOM, SELECTING_AREA, CHOOSING_PRESET, CONFIRMING = range(5)

class DashboardBot:
    def __init__(self):
        self.screenshot_service = ScreenshotService()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

Этот бот поможет вам создавать качественные скриншоты Google Sheets.

*Процесс создания скриншота:*
1. Выберите формат
2. Укажите масштаб (50-200%)
3. Выберите область (или весь лист)
4. Выберите пресет улучшения
5. Просмотрите результат

Выберите формат для начала 👇
"""
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
        return CHOOSING_FORMAT

    async def format_chosen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        format_type = query.data.split('_')[1]
        context.user_data['format'] = format_type

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
        query = update.callback_query
        await query.answer()

        zoom = int(query.data.split('_')[1])
        context.user_data['zoom'] = zoom

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
        query = update.callback_query
        await query.answer()

        area_type = query.data.split('_')[1]
        areas = {
            'full': None,
            'metrics': {'x': 0, 'y': 0, 'width': 2440, 'height': 500},
            'charts': {'x': 0, 'y': 500, 'width': 2440, 'height': 1500}
        }
        context.user_data['area'] = areas[area_type]

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
        query = update.callback_query
        await query.answer()

        preset = query.data.split('_')[1]
        context.user_data['preset'] = preset

        status_message = await query.edit_message_text("🔄 Создаю превью...")

        try:
            screenshot_data = await self.screenshot_service.get_screenshot(
                format=context.user_data['format'],
                enhance=True,
                zoom=context.user_data['zoom'],
                area=context.user_data['area'],
                preset=preset
            )

            keyboard = [
                [
                    InlineKeyboardButton("✅ Сохранить", callback_data="confirm_save"),
                    InlineKeyboardButton("🔄 Изменить настройки", callback_data="confirm_restart")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

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
        query = update.callback_query
        await query.answer()

        action = query.data.split('_')[1]
        if action == 'restart':
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="🤖 *Добро пожаловать в DashboardSJ Bot\!*\n\nЭтот бот поможет вам создавать качественные скриншоты Google Sheets.\n\n*Процесс создания скриншота:*\n1. Выберите формат\n2. Укажите масштаб (50-200%)\n3. Выберите область (или весь лист)\n4. Выберите пресет улучшения\n5. Просмотрите результат\n\nВыберите формат для начала 👇",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("📸 PNG", callback_data="format_png"),
                        InlineKeyboardButton("🖼 JPEG", callback_data="format_jpeg"),
                        InlineKeyboardButton("🌅 WebP", callback_data="format_webp")
                    ]
                ]),
                parse_mode='MarkdownV2'
            )
            return CHOOSING_FORMAT
        else:
            try:
                screenshot_data = await self.screenshot_service.get_screenshot(
                    format=context.user_data['format'],
                    enhance=True,
                    zoom=context.user_data['zoom'],
                    area=context.user_data['area'],
                    preset=context.user_data['preset']
                )

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
            application = Application.builder().token(TELEGRAM_TOKEN).build()

            # Add error handler
            async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
                logger.error(f"Exception while handling an update: {context.error}")
                if update and isinstance(update, Update) and update.effective_message:
                    await update.effective_message.reply_text(
                        "Произошла ошибка при обработке запроса. Попробуйте позже."
                    )

            application.add_error_handler(error_handler)

            # Conversation handler for screenshot creation
            screenshot_handler = ConversationHandler(
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

            application.add_handler(screenshot_handler)

            logger.info("Запуск бота...")
            application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

        except Exception as e:
            logger.error(f"Error running bot: {str(e)}")
            raise

if __name__ == '__main__':
    bot = DashboardBot()
    bot.run()