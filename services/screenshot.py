import aiohttp
import asyncio
from config import PAGEPIXELS_KEY, PAGEPIXELS_URL, SPREADSHEET_ID
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
            'key': PAGEPIXELS_KEY,
            'url': spreadsheet_url,
            'width': 2440,
            'height': 2000,
            'format': 'jpg',
            'quality': 100,
            'wait_for': '.grid-container',  # Wait for Google Sheets grid to load
            'scroll_to': f'A{start_row}',
            'inject_css': '''
                body { overflow: visible !important; }
                .grid-container, .waffle {
                    visibility: visible !important;
                    display: block !important;
                }
                .waffle-embedded-object-overlay {
                    visibility: visible !important;
                    opacity: 1 !important;
                }
            ''',
            'wait_time': 5000,  # Wait 5 seconds for content to load
            'block_resources': ['analytics', 'advertising'],  # Block unnecessary resources
            'cache_ttl': 0  # Disable caching on PagePixels side
        }

        try:
            logger.info("Sending request to PagePixels")
            async with aiohttp.ClientSession() as session:
                async with session.get(PAGEPIXELS_URL, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"PagePixels error: {error_text}")
                        raise Exception(f"Failed to get screenshot: {response.status}")

                    logger.info("Successfully received screenshot from PagePixels")
                    screenshot_data = await response.read()

                    # Cache the result
                    self.cache[cache_key] = (asyncio.get_event_loop().time(), screenshot_data)

                    return screenshot_data

        except Exception as e:
            logger.error(f"Screenshot service error: {str(e)}")
            raise