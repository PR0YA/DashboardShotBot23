import os
import json
import asyncio
import aiohttp
from utils.logger import logger

async def test_simple_apiflash():
    api_key = os.getenv('APIFLASH_KEY')
    if not api_key:
        print("Error: APIFLASH_KEY environment variable is not set")
        return False

    base_url = "https://api.apiflash.com/v1/urltoimage"
    test_url = "https://docs.google.com/spreadsheets/d/1o_RhLTXTC2D-W55sBvbftUnyJDv8z4OnbXoP-4tr_04/edit?gid=2045841507#gid=2045841507"

    params = {
        "access_key": api_key,
        "url": test_url,
        "format": "jpeg",
        "width": 2440,
        "height": 2000,
        "full_page": "true",
        "delay": 3  # Since we're testing with Google Sheets
    }

    print(f"Using API key (last 4 chars: ...{api_key[-4:]})")
    print(f"Making request to: {base_url}")
    print(f"Using URL: {test_url}")
    print("Request parameters:")
    for key, value in params.items():
        if key != 'access_key':
            print(f"  {key}: {value}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=params) as response:
                print(f"\nResponse status code: {response.status}")
                print(f"Response headers: {dict(response.headers)}")

                if response.status != 200:
                    error_text = await response.text()
                    print(f"Error response content: {error_text}")
                    try:
                        error_json = json.loads(error_text)
                        print(f"Detailed error: {json.dumps(error_json, indent=2)}")
                    except:
                        pass
                    return False

                print("Request successful!")

                if response.headers.get('Content-Type', '').startswith('image/'):
                    content = await response.read()
                    with open('test_screenshot.jpeg', 'wb') as f:
                        f.write(content)
                    print("Screenshot saved as test_screenshot.jpeg")

                return True

    except Exception as e:
        print(f"Request failed with error: {str(e)}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_simple_apiflash())
    print(f"\nTest result: {'Success' if result else 'Failed'}")