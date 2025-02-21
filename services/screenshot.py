import aiohttp
import asyncio
from config import APIFLASH_KEY, APIFLASH_URL, SPREADSHEET_ID
from utils.logger import logger
from urllib.parse import quote
from services.image_enhancer import ImageEnhancer
from services.cache_manager import CacheManager
import hashlib
import json

class ScreenshotService:
    def __init__(self):
        self.image_enhancer = ImageEnhancer()
        self.cache_manager = CacheManager(cache_dir="cache", max_size_mb=500)
        self.default_presets = {
            'default': {'clipLimit': 0.8, 'sharpness': 3.4},
            'high_contrast': {'clipLimit': 1.2, 'sharpness': 3.8},
            'text_optimal': {'clipLimit': 0.6, 'sharpness': 4.0},
            'chart_optimal': {'clipLimit': 1.0, 'sharpness': 3.0}
        }

    def _generate_cache_key(self, params: dict) -> str:
        """Генерирует уникальный ключ для кэширования"""
        params_str = json.dumps(params, sort_keys=True)
        return hashlib.sha256(params_str.encode()).hexdigest()

    async def get_screenshot(self, format='jpeg', enhance=False, zoom=100, 
                           area=None, preset='default', use_cache=True):
        """
        Get a screenshot with specified parameters and caching

        Args:
            format (str): Output format (jpeg, png, webp)
            enhance (bool): Whether to apply image enhancement
            zoom (int): Zoom level (50-200)
            area (dict): Area to capture {x, y, width, height} or None for full page
            preset (str): Enhancement preset name
            use_cache (bool): Whether to use caching
        """
        try:
            if not APIFLASH_KEY:
                raise ValueError("APIFlash key is not configured")

            # Параметры для кэширования
            cache_params = {
                'format': format,
                'enhance': enhance,
                'zoom': zoom,
                'area': area,
                'preset': preset
            }

            # Проверяем кэш, если включено использование кэша
            if use_cache:
                cached_data = await self.cache_manager.get_cached_screenshot(cache_params, format)
                if cached_data:
                    logger.info("Using cached screenshot")
                    return cached_data

            # Формируем URL с правильным gid
            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit?gid=2045841507#gid=2045841507"
            logger.info(f"Getting screenshot for spreadsheet in {format.upper()} format")

            # Кодируем URL Google Sheets
            encoded_url = quote(spreadsheet_url)

            # Базовые параметры запроса
            params = {
                'access_key': APIFLASH_KEY,
                'url': encoded_url,
                'format': format,
                'quality': '100',
                'full_page': 'true' if not area else 'false',
                'zoom': str(zoom)
            }

            # Оптимизация размера для превью
            if not enhance and area:
                area = {k: v // 2 if isinstance(v, int) else v for k, v in area.items()}

            # Добавляем параметры области, если указаны
            if area:
                params.update({
                    'x': str(area['x']),
                    'y': str(area['y']),
                    'width': str(area['width']),
                    'height': str(area['height'])
                })
            else:
                params.update({
                    'width': '2440',
                    'height': '2000'
                })

            try:
                logger.info(f"Sending request to APIFlash with parameters: {str({k: v for k, v in params.items() if k != 'access_key'})}")

                async with aiohttp.ClientSession() as session:
                    # Формируем полный URL с параметрами
                    query_params = "&".join([f"{k}={v}" for k, v in params.items()])
                    request_url = f"{APIFLASH_URL}?{query_params}"

                    async with session.get(request_url) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"APIFlash error: {error_text}")
                            raise Exception(f"Failed to get screenshot: {response.status}")

                        logger.info(f"Successfully received {format.upper()} screenshot from APIFlash")
                        screenshot_data = await response.read()

                        # Apply enhancement if requested
                        if enhance:
                            logger.info(f"Applying enhancement preset: {preset}")
                            preset_params = self.default_presets.get(preset, self.default_presets['default'])
                            screenshot_data = self.image_enhancer.enhance_screenshot(
                                screenshot_data, 
                                preset_params['clipLimit'],
                                preset_params['sharpness']
                            )
                            logger.info("Enhancement completed")

                        # Кэшируем результат, если включено использование кэша
                        if use_cache:
                            await self.cache_manager.cache_screenshot(cache_params, format, screenshot_data)

                        return screenshot_data

            except Exception as e:
                logger.error(f"Screenshot service error: {str(e)}")
                raise

        except Exception as e:
            logger.error(f"Screenshot service error: {str(e)}")
            raise

    def get_available_presets(self):
        """Returns list of available enhancement presets"""
        return list(self.default_presets.keys())

    def get_cache_stats(self):
        """Returns cache statistics"""
        return self.cache_manager.get_stats()