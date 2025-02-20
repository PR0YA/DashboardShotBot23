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

        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"

        logger.info(f"Getting screenshot for rows {start_row} to {end_row}")
        logger.info(f"Using spreadsheet URL: {spreadsheet_url}")

        # Calculate height based on number of rows (assuming ~24px per row)
        row_count = end_row - start_row + 1
        height = max(2000, row_count * 24 + 200)  # Add padding for headers and margins

        params = {
            'apikey': PAGEPIXELS_KEY,
            'url': spreadsheet_url,
            'width': str(2440),
            'height': str(height),
            'format': 'jpeg',
            'quality': '100',
            'delay': '5',
            'selector': '.grid-container',
            'full_page': 'false',
            'scroll_to': f'A{start_row}',
            'css_inject': '''
                body { overflow: visible !important; }
                .grid-container, .waffle {
                    visibility: visible !important;
                    display: block !important;
                }
                .waffle-embedded-object-overlay {
                    visibility: visible !important;
                    opacity: 1 !important;
                }
            '''
        }

        try:
            logger.info("Sending request to PagePixels")
            logger.debug(f"Request parameters: {params}")

            async with aiohttp.ClientSession() as session:
                async with session.get(PAGEPIXELS_URL, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"PagePixels error: {error_text}")
                        logger.error(f"Response status: {response.status}")
                        logger.error(f"Response headers: {response.headers}")
                        raise Exception(f"Failed to get screenshot: {response.status}, Details: {error_text}")

                    logger.info("Successfully received screenshot from PagePixels")
                    screenshot_data = await response.read()

                    # Cache the result
                    self.cache[cache_key] = (asyncio.get_event_loop().time(), screenshot_data)

                    return screenshot_data

        except Exception as e:
            logger.error(f"Screenshot service error: {str(e)}")
            raise