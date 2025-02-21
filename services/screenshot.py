import requests
from config import APIFLASH_KEY, APIFLASH_URL, SPREADSHEET_URL
from typing import Optional, Dict, Any
import logging
import hashlib
import json

logger = logging.getLogger(__name__)

class ScreenshotService:
    def __init__(self):
        self.format_options = ['jpeg', 'png', 'webp']
        self._default_params = {
            'width': '2440',
            'height': '2000',
            'full_page': 'true',
            'quality': '100'
        }
        logger.info("ScreenshotService initialized with default parameters")

    def get_screenshot(self, format: str = 'png', quality: int = 100) -> Optional[bytes]:
        """
        Получает скриншот таблицы с заданными параметрами

        Args:
            format: Формат изображения (jpeg, png, webp)
            quality: Качество изображения (1-100)

        Returns:
            bytes: Данные изображения или None в случае ошибки
        """
        try:
            if format not in self.format_options:
                raise ValueError(f"Unsupported format: {format}")

            if not APIFLASH_KEY:
                raise ValueError("APIFlash key is not configured")

            params = {
                'access_key': APIFLASH_KEY,
                'url': SPREADSHEET_URL,
                'format': format,
                'quality': str(quality),
                **self._default_params
            }

            logger.info(f"Making APIFlash request for format: {format}, quality: {quality}")

            response = requests.get(APIFLASH_URL, params=params)
            if response.status_code != 200:
                logger.error(f"APIFlash error: Status {response.status_code}, Response: {response.text}")
                raise Exception(f"Failed to get screenshot: {response.status_code}")

            logger.info(f"Successfully received {format.upper()} screenshot")
            return response.content

        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return None
        except requests.RequestException as e:
            logger.error(f"Network error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in screenshot service: {str(e)}")
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