import logging
from telegram import Update, Chat, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from services.screenshot import ScreenshotService
from services.image_enhancer import ImageEnhancer
from config import TELEGRAM_TOKEN

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация сервисов
screenshot_service = ScreenshotService()
image_enhancer = ImageEnhancer()

# Форматы изображений и их описания
IMAGE_FORMATS = {
    'png': 'PNG - Высокое качество, с прозрачностью',
    'jpeg': 'JPEG - Компактный размер',
    'webp': 'WebP - Современный формат'
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🎯 *Добро пожаловать в Dashboard Screenshot Bot!*\n\n"
        "Я помогу вам создавать качественные скриншоты Google Sheets таблиц.\n\n"
        "Доступные команды:\n"
        "/screenshot - Создать скриншот\n"
        "/formats - Выбрать формат изображения\n"
        "/help - Показать справку\n\n"
        "Используйте кнопки меню для удобной навигации.",
        parse_mode='MarkdownV2'
    )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    await update.message.reply_text(
        "📋 *Справка по использованию бота*\n\n"
        "*Основные команды:*\n"
        "🔸 /start - Начало работы\n"
        "🔸 /screenshot - Создание скриншота\n"
        "🔸 /formats - Выбор формата изображения\n\n"
        "*Параметры скриншота:*\n"
        "• Разрешение: 2440x2000\n"
        "• Качество: 100%\n"
        "• Захват: Полная страница\n\n"
        "*Форматы изображений:*\n"
        "• PNG - Высокое качество\n"
        "• JPEG - Компактный размер\n"
        "• WebP - Современный формат",
        parse_mode='MarkdownV2'
    )

async def formats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /formats - показывает доступные форматы"""
    keyboard = [[
        InlineKeyboardButton(desc, callback_data=f"format_{fmt}")
        for fmt, desc in IMAGE_FORMATS.items()
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🖼 *Выберите формат изображения:*",
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )

async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /screenshot"""
    try:
        # Сообщаем о начале процесса
        processing_message = await update.message.reply_text(
            "🔄 *Создаю скриншот...*\n"
            "⏳ Пожалуйста, подождите",
            parse_mode='MarkdownV2'
        )

        # Получаем скриншот
        format_type = context.user_data.get('format', 'png')
        screenshot_data = screenshot_service.get_screenshot(
            format=format_type,
            quality=100
        )

        if screenshot_data:
            # Создаем клавиатуру для улучшения изображения
            keyboard = [
                [InlineKeyboardButton("✨ Улучшить изображение", callback_data="enhance")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Отправляем скриншот
            await update.message.reply_document(
                document=screenshot_data,
                filename=f'screenshot.{format_type}',
                caption=(
                    "✅ *Скриншот готов!*\n\n"
                    "*Параметры:*\n"
                    "📏 Разрешение: 2440x2000\n"
                    "💯 Качество: 100%\n"
                    "📄 Режим: Полная страница\n\n"
                    "Нажмите кнопку ниже, чтобы улучшить изображение"
                ),
                parse_mode='MarkdownV2',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "❌ Произошла ошибка при создании скриншота.\n"
                "Пожалуйста, попробуйте позже.",
                parse_mode='MarkdownV2'
            )

        # Удаляем сообщение о процессе
        await processing_message.delete()

    except Exception as e:
        logger.error(f"Error in screenshot command: {str(e)}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке команды.\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode='MarkdownV2'
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()

    try:
        if query.data.startswith("format_"):
            # Обработка выбора формата
            format_type = query.data.split("_")[1]
            context.user_data['format'] = format_type
            await query.edit_message_text(
                f"✅ Формат {format_type.upper()} выбран!\n\n"
                "Используйте /screenshot для создания скриншота",
                parse_mode='MarkdownV2'
            )

        elif query.data == "enhance":
            # Улучшение изображения
            if not query.message.document:
                await query.edit_message_text(
                    "❌ Изображение не найдено.\n"
                    "Пожалуйста, создайте новый скриншот.",
                    parse_mode='MarkdownV2'
                )
                return

            await query.edit_message_text(
                "🔄 *Улучшаю изображение...*\n"
                "⏳ Пожалуйста, подождите",
                parse_mode='MarkdownV2'
            )

            # Получаем файл
            file = await context.bot.get_file(query.message.document.file_id)
            image_data = await file.download_as_bytearray()

            # Улучшаем изображение
            enhanced_data = image_enhancer.enhance_screenshot(
                bytes(image_data),
                clip_limit=1.2,  # Увеличенный контраст
                sharpness=3.8    # Повышенная резкость
            )

            # Отправляем улучшенное изображение
            await query.message.reply_document(
                document=enhanced_data,
                filename='screenshot_enhanced.png',
                caption=(
                    "✨ *Изображение улучшено!*\n\n"
                    "*Применённые улучшения:*\n"
                    "• Повышенный контраст\n"
                    "• Увеличенная резкость\n"
                    "• Подавление шума"
                ),
                parse_mode='MarkdownV2'
            )

    except Exception as e:
        logger.error(f"Error in button handler: {str(e)}")
        await query.edit_message_text(
            "❌ Произошла ошибка при обработке запроса.\n"
            "Пожалуйста, попробуйте снова.",
            parse_mode='MarkdownV2'
        )

async def main() -> None:
    """Запуск бота"""
    try:
        # Создаем приложение
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help))
        application.add_handler(CommandHandler("formats", formats))
        application.add_handler(CommandHandler("screenshot", screenshot))

        # Добавляем обработчик кнопок
        application.add_handler(CallbackQueryHandler(button_handler))

        # Запускаем бота
        await application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        raise

if __name__ == '__main__':
    try:
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")