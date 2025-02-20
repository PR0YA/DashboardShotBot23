from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import SPREADSHEET_ID, SHEET_NAME, CREDENTIALS_FILE
from utils.logger import logger
from typing import Dict, List, Optional, Tuple
import re
from datetime import datetime, timedelta

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

    async def get_metrics(self, include_plan: bool = False) -> Dict[str, Dict[str, float]]:
        """
        Extracts metrics from the Google Sheet.
        Returns a dictionary with metric names and their values.

        Args:
            include_plan: If True, includes planned values for metrics
        """
        try:
            sheet = self.service.spreadsheets()
            # Get specific ranges where metrics are located
            ranges = [
                f'{SHEET_NAME}!B3',  # Фактическая выручка
                f'{SHEET_NAME}!C3',  # Конверсия
                f'{SHEET_NAME}!H3',  # Средний чек
                f'{SHEET_NAME}!A3',  # План выручки
            ]

            result = sheet.values().batchGet(
                spreadsheetId=SPREADSHEET_ID,
                ranges=ranges
            ).execute()

            metrics = {}
            metric_names = ['revenue', 'conversion', 'average_check']

            for i, value_range in enumerate(result.get('valueRanges', [])):
                if i < 3:  # Actual metrics
                    values = value_range.get('values', [[0]])
                    try:
                        value_str = str(values[0][0]).replace(',', '.').strip('%').replace(' ', '')
                        # Skip header rows or non-numeric values
                        if not any(c.isdigit() for c in value_str):
                            value = 0.0
                        else:
                            value = float(value_str)
                            if '%' in str(values[0][0]):
                                value /= 100
                        metrics[metric_names[i]] = {'actual': value}
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Error parsing metric {metric_names[i]}: {e}")
                        metrics[metric_names[i]] = {'actual': 0.0}
                elif include_plan:  # Planned metrics
                    values = value_range.get('values', [[0]])
                    try:
                        value_str = str(values[0][0]).replace(',', '.').strip('%').replace(' ', '')
                        # Skip header rows or non-numeric values
                        if not any(c.isdigit() for c in value_str):
                            value = 0.0
                        else:
                            value = float(value_str)
                        metrics['revenue']['plan'] = value
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Error parsing planned revenue: {e}")
                        metrics['revenue']['plan'] = 0.0

            logger.info(f"Successfully extracted metrics: {metrics}")
            return metrics

        except Exception as e:
            logger.error(f"Error fetching metrics: {str(e)}")
            return {}

    async def get_historical_data(self, days: int = 7) -> Dict[str, List[Tuple[datetime, float]]]:
        """Get historical data for metrics over specified period"""
        try:
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f'{SHEET_NAME}!A2:H{2+days}'
            ).execute()

            values = result.get('values', [])
            historical_data = {
                'revenue': [],
                'conversion': [],
                'average_check': []
            }

            for row in values:
                try:
                    date = datetime.now() - timedelta(days=len(historical_data['revenue']))
                    if len(row) >= 8:
                        historical_data['revenue'].append(
                            (date, float(row[1].replace(',', '.').strip().replace(' ', '')))
                        )
                        historical_data['conversion'].append(
                            (date, float(row[2].replace(',', '.').strip('%')) / 100)
                        )
                        historical_data['average_check'].append(
                            (date, float(row[7].replace(',', '.').strip().replace(' ', '')))
                        )
                except (ValueError, IndexError) as e:
                    logger.warning(f"Error parsing historical data: {e}")
                    continue

            return historical_data

        except Exception as e:
            logger.error(f"Error fetching historical data: {str(e)}")
            return {
                'revenue': [],
                'conversion': [],
                'average_check': []
            }

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

            return 1, len(values)

        except HttpError as e:
            logger.error(f"Google Sheets API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error getting chart range: {str(e)}")
            raise