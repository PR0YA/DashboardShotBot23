import aiohttp
import logging
from typing import Optional, Dict
from config import (
    APIFLASH_KEY,
    APIFLASH_URL,
    SPREADSHEET_URL,
    SCREENSHOT_WIDTH,
    SCREENSHOT_HEIGHT,
    SCREENSHOT_QUALITY
)

logger = logging.getLogger(__name__)

class ScreenshotService:
    def __init__(self):
        self.formats = ['png', 'jpeg', 'webp']
        self._default_params = {
            'width': str(SCREENSHOT_WIDTH),
            'height': str(SCREENSHOT_HEIGHT),
            'quality': str(SCREENSHOT_QUALITY),
            'full_page': 'true'
        }

    async def get_screenshot(self, format: str = 'png') -> Optional[bytes]:
        """Асинхронное получение скриншота"""
        try:
            if format not in self.formats:
                raise ValueError(f"Unsupported format: {format}")

            params = {
                'access_key': APIFLASH_KEY,
                'url': SPREADSHEET_URL,
                'format': format,
                **self._default_params
            }

            logger.info(f"Making APIFlash request for format: {format}")

            async with aiohttp.ClientSession() as session:
                async with session.get(APIFLASH_URL, params=params) as response:
                    if response.status != 200:
                        logger.error(f"APIFlash error: {response.status}")
                        return None

                    return await response.read()

        except Exception as e:
            logger.error(f"Error in screenshot service: {e}")
            return None

    def get_format_options(self) -> Dict[str, str]:
        """Возвращает словарь доступных форматов с описаниями"""
        return {
            'png': 'PNG - Высокое качество, с прозрачностью',
            'jpeg': 'JPEG - Компактный размер',
            'webp': 'WebP - Современный формат'
        }

ScreenshotService.default_presets = {
    'default': {'clipLimit': 0.8, 'sharpness': 3.4},
    'high_contrast': {'clipLimit': 1.2, 'sharpness': 3.8},
    'text_optimal': {'clipLimit': 0.6, 'sharpness': 4.0},
    'chart_optimal': {'clipLimit': 1.0, 'sharpness': 3.0}
}