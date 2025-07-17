import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

def read_google_sheet(sheet_name, worksheet_index=0):
    """
    Reads data from a Google Sheet and returns a pandas DataFrame.
    """
    try:
        # Define the scope
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]

        # Authorize the client
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)

        print("✅ Successfully connected to Google Sheets API.")

        # Open the Google Sheet
        sheet = client.open(sheet_name)

        # Select the worksheet (default first worksheet)
        worksheet = sheet.get_worksheet(worksheet_index)

        # Get all records as list of dicts
        records = worksheet.get_all_records()

        # Convert to pandas DataFrame
        df = pd.DataFrame(records)

        print(f"✅ Successfully read {len(df)} rows from '{sheet_name}'.")

        return df

    except Exception as e:
        print("❌ Failed to read Google Sheet.")
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    # Change this to your actual sheet name (visible on Google Sheets)
    SHEET_NAME = "coding_team_profiles"

    df = read_google_sheet(SHEET_NAME)

    if df is not None:
        print("\n📊 Data from sheet:")
        print(df)
