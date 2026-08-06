from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    GarminConnectAuthenticationError,
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# === USTAWIENIA ===
EMAIL = ""
HASLO = ""

# Nazwa Twojego arkusza Google
NAZWA_ARKUSZA = "Garmin Aktywnosci"

# === LOGOWANIE DO GARMIN CONNECT ===
try:
    garmin = Garmin(EMAIL, HASLO)
    garmin.login()
    print("✅ Zalogowano do Garmin Connect")
except Exception as e:
    print("❌ Błąd logowania:", e)
    exit()

# === POBIERANIE AKTYWNOŚCI (np. z ostatnich 7 dni) ===
dzis = datetime.now()
poczatek = dzis - timedelta(days=7)
aktywnosci = garmin.get_activities(0, 20)  # maks. 20 ostatnich

# === PRZYGOTOWANIE DO ZAPISU DO GOOGLE SHEETS ===
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# Otwórz lub utwórz arkusz
try:
    sheet = client.open(NAZWA_ARKUSZA).sheet1
except:
    sheet = client.create(NAZWA_ARKUSZA).sheet1

# Nagłówki
sheet.update('A1', [['Data', 'Typ', 'Dystans (km)', 'Czas (min)', 'Kalorie']])

# Wpisz dane
wiersze = []
for a in aktywnosci:
    data = a['startTimeLocal'].split("T")[0]
    typ = a['activityType']['typeKey']
    dystans = round(a.get('distance', 0) / 1000, 2)
    czas = round(a.get('duration', 0) / 60, 2)
    kalorie = a.get('calories', 0)
    wiersze.append([data, typ, dystans, czas, kalorie])

# Zapisz dane
if wiersze:
    sheet.update(f'A2:E{len(wiersze)+1}', wiersze)
    print(f"✅ Zapisano {len(wiersze)} aktywności do Google Sheets")
else:
    print("ℹ️ Brak aktywności do zapisania.")
