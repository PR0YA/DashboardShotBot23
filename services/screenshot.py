import aiohttp
import asyncio
from config import APIFLASH_KEY, APIFLASH_URL, SPREADSHEET_ID
from utils.logger import logger

class ScreenshotService:
    def __init__(self):
        self.cache = {}

    async def get_screenshot(self, start_row, end_row):
        cache_key = f"{start_row}_{end_row}"

        # Check cache
        if cache_key in self.cache:
            timestamp, screenshot = self.cache[cache_key]
            if (asyncio.get_event_loop().time() - timestamp) < 300:  # 5 minutes cache
                return screenshot

        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid=2045841507"

        logger.info(f"Getting screenshot for rows {start_row} to {end_row}")

        params = {
            'access_key': APIFLASH_KEY,
            'url': spreadsheet_url,
            'viewport': '3840x2160',  # Увеличили размер viewport еще больше
            'scroll_to': f'A{start_row}',
            'element': '.waffle',  # Изменили селектор на специфичный для Google Sheets
            'format': 'jpeg',
            'quality': '100',
            'fresh': 'true',
            'full_page': 'true',
            'delay': '5',  # Увеличили задержку до 5 секунд
            'margin': '100',  # Увеличили отступы
            'css': '.grid-container { zoom: 0.8; }' # Добавили масштабирование для лучшего обзора
        }

        try:
            logger.info("Sending request to APIFlash")
            async with aiohttp.ClientSession() as session:
                async with session.get(APIFLASH_URL, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"APIFlash error: {error_text}")
                        raise Exception(f"Failed to get screenshot: {response.status}")

                    logger.info("Successfully received screenshot from APIFlash")
                    screenshot_data = await response.read()

                    # Cache the result
                    self.cache[cache_key] = (asyncio.get_event_loop().time(), screenshot_data)

                    return screenshot_data

        except Exception as e:
            logger.error(f"Screenshot service error: {str(e)}")
            raise