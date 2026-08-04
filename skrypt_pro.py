"""
Garmin → Google Sheets
======================

• loguje się do Garmin Connect
• pobiera n ostatnich aktywności
• filtruje tylko Running i Cycling
• zapisuje do osobnych zakładek: „Bieganie”, „Kolarstwo”
• nie duplikuje – sprawdza activityId w kolumnie A

Wymagane pakiety:
    pip install garminconnect gspread oauth2client python-dateutil
"""

from datetime import datetime
from dateutil import tz
from garminconnect import Garmin
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ──────────── 1. KONFIGURACJA ────────────
GC_EMAIL   = "mpiekarska@gmail.com"
GC_PASS = "4!aD5ETVFqo2FL"
SHEET_NAME = "Garmin Aktywnosci"     # nazwa całego pliku Google Sheets
LIMIT      = 50                      # ile najnowszych aktywności pobierać

# ──────────── 2. AUTORYZACJA GOOGLE ────────────
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds   = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gclient = gspread.authorize(creds)

# otwórz (albo utwórz) arkusz
try:
    ss = gclient.open(SHEET_NAME)
except gspread.SpreadsheetNotFound:
    ss = gclient.create(SHEET_NAME)

# utwórz / pobierz zakładki
def get_ws(title):
    try:
        return ss.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=title, rows=1_000, cols=20)
        ws.append_row(  # nagłówki
            ["ID", "Data", "Nazwa", "Dystans [km]", "Czas [min]", "Śr-HR", "Kalorie"],
            value_input_option="RAW",
        )
        return ws

ws_run  = get_ws("Bieganie")
ws_ride = get_ws("Kolarstwo")

# zbuduj zbiory ID już zapisanych aktywności
existing_run_ids  = set(ws_run.col_values(1)[1:])   # pomijamy nagłówek
existing_ride_ids = set(ws_ride.col_values(1)[1:])

# ──────────── 3. LOGOWANIE DO GARMIN ────────────
garmin = Garmin(GC_EMAIL, GC_PASS)
garmin.login()
print("✅ Zalogowano do Garmin Connect")

# ──────────── 4. POBIERANIE I ZAPIS ────────────
activities = garmin.get_activities(0, LIMIT)

added_run, added_ride = 0, 0
for act in activities:
    act_id   = str(act["activityId"])
    act_type = act["activityType"]["typeKey"]       # "running" / "cycling"
    if act_type not in ("running", "cycling"):
        continue  # pomijamy nie-bieg i nie-rower

    # unikamy duplikatów
    if act_type == "running" and act_id in existing_run_ids:
        continue
    if act_type == "cycling" and act_id in existing_ride_ids:
        continue

    # dane do zapisu
    t_local = datetime.fromisoformat(act["startTimeLocal"]).replace(tzinfo=tz.UTC)
    date_str = t_local.astimezone(tz.gettz("Europe/Warsaw")).strftime("%Y-%m-%d %H:%M")

    row = [
        act_id,
        date_str,
        act["activityName"],
        round(act.get("distance", 0) / 1000, 2),
        round(act.get("duration", 0) / 60, 1),
        act.get("averageHR", ""),
        act.get("calories", ""),
    ]

    if act_type == "running":
        ws_run.append_row(row, value_input_option="RAW")
        added_run += 1
    else:  # cycling
        ws_ride.append_row(row, value_input_option="RAW")
        added_ride += 1

print(f"➕ Dodano nowych: {added_run} biegów, {added_ride} jazd.")
