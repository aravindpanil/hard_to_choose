import gspread
from oauth2client.service_account import ServiceAccountCredentials


def import_xbox_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

    creds = ServiceAccountCredentials.from_json_keyfile_name("pygsheet-1faf6d690009.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1kspw-4paT-eE5-mrCrc4R9tg70lH2ZTFrJOUmOtOytg").sheet1
    data = sheet.get_all_values()
    headers = data.pop(0)
    return data, headers
