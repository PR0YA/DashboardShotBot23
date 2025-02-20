import aiohttp
import asyncio
from config import APIFLASH_KEY, APIFLASH_URL, SPREADSHEET_ID
from utils.logger import logger
from urllib.parse import quote
from services.image_enhancer import ImageEnhancer

class ScreenshotService:
    def __init__(self):
        self.cache = {}
        self.image_enhancer = ImageEnhancer()

    async def get_screenshot(self, format='jpeg', enhance=False):
        try:
            if not APIFLASH_KEY:
                raise ValueError("APIFlash key is not configured")

            # Формируем URL с правильным gid
            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit?gid=2045841507#gid=2045841507"

            logger.info(f"Getting screenshot for spreadsheet in {format.upper()} format")
            logger.info(f"Using spreadsheet URL: {spreadsheet_url}")

            # Кодируем URL Google Sheets
            encoded_url = quote(spreadsheet_url)

            # Базовые параметры запроса
            params = {
                'access_key': APIFLASH_KEY,
                'url': encoded_url,
                'width': '2440',
                'height': '2000',
                'full_page': 'true',
                'format': format,
                'quality': '100'  # Установка максимального качества
            }

            try:
                logger.info(f"Sending request to APIFlash for {format.upper()} format with parameters: {str({k: v for k, v in params.items() if k != 'access_key'})}")

                async with aiohttp.ClientSession() as session:
                    # Формируем полный URL с параметрами
                    query_params = "&".join([f"{k}={v}" for k, v in params.items()])
                    request_url = f"{APIFLASH_URL}?{query_params}"

                    # Логируем URL (скрывая ключ)
                    safe_url = request_url.replace(APIFLASH_KEY, "***")
                    logger.debug(f"Request URL (key hidden): {safe_url}")

                    async with session.get(request_url) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"APIFlash error: {error_text}")
                            logger.error(f"Response status: {response.status}")
                            logger.error(f"Response headers: {response.headers}")
                            raise Exception(f"Failed to get screenshot: {response.status}, Details: {error_text}")

                        logger.info(f"Successfully received {format.upper()} screenshot from APIFlash")
                        screenshot_data = await response.read()

                        # Apply AI enhancement if requested
                        if enhance:
                            logger.info("Applying AI enhancement to the screenshot")
                            screenshot_data = self.image_enhancer.enhance_screenshot(screenshot_data)
                            logger.info("AI enhancement completed")

                        return screenshot_data

            except Exception as e:
                logger.error(f"Screenshot service error: {str(e)}")
                raise

        except Exception as e:
            logger.error(f"Screenshot service error: {str(e)}")
            raise