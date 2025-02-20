import asyncio
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import TELEGRAM_TOKEN
from services.google_sheets import GoogleSheetsService
from services.screenshot import ScreenshotService
from services.metrics_tracker import MetricsTracker, ReportTemplate
from utils.logger import logger
import io
import json
import re
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import numpy as np

# Состояния разговора
CHOOSING_FORMAT, SELECTING_AREA, CHOOSING_ZOOM, CHOOSING_PRESET, CONFIRMING = range(5)
SETTING_ALERT, VIEWING_METRICS, GENERATING_REPORT = range(8, 11)
TEMPLATE_CREATION, TEMPLATE_METRICS, TEMPLATE_PERIOD = range(11, 14)
COMPARISON_PERIOD = 14


class DashboardBot:
    def __init__(self):
        self.google_sheets_service = GoogleSheetsService()
        self.screenshot_service = ScreenshotService()
        self.metrics_tracker = MetricsTracker(self.google_sheets_service)
        self.user_data = {}

    async def start_services(self):
        """Start background services"""
        self.metrics_tracker.start_periodic_updates()
        logger.info("Started metrics tracking service")

    async def stop_services(self):
        """Stop background services"""
        self.metrics_tracker.stop_periodic_updates()
        logger.info("Stopped metrics tracking service")

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
        """Generate a comprehensive report with multiple screenshots and analytics"""
        try:
            report = await self.metrics_tracker.generate_report()

            if not report:
                await update.message.reply_text("Нет данных для отчета")
                return ConversationHandler.END

            status_message = await update.message.reply_text("🔄 Генерация отчета...")

            # Подготовка скриншотов разных частей дашборда
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

            # Формируем текстовую часть отчета
            report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
            header = f"📊 *Аналитический отчет от {report_date}*\n\n"

            for metric in report:
                # Получаем детальный анализ метрики
                analysis = await self.metrics_tracker.analyze_metric_changes(metric['name'])

                trend_emoji = "📈" if metric['trend_direction'] == 'up' else "📉" if metric['trend_direction'] == 'down' else "➡️"
                header += f"*{metric['name']}*:\n"
                header += f"Текущее значение: {metric['current_value']:.2f} {trend_emoji}\n"

                if analysis:
                    header += f"Изменение за период: {analysis['change_percent']:.1f}%\n"
                    header += f"Минимум: {analysis['min_value']:.2f}\n"
                    header += f"Максимум: {analysis['max_value']:.2f}\n"
                    header += f"Среднее: {analysis['average']:.2f}\n"

                    if 'forecast' in analysis:
                        header += f"Прогноз: {analysis['forecast']['next_value']:.2f} "
                        header += f"(уверенность: {analysis['forecast']['confidence']*100:.0f}%)\n"

                if metric['alerts']:
                    header += "❗️ *Алерты:*\n"
                    for alert in metric['alerts']:
                        header += f"- {alert}\n"

                header += "\n"

            # Отправляем текстовую часть
            await update.message.reply_text(header, parse_mode='MarkdownV2')

            # Отправляем скриншоты
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

    async def view_historical_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command handler for viewing historical data with visualizations"""
        try:
            keyboard = [
                [InlineKeyboardButton("Конверсия", callback_data="history_conversion")],
                [InlineKeyboardButton("Средний чек", callback_data="history_average_check")],
                [InlineKeyboardButton("Выручка", callback_data="history_revenue")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "Выберите метрику для просмотра графика изменений:",
                reply_markup=reply_markup
            )
            return VIEWING_METRICS

        except Exception as e:
            logger.error(f"Error in view_historical_data: {str(e)}")
            await update.message.reply_text("Произошла ошибка при получении данных")
            return ConversationHandler.END

    async def show_metric_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show historical data visualization for selected metric"""
        query = update.callback_query
        await query.answer()

        metric_name = query.data.split('_')[1]
        history = self.metrics_tracker.get_metric_history(metric_name)

        if not history:
            await query.edit_message_text("Нет исторических данных для этой метрики")
            return ConversationHandler.END

        # Create a plot with improved styling
        plt.style.use('seaborn')
        plt.figure(figsize=(12, 6))

        times = [m.timestamp for m in history]
        values = [m.current_value for m in history]

        # Plot with gradient fill
        plt.plot(times, values, 'b-', linewidth=2, marker='o')
        plt.fill_between(times, values, alpha=0.2)

        # Customize appearance
        plt.title(f'Динамика изменений: {metric_name}', fontsize=14, pad=20)
        plt.xlabel('Время', fontsize=12)
        plt.ylabel('Значение', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(rotation=45)

        # Add trend line
        z = np.polyfit(range(len(times)), values, 1)
        p = np.poly1d(z)
        plt.plot(times, p(range(len(times))), "r--", alpha=0.8, label='Тренд')

        plt.legend()
        plt.tight_layout()

        # Save plot to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300)
        buf.seek(0)
        plt.close()

        # Get current metric data
        metrics = await self.metrics_tracker.generate_report()
        current_metric = next((m for m in metrics if m['name'] == metric_name), None)

        caption = f"📊 График изменений метрики *{metric_name}*\n"
        if current_metric:
            trend_emoji = "📈" if current_metric['trend_direction'] == 'up' else "📉" if current_metric['trend_direction'] == 'down' else "➡️"
            caption += f"\nТекущее значение: {current_metric['current_value']:.2f}\n"
            caption += f"Изменение за период: {current_metric['change_percent']:.1f}%\n"
            caption += f"Тренд: {trend_emoji}"

        # Send the plot with caption
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=buf,
            caption=caption,
            parse_mode='Markdown'
        )

        return ConversationHandler.END

    async def start_template_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start creating a new report template"""
        await update.message.reply_text(
            "Давайте создадим новый шаблон отчета.\n"
            "Введите название для шаблона:"
        )
        return TEMPLATE_CREATION

    async def handle_template_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle template name input"""
        template_name = update.message.text
        context.user_data['template_name'] = template_name

        keyboard = [
            [InlineKeyboardButton("Конверсия", callback_data="metric_conversion")],
            [InlineKeyboardButton("Средний чек", callback_data="metric_average_check")],
            [InlineKeyboardButton("Выручка", callback_data="metric_revenue")],
            [InlineKeyboardButton("✅ Готово", callback_data="metrics_done")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Выберите метрики для включения в шаблон:",
            reply_markup=reply_markup
        )
        context.user_data['template_metrics'] = []
        return TEMPLATE_METRICS

    async def handle_template_metrics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle template metrics selection"""
        query = update.callback_query
        await query.answer()

        if query.data == "metrics_done":
            keyboard = [
                [InlineKeyboardButton("День", callback_data="period_day")],
                [InlineKeyboardButton("Неделя", callback_data="period_week")],
                [InlineKeyboardButton("Месяц", callback_data="period_month")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "Выберите период для отчета:",
                reply_markup=reply_markup
            )
            return TEMPLATE_PERIOD

        metric = query.data.split('_')[1]
        if metric not in context.user_data['template_metrics']:
            context.user_data['template_metrics'].append(metric)

        await query.edit_message_text(
            f"Выбранные метрики: {', '.join(context.user_data['template_metrics'])}\n"
            "Выберите еще или нажмите Готово:",
            reply_markup=query.message.reply_markup
        )
        return TEMPLATE_METRICS

    async def handle_template_period(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle template period selection and save template"""
        query = update.callback_query
        await query.answer()

        period = query.data.split('_')[1]
        template = ReportTemplate(
            name=context.user_data['template_name'],
            metrics=context.user_data['template_metrics'],
            period=period
        )
        self.metrics_tracker.save_template(template)

        await query.edit_message_text(
            f"✅ Шаблон '{template.name}' создан!\n"
            f"Метрики: {', '.join(template.metrics)}\n"
            f"Период: {period}\n\n"
            "Используйте /report <название_шаблона> для создания отчета"
        )
        return ConversationHandler.END

    async def generate_report_from_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate a report using a saved template"""
        try:
            args = context.args
            if not args:
                templates = list(self.metrics_tracker.report_templates.keys())
                if not templates:
                    await update.message.reply_text(
                        "У вас нет сохраненных шаблонов.\n"
                        "Используйте /template для создания нового шаблона."
                    )
                    return ConversationHandler.END

                keyboard = [[InlineKeyboardButton(name, callback_data=f"template_{name}")]
                          for name in templates]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    "Выберите шаблон для отчета:",
                    reply_markup=reply_markup
                )
                return GENERATING_REPORT

            template_name = args[0]
            status_message = await update.message.reply_text("🔄 Генерация отчета...")

            report = await self.metrics_tracker.generate_report_from_template(template_name)
            if not report:
                await status_message.edit_text("❌ Ошибка при генерации отчета")
                return ConversationHandler.END

            # Отправляем текстовую часть отчета
            report_text = f"📊 *Отчет по шаблону '{report['name']}'*\n"
            report_text += f"Дата: {report['timestamp']}\n\n"

            for metric_name, data in report['metrics'].items():
                trend_emoji = "📈" if data.get('current', 0) > data.get('plan', 0) else "📉"
                report_text += f"*{metric_name}*:\n"
                report_text += f"Текущее значение: {data['current']:.2f} {trend_emoji}\n"

                if 'plan' in data:
                    report_text += f"План: {data['plan']:.2f}\n"
                    report_text += f"Выполнение плана: {data['plan_achievement']:.1f}%\n"

                report_text += "\n"

            await update.message.reply_text(report_text, parse_mode='MarkdownV2')

            # Если в шаблоне включены графики, генерируем их
            template = self.metrics_tracker.report_templates[template_name]
            if template.include_charts:
                for metric_name in template.metrics:
                    if metric_name in report['metrics'] and 'history' in report['metrics'][metric_name]:
                        await self.send_metric_chart(
                            update.message.chat_id,
                            metric_name,
                            report['metrics'][metric_name]['history'],
                            context
                        )

            await status_message.delete()

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            await update.message.reply_text("❌ Ошибка при генерации отчета")

        return ConversationHandler.END

    async def compare_metrics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Compare metrics between periods"""
        keyboard = [
            [InlineKeyboardButton("День", callback_data="compare_day")],
            [InlineKeyboardButton("Неделя", callback_data="compare_week")],
            [InlineKeyboardButton("Месяц", callback_data="compare_month")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Выберите период для сравнения:",
            reply_markup=reply_markup
        )
        return COMPARISON_PERIOD

    async def handle_comparison_period(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle period selection for comparison"""
        query = update.callback_query
        await query.answer()

        period = query.data.split('_')[1]
        status_message = await query.edit_message_text("🔄 Анализ данных...")

        try:
            report = await self.metrics_tracker.generate_comparison_report(period)

            if not report:
                await status_message.edit_text("❌ Недостаточно данных для сравнения")
                return ConversationHandler.END

            message = f"📊 *Сравнительный анализ* \(период: {period}\)\n\n"

            for metric_name, data in report.items():
                comparison = data['comparison']
                trend_emoji = "📈" if comparison['trend'] == 'up' else "📉" if comparison['trend'] == 'down' else "➡️"

                message += f"*{metric_name}*:\n"
                message += f"Текущее значение: {data['current']:.2f}\n"
                if 'plan' in data:
                    message += f"План: {data['plan']:.2f}\n"
                message += f"Изменение: {comparison['change_percent']:.1f}% {trend_emoji}\n"
                message += f"Среднее за период: {comparison['period1_avg']:.2f}\n"
                message += f"Среднее за пред\. период: {comparison['period2_avg']:.2f}\n\n"

            await query.message.reply_text(message, parse_mode='MarkdownV2')

        except Exception as e:
            logger.error(f"Error in comparison: {e}")
            await status_message.edit_text("❌ Ошибка при сравнении данных")

        return ConversationHandler.END

    async def send_metric_chart(self, chat_id, metric_name, history, context):
        plt.style.use('seaborn')
        plt.figure(figsize=(12, 6))

        times = [m.timestamp for m in history]
        values = [m.current_value for m in history]

        plt.plot(times, values, 'b-', linewidth=2, marker='o')
        plt.fill_between(times, values, alpha=0.2)

        plt.title(f'Динамика изменений: {metric_name}', fontsize=14, pad=20)
        plt.xlabel('Время', fontsize=12)
        plt.ylabel('Значение', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(rotation=45)

        z = np.polyfit(range(len(times)), values, 1)
        p = np.poly1d(z)
        plt.plot(times, p(range(len(times))), "r--", alpha=0.8, label='Тренд')

        plt.legend()
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300)
        buf.seek(0)
        plt.close()

        await context.bot.send_photo(chat_id=chat_id, photo=buf, caption=f"График для {metric_name}")

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

            # Setup startup and shutdown handlers
            async def start_services_wrapper(app: Application):
                await self.start_services()

            async def stop_services_wrapper(app: Application):
                await self.stop_services()

            application.add_handler(
                CommandHandler("start", self.start)
            )

            screenshot_handler = ConversationHandler(
                entry_points=[CommandHandler("start", self.start)],
                states={
                    CHOOSING_FORMAT: [CallbackQueryHandler(self.format_chosen, pattern=r"^format_", per_message=True)],
                    CHOOSING_ZOOM: [CallbackQueryHandler(self.zoom_chosen, pattern=r"^zoom_", per_message=True)],
                    SELECTING_AREA: [CallbackQueryHandler(self.area_chosen, pattern=r"^area_", per_message=True)],
                    CHOOSING_PRESET: [CallbackQueryHandler(self.preset_chosen, pattern=r"^preset_", per_message=True)],
                    CONFIRMING: [CallbackQueryHandler(self.handle_confirmation, pattern=r"^confirm_", per_message=True)]
                },
                fallbacks=[CommandHandler("start", self.start)],
                per_message=True
            )

            analytics_handler = ConversationHandler(
                entry_points=[
                    CommandHandler("alert", self.setup_alert),
                    CommandHandler("metrics", self.view_metrics),
                    CommandHandler("report", self.generate_full_report),
                    CommandHandler("history", self.view_historical_data)
                ],
                states={
                    SETTING_ALERT: [
                        CallbackQueryHandler(self.alert_metric_chosen, pattern=r"^alert_", per_message=True),
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_alert_condition)
                    ],
                    VIEWING_METRICS: [
                        CallbackQueryHandler(self.show_metric_history, pattern=r"^history_", per_message=True)
                    ]
                },
                fallbacks=[CommandHandler("start", self.start)],
                per_message=True
            )

            template_handler = ConversationHandler(
                entry_points=[CommandHandler("template", self.start_template_creation)],
                states={
                    TEMPLATE_CREATION: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_template_name)
                    ],
                    TEMPLATE_METRICS: [
                        CallbackQueryHandler(self.handle_template_metrics, pattern=r"^metric_", per_message=True)
                    ],
                    TEMPLATE_PERIOD: [
                        CallbackQueryHandler(self.handle_template_period, pattern=r"^period_", per_message=True)
                    ]
                },
                fallbacks=[CommandHandler("start", self.start)],
                per_message=True
            )

            comparison_handler = ConversationHandler(
                entry_points=[CommandHandler("compare", self.compare_metrics)],
                states={
                    COMPARISON_PERIOD: [
                        CallbackQueryHandler(self.handle_comparison_period, pattern=r"^compare_", per_message=True)
                    ]
                },
                fallbacks=[CommandHandler("start", self.start)],
                per_message=True
            )

            # Add handlers
            application.add_handler(screenshot_handler)
            application.add_handler(analytics_handler)
            application.add_handler(template_handler)
            application.add_handler(comparison_handler)
            application.add_handler(CommandHandler("report", self.generate_report_from_template))
            application.add_handler(CommandHandler("alert", self.setup_alert))

            # Add startup and shutdown handlers
            async def start_services_wrapper(app: Application):
                await self.start_services()

            async def stop_services_wrapper(app: Application):
                await self.stop_services()

            application.post_init = start_services_wrapper
            application.post_shutdown = stop_services_wrapper

            logger.info("Запуск бота...")
            application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

        except Exception as e:
            logger.error(f"Error running bot: {str(e)}")
            raise

if __name__ == '__main__':
    bot = DashboardBot()
    bot.run()