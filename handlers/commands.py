import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from states.dialog import ScreenshotDialog
from keyboards.inline import KeyboardFactory
from services.screenshot import ScreenshotService
from services.image_enhancer import ImageEnhancer

logger = logging.getLogger(__name__)
router = Router()
screenshot_service = ScreenshotService()
image_enhancer = ImageEnhancer()

# Форматы изображений и их описания
IMAGE_FORMATS = {
    'png': 'PNG - Высокое качество, с прозрачностью',
    'jpeg': 'JPEG - Компактный размер',
    'webp': 'WebP - Современный формат'
}

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    logger.info(f"User {message.from_user.id} started the bot")
    await message.answer(
        "🎯 *Добро пожаловать в Dashboard Screenshot Bot!*\n\n"
        "Я помогу вам создавать качественные скриншоты Google Sheets таблиц.\n\n"
        "Доступные команды:\n"
        "/screenshot - Создать скриншот\n"
        "/formats - Выбрать формат изображения\n"
        "/help - Показать справку\n\n"
        "Используйте кнопки меню для удобной навигации.",
        parse_mode=ParseMode.MARKDOWN_V2
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    logger.info(f"User {message.from_user.id} requested help")
    await message.answer(
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
        parse_mode=ParseMode.MARKDOWN_V2
    )

@router.message(Command("formats"))
async def cmd_formats(message: Message, state: FSMContext):
    """Обработчик команды /formats"""
    logger.info(f"User {message.from_user.id} requested format selection")
    keyboard = KeyboardFactory.format_selection(IMAGE_FORMATS)
    await message.answer(
        "🖼 *Выберите формат изображения:*",
        reply_markup=keyboard.as_markup(),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    await state.set_state(ScreenshotDialog.choosing_format)

@router.message(Command("screenshot"))
async def cmd_screenshot(message: Message, state: FSMContext):
    """Обработчик команды /screenshot"""
    # Получаем данные о формате из состояния
    data = await state.get_data()
    format_type = data.get('format', 'png')

    logger.info(f"User {message.from_user.id} requested screenshot in format: {format_type}")

    try:
        # Сообщаем о начале процесса
        processing_message = await message.answer(
            "🔄 *Создаю скриншот...*\n"
            "⏳ Пожалуйста, подождите",
            parse_mode=ParseMode.MARKDOWN_V2
        )

        # Получаем скриншот
        screenshot_data = screenshot_service.get_screenshot(
            format=format_type,
            quality=100
        )

        if screenshot_data:
            # Создаем клавиатуру для улучшения изображения
            keyboard = KeyboardFactory.enhancement_keyboard()

            # Отправляем скриншот
            await message.answer_document(
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
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard.as_markup()
            )
            await state.set_state(ScreenshotDialog.enhancing_image)
            logger.info(f"Screenshot successfully created and sent to user {message.from_user.id}")
        else:
            logger.error(f"Failed to create screenshot for user {message.from_user.id}")
            await message.answer(
                "❌ Произошла ошибка при создании скриншота.\n"
                "Пожалуйста, попробуйте позже.",
                parse_mode=ParseMode.MARKDOWN_V2
            )

        # Удаляем сообщение о процессе
        await processing_message.delete()

    except Exception as e:
        logger.error(f"Error in screenshot command for user {message.from_user.id}: {str(e)}")
        await message.answer(
            "❌ Произошла ошибка при обработке команды.\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.MARKDOWN_V2
        )