import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

def read_google_sheet(sheet_name, worksheet_index=0):
    """
    Reads data from a Google Sheet and returns a pandas DataFrame.
    """
    try:
        # Get credentials from environment variable
        gsheets_cred_json = os.environ.get("GSHEETS_CREDENTIALS")
        if not gsheets_cred_json:
            raise ValueError("❌ GSHEETS_CREDENTIALS environment variable not found.")

        # Load credentials from string (don't write to file)
        creds_dict = json.loads(gsheets_cred_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        print("✅ Successfully connected to Google Sheets API.")

        # Open the Google Sheet and read
        sheet = client.open(sheet_name)
        worksheet = sheet.get_worksheet(worksheet_index)
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)

        print(f"✅ Successfully read {len(df)} rows from '{sheet_name}'.")

        return df

    except Exception as e:
        print("❌ Failed to read Google Sheet.")
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    SHEET_NAME = "coding_team_profiles"
    df = read_google_sheet(SHEET_NAME)

    if df is not None:
        print("\n📊 Data from sheet:")
        print(df)
