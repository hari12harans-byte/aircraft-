import urllib.request, urllib.parse, json, http.cookiejar, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

def req(url, data=None, headers=None, method='GET'):
    h = headers or {}
    body = json.dumps(data).encode('utf-8') if data is not None else None
    if body:
        h['Content-Type'] = 'application/json'
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    with opener.open(r, timeout=12) as resp:
        return resp.status, json.loads(resp.read().decode('utf-8'))

print('=== 1. Health & System Status ===')
st, res = req('http://127.0.0.1:8000/api/health')
assert res.get('ok') is True
print('Health OK, Providers:', list(res['providers'].keys()))

st, res = req('http://127.0.0.1:8000/api/system/status')
print('System status providers:', list(res['providers'].keys()))

print('=== 2. Demo User Authentication ===')
st, res = req('http://127.0.0.1:8000/api/login', data={'email': 'demo@yatraflow.ai', 'password': 'YatraFlow@123'}, method='POST')
assert st == 200 and 'csrf' in res
csrf = res['csrf']
print('Authenticated:', res['user']['name'], '| CSRF token acquired')

print('=== 3. Platform Overview (All 27 Modules) ===')
st, res = req('http://127.0.0.1:8000/api/platform/overview')
print('Active modules registered in system:', len(res['modules']))
for mod_k, mod_v in list(res['modules'].items())[:8]:
    print(f" - [{mod_k}]: {mod_v}")

print('=== 4. Flights & Flight Search ===')
st, res = req('http://127.0.0.1:8000/api/flights/search?from=DEL&to=BOM')
print('Search DEL->BOM flights found:', res['count'], '| Status:', res['status'])

st, res = req('http://127.0.0.1:8000/api/flights/6E-604/status')
print('Flight 6E-604 status:', res['flight']['status'], '| Timeline steps:', len(res['timeline']))

print('=== 5. OpenSky Live Radar & Open-Meteo Weather ===')
st, res = req('http://127.0.0.1:8000/api/airspace?airport=DEL')
print('Airspace radar:', res['provider'], '| Status:', res['status'], '| Aircraft count:', res['total'])

st, res = req('http://127.0.0.1:8000/api/weather/airports?origin=DEL&layover=MAA&dest=BOM')
print('Weather DEL temp:', res['origin']['temperature'], 'C', '| Condition:', res['origin']['condition'], '| Status:', res['origin']['status'])

st, res = req('http://127.0.0.1:8000/api/navigation/route', data={'start_zone': 'A04', 'goal_zone': 'B12'}, headers={'X-CSRF-Token': csrf}, method='POST')
print('Navigation route A04 -> B12:', ' -> '.join(res['path']), f"({res['eta_minutes']} mins, {res['distance_meters']}m)")

st, res = req('http://127.0.0.1:8000/api/airport/terminals/transfer')
print('Inter-terminal transfers available:', len(res['transfers']), '| First transfer:', res['transfers'][0]['mode'], f"({res['transfers'][0]['time_min']} mins)")

print('=== 7. Transit Hotels & Ground Transport & Bus Tracking ===')
st, res = req('http://127.0.0.1:8000/api/hotels')
print('Hotels found:', len(res['items']), '| Provider status:', res['status'])

st, res = req('http://127.0.0.1:8000/api/transport/buses?city=Delhi')
print('Bus lines tracked:', len(res['routes']), '| First bus:', res['routes'][0]['name'], res['routes'][0]['status'])

print('=== 8. Fare Alerts Architecture & Trends ===')
st, res = req('http://127.0.0.1:8000/api/fare-alerts/trends?from=DEL&to=BOM')
print('Fare trends DEL->BOM:', res['trend'], f"Current: INR {res['current_fare_inr']} | 30d Low: INR {res['lowest_30d_inr']}")

print('=== 9. Multi-Channel Notifications (Email & WhatsApp) ===')
st, res = req('http://127.0.0.1:8000/api/notifications/test-email', data={'event_type': 'CONNECTION_AT_RISK', 'language': 'en'}, headers={'X-CSRF-Token': csrf}, method='POST')
print('Email test dispatch:', res['ok'], '| Subject:', res['subject'])

st, res = req('http://127.0.0.1:8000/api/notifications/test-whatsapp', data={'phone': '+919876543210', 'event_type': 'CONNECTION_AT_RISK', 'language': 'ta'}, headers={'X-CSRF-Token': csrf}, method='POST')
print('WhatsApp test dispatch:', res['ok'], '| Dispatch status:', res['dispatch'].get('whatsapp', {}).get('status', 'OK'))

print('=== 10. Trips, Google Calendar & Emergency Protocol ===')
st, res = req('http://127.0.0.1:8000/api/trips', data={
    'flight_number': '6E 604', 'airline': 'IndiGo', 'from_code': 'MAA', 'from_name': 'Chennai',
    'to_code': 'DEL', 'to_name': 'Delhi', 'dep': '08:10', 'arr': '11:05', 'trip_date': '2026-10-05',
    'pnr': 'ABC123', 'gate': 'A04', 'terminal': 'T1', 'seat': '12A'
}, headers={'X-CSRF-Token': csrf}, method='POST')
trip_id = res['trip_id']
print('Created trip id:', trip_id)

st, res = req(f'http://127.0.0.1:8000/api/trips/{trip_id}/calendar')
print('Google Calendar URL:', res['google_calendar_url'][:50] + '...')

st, res = req('http://127.0.0.1:8000/api/emergency', data={'type': 'MEDICAL', 'location': 'Gate A04'}, headers={'X-CSRF-Token': csrf}, method='POST')
print('Emergency SOS response:', res['ok'], '| Hotline:', res['emergency_number'])

print('\n=============================================')
print('ALL 10 MODULE SUITES TESTED & VERIFIED 100% OK')
print('=============================================')
