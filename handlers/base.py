from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode

from services.screenshot import ScreenshotService
from services.image_enhancer import ImageEnhancer
import logging

logger = logging.getLogger(__name__)

router = Router()
screenshot_service = ScreenshotService()
image_enhancer = ImageEnhancer()

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "*Добро пожаловать в Screenshot Bot\!*\n\n"
        "Я помогу создать качественные скриншоты Google Sheets\.\n\n"
        "*Доступные команды:*\n"
        "📸 /screenshot \- Создать скриншот\n"
        "🖼 /format \- Выбрать формат\n"
        "❓ /help \- Помощь",
        parse_mode=ParseMode.MARKDOWN_V2
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    await message.answer(
        "*Справка по использованию бота*\n\n"
        "*Основные команды:*\n"
        "• /start \- Начало работы\n"
        "• /screenshot \- Создать скриншот\n"
        "• /format \- Выбрать формат\n\n"
        "*Форматы:*\n"
        "• PNG \- Высокое качество\n"
        "• JPEG \- Компактный размер\n"
        "• WebP \- Современный формат",
        parse_mode=ParseMode.MARKDOWN_V2
    )

@router.message(Command("format"))
async def cmd_format(message: Message):
    """Обработчик выбора формата"""
    keyboard = InlineKeyboardBuilder()
    formats = {
        'png': 'PNG - Высокое качество',
        'jpeg': 'JPEG - Компактный размер',
        'webp': 'WebP - Современный формат'
    }

    for fmt, desc in formats.items():
        keyboard.button(text=desc, callback_data=f"format_{fmt}")
    keyboard.adjust(1)

    await message.answer(
        "*Выберите формат изображения:*",
        reply_markup=keyboard.as_markup(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

@router.callback_query(lambda c: c.data.startswith("format_"))
async def process_format_selection(callback: CallbackQuery):
    """Обработчик выбора формата"""
    format_type = callback.data.split("_")[1]
    await callback.answer(f"Выбран формат: {format_type.upper()}")
    await callback.message.edit_text(
        f"Формат *{format_type\.upper()}* выбран\!\n"
        "Используйте /screenshot для создания скриншота",
        parse_mode=ParseMode.MARKDOWN_V2
    )

@router.message(Command("screenshot"))
async def cmd_screenshot(message: Message):
    """Обработчик создания скриншота"""
    # Отправляем сообщение о начале процесса
    status_msg = await message.answer(
        "*Создаю скриншот\.\.\.*\n"
        "Пожалуйста, подождите",
        parse_mode=ParseMode.MARKDOWN_V2
    )

    try:
        # Получаем скриншот
        screenshot_data = await screenshot_service.get_screenshot()

        if not screenshot_data:
            await message.answer(
                "❌ *Ошибка при создании скриншота*\n"
                "Попробуйте позже",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

        # Создаем клавиатуру для улучшения
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✨ Улучшить изображение", callback_data="enhance")

        # Отправляем скриншот
        await message.answer_document(
            document=screenshot_data,
            filename="screenshot.png",
            caption=(
                "✅ *Скриншот готов\!*\n\n"
                "*Параметры:*\n"
                "• Разрешение: 2440x2000\n"
                "• Качество: 100%\n"
                "• Режим: Полная страница"
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard.as_markup()
        )

    except Exception as e:
        logger.error(f"Error creating screenshot: {e}")
        await message.answer(
            "❌ *Произошла ошибка*\n"
            "Попробуйте позже",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    finally:
        await status_msg.delete()

@router.callback_query(F.data == "enhance")
async def process_enhancement(callback: CallbackQuery):
    """Обработчик улучшения изображения"""
    try:
        await callback.message.edit_text(
            "*Улучшаю изображение\.\.\.*",
            parse_mode=ParseMode.MARKDOWN_V2
        )

        # Получаем файл
        if not callback.message.document:
            await callback.message.edit_text(
                "❌ *Ошибка: изображение не найдено*",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

        file = await callback.bot.get_file(callback.message.document.file_id)
        file_content = await callback.bot.download_file(file.file_path)

        # Улучшаем изображение
        enhanced_data = await image_enhancer.enhance_screenshot(
            file_content.read(),
            clip_limit=1.2,
            sharpness=3.8
        )

        # Отправляем улучшенное изображение
        await callback.message.answer_document(
            document=enhanced_data,
            filename="screenshot_enhanced.png",
            caption=(
                "✨ *Изображение улучшено\!*\n\n"
                "*Применённые улучшения:*\n"
                "• Повышенный контраст\n"
                "• Увеличенная резкость\n"
                "• Оптимизация цветов"
            ),
            parse_mode=ParseMode.MARKDOWN_V2
        )

    except Exception as e:
        logger.error(f"Error enhancing image: {e}")
        await callback.message.edit_text(
            "❌ *Ошибка при улучшении изображения*",
            parse_mode=ParseMode.MARKDOWN_V2
        )