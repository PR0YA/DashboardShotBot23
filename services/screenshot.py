import aiohttp
import asyncio
from config import APIFLASH_KEY, APIFLASH_URL, SPREADSHEET_ID
from utils.logger import logger

class ScreenshotService:
    def __init__(self):
        self.cache = {}

    async def get_screenshot(self, start_row=None, end_row=None):
        try:
            if not APIFLASH_KEY:
                raise ValueError("APIFlash key is not configured")

            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"

            logger.info(f"Getting screenshot for spreadsheet")
            logger.info(f"Using spreadsheet URL: {spreadsheet_url}")

            params = {
                'url': spreadsheet_url,
                'width': 2440,
                'height': 2000,
                'fresh': True,
                'full_page': True,
                'format': 'jpeg',
                'delay': 5000
            }

            try:
                logger.info("Sending request to APIFlash")
                logger.debug(f"Request URL: {APIFLASH_URL}")
                logger.debug(f"Request parameters: {params}")

                async with aiohttp.ClientSession() as session:
                    # Формируем URL с ключом доступа
                    request_url = f"{APIFLASH_URL}?access_key={APIFLASH_KEY}"
                    # Добавляем остальные параметры
                    for key, value in params.items():
                        request_url += f"&{key}={str(value).lower()}"

                    logger.debug(f"Sending request to: {request_url.replace(APIFLASH_KEY, '***')}")

                    async with session.get(request_url) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"APIFlash error: {error_text}")
                            logger.error(f"Response status: {response.status}")
                            logger.error(f"Response headers: {response.headers}")
                            raise Exception(f"Failed to get screenshot: {response.status}, Details: {error_text}")

                        logger.info("Successfully received screenshot from APIFlash")
                        screenshot_data = await response.read()
                        return screenshot_data

            except Exception as e:
                logger.error(f"Screenshot service error: {str(e)}")
                raise

        except Exception as e:
            logger.error(f"Screenshot service error: {str(e)}")
            raise