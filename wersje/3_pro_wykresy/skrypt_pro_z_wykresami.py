import os
import datetime
from garminconnect import Garmin
import gspread
from google.oauth2.service_account import Credentials as GoogleCreds
from googleapiclient.discovery import build

# === KONFIGURACJA ===
GARMIN_USER = "mpiekarska@gmail.com"
GARMIN_PASS = "4!aD5ETVFqo2FL"
SPREADSHEET_NAME = "Garmin Aktywnosci"

# === AUTORYZACJA GOOGLE SHEETS ===
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = GoogleCreds.from_service_account_file("credentials.json", scopes=SCOPES)
gc = gspread.authorize(creds)
service = build("sheets", "v4", credentials=creds)

# === AUTORYZACJA GARMIN ===
client = Garmin(GARMIN_USER, GARMIN_PASS)
client.login()
print("✅ Zalogowano do Garmin Connect")

# === OTWARCIE / UTWORZENIE ARKUSZA ===
try:
    ss = gc.open(SPREADSHEET_NAME)
except gspread.SpreadsheetNotFound:
    ss = gc.create(SPREADSHEET_NAME)
    ss.share(creds.service_account_email, perm_type="user", role="writer")

# === FUNKCJE ===
def get_or_create_sheet(name):
    try:
        return ss.worksheet(name)
    except:
        ws = ss.add_worksheet(title=name, rows="1000", cols="20")
        ws.append_row(["ID", "Data", "Typ", "Dystans [km]", "Czas [min]", "Śr. prędkość", "Śr. HR", "Kalorie"])
        return ws

def get_existing_ids(sheet):
    records = sheet.get_all_values()[1:]
    return set(row[0] for row in records)

def parse_activity(act):
    return {
        "id": str(act["activityId"]),
        "date": act["startTimeLocal"].split("T")[0],
        "type": act["activityType"]["typeKey"],
        "distance": round(act.get("distance", 0) / 1000, 2),
        "duration": round(act.get("duration", 0) / 60, 2),
        "speed": round(act.get("averageSpeed", 0) * 3.6, 2),
        "hr": round(act.get("averageHR", 0), 1),
        "calories": act.get("calories", 0)
    }

def save_to_sheet(sheet, activities):
    for act in activities:
        row = [
            act["id"], act["date"], act["type"],
            act["distance"], act["duration"], act["speed"],
            act["hr"], act["calories"]
        ]
        sheet.append_row(row)

def create_chart(sheet_title, chart_title, col_x, col_y, offset_col=8):
    sheet_id = ss.worksheet(sheet_title)._properties["sheetId"]
    req = {
        "addChart": {
            "chart": {
                "spec": {
                    "title": chart_title,
                    "basicChart": {
                        "chartType": "LINE",
                        "legendPosition": "BOTTOM_LEGEND",
                        "axis": [
                            {"position": "BOTTOM_AXIS", "title": "Data"},
                            {"position": "LEFT_AXIS", "title": chart_title},
                        ],
                        "domains": [{
                            "domain": {
                                "sourceRange": {
                                    "sources": [{
                                        "sheetId": sheet_id,
                                        "startRowIndex": 1,
                                        "endRowIndex": 1000,
                                        "startColumnIndex": col_x,
                                        "endColumnIndex": col_x + 1,
                                    }]
                                }
                            }
                        }],
                        "series": [{
                            "series": {
                                "sourceRange": {
                                    "sources": [{
                                        "sheetId": sheet_id,
                                        "startRowIndex": 1,
                                        "endRowIndex": 1000,
                                        "startColumnIndex": col_y,
                                        "endColumnIndex": col_y + 1,
                                    }]
                                }
                            },
                            "targetAxis": "LEFT_AXIS",
                        }],
                        "headerCount": 1,
                    },
                },
                "position": {
                    "overlayPosition": {
                        "anchorCell": {"sheetId": sheet_id, "rowIndex": 1, "columnIndex": offset_col},
                        "offsetXPixels": 0,
                        "offsetYPixels": 0,
                    }
                },
            }
        }
    }
    service.spreadsheets().batchUpdate(spreadsheetId=ss.id, body={"requests": [req]}).execute()

# === GŁÓWNY KOD ===
activities = client.get_activities(0, 100)
parsed = [parse_activity(a) for a in activities]

for sport in ["running", "cycling"]:
    sheet_name = "Bieganie" if sport == "running" else "Kolarstwo"
    sheet = get_or_create_sheet(sheet_name)
    existing_ids = get_existing_ids(sheet)
    new_acts = [a for a in parsed if a["type"] == sport and a["id"] not in existing_ids]
    if new_acts:
        save_to_sheet(sheet, new_acts)
        print(f"✅ Zapisano {len(new_acts)} nowych aktywności do: {sheet_name}")
    else:
        print(f"ℹ️ Brak nowych aktywności dla: {sheet_name}")

    # === WYKRESY ===
    create_chart(sheet_name, "Dystans (km)", 1, 3)
    create_chart(sheet_name, "Średnie tętno", 1, 6, offset_col=10)
    create_chart(sheet_name, "Kalorie", 1, 7, offset_col=12)
