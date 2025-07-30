import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import os
import json

def read_google_sheet(sheet_name, worksheet_index=0):
    """
    Reads data from a Google Sheet and returns a pandas DataFrame.
    Uses google-auth instead of deprecated oauth2client.
    """
    try:
        # Get credentials from environment variable
        gsheets_cred_json = os.environ.get("GSHEETS_CREDENTIALS")
        if not gsheets_cred_json:
            raise ValueError("❌ GSHEETS_CREDENTIALS environment variable not found.")

        # Convert JSON string to dictionary
        creds_dict = json.loads(gsheets_cred_json)

        # Define required scopes
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        # Load credentials
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(credentials)

        print("✅ Connected to Google Sheets.")

        # Access sheet
        sheet = client.open(sheet_name)
        worksheet = sheet.get_worksheet(worksheet_index)
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)

        print(f"✅ Read {len(df)} rows from '{sheet_name}'.")

        return df

    except Exception as e:
        print("❌ Failed to read Google Sheet.")
        print(f"Error: {e}")
        return None

# For local testing
if __name__ == "__main__":
    SHEET_NAME = "coding_team_profiles"
    df = read_google_sheet(SHEET_NAME)

    if df is not None:
        print("\n📊 Data from sheet:")
        print(df)
