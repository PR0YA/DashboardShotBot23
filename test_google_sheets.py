from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import SPREADSHEET_ID, SHEET_NAME, CREDENTIALS_FILE, START_MARKER, END_MARKER

def test_google_sheets_connection():
    try:
        # Initialize credentials
        credentials = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        
        # Build service
        service = build('sheets', 'v4', credentials=credentials)
        
        # Test API call
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A:A'
        ).execute()
        
        values = result.get('values', [])
        if not values:
            print("No data found in the sheet")
            return False
            
        # Look for markers
        start_found = False
        end_found = False
        for row in values:
            if row and row[0].lower() == START_MARKER:
                start_found = True
                print(f"Found start marker at row {values.index(row) + 1}")
            elif row and row[0].lower() == END_MARKER:
                end_found = True
                print(f"Found end marker at row {values.index(row) + 1}")
        
        if start_found and end_found:
            print("Successfully connected to Google Sheets and found both markers!")
            return True
        else:
            print("Connected to Google Sheets but markers not found")
            return False
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return False

if __name__ == '__main__':
    test_google_sheets_connection()
