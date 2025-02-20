from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import SPREADSHEET_ID, SHEET_NAME, CREDENTIALS_FILE
from utils.logger import logger

class GoogleSheetsService:
    def __init__(self):
        self.service = None
        self.setup_service()

    def setup_service(self):
        try:
            credentials = service_account.Credentials.from_service_account_file(
                CREDENTIALS_FILE,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("Google Sheets service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {str(e)}")
            raise

    async def get_chart_range(self):
        try:
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f'{SHEET_NAME}!A:A'
            ).execute()

            values = result.get('values', [])
            if not values:
                raise ValueError("No data found in the sheet")

            return 1, len(values)  # Возвращаем весь диапазон листа

        except HttpError as e:
            logger.error(f"Google Sheets API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error getting chart range: {str(e)}")
            raise