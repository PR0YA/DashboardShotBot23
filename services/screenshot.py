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
        
        params = {
            'access_key': APIFLASH_KEY,
            'url': spreadsheet_url,
            'viewport': '1920x1080',
            'scroll_to': f'A{start_row}',
            'element': f'#sheet-container',
            'wait_until': 'networkidle0',
            'fresh': 'true'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(APIFLASH_URL, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"APIFlash error: {error_text}")
                        raise Exception(f"Failed to get screenshot: {response.status}")
                    
                    screenshot_data = await response.read()
                    
                    # Cache the result
                    self.cache[cache_key] = (asyncio.get_event_loop().time(), screenshot_data)
                    
                    return screenshot_data

        except Exception as e:
            logger.error(f"Screenshot service error: {str(e)}")
            raise
