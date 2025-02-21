from aiogram.fsm.state import State, StatesGroup

class ScreenshotDialog(StatesGroup):
    """Состояния диалога для создания скриншота"""
    choosing_format = State()  # Выбор формата изображения
    creating_screenshot = State()  # Создание скриншота
    enhancing_image = State()  # Улучшение изображения
