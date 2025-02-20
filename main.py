import asyncio
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import TELEGRAM_TOKEN
from services.google_sheets import GoogleSheetsService
from services.screenshot import ScreenshotService
from services.metrics_tracker import MetricsTracker
from utils.logger import logger
import io
import json
import re
from datetime import datetime

# Состояния разговора
CHOOSING_FORMAT, SELECTING_AREA, CHOOSING_ZOOM, CHOOSING_PRESET, CONFIRMING = range(5)
SETTING_ALERT, VIEWING_METRICS, GENERATING_REPORT = range(8, 11)

class DashboardBot:
    def __init__(self):
        self.google_sheets_service = GoogleSheetsService()
        self.screenshot_service = ScreenshotService()
        self.metrics_tracker = MetricsTracker(self.google_sheets_service)
        self.user_data = {}

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
            await self.start(update, context)
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

    async def setup_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("Конверсия", callback_data="alert_conversion")],
            [InlineKeyboardButton("Средний чек", callback_data="alert_average_check")],
            [InlineKeyboardButton("Выручка", callback_data="alert_revenue")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Выберите метрику для установки алерта:",
            reply_markup=reply_markup
        )
        return SETTING_ALERT

    async def alert_metric_chosen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        metric = query.data.split('_')[1]
        context.user_data['alert_metric'] = metric

        await query.edit_message_text(
            f"Введите условие и значение для алерта в формате:\n"
            f"> 1000 или < 500\n"
            f"Текущая метрика: {metric}"
        )
        return SETTING_ALERT

    async def handle_alert_condition(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        match = re.match(r'([<>]=?)\s*(\d+\.?\d*)', text)

        if not match:
            await update.message.reply_text(
                "Неверный формат. Используйте: > 1000 или < 500"
            )
            return SETTING_ALERT

        condition, threshold = match.groups()
        metric = context.user_data['alert_metric']

        message = "🚨 {metric}: текущее значение {value} {condition} {threshold}"
        self.metrics_tracker.add_alert(metric, condition, float(threshold), message)

        await update.message.reply_text(
            f"✅ Алерт установлен для {metric} {condition} {threshold}"
        )
        return ConversationHandler.END

    async def view_metrics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            report = await self.metrics_tracker.generate_report()

            if not report:
                await update.message.reply_text("Пока нет данных для отображения")
                return ConversationHandler.END

            message = "📊 *Текущие метрики:*\n\n"
            for metric in report:
                trend_emoji = "📈" if metric['trend_direction'] == 'up' else "📉" if metric['trend_direction'] == 'down' else "➡️"
                change_emoji = "🔼" if metric['change_percent'] > 0 else "🔽" if metric['change_percent'] < 0 else "➡️"

                message += f"*{metric['name']}*\n"
                message += f"Текущее значение: {metric['current_value']:.2f} {change_emoji}\n"
                message += f"Изменение: {metric['change_percent']:.1f}%\n"
                message += f"Тренд: {trend_emoji}\n"

                if metric['alerts']:
                    message += "❗️ *Алерты:*\n"
                    for alert in metric['alerts']:
                        message += f"- {alert}\n"

                message += "\n"

            await update.message.reply_text(message, parse_mode='MarkdownV2')

        except Exception as e:
            logger.error(f"Error viewing metrics: {str(e)}")
            await update.message.reply_text("Произошла ошибка при получении метрик")

        return ConversationHandler.END

    async def generate_full_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            report = await self.metrics_tracker.generate_report()

            if not report:
                await update.message.reply_text("Нет данных для отчета")
                return ConversationHandler.END

            status_message = await update.message.reply_text("🔄 Генерация отчета...")

            screenshots = []
            areas = {
                'metrics': {'x': 0, 'y': 0, 'width': 2440, 'height': 500},
                'charts': {'x': 0, 'y': 500, 'width': 2440, 'height': 1500}
            }

            for area_name, area in areas.items():
                screenshot_data = await self.screenshot_service.get_screenshot(
                    format='png',
                    enhance=True,
                    zoom=100,
                    area=area,
                    preset='default'
                )
                screenshots.append((area_name, screenshot_data))

            report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
            header = f"📊 *Аналитический отчет от {report_date}*\n\n"

            for metric in report:
                trend_emoji = "📈" if metric['trend_direction'] == 'up' else "📉" if metric['trend_direction'] == 'down' else "➡️"
                header += f"*{metric['name']}*: {metric['current_value']:.2f} {trend_emoji}\n"
                header += f"Изменение: {metric['change_percent']:.1f}%\n\n"

            await update.message.reply_text(header, parse_mode='MarkdownV2')

            for name, data in screenshots:
                caption = "📈 Метрики" if name == 'metrics' else "📊 Графики"
                await update.message.reply_photo(
                    photo=io.BytesIO(data),
                    caption=caption
                )

            await status_message.delete()

        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            await update.message.reply_text("Произошла ошибка при генерации отчета")

        return ConversationHandler.END

    def run(self):
        try:
            application = Application.builder().token(TELEGRAM_TOKEN).build()

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

            analytics_handler = ConversationHandler(
                entry_points=[
                    CommandHandler("alert", self.setup_alert),
                    CommandHandler("metrics", self.view_metrics),
                    CommandHandler("report", self.generate_full_report)
                ],
                states={
                    SETTING_ALERT: [
                        CallbackQueryHandler(self.alert_metric_chosen, pattern=r"^alert_"),
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_alert_condition)
                    ]
                },
                fallbacks=[CommandHandler("start", self.start)]
            )

            application.add_handler(screenshot_handler)
            application.add_handler(analytics_handler)

            logger.info("Запуск бота...")
            application.run_polling()

        except Exception as e:
            logger.error(f"Ошибка инициализации бота: {str(e)}")
            raise

if __name__ == '__main__':
    bot = DashboardBot()
    bot.run()