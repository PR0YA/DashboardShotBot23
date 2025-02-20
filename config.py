import os

# Telegram Configuration
TELEGRAM_TOKEN = "7770923655:AAHcyQiCKWSYKRB9JfxsD9wMSAutdyCz9NQ"

# Google Sheets Configuration
SPREADSHEET_ID = "1o_RhLTXTC2D-W55sBvbftUnyJDv8z4OnbXoP-4tr_04"
SHEET_NAME = "тестовая ре-визуализация"
CREDENTIALS_FILE = "attached_assets/ageless-welder-451507-k4-31eed6cef9d3.json"

# Screenshot Service Configuration
PAGEPIXELS_KEY = os.environ.get('PAGEPIXELS_API_KEY')
PAGEPIXELS_URL = "https://api.pagepixels.com/v1/snapshot"

# Marker Configuration
START_MARKER = "начало"
END_MARKER = "конец"

# Cache Configuration
CACHE_DURATION = 300  # 5 minutes in seconds