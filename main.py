import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from config import TELEGRAM_TOKEN, logger
from services.screenshot_service import ScreenshotService
from services.image_enhancer import ImageEnhancer
import io
import os
import signal
import sys
import psutil

# Инициализация сервисов
screenshot_service = ScreenshotService()
image_enhancer = ImageEnhancer()

def is_bot_already_running() -> bool:
    """Проверяет, запущен ли уже бот"""
    current_pid = os.getpid()

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.pid != current_pid and 'python' in proc.name().lower():
                cmdline = ' '.join(proc.cmdline())
                if 'main.py' in cmdline:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def cleanup_processes():
    """Очистка старых процессов бота"""
    if is_bot_already_running():
        logger.error("Another bot instance is already running")
        sys.exit(1)

    pid = str(os.getpid())
    with open('bot.pid', 'w') as f:
        f.write(pid)
    logger.info(f"Started new bot process with PID: {pid}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🎯 *Добро пожаловать в Dashboard Screenshot Bot\!*\n\n"
        "Я помогу вам создавать качественные скриншоты Google Sheets таблиц\.\n\n"
        "*Доступные команды:*\n"
        "📸 /screenshot \- Создать скриншот\n"
        "🖼 /format \- Выбрать формат изображения\n"
        "❓ /help \- Показать справку",
        parse_mode='MarkdownV2'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(
        "📋 *Справка по использованию бота*\n\n"
        "*Основные команды:*\n"
        "🔸 /start \- Начало работы\n"
        "🔸 /screenshot \- Создание скриншота\n"
        "🔸 /format \- Выбор формата изображения\n\n"
        "*Параметры скриншота:*\n"
        "• Разрешение: 2440x2000\n"
        "• Качество: 100%\n"
        "• Захват: Полная страница\n\n"
        "*Форматы изображений:*\n"
        "• PNG \- Высокое качество\n"
        "• JPEG \- Компактный размер\n"
        "• WebP \- Современный формат",
        parse_mode='MarkdownV2'
    )

async def format_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды выбора формата"""
    keyboard = []
    for fmt, desc in screenshot_service.get_format_options().items():
        keyboard.append([InlineKeyboardButton(desc, callback_data=f"format_{fmt}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "*Выберите формат изображения:*",
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )

async def handle_format_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора формата"""
    query = update.callback_query
    await query.answer()

    format_type = query.data.split('_')[1]
    context.user_data['format'] = format_type

    await query.edit_message_text(
        f"Формат *{format_type.upper()}* выбран\!\n"
        "Используйте /screenshot для создания скриншота",
        parse_mode='MarkdownV2'
    )

async def screenshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды создания скриншота"""
    format_type = context.user_data.get('format', 'png')

    # Отправляем сообщение о начале процесса
    message = await update.message.reply_text(
        "🔄 *Создаю скриншот\.\.\.* \n"
        "Пожалуйста, подождите",
        parse_mode='MarkdownV2'
    )

    try:
        # Получаем скриншот
        screenshot_data = await screenshot_service.get_screenshot(format_type)

        if not screenshot_data:
            await message.edit_text(
                "❌ *Ошибка при создании скриншота*\n"
                "Попробуйте позже",
                parse_mode='MarkdownV2'
            )
            return

        # Создаем кнопку для улучшения
        keyboard = [[InlineKeyboardButton("✨ Улучшить изображение", callback_data="enhance")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем файл
        await update.message.reply_document(
            document=io.BytesIO(screenshot_data),
            filename=f"screenshot.{format_type}",
            caption=(
                "✅ *Скриншот готов\!*\n\n"
                "*Параметры:*\n"
                f"• Формат: {format_type.upper()}\n"
                "• Разрешение: 2440x2000\n"
                "• Качество: 100%\n"
                "• Режим: Полная страница"
            ),
            parse_mode='MarkdownV2',
            reply_markup=reply_markup
        )

        await message.delete()

    except Exception as e:
        logger.error(f"Error creating screenshot: {e}")
        await message.edit_text(
            "❌ *Произошла ошибка*\n"
            "Попробуйте позже",
            parse_mode='MarkdownV2'
        )

async def handle_enhancement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик улучшения изображения"""
    query = update.callback_query
    await query.answer()

    try:
        # Получаем файл
        file_id = query.message.document.file_id
        file = await context.bot.get_file(file_id)
        file_data = await file.download_as_bytearray()

        # Улучшаем изображение
        enhanced_data = await image_enhancer.enhance_image(file_data)

        if not enhanced_data:
            await query.edit_message_text(
                "❌ *Ошибка при улучшении изображения*",
                parse_mode='MarkdownV2'
            )
            return

        # Отправляем улучшенное изображение
        await query.message.reply_document(
            document=io.BytesIO(enhanced_data),
            filename="screenshot_enhanced.png",
            caption=(
                "✨ *Изображение улучшено\!*\n\n"
                "*Применённые улучшения:*\n"
                "• Повышенный контраст\n"
                "• Увеличенная резкость\n"
                "• Оптимизация цветов"
            ),
            parse_mode='MarkdownV2'
        )

    except Exception as e:
        logger.error(f"Error enhancing image: {e}")
        await query.edit_message_text(
            "❌ *Ошибка при улучшении изображения*",
            parse_mode='MarkdownV2'
        )

def main():
    """Запуск бота"""
    try:
        # Очистка старых процессов
        cleanup_processes()

        # Создаем приложение
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("format", format_command))
        application.add_handler(CommandHandler("screenshot", screenshot_command))

        # Добавляем обработчики callback
        application.add_handler(CallbackQueryHandler(handle_format_selection, pattern="^format_"))
        application.add_handler(CallbackQueryHandler(handle_enhancement, pattern="^enhance$"))

        # Запускаем бота
        logger.info("Starting bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        if os.path.exists('bot.pid'):
            os.remove('bot.pid')
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        if os.path.exists('bot.pid'):
            os.remove('bot.pid')
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        if os.path.exists('bot.pid'):
            os.remove('bot.pid')