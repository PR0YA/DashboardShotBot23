import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def get_env_or_default(key: str, default: Optional[str] = None) -> str:
    """Get environment variable with logging"""
    value = os.getenv(key, default)
    if value is None:
        logger.warning(f"Environment variable {key} is not set")
        raise ValueError(f"Required environment variable {key} is not set")
    return value

# Telegram Configuration
TELEGRAM_TOKEN = "7770923655:AAHcyQiCKWSYKRB9JfxsD9wMSAutdyCz9NQ"

# Google Sheets Configuration
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1o_RhLTXTC2D-W55sBvbftUnyJDv8z4OnbXoP-4tr_04/edit?gid=2045841507#gid=2045841507"

# Screenshot Service Configuration
APIFLASH_KEY = "3e4126ce2c144fac974d1a91cba62de1"
APIFLASH_URL = "https://api.apiflash.com/v1/urltoimage"

# Image Enhancement Settings
DEFAULT_QUALITY = 100
DEFAULT_WIDTH = 2440
DEFAULT_HEIGHT = 2000

# Cache Configuration
CACHE_DURATION = 300  # 5 minutes in seconds

# Validate configuration
try:
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN is not configured")
    if not APIFLASH_KEY:
        raise ValueError("APIFLASH_KEY is not configured")
    if not SPREADSHEET_URL:
        raise ValueError("SPREADSHEET_URL is not configured")

    logger.info("Configuration loaded successfully")
except ValueError as e:
    logger.error(f"Configuration error: {str(e)}")
    raise