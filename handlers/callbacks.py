import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from states.dialog import ScreenshotDialog
from services.image_enhancer import ImageEnhancer

logger = logging.getLogger(__name__)
router = Router()
image_enhancer = ImageEnhancer()

@router.callback_query(lambda c: c.data.startswith("format_"))
async def process_format_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора формата изображения"""
    try:
        format_type = callback.data.split("_")[1]
        logger.info(f"User {callback.from_user.id} selected format: {format_type}")

        # Сохраняем выбранный формат в состоянии
        await state.update_data(format=format_type)

        await callback.message.edit_text(
            f"✅ Формат {format_type.upper()} выбран!\n\n"
            "Используйте /screenshot для создания скриншота",
            parse_mode=ParseMode.MARKDOWN_V2
        )

        # Сбрасываем состояние
        await state.clear()
    except Exception as e:
        logger.error(f"Error in format selection: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при выборе формата.\n"
            "Пожалуйста, попробуйте снова.",
            parse_mode=ParseMode.MARKDOWN_V2
        )

@router.callback_query(F.data == "enhance")
async def process_enhancement(callback: CallbackQuery, state: FSMContext):
    """Обработчик улучшения изображения"""
    try:
        await callback.message.edit_text(
            "🔄 *Улучшаю изображение...*\n"
            "⏳ Пожалуйста, подождите",
            parse_mode=ParseMode.MARKDOWN_V2
        )

        # Получаем файл
        message = callback.message
        if not message.document:
            logger.warning(f"No document found in message for user {callback.from_user.id}")
            await callback.message.edit_text(
                "❌ Изображение не найдено.\n"
                "Пожалуйста, создайте новый скриншот.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

        file = await callback.bot.get_file(message.document.file_id)
        file_content = await callback.bot.download_file(file.file_path)

        logger.info(f"Enhancing image for user {callback.from_user.id}")
        # Улучшаем изображение
        enhanced_data = image_enhancer.enhance_screenshot(
            file_content.read(),
            clip_limit=1.2,  # Увеличенный контраст
            sharpness=3.8    # Повышенная резкость
        )

        # Отправляем улучшенное изображение
        await message.answer_document(
            document=enhanced_data,
            filename='screenshot_enhanced.png',
            caption=(
                "✨ *Изображение улучшено!*\n\n"
                "*Применённые улучшения:*\n"
                "• Повышенный контраст\n"
                "• Увеличенная резкость\n"
                "• Подавление шума"
            ),
            parse_mode=ParseMode.MARKDOWN_V2
        )

        # Сбрасываем состояние
        await state.clear()

    except Exception as e:
        logger.error(f"Error in enhancement process: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при обработке запроса.\n"
            "Пожалуйста, попробуйте снова.",
            parse_mode=ParseMode.MARKDOWN_V2
        )