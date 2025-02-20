import asyncio
import json
import requests
import os
from services.screenshot import ScreenshotService
from utils.logger import logger

async def test_screenshot():
    try:
        screenshot_service = ScreenshotService()
        test_url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

        logger.info("Starting screenshot test with APIFlash...")
        logger.info(f"Using test URL: {test_url}")

        # Log the API key length for verification
        api_key = screenshot_service.api_key
        logger.info(f"API Key length: {len(api_key)}")
        logger.info(f"Using base URL: {screenshot_service.base_url}")

        # Test API key validation with minimal parameters
        params = {
            "access_key": api_key,
            "url": "https://example.com",
            "format": "png"
        }

        # Make a test request
        logger.info("Making test request to APIFlash...")
        logger.info(f"Request parameters: {params}")

        response = requests.get(screenshot_service.base_url, params=params)
        logger.info(f"Test request status code: {response.status_code}")
        logger.info(f"Test request headers: {dict(response.headers)}")

        if response.status_code != 200:
            error_text = response.text[:1000] if len(response.text) > 1000 else response.text
            try:
                error_json = json.loads(error_text)
                logger.error(f"APIFlash detailed error: {json.dumps(error_json, indent=2)}")
            except:
                logger.error(f"APIFlash error response: {error_text}")
            raise Exception(f"APIFlash error: {response.status_code} - {error_text}")

        # If we get here, try the full screenshot
        logger.info("Test request successful, attempting full screenshot...")
        screenshot_data = await screenshot_service.get_screenshot(
            url=test_url,
            format="png",
            enhance=True,
            zoom=100
        )

        # Save the screenshot to verify it worked
        with open("test_screenshot.png", "wb") as f:
            f.write(screenshot_data)

        logger.info("Screenshot test completed successfully - saved as test_screenshot.png")
        print("Screenshot test completed successfully!")
        return True

    except Exception as e:
        error_msg = f"Screenshot test failed: {str(e)}"
        logger.error(error_msg)
        print(error_msg)
        return False

if __name__ == "__main__":
    asyncio.run(test_screenshot())