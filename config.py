import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логгирования
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Telegram Bot Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Google Sheets Configuration
SPREADSHEET_URL = os.getenv("SPREADSHEET_URL")

# APIFlash Configuration
APIFLASH_KEY = os.getenv("APIFLASH_KEY")
APIFLASH_URL = "https://api.apiflash.com/v1/urltoimage"

# Screenshot Configuration
SCREENSHOT_WIDTH = int(os.getenv("SCREENSHOT_WIDTH", 2440))
SCREENSHOT_HEIGHT = int(os.getenv("SCREENSHOT_HEIGHT", 2000))
SCREENSHOT_QUALITY = int(os.getenv("SCREENSHOT_QUALITY", 100))

# Проверка конфигурации
required_vars = {
    "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
    "APIFLASH_KEY": APIFLASH_KEY,
    "SPREADSHEET_URL": SPREADSHEET_URL
}

for var_name, var_value in required_vars.items():
    if not var_value:
        raise ValueError(f"Missing required configuration: {var_name}")

logger.info("Configuration loaded successfully")