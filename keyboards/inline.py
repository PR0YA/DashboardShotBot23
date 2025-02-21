from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Dict

class KeyboardFactory:
    """Фабрика клавиатур для бота"""
    
    @staticmethod
    def format_selection(formats: Dict[str, str]) -> InlineKeyboardBuilder:
        """Создает клавиатуру для выбора формата изображения"""
        builder = InlineKeyboardBuilder()
        for fmt, desc in formats.items():
            builder.button(text=desc, callback_data=f"format_{fmt}")
        builder.adjust(1)
        return builder

    @staticmethod
    def enhancement_keyboard() -> InlineKeyboardBuilder:
        """Создает клавиатуру для улучшения изображения"""
        builder = InlineKeyboardBuilder()
        builder.button(text="✨ Улучшить изображение", callback_data="enhance")
        return builder
