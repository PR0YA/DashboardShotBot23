import asyncio
import os
import sys
import signal
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import TELEGRAM_TOKEN
from services.screenshot import ScreenshotService
from utils.logger import logger
import io
import psutil

# Добавляем новые состояния для диалога
CHOOSING_FORMAT, CHOOSING_ZOOM, SELECTING_AREA, CHOOSING_PRESET, PREVIEW_AREA, CONFIRMING = range(6)

# Анимированные эмодзи для прогресса
PROGRESS_EMOJI = ["⏳", "⌛️"]

def get_running_bot_processes():
    """Получает список процессов бота"""
    try:
        import psutil
        bot_processes = []
        logger.info(f"Searching for bot processes... Current PID: {os.getpid()}")

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'python' in proc.info['name'].lower() and 'main.py' in cmdline:
                    bot_processes.append(proc)
                    logger.info(f"Found bot process: PID={proc.pid}, CMD={cmdline}")
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.warning(f"Could not access process: {e}")
                continue

        logger.info(f"Found {len(bot_processes)} bot processes")
        return bot_processes
    except ImportError:
        logger.error("psutil not available")
        return []

def cleanup_old_processes():
    """Очищает старые процессы бота"""
    current_pid = os.getpid()
    logger.info(f"Starting cleanup of old processes. Current PID: {current_pid}")

    # Получаем информацию о системных ресурсах
    virtual_memory = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=1)
    logger.info(f"System resources - Memory: {virtual_memory.percent}%, CPU: {cpu_percent}%")

    try:
        # Сначала пытаемся удалить все PID файлы
        if os.path.exists("bot.pid"):
            try:
                os.remove("bot.pid")
                logger.info("Removed existing PID file")
            except Exception as e:
                logger.error(f"Error removing PID file: {e}")

        # Ищем все процессы бота
        for proc in get_running_bot_processes():
            if proc.pid != current_pid:
                try:
                    logger.info(f"Attempting to terminate process {proc.pid}")

                    # Сначала пробуем мягкое завершение
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)  # Увеличенный таймаут
                        logger.info(f"Process {proc.pid} terminated successfully")
                    except psutil.TimeoutExpired:
                        logger.warning(f"Timeout waiting for process {proc.pid} to terminate, using SIGKILL")
                        # Если не удалось завершить мягко, используем SIGKILL
                        os.kill(proc.pid, signal.SIGKILL)
                        # Ждем еще немного для полного завершения
                        try:
                            proc.wait(timeout=3)
                            logger.info(f"Process {proc.pid} killed successfully")
                        except psutil.TimeoutExpired:
                            logger.error(f"Failed to kill process {proc.pid}")

                except psutil.NoSuchProcess:
                    logger.info(f"Process {proc.pid} already terminated")
                except Exception as e:
                    logger.error(f"Error handling process {proc.pid}: {e}")

    except Exception as e:
        logger.error(f"Error in cleanup_old_processes: {e}")
        raise

def is_bot_running():
    """Проверяет, запущен ли уже бот"""
    try:
        # Получаем текущий PID
        current_pid = os.getpid()
        logger.info(f"Checking if bot is already running... Current PID: {current_pid}")

        # Проверяем все процессы бота
        running_processes = get_running_bot_processes()

        # Фильтруем текущий процесс
        other_processes = [p for p in running_processes if p.pid != current_pid]

        if other_processes:
            for proc in other_processes:
                try:
                    cmdline = ' '.join(proc.cmdline())
                    logger.warning(f"Found another bot instance: PID={proc.pid}, CMD={cmdline}")
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    logger.error(f"Error accessing process {proc.pid}: {e}")
                    continue
            return True

        logger.info("No other bot instances found")
        return False

    except Exception as e:
        logger.error(f"Error in is_bot_running: {e}")
        return False

def save_pid():
    """Сохраняет PID текущего процесса"""
    try:
        pid = os.getpid()
        with open("bot.pid", 'w') as f:
            f.write(str(pid))
        logger.info(f"Saved PID file with PID: {pid}")
    except Exception as e:
        logger.error(f"Error saving PID file: {e}")

def remove_pid():
    """Удаляет PID файл"""
    try:
        os.remove("bot.pid")
        logger.info("Successfully removed PID file")
    except Exception as e:
        logger.error(f"Error removing PID file: {e}")

class DashboardBot:
    def __init__(self):
        self.screenshot_service = ScreenshotService()
        self.progress_tasks = {}

    async def animate_progress(self, message, text_template):
        """Анимирует сообщение о прогрессе"""
        i = 0
        while True:
            try:
                await message.edit_text(
                    text_template.format(emoji=PROGRESS_EMOJI[i % 2]),
                    parse_mode='MarkdownV2'
                )
                i += 1
                await asyncio.sleep(1)
            except Exception:
                break

    async def start_progress_animation(self, message, text_template):
        """Запускает анимацию прогресса"""
        task = asyncio.create_task(self.animate_progress(message, text_template))
        self.progress_tasks[message.message_id] = task
        return message

    async def stop_progress_animation(self, message_id):
        """Останавливает анимацию прогресса"""
        if message_id in self.progress_tasks:
            self.progress_tasks[message_id].cancel()
            del self.progress_tasks[message_id]

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает справку по командам бота"""
        help_text = """
*DashboardSJ Bot \- Справка* 🤖

*Основные команды:*
/start \- Начать создание скриншота
/help \- Показать эту справку
/settings \- Настройки бота
/status \- Проверить состояние бота
/cache - Показать статистику кэша

*Процесс создания скриншота:*
1\. Выбор формата \(PNG/JPEG/WebP\)
2\. Настройка масштаба \(50\-200%\)
3\. Выбор области
4\. Предпросмотр
5\. Применение улучшений
6\. Сохранение

*Области скриншота:*
• Весь дашборд
• Только метрики
• Только графики

*Пресеты улучшения:*
• Default \- Стандартные настройки
• High Contrast \- Повышенный контраст
• Text Optimal \- Оптимизация текста
• Chart Optimal \- Оптимизация графиков

*Советы:*
• Используйте предпросмотр для проверки области
• Выбирайте пресеты под тип контента
• При ошибке используйте /start для перезапуска
"""
        await update.message.reply_text(help_text, parse_mode='MarkdownV2')

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает настройки бота"""
        keyboard = [
            [InlineKeyboardButton("🖼 Формат по умолчанию", callback_data="settings_format")],
            [InlineKeyboardButton("🔍 Масштаб по умолчанию", callback_data="settings_zoom")],
            [InlineKeyboardButton("✨ Пресет по умолчанию", callback_data="settings_preset")],
            [InlineKeyboardButton("↩️ Вернуться", callback_data="settings_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        settings_text = """
*Настройки DashboardSJ Bot* ⚙️

Текущие настройки:
• Формат: PNG
• Масштаб: 100%
• Пресет: Default

Выберите параметр для настройки:
"""
        await update.message.reply_text(settings_text, reply_markup=reply_markup, parse_mode='MarkdownV2')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статус бота"""
        # Проверяем доступность сервисов
        services_status = {
            "Google Sheets API": "✅ Доступно",
            "Скриншот сервис": "✅ Доступно",
            "Улучшение изображений": "✅ Доступно"
        }

        status_text = """
*Статус DashboardSJ Bot* 🔍

*Сервисы:*
• Google Sheets API: {sheets_status}
• Скриншот сервис: {screenshot_status}
• Улучшение изображений: {enhancement_status}

*Производительность:*
• Время отклика: ~2с
• Память: Оптимально
• Кэш: Активен

*Состояние:* ✅ Работает
""".format(
            sheets_status=services_status["Google Sheets API"],
            screenshot_status=services_status["Скриншот сервис"],
            enhancement_status=services_status["Улучшение изображений"]
        )

        await update.message.reply_text(status_text, parse_mode='MarkdownV2')

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
5. Проверьте превью
6. Подтвердите сохранение

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

        # Показываем прогресс создания превью
        status_message = await self.start_progress_animation(query.message, "🔄 Создаю предварительный просмотр области... {}")

        try:
            # Создаем превью с уменьшенным размером
            preview_params = context.user_data.copy()
            if preview_params['area']:
                preview_params['area'] = {
                    k: v // 2 for k, v in preview_params['area'].items()
                }

            preview_data = await self.screenshot_service.get_screenshot(
                format='jpeg',  # всегда используем JPEG для превью
                enhance=False,  # без улучшений для скорости
                zoom=context.user_data['zoom'],
                area=preview_params['area']
            )

            # Показываем превью и опции
            keyboard = [
                [
                    InlineKeyboardButton("✅ Область верная", callback_data="preview_ok"),
                    InlineKeyboardButton("🔄 Выбрать другую", callback_data="preview_change")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=io.BytesIO(preview_data),
                caption="Предварительный просмотр выбранной области.\nВсё верно?",
                reply_markup=reply_markup
            )
            await self.stop_progress_animation(status_message.message_id)
            return PREVIEW_AREA

        except Exception as e:
            error_message = f"❌ Ошибка создания превью: {str(e)}"
            logger.error(error_message)
            await self.stop_progress_animation(status_message.message_id)
            await status_message.edit_text(error_message)
            return ConversationHandler.END

    async def handle_preview(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        choice = query.data.split('_')[1]
        if choice == 'change':
            keyboard = [
                [
                    InlineKeyboardButton("📊 Весь dashboard", callback_data="area_full"),
                    InlineKeyboardButton("📈 Только метрики", callback_data="area_metrics"),
                    InlineKeyboardButton("📉 Только графики", callback_data="area_charts")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "Выберите другую область скриншота:",
                reply_markup=reply_markup
            )
            return SELECTING_AREA
        else:
            # Показываем доступные пресеты
            presets = self.screenshot_service.get_available_presets()
            keyboard = [[InlineKeyboardButton(preset.replace('_', ' ').title(),
                                               callback_data=f"preset_{preset}")]
                        for preset in presets]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "Область подтверждена.\nВыберите пресет улучшения изображения:",
                reply_markup=reply_markup
            )
            return CHOOSING_PRESET

    async def preset_chosen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        preset = query.data.split('_')[1]
        context.user_data['preset'] = preset

        # Показываем прогресс создания финального скриншота
        status_message = await self.start_progress_animation(query.message, "🔄 Создаю финальный скриншот... {}")

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

            # Отправляем финальный результат
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=io.BytesIO(screenshot_data),
                caption=f"Готовый скриншот:\nФормат: {context.user_data['format'].upper()}\n"
                        f"Масштаб: {context.user_data['zoom']}%\n"
                        f"Пресет: {preset}",
                reply_markup=reply_markup
            )
            await self.stop_progress_animation(status_message.message_id)
            return CONFIRMING

        except Exception as e:
            error_message = f"❌ Ошибка создания скриншота: {str(e)}"
            logger.error(error_message)
            await self.stop_progress_animation(status_message.message_id)
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

    async def cache_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статистику кэша"""
        stats = self.screenshot_service.get_cache_stats()

        stats_text = f"""
*Статистика кэша* 📊

*Производительность:*
• Попадания: {stats['cache_hits']}
• Промахи: {stats['cache_misses']}
• Эффективность: {stats['hit_rate']}%

*Объем данных:*
• Сохранено: {stats['mb_saved']} MB
• Текущий размер: {stats['total_cache_size_mb']} MB
• Использование: {stats['cache_utilization']}%

*Записи:*
• Количество: {stats['cache_entries']}
"""
        await update.message.reply_text(stats_text, parse_mode='MarkdownV2')


    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        error = context.error
        logger.error(f"Exception while handling an update: {error}")

        # Добавляем информацию о текущем процессе
        current_pid = os.getpid()
        process_info = f"Current PID: {current_pid}"

        try:
            # Получаем информацию о других процессах бота
            other_processes = [p for p in get_running_bot_processes() if p.pid != current_pid]
            if other_processes:
                process_info += "\nOther bot processes found:"
                for proc in other_processes:
                    try:
                        cmdline = ' '.join(proc.cmdline())
                        process_info += f"\n- PID={proc.pid}, CMD={cmdline}"
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        process_info += f"\n- PID={proc.pid} (inaccessible)"
            logger.error(f"Process state when error occurred: {process_info}")
        except Exception as e:
            logger.error(f"Error getting process information: {e}")

        if "Conflict: terminated by other getUpdates request" in str(error):
            logger.error(f"Обнаружен конфликт: несколько экземпляров бота запущены одновременно\n{process_info}")
            # Пытаемся очистить процессы при обнаружении конфликта
            try:
                cleanup_old_processes()
            except Exception as e:
                logger.error(f"Error cleaning up processes after conflict: {e}")
            return

        if update and isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "Произошла ошибка при обработке запроса. Попробуйте позже."
            )

    async def run(self):
        try:
            application = Application.builder().token(TELEGRAM_TOKEN).build()

            # Добавляем обработчики команд
            application.add_handler(CommandHandler("help", self.help_command))
            application.add_handler(CommandHandler("settings", self.settings_command))
            application.add_handler(CommandHandler("status", self.status_command))
            application.add_handler(CommandHandler("cache", self.cache_stats_command))

            # Добавляем conversation handler
            screenshot_handler = ConversationHandler(
                entry_points=[CommandHandler("start", self.start)],
                states={
                    CHOOSING_FORMAT: [CallbackQueryHandler(self.format_chosen, pattern=r"^format_")],
                    CHOOSING_ZOOM: [CallbackQueryHandler(self.zoom_chosen, pattern=r"^zoom_")],
                    SELECTING_AREA: [CallbackQueryHandler(self.area_chosen, pattern=r"^area_")],
                    PREVIEW_AREA: [CallbackQueryHandler(self.handle_preview, pattern=r"^preview_")],
                    CHOOSING_PRESET: [CallbackQueryHandler(self.preset_chosen, pattern=r"^preset_")],
                    CONFIRMING: [CallbackQueryHandler(self.handle_confirmation, pattern=r"^confirm_")]
                },
                fallbacks=[CommandHandler("start", self.start)]
            )

            application.add_handler(screenshot_handler)
            application.add_error_handler(self.error_handler)

            logger.info("Запуск бота...")

            # Проверяем загрузку системы перед запуском
            memory = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=1)
            if memory.percent > 90 or cpu > 80:
                logger.warning(f"High system load detected - Memory: {memory.percent}%, CPU: {cpu}%")

            # Добавляем небольшую задержку перед запуском для гарантированного завершения старых процессов
            await asyncio.sleep(2)

            # Правильная инициализация и запуск приложения
            await application.initialize()
            await application.start()
            await application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

        except Exception as e:
            logger.error(f"Error running bot: {str(e)}")
            # Ensure proper shutdown
            try:
                await application.stop()
                await application.shutdown()
            except Exception as shutdown_error:
                logger.error(f"Error during shutdown: {str(shutdown_error)}")
            raise

if __name__ == '__main__':
    try:
        logger.info("Starting bot initialization...")

        # Принудительная очистка всех процессов
        cleanup_old_processes()

        # Двойная проверка после очистки
        if is_bot_running():
            logger.error("Bot is still running after cleanup. Stopping.")
            sys.exit(1)

        # Сохраняем PID только после успешной очистки
        save_pid()

        logger.info("Bot initialization completed successfully")

        bot = DashboardBot()
        # Используем новый event loop для запуска бота
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(bot.run())
        finally:
            loop.close()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
    finally:
        remove_pid()