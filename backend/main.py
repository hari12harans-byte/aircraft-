import asyncio, hashlib, hmac, json, math, os, secrets, sqlite3, time, urllib.parse, urllib.request, datetime
from typing import Optional, Any, Union
from pathlib import Path
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent.parent
load_dotenv(BASE / '.env')

from fastapi import FastAPI, HTTPException, Request, Response, Cookie, Header, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response as PlainResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from backend.providers import (
    ProviderStatus,
    FlightProvider,
    WeatherProvider,
    RadarProvider,
    HotelProvider,
    TransportProvider,
    CalendarProvider,
    FareAlertProvider,
    GoogleOAuthProvider,
    SupabaseProvider
)
from backend.automation import (
    dispatch_automation_event,
    SUPPORTED_EVENT_TYPES,
    validate_phone_e164,
    generate_otp,
    get_whatsapp_template_message
)
from backend.email_templates import get_email_template

FRONT = BASE / 'frontend'; DATA = BASE / 'data'; DATA.mkdir(exist_ok=True)
DB = DATA / 'guardian.db'
VERSION = '2.2.0'
SESSION_TTL = 8 * 60 * 60
SECURE_COOKIE = os.getenv('COOKIE_SECURE', '0') == '1'
REFRESH_SECONDS = max(15, int(os.getenv('REFRESH_SECONDS', '30')))

SUPABASE_URL = os.getenv('SUPABASE_URL', '').strip()
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '').strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '').strip()
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000').strip()

# Initialize provider abstractions
flight_prov = FlightProvider()
weather_prov = WeatherProvider()
radar_prov = RadarProvider()
hotel_prov = HotelProvider()
transport_prov = TransportProvider()
calendar_prov = CalendarProvider()
fare_prov = FareAlertProvider()
google_prov = GoogleOAuthProvider()
supabase_prov = SupabaseProvider()

app = FastAPI(
    title='YatraFlow — Intelligent Airport Connection Companion',
    version=VERSION,
    description='Aviation Copilot and Travel Platform API with strict LIVE / DEMO / UNAVAILABLE provider states.',
    docs_url='/api/docs',
    redoc_url=None
)

# CORS setup
allowed_origins = ['http://127.0.0.1:8000', 'http://localhost:8000']
if API_BASE_URL:
    clean_base = API_BASE_URL.rstrip('/')
    if clean_base not in allowed_origins:
        allowed_origins.append(clean_base)
allowed_env = os.getenv('ALLOWED_ORIGINS', '').strip()
if allowed_env:
    for o in allowed_env.split(','):
        if o.strip() and o.strip() not in allowed_origins:
            allowed_origins.append(o.strip())

app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_origin_regex=r"https?://.*\.onrender\.com", allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
RATE: dict[str, list[float]] = {}
CLIENTS: set[WebSocket] = set()

# Indoor digital twin zones and routes
ZONES = {
    'A04': {'name':'Gate A04 (Concourse A)','x':18,'y':67,'terminal':'T3','type':'gate','accessible':True},
    'Security': {'name':'Security Checkpoint (Domestic)','x':43,'y':52,'terminal':'T3','type':'security','accessible':True},
    'Immigration': {'name':'Immigration & Passport Control','x':55,'y':35,'terminal':'T3','type':'immigration','accessible':True},
    'Baggage': {'name':'Baggage Reclaim (Belt 04)','x':74,'y':64,'terminal':'T3','type':'baggage','accessible':True},
    'B12': {'name':'Gate B12 (Concourse B)','x':84,'y':27,'terminal':'T3','type':'gate','accessible':True},
    'Ground': {'name':'Ground Transport & Metro Link','x':80,'y':84,'terminal':'T3','type':'ground','accessible':True},
    'HelpDesk': {'name':'Passenger Connection Desk','x':57,'y':72,'terminal':'T3','type':'support','accessible':True},
    'TransitHotel': {'name':'Holiday Inn Express Transit Hotel','x':68,'y':38,'terminal':'T3','type':'hotel','accessible':True},
    'Lounge': {'name':'Encalm Premium Lounge','x':50,'y':45,'terminal':'T3','type':'lounge','accessible':True}
}

ROUTES = {
    'A04': {'Security':7,'HelpDesk':8},
    'Security': {'A04':7,'Immigration':5,'HelpDesk':5,'Lounge':4},
    'Immigration': {'Security':5,'B12':9,'Baggage':7,'TransitHotel':4},
    'Baggage': {'Immigration':7,'B12':8,'Ground':5},
    'B12': {'Immigration':9,'Baggage':8,'Ground':6,'TransitHotel':5},
    'HelpDesk': {'A04':8,'Security':5,'Ground':6},
    'Ground': {'B12':6,'Baggage':5,'HelpDesk':6},
    'TransitHotel': {'Immigration':4,'B12':5},
    'Lounge': {'Security':4,'B12':7}
}

# Models
class Login(BaseModel): email: EmailStr; password: str = Field(min_length=1, max_length=128)
class Register(BaseModel): name: str = Field(min_length=2, max_length=80); email: EmailStr; password: str = Field(min_length=8, max_length=128)
class Setup(BaseModel): inbound_id: str; outbound_id: str; passenger_zone: str = 'A04'; bags: int = Field(default=1, ge=0, le=8); immigration: bool = False; walking_speed: str = 'NORMAL'
class Position(BaseModel): zone: str
class GPSIn(BaseModel): lat: float = Field(ge=-90, le=90); lon: float = Field(ge=-180, le=180); accuracy: float = Field(default=0, ge=0, le=100000)
class Scenario(BaseModel): delay: int = Field(default=0, ge=0, le=240); gate_change: Optional[str] = None; baggage_delay: int = Field(default=0, ge=0, le=60); crowd: int = Field(default=50, ge=0, le=100)
class ProfileIn(BaseModel): phone: str = Field(default='', max_length=30); pnr: str = Field(default='', max_length=30); flight_id: str = Field(default='', max_length=80); accessibility: list[str] = Field(default_factory=list, max_length=12); language: str = Field(default='English', max_length=30); simple_mode: bool = False
class BagIn(BaseModel): tag: str = Field(min_length=2, max_length=40); status: str = Field(default='CHECKED_IN', max_length=30); last_location: str = Field(default='Check-in', max_length=100)
class TransportIn(BaseModel): vehicle_no: str = Field(min_length=1, max_length=30); route: str = Field(default='Airport Shuttle', max_length=100); pickup: str = Field(default='Terminal', max_length=100); destination: str = Field(default='Gate / Parking', max_length=100); lat: float = 0; lon: float = 0; eta: int = Field(default=10, ge=0, le=300)
class AssistanceIn(BaseModel): type: str = Field(min_length=2, max_length=50); priority: str = Field(default='NORMAL', max_length=20); location: str = Field(default='Current location', max_length=100); notes: str = Field(default='', max_length=300)
class EmergencyIn(BaseModel): type: str = Field(default='GENERAL', max_length=40); location: str = Field(default='Current location', max_length=100)
class SimulateIn(BaseModel): event_type: str = Field(min_length=2, max_length=50); value: int = Field(default=0, ge=0, le=240)

class TripIn(BaseModel):
    flight_number: str = Field(min_length=2, max_length=30)
    airline: str = Field(default="IndiGo", max_length=60)
    from_code: str = Field(min_length=2, max_length=10)
    from_name: str = Field(default="", max_length=100)
    to_code: str = Field(min_length=2, max_length=10)
    to_name: str = Field(default="", max_length=100)
    dep: str = Field(default="10:00", max_length=10)
    arr: str = Field(default="12:30", max_length=10)
    trip_date: str = Field(default="", max_length=30)
    pnr: str = Field(default="", max_length=30)
    gate: str = Field(default="A04", max_length=20)
    terminal: str = Field(default="T3", max_length=20)
    seat: str = Field(default="12A", max_length=20)

class FareAlertIn(BaseModel):
    from_code: str = Field(min_length=2, max_length=10)
    to_code: str = Field(min_length=2, max_length=10)
    target_price: int = Field(gt=500, le=200000)
    airline: Optional[str] = "Any Airline"

class HotelInquiryIn(BaseModel):
    hotel_id: str
    hotel_name: str
    check_in_date: str
    hours: int = 6
    guest_name: str
    contact: str

class RouteNavIn(BaseModel):
    start_zone: str = 'A04'
    goal_zone: str = 'B12'
    accessible: bool = False

class PreferencesIn(BaseModel):
    email_enabled: bool = True
    whatsapp_enabled: bool = False
    push_enabled: bool = True
    flight_change: bool = True
    gate_change: bool = True
    connection_risk: bool = True
    boarding_reminder: bool = True
    transport_update: bool = True
    weather_alert: bool = True
    assistance_update: bool = True

class TestEmailIn(BaseModel):
    event_type: str = "CONNECTION_AT_RISK"
    language: str = "en"

class TestWhatsAppIn(BaseModel):
    phone: str
    event_type: str = "CONNECTION_AT_RISK"
    language: str = "en"

class SendOTPIn(BaseModel):
    phone: str

class VerifyOTPIn(BaseModel):
    phone: str
    otp: str

class GoogleAuthIn(BaseModel):
    credential: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None


# Database functions
def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def limit(key: str, n=30, window=60):
    now=time.time(); vals=[x for x in RATE.get(key,[]) if now-x<window]
    if len(vals)>=n: raise HTTPException(429,'Too many requests. Try again shortly.')
    vals.append(now); RATE[key]=vals

def hash_pw(pw,salt=None):
    salt=salt or secrets.token_bytes(16)
    return hashlib.scrypt(pw.encode(),salt=salt,n=2**14,r=8,p=1,dklen=32).hex(), salt.hex()

def verify_pw(pw,h,s):
    return hmac.compare_digest(hashlib.scrypt(pw.encode(),salt=bytes.fromhex(s),n=2**14,r=8,p=1,dklen=32).hex(),h)

def th(t):
    return hashlib.sha256(t.encode()).hexdigest()

def init_db():
    c = db()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        google_id TEXT DEFAULT NULL,
        google_avatar TEXT DEFAULT NULL,
        created_at INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS sessions(
        token_hash TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        csrf TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        expires_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS connection_sessions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        inbound_id TEXT NOT NULL,
        outbound_id TEXT NOT NULL,
        zone TEXT NOT NULL,
        bags INTEGER NOT NULL,
        immigration INTEGER NOT NULL,
        scenario TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS passenger_profiles(
        user_id INTEGER PRIMARY KEY,
        phone TEXT DEFAULT '',
        pnr TEXT DEFAULT '',
        flight_id TEXT DEFAULT '',
        accessibility TEXT DEFAULT '[]',
        language TEXT DEFAULT 'English',
        simple_mode INTEGER DEFAULT 0,
        whatsapp_enabled INTEGER DEFAULT 0,
        whatsapp_verified INTEGER DEFAULT 0,
        whatsapp_number TEXT DEFAULT '',
        email_notifications_enabled INTEGER DEFAULT 1,
        google_connected INTEGER DEFAULT 0,
        last_lat REAL DEFAULT 0,
        last_lon REAL DEFAULT 0,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS trips(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        flight_number TEXT NOT NULL,
        airline TEXT NOT NULL,
        from_code TEXT NOT NULL,
        from_name TEXT NOT NULL,
        to_code TEXT NOT NULL,
        to_name TEXT NOT NULL,
        dep TEXT NOT NULL,
        arr TEXT NOT NULL,
        trip_date TEXT NOT NULL,
        status TEXT DEFAULT 'CONFIRMED',
        pnr TEXT DEFAULT '',
        gate TEXT DEFAULT 'A04',
        terminal TEXT DEFAULT 'T3',
        seat TEXT DEFAULT '12A',
        baggage_belt TEXT DEFAULT 'Belt 04',
        created_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS bags(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        tag TEXT NOT NULL,
        status TEXT NOT NULL,
        last_location TEXT NOT NULL,
        updated_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS transport(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        vehicle_no TEXT NOT NULL,
        route TEXT NOT NULL,
        pickup TEXT NOT NULL,
        destination TEXT NOT NULL,
        lat REAL DEFAULT 0,
        lon REAL DEFAULT 0,
        eta INTEGER DEFAULT 0,
        status TEXT DEFAULT 'AVAILABLE',
        updated_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS assistance_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        priority TEXT NOT NULL,
        status TEXT NOT NULL,
        location TEXT NOT NULL,
        notes TEXT DEFAULT '',
        created_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS emergency_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        status TEXT NOT NULL,
        location TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        read INTEGER DEFAULT 0,
        created_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS notification_preferences(
        user_id INTEGER PRIMARY KEY,
        email_enabled INTEGER DEFAULT 1,
        whatsapp_enabled INTEGER DEFAULT 0,
        push_enabled INTEGER DEFAULT 1,
        flight_change INTEGER DEFAULT 1,
        gate_change INTEGER DEFAULT 1,
        connection_risk INTEGER DEFAULT 1,
        boarding_reminder INTEGER DEFAULT 1,
        transport_update INTEGER DEFAULT 1,
        weather_alert INTEGER DEFAULT 1,
        assistance_update INTEGER DEFAULT 1,
        updated_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS notification_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        event_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        notification_type TEXT NOT NULL,
        status TEXT NOT NULL,
        provider_message_id TEXT DEFAULT '',
        created_at INTEGER NOT NULL,
        sent_at INTEGER DEFAULT 0,
        error_message TEXT DEFAULT '',
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS fare_alerts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        from_code TEXT NOT NULL,
        to_code TEXT NOT NULL,
        target_price INTEGER NOT NULL,
        current_price INTEGER NOT NULL,
        airline TEXT DEFAULT 'Any Airline',
        active INTEGER DEFAULT 1,
        created_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS hotel_inquiries(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        hotel_id TEXT NOT NULL,
        hotel_name TEXT NOT NULL,
        check_in_date TEXT NOT NULL,
        hours INTEGER DEFAULT 6,
        status TEXT DEFAULT 'CONFIRMED',
        guest_name TEXT NOT NULL,
        contact TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS whatsapp_otps(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        phone TEXT NOT NULL,
        otp_hash TEXT NOT NULL,
        attempts INTEGER DEFAULT 0,
        verified INTEGER DEFAULT 0,
        created_at INTEGER NOT NULL,
        expires_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS simulation_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        payload TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # Column migrations for existing databases
    for stmt in [
        "ALTER TABLE users ADD COLUMN google_id TEXT DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN google_avatar TEXT DEFAULT NULL",
        "ALTER TABLE passenger_profiles ADD COLUMN whatsapp_enabled INTEGER DEFAULT 0",
        "ALTER TABLE passenger_profiles ADD COLUMN whatsapp_verified INTEGER DEFAULT 0",
        "ALTER TABLE passenger_profiles ADD COLUMN whatsapp_number TEXT DEFAULT ''",
        "ALTER TABLE passenger_profiles ADD COLUMN email_notifications_enabled INTEGER DEFAULT 1",
        "ALTER TABLE passenger_profiles ADD COLUMN google_connected INTEGER DEFAULT 0",
        "ALTER TABLE passenger_profiles ADD COLUMN last_lat REAL DEFAULT 0",
        "ALTER TABLE passenger_profiles ADD COLUMN last_lon REAL DEFAULT 0"
    ]:
        try:
            c.execute(stmt)
        except Exception:
            pass


    # Seed demo account if not exists
    user_row = c.execute('SELECT id FROM users WHERE email=?', ('demo@yatraflow.ai',)).fetchone()
    if not user_row:
        h, s = hash_pw('YatraFlow@123')
        now = int(time.time())
        cur = c.execute(
            'INSERT INTO users(email,name,password_hash,salt,created_at) VALUES(?,?,?,?,?)',
            ('demo@yatraflow.ai', 'Saravanan Traveler', h, s, now)
        )
        uid = cur.lastrowid
        # Seed profile
        c.execute('''
            INSERT INTO passenger_profiles(user_id,phone,pnr,flight_id,accessibility,language,simple_mode,whatsapp_enabled,whatsapp_verified,whatsapp_number,email_notifications_enabled,google_connected,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (uid, '+919876543210', 'YF-8921', '6E 604', '[]', 'English', 0, 1, 1, '+919876543210', 1, 1, now, now))

        # Seed notification preferences
        c.execute('''
            INSERT INTO notification_preferences(user_id,email_enabled,whatsapp_enabled,push_enabled,flight_change,gate_change,connection_risk,boarding_reminder,transport_update,weather_alert,assistance_update,updated_at)
            VALUES(?,1,1,1,1,1,1,1,1,1,1,?)
        ''', (uid, now))

        # Seed default connection session
        scenario_data = json.dumps({'delay': 0, 'gate_change': None, 'baggage_delay': 0, 'crowd': 50})
        c.execute('''
            INSERT INTO connection_sessions(user_id,inbound_id,outbound_id,zone,bags,immigration,scenario,created_at)
            VALUES(?,?,?,?,?,?,?,?)
        ''', (uid, '6E-604', 'AI-201', 'A04', 1, 0, scenario_data, now))

        # Seed sample saved trips
        today_str = datetime.date.today().isoformat()
        next_week = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
        c.execute('''
            INSERT INTO trips(user_id,flight_number,airline,from_code,from_name,to_code,to_name,dep,arr,trip_date,status,pnr,gate,terminal,seat,baggage_belt,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (uid, '6E 604', 'IndiGo', 'MAA', 'Chennai International', 'DEL', 'Delhi IGI Airport', '08:10', '11:05', today_str, 'ACTIVE', 'YF-8921', 'A04', 'T1', '14C', 'Belt 04', now))

        c.execute('''
            INSERT INTO trips(user_id,flight_number,airline,from_code,from_name,to_code,to_name,dep,arr,trip_date,status,pnr,gate,terminal,seat,baggage_belt,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (uid, 'AI 201', 'Air India', 'DEL', 'Delhi IGI Airport', 'LHR', 'London Heathrow T2', '11:55', '16:40', today_str, 'CONFIRMED', 'YF-8921', 'B12', 'T3', '24K', 'Belt 11', now))

        c.execute('''
            INSERT INTO trips(user_id,flight_number,airline,from_code,from_name,to_code,to_name,dep,arr,trip_date,status,pnr,gate,terminal,seat,baggage_belt,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (uid, 'UK 820', 'Vistara', 'BOM', 'Mumbai CSMIA T2', 'DEL', 'Delhi IGI Airport', '09:30', '11:45', next_week, 'UPCOMING', 'YF-4412', 'B08', 'T2', '08A', 'Belt 07', now))

        # Seed initial notification
        c.execute('''
            INSERT INTO notifications(user_id,type,title,message,read,created_at)
            VALUES(?,?,?,?,0,?)
        ''', (uid, 'FLIGHT', 'Welcome to YatraFlow Super-App', 'Your flight 6E 604 → AI 201 connection is being monitored in real time.', now))

        # Seed sample fare alert
        c.execute('''
            INSERT INTO fare_alerts(user_id,from_code,to_code,target_price,current_price,airline,active,created_at)
            VALUES(?,?,?,?,?,?,?,?)
        ''', (uid, 'DEL', 'BOM', 4500, 4950, 'Any Airline', 1, now))

    c.commit()
    c.close()


def session_row(token: Optional[str]):
    if not token: raise HTTPException(401, 'Please sign in again.')
    c = db()
    r = c.execute(
        'SELECT s.*, u.email, u.name, u.google_avatar FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?',
        (th(token), int(time.time()))
    ).fetchone()
    c.close()
    if not r: raise HTTPException(401, 'Your session has expired. Please sign in again.')
    return r

def csrf_ok(s, h):
    if not h or not hmac.compare_digest(h, s['csrf']):
        raise HTTPException(403, 'Security check failed. Refresh the page.')

def set_cookie(resp: Response, token: str):
    resp.set_cookie('yatraflow_session', token, httponly=True, secure=SECURE_COOKIE, samesite='lax', max_age=SESSION_TTL, path='/')

def new_session(uid: int):
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    now = int(time.time())
    c = db()
    c.execute('INSERT INTO sessions VALUES(?,?,?,?,?)', (th(token), uid, csrf, now, now + SESSION_TTL))
    c.execute('DELETE FROM sessions WHERE expires_at<?', (now,))
    c.commit()
    c.close()
    return token, csrf

def write_notification(uid: int, typ: str, title: str, message: str):
    c = db()
    c.execute(
        'INSERT INTO notifications(user_id,type,title,message,read,created_at) VALUES(?,?,?,?,0,?)',
        (uid, typ, title, message, int(time.time()))
    )
    c.commit()
    c.close()

def minutes(hm: str) -> int:
    if not hm: raise ValueError('Missing flight time')
    raw = hm[11:16] if len(hm) >= 16 and hm[4] == '-' else hm[:5]
    h, m = map(int, raw.split(':'))
    return h * 60 + m

def safe_minutes(hm: str, fallback: int = 0) -> int:
    try: return minutes(hm)
    except Exception: return fallback

def connection_engine(inbound: dict, outbound: dict, zone: str, bags: int, immigration: bool, scenario: dict, walking_speed: str = 'NORMAL'):
    inbound = dict(inbound); outbound = dict(outbound)
    delay = int(scenario.get('delay', 0))
    baggage_delay = int(scenario.get('baggage_delay', 0))
    crowd = int(scenario.get('crowd', 50))
    gate_change = scenario.get('gate_change')

    inbound_arr = safe_minutes(inbound.get('arr'), 0)
    outbound_dep = safe_minutes(outbound.get('dep'), inbound_arr + 60)
    if outbound_dep <= inbound_arr:
        outbound_dep += 24 * 60

    inbound['arrival_minutes'] = inbound_arr + delay
    outbound_gate = gate_change or outbound.get('gate', 'B12') or 'B12'
    boarding_close = outbound_dep - 15
    available = max(0, boarding_close - inbound['arrival_minutes'])

    # Base walking calculation
    base_walk = ROUTES.get(zone, {}).get(outbound_gate, 14)
    speed_factor = 1.35 if walking_speed in ('WHEELCHAIR', 'ELDERLY', 'SLOW') else (0.85 if walking_speed == 'FAST' else 1.0)
    crowd_factor = 1 + max(0, crowd - 50) / 250
    walk = round(base_walk * speed_factor * crowd_factor, 1)

    security = 8 + round(max(0, crowd - 50) / 25)
    immigration_time = 12 if immigration else 0
    baggage = 10 + baggage_delay if bags else 0
    buffer = 5
    required = round(walk + security + immigration_time + baggage + buffer, 1)
    margin = round(available - required, 1)

    risk = max(0, min(99, round(50 - margin * 3.4 + crowd * .18 + (10 if bags else 0))))
    if margin >= 15: level = 'SAFE'
    elif margin >= 0: level = 'TIGHT'
    elif margin >= -10: level = 'AT RISK'
    else: level = 'LIKELY MISSED'

    actions = []
    if level in ('AT RISK', 'LIKELY MISSED'):
        actions = [
            'Proceed directly to the connection route without stopping',
            'Follow express transfer signs to Terminal 3 Gate concourse',
            'Show your tight connection boarding pass at Security Fast-Track Lane',
            'Alert airline ground assistance staff at Connection Desk'
        ]
        if bags: actions.append('Confirm automated baggage tag transfer with baggage agent')
        if immigration: actions.append('Use designated e-Visa / priority immigration counter')
        actions.append('Prepare airline recovery options and later flight alternatives')
    elif level == 'TIGHT':
        actions = [
            'Proceed directly to security checkpoint',
            'Keep your boarding pass and photo ID in hand',
            'Verify outbound gate B12 on information displays'
        ]
    else:
        actions = [
            'Your connection has a comfortable buffer',
            'You may visit duty-free, dining or Encalm Transit Lounge near Gate 15',
            'Boarding gate closes 15 minutes before scheduled departure'
        ]

    return {
        'bags': bags,
        'immigration': immigration,
        'level': level,
        'risk': risk,
        'available_minutes': available,
        'required_minutes': required,
        'margin_minutes': margin,
        'walk_minutes': walk,
        'security_minutes': security,
        'immigration_minutes': immigration_time,
        'baggage_minutes': baggage,
        'buffer_minutes': buffer,
        'outbound_gate': outbound_gate,
        'boarding_close': f"{outbound.get('dep','—')} - 15m",
        'actions': actions,
        'inbound_delay': delay,
        'crowd': crowd,
        'baggage_status': 'At risk' if baggage_delay > 10 else 'Transfer expected',
        'message': {
            'SAFE': 'Your connection has a healthy time buffer.',
            'TIGHT': 'Your connection is viable, but avoid non-essential stops.',
            'AT RISK': 'Connection window is tight! Follow the priority rescue route.',
            'LIKELY MISSED': 'The transfer buffer is depleted. Review alternative recovery flights.'
        }[level]
    }

def graph_route(start: str, goal: str, accessible: bool = False):
    if start == goal: return [start], 0, ["You have reached your destination."]
    dist = {k: math.inf for k in ZONES}; prev = {}; dist[start] = 0; seen = set()
    while len(seen) < len(ZONES):
        u = min((k for k in ZONES if k not in seen), key=lambda k: dist[k], default=None)
        if u is None or dist[u] == math.inf: break
        seen.add(u)
        for v, w in ROUTES.get(u, {}).items():
            cost = w
            if accessible and (u in ('Security', 'Immigration') or v in ('Security', 'Immigration')):
                cost = round(w * 1.2, 1)  # extra time for elevator/ramp access
            nd = dist[u] + cost
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u

    if goal not in prev and goal != start:
        return [start, goal], 15, ["Proceed along main terminal concourse."]

    path = []; x = goal
    while x != start:
        path.append(x)
        x = prev[x]
    path.append(start); path.reverse()

    steps = []
    for i in range(len(path) - 1):
        from_n = ZONES.get(path[i], {}).get('name', path[i])
        to_n = ZONES.get(path[i+1], {}).get('name', path[i+1])
        if accessible:
            steps.append(f"From {from_n}, follow accessible tactile path and use elevator to reach {to_n}.")
        else:
            steps.append(f"From {from_n}, walk straight along main terminal corridor towards {to_n}.")
    steps.append(f"Arrive at {ZONES.get(goal, {}).get('name', goal)}.")

    return path, round(dist[goal], 1), steps

def get_session_state(uid: int):
    c = db()
    r = c.execute('SELECT * FROM connection_sessions WHERE user_id=? ORDER BY id DESC LIMIT 1', (uid,)).fetchone()
    c.close()
    if not r: return None
    try: scenario = json.loads(r['scenario'])
    except Exception: scenario = {}
    return {
        'id': r['id'],
        'inbound_id': r['inbound_id'],
        'outbound_id': r['outbound_id'],
        'zone': r['zone'],
        'bags': r['bags'],
        'immigration': bool(r['immigration']),
        'scenario': scenario
    }

def state_payload(uid: int):
    s = get_session_state(uid)
    if not s:
        s = {
            'inbound_id': '6E-604',
            'outbound_id': 'AI-201',
            'zone': 'A04',
            'bags': 1,
            'immigration': False,
            'scenario': {'delay': 0, 'gate_change': None, 'baggage_delay': 0, 'crowd': 50}
        }

    flight_list = flight_prov.list_all()['items']
    inbound = next((f for f in flight_list if f['id'] == s['inbound_id'] or f['number'].replace(' ','') == s['inbound_id'].replace(' ','')), flight_list[0])
    outbound = next((f for f in flight_list if f['id'] == s['outbound_id'] or f['number'].replace(' ','') == s['outbound_id'].replace(' ','')), flight_list[1])

    engine = connection_engine(inbound, outbound, s['zone'], s['bags'], s['immigration'], s['scenario'])
    path, eta, step_instructions = graph_route(s['zone'], engine['outbound_gate'])
    rec = engine.copy(); rec['route'] = path; rec['route_eta'] = eta; rec['step_instructions'] = step_instructions

    airport_code = outbound.get('from') or inbound.get('to') or 'DEL'
    sky = radar_prov.get_airspace(airport_code)
    weather_info = weather_prov.get_weather(airport_code)

    return {
        'inbound': inbound,
        'outbound': outbound,
        'engine': rec,
        'position': ZONES.get(s['zone'], ZONES['A04']),
        'zone': s['zone'],
        'zones': ZONES,
        'route_edges': ROUTES,
        'scenario': {**s['scenario'], 'bags': s['bags'], 'immigration': s['immigration']},
        'weather': weather_info,
        'airspace': sky,
        'flights': flight_list,
        'source': {
            'flights': flight_prov.get_metadata()['status'],
            'airspace': sky.get('status', 'DEMO'),
            'weather': weather_info.get('status', 'DEMO'),
            'indoor': 'Airport Digital Twin (High-Fidelity)',
            'baggage': 'Operational Baggage Feed (Demo)',
            'ground': 'Airport Transit Feeder (Demo)'
        },
        'updated': {
            'flights': int(time.time()),
            'weather': weather_info.get('updated_at', int(time.time())),
            'airspace': sky.get('updated_at', int(time.time()))
        }
    }


# Middlewares
@app.middleware('http')
async def security_middleware(request: Request, call_next):
    r = await call_next(request)
    r.headers.update({
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(self),camera=(),microphone=(self)',
        'Content-Security-Policy': "default-src 'self' https: data: blob:; img-src 'self' data: https: blob:; style-src 'self' 'unsafe-inline' https:; script-src 'self' 'unsafe-inline' https:; frame-src 'self' https:; connect-src 'self' ws: wss: https: http:; font-src 'self' https: data:; frame-ancestors 'none'"
    })
    if request.url.path.startswith('/api/'):
        r.headers['Cache-Control'] = 'no-store'
    return r

@app.on_event('startup')
async def on_startup():
    init_db()
    asyncio.create_task(background_broadcast_loop())

async def broadcast_ws(msg: dict):
    for ws in list(CLIENTS):
        try: await ws.send_json(msg)
        except Exception: CLIENTS.discard(ws)

async def background_broadcast_loop():
    while True:
        await asyncio.sleep(REFRESH_SECONDS)
        try:
            sky = await asyncio.to_thread(radar_prov.get_airspace, 'DEL')
            w = await asyncio.to_thread(weather_prov.get_weather, 'DEL')
            await broadcast_ws({
                'type': 'heartbeat',
                'time': int(time.time()),
                'weather': w,
                'airspace': sky
            })
        except Exception:
            pass


# ---------------- API ENDPOINTS ----------------

@app.get('/api/health')
def health():
    return {
        'ok': True,
        'app': 'YatraFlow',
        'version': VERSION,
        'providers': {
            'flights': flight_prov.get_metadata(),
            'weather': weather_prov.get_metadata(),
            'radar': radar_prov.get_metadata(),
            'google_oauth': google_prov.get_metadata(),
            'supabase': 'Configured' if supabase_prov.is_configured else 'Ready / Optional'
        }
    }

@app.get('/api/system/status')
def system_status():
    return {
        'app': 'YatraFlow Super-App',
        'version': VERSION,
        'tagline': 'Your intelligent airport connection companion.',
        'providers': {
            'flights': flight_prov.get_metadata(),
            'weather': weather_prov.get_metadata(),
            'radar': radar_prov.get_metadata(),
            'hotels': hotel_prov.get_metadata(),
            'transport': transport_prov.get_metadata(),
            'calendar': calendar_prov.get_metadata(),
            'fare_alerts': fare_prov.get_metadata(),
            'google_oauth': google_prov.get_metadata(),
            'supabase': supabase_prov.ping()
        },
        'environment': {
            'api_base_url': API_BASE_URL,
            'pwa_ready': True,
            'android_capacitor_ready': True,
            'multi_language': ['English', 'Tamil', 'Hindi']
        }
    }

@app.get('/api/supabase/status')
def supabase_status():
    return supabase_prov.ping()


# Auth Endpoints
@app.post('/api/register')
def register(p: Register, request: Request, response: Response):
    limit('register:' + str(request.client.host), 5, 300)
    email = p.email.lower().strip()
    if not (any(x.islower() for x in p.password) and any(x.isupper() for x in p.password) and any(x.isdigit() for x in p.password)):
        raise HTTPException(400, 'Password must contain uppercase, lowercase and a number.')
    h, s = hash_pw(p.password)
    c = db()
    try:
        cur = c.execute('INSERT INTO users(email,name,password_hash,salt,created_at) VALUES(?,?,?,?,?)', (email, p.name.strip(), h, s, int(time.time())))
        uid = cur.lastrowid
        c.execute('INSERT INTO passenger_profiles(user_id,language,created_at,updated_at) VALUES(?,?,?,?)', (uid, 'English', int(time.time()), int(time.time())))
        c.execute('INSERT INTO notification_preferences(user_id,updated_at) VALUES(?,?)', (uid, int(time.time())))
        c.commit()
    except sqlite3.IntegrityError:
        c.close(); raise HTTPException(409, 'An account with this email already exists.')
    c.close()
    tok, csrf = new_session(uid)
    set_cookie(response, tok)
    return {'ok': True, 'csrf': csrf, 'user': {'name': p.name.strip(), 'email': email}}

@app.post('/api/login')
def login(p: Login, request: Request, response: Response):
    limit('login:' + str(request.client.host), 15, 300)
    c = db()
    r = c.execute('SELECT * FROM users WHERE email=?', (p.email.lower().strip(),)).fetchone()
    c.close()
    if not r or not verify_pw(p.password, r['password_hash'], r['salt']):
        raise HTTPException(401, 'Email or password is incorrect.')
    tok, csrf = new_session(r['id'])
    set_cookie(response, tok)
    return {'ok': True, 'csrf': csrf, 'user': {'name': r['name'], 'email': r['email']}}

@app.post('/api/auth/google')
def google_auth(p: GoogleAuthIn, response: Response):
    """Google Sign-in and account linking with live or demo fallback."""
    v = google_prov.verify_id_token_or_demo(p.credential, p.email, p.name)
    email = v['email'].lower().strip()
    c = db()
    r = c.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
    now = int(time.time())
    if not r:
        h, s = hash_pw(secrets.token_urlsafe(16))
        cur = c.execute(
            'INSERT INTO users(email,name,password_hash,salt,google_id,google_avatar,created_at) VALUES(?,?,?,?,?,?,?)',
            (email, v['name'], h, s, v.get('google_id'), v.get('avatar'), now)
        )
        uid = cur.lastrowid
        c.execute('INSERT INTO passenger_profiles(user_id,google_connected,created_at,updated_at) VALUES(?,1,?,?)', (uid, now, now))
        c.execute('INSERT INTO notification_preferences(user_id,updated_at) VALUES(?,?)', (uid, now))
        c.commit()
    else:
        uid = r['id']
        c.execute('UPDATE users SET google_id=?, google_avatar=? WHERE id=?', (v.get('google_id'), v.get('avatar'), uid))
        c.execute('UPDATE passenger_profiles SET google_connected=1 WHERE user_id=?', (uid,))
        c.commit()
    c.close()

    tok, csrf = new_session(uid)
    set_cookie(response, tok)
    return {
        'ok': True,
        'csrf': csrf,
        'provider': v['provider'],
        'status': v['status'],
        'user': {'name': v['name'], 'email': email, 'avatar': v.get('avatar')}
    }

@app.post('/api/logout')
def logout(response: Response, token: Optional[str] = Cookie(default=None, alias='yatraflow_session')):
    if token:
        c = db()
        c.execute('DELETE FROM sessions WHERE token_hash=?', (th(token),))
        c.commit(); c.close()
    response.delete_cookie('yatraflow_session', path='/')
    return {'ok': True}

@app.get('/api/state')
def get_state(token: Optional[str] = Cookie(default=None, alias='yatraflow_session')):
    s = session_row(token)
    return {
        'user': {'name': s['name'], 'email': s['email'], 'csrf': s['csrf'], 'avatar': s['google_avatar']},
        'state': state_payload(s['user_id'])
    }

@app.get('/api/platform/overview')
def platform_overview(token: Optional[str] = Cookie(default=None, alias='yatraflow_session')):
    s = session_row(token); uid = s['user_id']
    st = state_payload(uid)
    c = db()
    counts = {
        'assistance': c.execute("SELECT COUNT(*) FROM assistance_requests WHERE user_id=? AND status!='RESOLVED'", (uid,)).fetchone()[0],
        'emergency': c.execute("SELECT COUNT(*) FROM emergency_events WHERE user_id=? AND status!='CLOSED'", (uid,)).fetchone()[0],
        'notifications': c.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND read=0", (uid,)).fetchone()[0],
        'trips': c.execute("SELECT COUNT(*) FROM trips WHERE user_id=?", (uid,)).fetchone()[0],
        'fare_alerts': c.execute("SELECT COUNT(*) FROM fare_alerts WHERE user_id=? AND active=1", (uid,)).fetchone()[0],
        'bags': c.execute("SELECT COUNT(*) FROM bags WHERE user_id=?", (uid,)).fetchone()[0],
        'transport': c.execute("SELECT COUNT(*) FROM transport WHERE user_id=?", (uid,)).fetchone()[0]
    }
    c.close()
    return {
        'product': 'YatraFlow',
        'version': VERSION,
        'state': st,
        'counts': counts,
        'modules': {
            'flights': flight_prov.get_metadata()['status'],
            'flight_search': flight_prov.get_metadata()['status'],
            'flight_status': flight_prov.get_metadata()['status'],
            'live_aircraft_radar': st['airspace'].get('status', 'DEMO'),
            'connection_intelligence': 'LIVE ENGINE',
            'airport_live_map': 'INTERACTIVE LEAFLET + OSM',
            'current_location': 'DEVICE GPS SENSOR',
            'gate_navigation': 'INDOOR DIJKSTRA + ACCESSIBILITY',
            'terminal_navigation': 'INTER-TERMINAL SHUTTLES',
            'hotels': 'TRANSIT STAYS DIRECTORY',
            'ground_transport': 'MULTI-MODAL HUB',
            'bus_tracking': 'SIMULATED GPS TELEMETRY',
            'weather': st['weather'].get('status', 'DEMO'),
            'notifications': 'IN-APP + EMAIL + WHATSAPP',
            'email': 'RESPONSIVE TRI-LINGUAL TEMPLATES',
            'whatsapp': 'META BUSINESS CLOUD API FORMAT',
            'google_account': google_prov.get_metadata()['status'],
            'google_calendar': '1-CLICK EVENT & ICAL ICS',
            'voice_assistant': 'WEB SPEECH API (EN/TA/HI)',
            'languages': 'EN, TA, HI (3 LANGUAGES)',
            'emergency_assistance': 'INDIA 112 + AIRPORT SECURITY',
            'travel_timeline': 'ACTIVE JOURNEY STAGES',
            'saved_trips': 'LOCAL + DB PERSISTENCE',
            'database_supabase': 'LIVE (CONNECTED)' if supabase_prov.ping().get('connected') else 'LOCAL SQLITE (ACTIVE)',
            'fare_alerts': 'PRICE DROP ENGINE',
            'pwa_installation': 'OFFLINE SHELL READY',
            'android_readiness': 'CAPACITOR READY'
        },
        'updated': int(time.time())
    }


# Flights & Search Endpoints
@app.get('/api/flights')
def get_flights():
    return flight_prov.list_all()

@app.get('/api/flights/search')
def search_flights(
    from_code: Optional[str] = None,
    to_code: Optional[str] = None,
    travel_date: Optional[str] = None,
    airline: Optional[str] = None,
    cabin_class: Optional[str] = None,
    sort_by: str = 'price_asc'
):
    return flight_prov.search(from_code, to_code, travel_date, airline, cabin_class, sort_by)

@app.get('/api/flights/{flight_id}/status')
def get_flight_status(flight_id: str):
    return flight_prov.get_status(flight_id)

@app.get('/api/airspace')
def get_airspace(airport: str = 'DEL'):
    return radar_prov.get_airspace(airport)


# Trips Endpoints
@app.get('/api/trips')
def get_trips(token: Optional[str] = Cookie(default=None, alias='yatraflow_session')):
    s = session_row(token); uid = s['user_id']
    c = db()
    rows = [dict(r) for r in c.execute('SELECT * FROM trips WHERE user_id=? ORDER BY id DESC', (uid,)).fetchall()]
    if not rows:
        today_str = datetime.date.today().isoformat()
        now = int(time.time())
        c.execute('''
            INSERT INTO trips(user_id,flight_number,airline,from_code,from_name,to_code,to_name,dep,arr,trip_date,status,pnr,gate,terminal,seat,baggage_belt,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (uid, '6E 604', 'IndiGo', 'MAA', 'Chennai International Airport', 'DEL', 'Delhi Indira Gandhi Airport', '08:10', '11:05', today_str, 'ACTIVE', 'YF-8921', 'A04', 'T1', '14C', 'Belt 04', now))
        c.execute('''
            INSERT INTO trips(user_id,flight_number,airline,from_code,from_name,to_code,to_name,dep,arr,trip_date,status,pnr,gate,terminal,seat,baggage_belt,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (uid, 'AI 201', 'Air India', 'DEL', 'Delhi Indira Gandhi Airport', 'LHR', 'London Heathrow Airport T2', '11:55', '16:40', today_str, 'CONFIRMED', 'YF-8921', 'B12', 'T3', '24K', 'Belt 11', now))
        c.commit()
        rows = [dict(r) for r in c.execute('SELECT * FROM trips WHERE user_id=? ORDER BY id DESC', (uid,)).fetchall()]
    c.close()
    return {'success': True, 'items': rows, 'count': len(rows)}

@app.post('/api/trips')
def create_trip(p: TripIn, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); uid = s['user_id']
    now = int(time.time())
    today = p.trip_date or datetime.date.today().isoformat()
    c = db()
    cur = c.execute('''
        INSERT INTO trips(user_id,flight_number,airline,from_code,from_name,to_code,to_name,dep,arr,trip_date,status,pnr,gate,terminal,seat,baggage_belt,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (uid, p.flight_number.upper(), p.airline, p.from_code.upper(), p.from_name or p.from_code, p.to_code.upper(), p.to_name or p.to_code, p.dep, p.arr, today, 'CONFIRMED', p.pnr or f"YF-{secrets.randbelow(9000)+1000}", p.gate, p.terminal, p.seat, 'Belt 04', now))
    tid = cur.lastrowid
    c.commit(); c.close()

    write_notification(uid, 'TRIP', 'Trip Confirmed', f"Trip {p.flight_number} ({p.from_code} → {p.to_code}) added to My Trips.")
    return {'ok': True, 'trip_id': tid}

@app.delete('/api/trips/{trip_id}')
def delete_trip(trip_id: int, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); uid = s['user_id']
    c = db()
    c.execute('DELETE FROM trips WHERE id=? AND user_id=?', (trip_id, uid))
    c.commit(); c.close()
    return {'ok': True}

@app.get('/api/trips/{trip_id}/calendar')
def trip_calendar(trip_id: int, format: str = 'json', token: Optional[str] = Cookie(default=None, alias='yatraflow_session')):
    s = session_row(token); uid = s['user_id']
    c = db()
    r = c.execute('SELECT * FROM trips WHERE id=? AND user_id=?', (trip_id, uid)).fetchone()
    c.close()
    if not r: raise HTTPException(404, 'Trip not found.')

    data = calendar_prov.generate_calendar_links(
        flight_number=r['flight_number'],
        airline=r['airline'],
        from_code=r['from_code'],
        from_name=r['from_name'],
        to_code=r['to_code'],
        to_name=r['to_name'],
        dep_time=r['dep'],
        arr_time=r['arr'],
        date_str=r['trip_date'],
        terminal=r['terminal'],
        gate=r['gate'],
        pnr=r['pnr']
    )

    if format == 'ics':
        return PlainResponse(content=data['ics_content'], media_type='text/calendar', headers={'Content-Disposition': f'attachment; filename="trip_{r["flight_number"]}.ics"'})
    return {'success': True, **data}


# Connection Intelligence
@app.post('/api/connection/setup')
def setup_connection(p: Setup, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf)
    if p.inbound_id == p.outbound_id: raise HTTPException(400, 'Choose two different connecting flights.')
    if p.passenger_zone not in ZONES: raise HTTPException(400, 'Unknown airport zone.')
    scenario = {'delay': 0, 'gate_change': None, 'baggage_delay': 0, 'crowd': 50}
    c = db()
    c.execute(
        'INSERT INTO connection_sessions(user_id,inbound_id,outbound_id,zone,bags,immigration,scenario,created_at) VALUES(?,?,?,?,?,?,?,?)',
        (s['user_id'], p.inbound_id, p.outbound_id, p.passenger_zone, p.bags, int(p.immigration), json.dumps(scenario), int(time.time()))
    )
    c.commit(); c.close()
    write_notification(s['user_id'], 'CONNECTION', 'Connection Monitoring Started', f"Monitoring connection {p.inbound_id} → {p.outbound_id}.")
    return {'ok': True, 'state': state_payload(s['user_id'])}

@app.post('/api/position')
def update_position(p: Position, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf)
    if p.zone not in ZONES: raise HTTPException(400, 'Unknown airport zone.')
    c = db()
    r = c.execute('SELECT id FROM connection_sessions WHERE user_id=? ORDER BY id DESC LIMIT 1', (s['user_id'],)).fetchone()
    if not r: raise HTTPException(400, 'Set up a connection first.')
    c.execute('UPDATE connection_sessions SET zone=? WHERE id=?', (p.zone, r['id']))
    c.commit(); c.close()
    return {'ok': True, 'state': state_payload(s['user_id'])}

@app.post('/api/position/gps')
def update_gps(p: GPSIn, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf)
    c = db()
    c.execute('UPDATE passenger_profiles SET last_lat=?, last_lon=? WHERE user_id=?', (p.lat, p.lon, s['user_id']))
    c.commit(); c.close()
    return {
        'ok': True,
        'state': state_payload(s['user_id']),
        'gps': {'lat': p.lat, 'lon': p.lon, 'accuracy': p.accuracy, 'updated_at': int(time.time())}
    }

@app.post('/api/scenario')
def update_scenario(p: Scenario, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); c = db()
    r = c.execute('SELECT * FROM connection_sessions WHERE user_id=? ORDER BY id DESC LIMIT 1', (s['user_id'],)).fetchone()
    if not r: raise HTTPException(400, 'Set up a connection first.')
    old = json.loads(r['scenario']); merged = {**old, **p.model_dump(exclude_none=True)}
    c.execute('UPDATE connection_sessions SET scenario=? WHERE id=?', (json.dumps(merged), r['id']))
    c.commit(); c.close()
    return {'ok': True, 'state': state_payload(s['user_id'])}


# Navigation & Airport Digital Twin
@app.get('/api/airport/map-data')
def get_airport_map_data(airport: str = 'DEL'):
    """Returns rich interactive map points for terminals, gates, security, hotels, and transit."""
    base_lat = 28.5562; base_lon = 77.1000
    points = [
        {"id": "del-t3", "name": "Terminal 3 (Integrated)", "type": "terminal", "lat": 28.5562, "lon": 77.1000, "details": "International & Major Domestic Operations"},
        {"id": "del-t2", "name": "Terminal 2", "type": "terminal", "lat": 28.5575, "lon": 77.0980, "details": "Domestic Operations (IndiGo / Akasa)"},
        {"id": "del-t1", "name": "Terminal 1 (New)", "type": "terminal", "lat": 28.5680, "lon": 77.1180, "details": "Domestic Departures & Arrivals"},
        {"id": "gate-a04", "name": "Gate A04", "type": "gate", "lat": 28.5558, "lon": 77.0990, "details": "Concourse A Domestic"},
        {"id": "gate-b12", "name": "Gate B12", "type": "gate", "lat": 28.5570, "lon": 77.1015, "details": "Concourse B International"},
        {"id": "sec-t3", "name": "Security Screening Fast-Track", "type": "security", "lat": 28.5565, "lon": 77.0995, "details": "Smart Security E-Gates"},
        {"id": "bag-t3", "name": "Baggage Claim Belts 1-14", "type": "baggage", "lat": 28.5555, "lon": 77.1005, "details": "Ground Level Arrivals"},
        {"id": "hotel-t3", "name": "Holiday Inn Express Transit Hotel", "type": "hotel", "lat": 28.5568, "lon": 77.1008, "details": "Airside Level 5 - Day & Night Stays"},
        {"id": "metro-t3", "name": "Airport Express Metro Station", "type": "metro", "lat": 28.5548, "lon": 77.0985, "details": "Direct Rail Link to New Delhi Station"},
        {"id": "shuttle-t3", "name": "Inter-Terminal Shuttle Bus Bay", "type": "bus", "lat": 28.5552, "lon": 77.0975, "details": "Free Transfer to T1 & T2 (Every 15 mins)"},
        {"id": "sos-t3", "name": "Airport Medical & Emergency SOS", "type": "medical", "lat": 28.5563, "lon": 77.0992, "details": "24/7 Medanta Medical Clinic inside T3"}
    ]
    return {
        "success": True,
        "airport": airport.upper(),
        "center": {"lat": base_lat, "lon": base_lon, "zoom": 16},
        "points": points
    }

@app.post('/api/navigation/route')
def get_indoor_route(p: RouteNavIn):
    """Step-by-step turn-by-turn indoor routing."""
    start = p.start_zone if p.start_zone in ZONES else 'A04'
    goal = p.goal_zone if p.goal_zone in ZONES else 'B12'
    path, eta, steps = graph_route(start, goal, accessible=p.accessible)
    distance_meters = int(eta * 55)  # approximate distance in meters
    return {
        'success': True,
        'start_zone': start,
        'start_name': ZONES.get(start, {}).get('name', start),
        'goal_zone': goal,
        'goal_name': ZONES.get(goal, {}).get('name', goal),
        'accessible_route': p.accessible,
        'eta_minutes': eta,
        'distance_meters': distance_meters,
        'path': path,
        'steps': steps
    }

@app.get('/api/airport/terminals/transfer')
def terminal_transfers():
    return {
        'airport': 'DEL',
        'transfers': [
            {
                'from_terminal': 'Terminal 3',
                'to_terminal': 'Terminal 2',
                'mode': 'Walkway',
                'time_min': 5,
                'distance': '350m',
                'cost': 'Free',
                'directions': 'Follow covered pedestrian walkway connecting T3 Arrivals to T2.'
            },
            {
                'from_terminal': 'Terminal 3 / T2',
                'to_terminal': 'Terminal 1',
                'mode': 'Inter-Terminal Shuttle Bus',
                'time_min': 15,
                'frequency': 'Every 15 minutes (24/7)',
                'cost': 'Free with Boarding Pass',
                'boarding_point': 'T3 Pillar 10 / T2 Arrivals Bay 4',
                'directions': 'Collect complimentary shuttle slip at Inter-Terminal Transfer Counter.'
            },
            {
                'from_terminal': 'Terminal 3',
                'to_terminal': 'Terminal 1',
                'mode': 'Airport Express Metro Link',
                'time_min': 12,
                'frequency': 'Every 10-12 minutes',
                'cost': '₹20',
                'boarding_point': 'IGI Airport Metro Station',
                'directions': 'Take Airport Express to Aerocity, then feeder link to T1.'
            }
        ]
    }


# Hotels & Transit Stays
@app.get('/api/hotels')
def list_hotels(airport: str = 'DEL', airside: bool = False):
    return hotel_prov.list_hotels(airport, airside)

@app.post('/api/hotels/inquire')
def inquire_hotel(p: HotelInquiryIn, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); uid = s['user_id']
    now = int(time.time())
    c = db()
    cur = c.execute('''
        INSERT INTO hotel_inquiries(user_id,hotel_id,hotel_name,check_in_date,hours,status,guest_name,contact,created_at)
        VALUES(?,?,?,?,?,?,?,?,?)
    ''', (uid, p.hotel_id, p.hotel_name, p.check_in_date, p.hours, 'CONFIRMED', p.guest_name, p.contact, now))
    hid = cur.lastrowid
    c.commit(); c.close()

    write_notification(uid, 'HOTEL', 'Transit Stay Confirmed', f"Reservation #{hid} at {p.hotel_name} for {p.hours} hours.")
    return {'ok': True, 'inquiry_id': hid, 'status': 'CONFIRMED', 'message': f"Booking at {p.hotel_name} registered successfully."}


# Ground Transport & Buses
@app.get('/api/transport/options')
def transport_options(airport: str = 'DEL'):
    return transport_prov.get_transport_options(airport)

@app.get('/api/transport/buses')
def transport_buses(airport: str = 'DEL'):
    return transport_prov.get_bus_routes(airport)

@app.get('/api/transport')
def get_user_transport(token: Optional[str] = Cookie(default=None, alias='yatraflow_session')):
    s = session_row(token); c = db()
    rows = [dict(r) for r in c.execute('SELECT * FROM transport WHERE user_id=? ORDER BY id DESC', (s['user_id'],)).fetchall()]
    c.close()
    if not rows:
        rows = [{'id': 0, 'vehicle_no': 'TN-01-AX-2048', 'route': 'Airport Shuttle Feeder', 'pickup': 'T2 Arrivals', 'destination': 'T1 Departures', 'lat': 28.5562, 'lon': 77.1000, 'eta': 8, 'status': 'AVAILABLE', 'updated_at': int(time.time())}]
    return {'items': rows, 'source': 'DEMO / USER INPUT'}

@app.post('/api/transport')
def add_user_transport(p: TransportIn, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); c = db()
    c.execute(
        'INSERT INTO transport(user_id,vehicle_no,route,pickup,destination,lat,lon,eta,status,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
        (s['user_id'], p.vehicle_no, p.route, p.pickup, p.destination, p.lat, p.lon, p.eta, 'AVAILABLE', int(time.time()))
    )
    c.commit(); c.close()
    return {'ok': True}


# Weather
@app.get('/api/weather/airports')
def get_weather_multi(origin: str = 'MAA', layover: str = 'DEL', dest: str = 'LHR'):
    return {
        'origin': weather_prov.get_weather(origin),
        'layover': weather_prov.get_weather(layover),
        'destination': weather_prov.get_weather(dest)
    }


# Fare Alerts
@app.get('/api/fare-alerts')
def list_fare_alerts(token: Optional[str] = Cookie(default=None, alias='yatraflow_session')):
    s = session_row(token); c = db()
    rows = [dict(r) for r in c.execute('SELECT * FROM fare_alerts WHERE user_id=? ORDER BY id DESC', (s['user_id'],)).fetchall()]
    c.close()
    return {'success': True, 'items': rows}

@app.post('/api/fare-alerts')
def create_fare_alert(p: FareAlertIn, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); uid = s['user_id']
    trend_data = fare_prov.get_route_price_trends(p.from_code, p.to_code)
    current_price = trend_data.get('current_fare_inr', 5000)
    c = db()
    cur = c.execute(
        'INSERT INTO fare_alerts(user_id,from_code,to_code,target_price,current_price,airline,active,created_at) VALUES(?,?,?,?,?,?,?,?)',
        (uid, p.from_code.upper(), p.to_code.upper(), p.target_price, current_price, p.airline or 'Any Airline', 1, int(time.time()))
    )
    aid = cur.lastrowid
    c.commit(); c.close()

    write_notification(uid, 'FARE_ALERT', 'Fare Alert Activated', f"Tracking {p.from_code.upper()} → {p.to_code.upper()} when fare drops below ₹{p.target_price}.")
    return {'ok': True, 'alert_id': aid, 'current_price': current_price}

@app.delete('/api/fare-alerts/{alert_id}')
def delete_fare_alert(alert_id: int, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); uid = s['user_id']
    c = db()
    c.execute('DELETE FROM fare_alerts WHERE id=? AND user_id=?', (alert_id, uid))
    c.commit(); c.close()
    return {'ok': True}

@app.get('/api/fare-alerts/trends')
def fare_trends(from_code: str = 'DEL', to_code: str = 'BOM'):
    return fare_prov.get_route_price_trends(from_code, to_code)


# Notification Center & Channels
@app.get('/api/notifications')
def get_notifications(token: Optional[str] = Cookie(default=None, alias='yatraflow_session')):
    s = session_row(token); c = db()
    rows = [dict(r) for r in c.execute('SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 50', (s['user_id'],)).fetchall()]
    c.close()
    return {'items': rows}

@app.post('/api/notifications/read')
def mark_notifications_read(token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); c = db()
    c.execute('UPDATE notifications SET read=1 WHERE user_id=?', (s['user_id'],))
    c.commit(); c.close()
    return {'ok': True}

@app.post('/api/notifications/clear')
def clear_notifications(token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); c = db()
    c.execute('DELETE FROM notifications WHERE user_id=?', (s['user_id'],))
    c.commit(); c.close()
    return {'ok': True}

@app.get('/api/notifications/preferences')
def get_preferences(token: Optional[str] = Cookie(default=None, alias='yatraflow_session')):
    s = session_row(token); c = db()
    r = c.execute('SELECT * FROM notification_preferences WHERE user_id=?', (s['user_id'],)).fetchone()
    c.close()
    if not r:
        return {'preferences': {'email_enabled': True, 'whatsapp_enabled': False, 'push_enabled': True, 'flight_change': True, 'gate_change': True, 'connection_risk': True, 'boarding_reminder': True, 'transport_update': True, 'weather_alert': True, 'assistance_update': True}}
    d = dict(r)
    return {'preferences': {k: bool(v) for k, v in d.items() if k not in ('user_id', 'updated_at')}}

@app.post('/api/notifications/preferences')
def save_preferences(p: PreferencesIn, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); uid = s['user_id']; now = int(time.time()); c = db()
    c.execute('''
        INSERT INTO notification_preferences(user_id,email_enabled,whatsapp_enabled,push_enabled,flight_change,gate_change,connection_risk,boarding_reminder,transport_update,weather_alert,assistance_update,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
            email_enabled=excluded.email_enabled,
            whatsapp_enabled=excluded.whatsapp_enabled,
            push_enabled=excluded.push_enabled,
            flight_change=excluded.flight_change,
            gate_change=excluded.gate_change,
            connection_risk=excluded.connection_risk,
            boarding_reminder=excluded.boarding_reminder,
            transport_update=excluded.transport_update,
            weather_alert=excluded.weather_alert,
            assistance_update=excluded.assistance_update,
            updated_at=excluded.updated_at
    ''', (uid, int(p.email_enabled), int(p.whatsapp_enabled), int(p.push_enabled), int(p.flight_change), int(p.gate_change), int(p.connection_risk), int(p.boarding_reminder), int(p.transport_update), int(p.weather_alert), int(p.assistance_update), now))
    c.commit(); c.close()
    return {'ok': True}

@app.post('/api/notifications/test-email')
async def test_email(p: TestEmailIn, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); uid = s['user_id']
    ctx = {
        'name': s['name'],
        'flight_number': '6E 604',
        'margin_minutes': '8',
        'outbound_gate': 'B12',
        'old_gate': 'A04',
        'new_gate': 'B12',
        'api_base_url': API_BASE_URL
    }
    tmpl = get_email_template(p.event_type, ctx, lang=p.language)
    c = db()
    disp = await dispatch_automation_event(c, p.event_type, uid, ctx, channels=['email'], language=p.language)
    c.close()
    write_notification(uid, 'EMAIL', f"Email Sent ({p.language.upper()}): {tmpl['subject']}", f"Dispatched via YatraFlow notification engine.")
    return {'ok': True, 'subject': tmpl['subject'], 'html_preview': tmpl['html'], 'dispatch': disp}

@app.post('/api/notifications/test-whatsapp')
async def test_whatsapp(p: TestWhatsAppIn, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); uid = s['user_id']
    if not validate_phone_e164(p.phone):
        raise HTTPException(400, 'Invalid phone number. Use E.164 format (e.g. +919876543210).')
    ctx = {
        'flight_number': 'AI 201',
        'margin_minutes': '9',
        'gate': 'B12',
        'phone': p.phone
    }
    payload_msg = get_whatsapp_template_message('connection_risk_alert', p.phone, p.language, ['AI 201', '9 min', 'Gate B12'])
    c = db()
    disp = await dispatch_automation_event(c, p.event_type, uid, ctx, channels=['whatsapp'], language=p.language)
    c.close()
    write_notification(uid, 'WHATSAPP', f"WhatsApp Alert Dispatched to {p.phone}", "Payload conforming to Meta WhatsApp Business Cloud API specification.")
    return {'ok': True, 'template_payload': payload_msg, 'dispatch': disp}

@app.post('/api/whatsapp/send-otp')
def send_whatsapp_otp(p: SendOTPIn, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); uid = s['user_id']
    if not validate_phone_e164(p.phone):
        raise HTTPException(400, 'Invalid phone number. Use format +919876543210.')
    otp = generate_otp()
    otp_hash = th(otp)
    now = int(time.time())
    c = db()
    c.execute(
        'INSERT INTO whatsapp_otps(user_id,phone,otp_hash,created_at,expires_at) VALUES(?,?,?,?,?)',
        (uid, p.phone, otp_hash, now, now + 600)
    )
    c.commit(); c.close()
    write_notification(uid, 'WHATSAPP', 'WhatsApp Verification Code', f"Your 6-digit verification code is: {otp}. Valid for 10 minutes.")
    return {'ok': True, 'demo_otp': otp, 'message': f'Verification OTP sent to {p.phone}. Valid for 10 minutes.'}

@app.post('/api/whatsapp/verify-otp')
def verify_whatsapp_otp(p: VerifyOTPIn, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); uid = s['user_id']
    c = db()
    r = c.execute(
        'SELECT * FROM whatsapp_otps WHERE user_id=? AND phone=? AND verified=0 AND expires_at>? ORDER BY id DESC LIMIT 1',
        (uid, p.phone, int(time.time()))
    ).fetchone()
    if not r or not hmac.compare_digest(th(p.otp), r['otp_hash']):
        c.close(); raise HTTPException(400, 'Invalid or expired OTP code.')
    c.execute('UPDATE whatsapp_otps SET verified=1 WHERE id=?', (r['id'],))
    c.execute('UPDATE passenger_profiles SET whatsapp_verified=1, whatsapp_enabled=1, whatsapp_number=? WHERE user_id=?', (p.phone, uid))
    c.execute('UPDATE notification_preferences SET whatsapp_enabled=1 WHERE user_id=?', (uid,))
    c.commit(); c.close()
    write_notification(uid, 'WHATSAPP', 'WhatsApp Verified', f"Phone {p.phone} is now verified for real-time travel alerts.")
    return {'ok': True, 'message': 'WhatsApp number verified successfully!'}


# Profile, Bags, Assistance, Emergency
@app.get('/api/passenger/profile')
def get_passenger_profile(token: Optional[str] = Cookie(default=None, alias='yatraflow_session')):
    s = session_row(token); c = db()
    r = c.execute('SELECT * FROM passenger_profiles WHERE user_id=?', (s['user_id'],)).fetchone()
    c.close()
    if not r:
        return {'profile': {'phone': '', 'pnr': '', 'flight_id': '', 'accessibility': [], 'language': 'English', 'simple_mode': False, 'whatsapp_enabled': False, 'whatsapp_verified': False, 'google_connected': False}}
    d = dict(r)
    d['accessibility'] = json.loads(d.get('accessibility') or '[]')
    d['simple_mode'] = bool(d.get('simple_mode'))
    d['whatsapp_enabled'] = bool(d.get('whatsapp_enabled'))
    d['whatsapp_verified'] = bool(d.get('whatsapp_verified'))
    d['google_connected'] = bool(d.get('google_connected'))
    return {'profile': d}

@app.post('/api/passenger/profile')
def save_passenger_profile(p: ProfileIn, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); now = int(time.time()); c = db()
    c.execute('''
        INSERT INTO passenger_profiles(user_id,phone,pnr,flight_id,accessibility,language,simple_mode,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
            phone=excluded.phone,
            pnr=excluded.pnr,
            flight_id=excluded.flight_id,
            accessibility=excluded.accessibility,
            language=excluded.language,
            simple_mode=excluded.simple_mode,
            updated_at=excluded.updated_at
    ''', (s['user_id'], p.phone, p.pnr, p.flight_id, json.dumps(p.accessibility), p.language, int(p.simple_mode), now, now))
    c.commit(); c.close()
    return {'ok': True}

@app.get('/api/baggage')
def get_baggage(token: Optional[str] = Cookie(default=None, alias='yatraflow_session')):
    s = session_row(token); c = db()
    rows = [dict(r) for r in c.execute('SELECT * FROM bags WHERE user_id=? ORDER BY id DESC', (s['user_id'],)).fetchall()]
    c.close()
    if not rows:
        rows = [{'id': 0, 'tag': 'DEMO-1042', 'status': 'TRANSFER', 'last_location': 'Transfer Belt 3 (T3)', 'updated_at': int(time.time())}]
    return {'items': rows, 'source': 'DEMO OPERATIONAL FEED'}

@app.post('/api/baggage')
def add_baggage(p: BagIn, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); c = db()
    c.execute('INSERT INTO bags(user_id,tag,status,last_location,updated_at) VALUES(?,?,?,?,?)', (s['user_id'], p.tag, p.status.upper(), p.last_location, int(time.time())))
    c.commit(); c.close()
    return {'ok': True}

@app.get('/api/assistance')
def get_assistance_list(token: Optional[str] = Cookie(default=None, alias='yatraflow_session')):
    s = session_row(token); c = db()
    rows = [dict(r) for r in c.execute('SELECT * FROM assistance_requests WHERE user_id=? ORDER BY id DESC LIMIT 20', (s['user_id'],)).fetchall()]
    c.close()
    return {'items': rows}

@app.post('/api/assistance')
def request_assistance(p: AssistanceIn, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); c = db(); now = int(time.time())
    cur = c.execute(
        'INSERT INTO assistance_requests(user_id,type,priority,status,location,notes,created_at) VALUES(?,?,?,?,?,?,?)',
        (s['user_id'], p.type.upper(), p.priority.upper(), 'OPEN', p.location, p.notes, now)
    )
    rid = cur.lastrowid
    c.commit(); c.close()
    write_notification(s['user_id'], 'ASSISTANCE', 'Assistance Request Submitted', f"{p.type} assistance request #{rid} assigned to airport team.")
    return {'ok': True, 'request_id': rid}

@app.get('/api/emergency')
def get_emergency_status(token: Optional[str] = Cookie(default=None, alias='yatraflow_session')):
    s = session_row(token); c = db()
    rows = [dict(r) for r in c.execute('SELECT * FROM emergency_events WHERE user_id=? ORDER BY id DESC LIMIT 10', (s['user_id'],)).fetchall()]
    c.close()
    return {
        'emergency_number': '112',
        'airport_security': 'CISF Airport Security Control Room: 011-25652389 / 044-22563240',
        'items': rows
    }

@app.post('/api/emergency')
def create_emergency(p: EmergencyIn, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); c = db(); now = int(time.time())
    cur = c.execute(
        'INSERT INTO emergency_events(user_id,type,status,location,created_at) VALUES(?,?,?,?,?)',
        (s['user_id'], p.type.upper(), 'OPEN', p.location, now)
    )
    rid = cur.lastrowid
    c.commit(); c.close()
    write_notification(s['user_id'], 'EMERGENCY', 'Emergency Protocol Initiated', f"Event #{rid} created. National emergency number: 112.")
    return {
        'ok': True,
        'event_id': rid,
        'emergency_number': '112',
        'message': 'Confirm phone call to 112 on your device when ready.'
    }

@app.post('/api/simulation/event')
def run_simulation_event(p: SimulateIn, token: Optional[str] = Cookie(default=None, alias='yatraflow_session'), x_csrf: Optional[str] = Header(default=None, alias='X-CSRF-Token')):
    s = session_row(token); csrf_ok(s, x_csrf); typ = p.event_type.upper(); now = int(time.time())
    if typ in ('FLIGHT_DELAY', 'DELAY'):
        res = update_scenario(Scenario(delay=p.value), token, x_csrf)
    elif typ in ('BAGGAGE_DELAY', 'BAG_DELAY'):
        res = update_scenario(Scenario(baggage_delay=p.value), token, x_csrf)
    elif typ == 'CROWD':
        res = update_scenario(Scenario(crowd=min(100, p.value)), token, x_csrf)
    else:
        res = {'ok': True, 'state': state_payload(s['user_id'])}

    c = db()
    c.execute(
        'INSERT INTO simulation_events(user_id,event_type,payload,created_at) VALUES(?,?,?,?)',
        (s['user_id'], typ, json.dumps(p.model_dump()), now)
    )
    c.commit(); c.close()
    write_notification(s['user_id'], 'SIMULATION', f"Simulation Event: {typ}", f"Value applied: +{p.value}")
    return res

@app.get('/api/analytics')
def get_analytics(token: Optional[str] = Cookie(default=None, alias='yatraflow_session')):
    s = session_row(token); c = db()
    open_assist = c.execute("SELECT COUNT(*) FROM assistance_requests WHERE user_id=? AND status='OPEN'", (s['user_id'],)).fetchone()[0]
    emergencies = c.execute("SELECT COUNT(*) FROM emergency_events WHERE user_id=?", (s['user_id'],)).fetchone()[0]
    trips_count = c.execute("SELECT COUNT(*) FROM trips WHERE user_id=?", (s['user_id'],)).fetchone()[0]
    alerts_count = c.execute("SELECT COUNT(*) FROM fare_alerts WHERE user_id=?", (s['user_id'],)).fetchone()[0]
    bags_count = c.execute("SELECT COUNT(*) FROM bags WHERE user_id=?", (s['user_id'],)).fetchone()[0]
    c.close()
    return {
        'metrics': {
            'connection_monitoring': 1,
            'active_trips': trips_count,
            'fare_alerts_active': alerts_count,
            'open_assistance': open_assist,
            'emergency_events': emergencies,
            'bags_tracked': bags_count
        },
        'note': 'Operational metrics updated from local and provider data stores.'
    }

@app.get('/api/airport/contacts')
def airport_contacts():
    return {
        'airport': 'DEL (Indira Gandhi International) / MAA (Chennai)',
        'national_emergency': '112',
        'police_cisf': '011-25652389 / 044-22563240',
        'medical_emergency': '011-49652000 (Medanta T3 Clinic)',
        'lost_and_found': '011-49652222',
        'transit_hotel': {
            'name': 'Holiday Inn Express / Plaza Premium Transit Hotel',
            'terminal': 'Terminal 3 (Airside & Landside)',
            'phone': '+91-11-45252000'
        },
        'ground_transport': {
            'metro': 'Airport Express Metro (Orange Line)',
            'shuttle': 'Inter-Terminal Shuttle 24/7 (Free with ticket)',
            'prepaid_taxi': 'Traffic Police Prepaid Booth inside Arrivals'
        }
    }

@app.get('/api/airport/accessibility')
def airport_accessibility():
    return {
        'wheelchair_routes': True,
        'elevator_routing': True,
        'tactile_paving': True,
        'accessible_restrooms': True,
        'visual_alerts': True,
        'audio_navigation': True,
        'simple_mode': True,
        'language_support': ['English', 'Tamil', 'Hindi'],
        'note': 'Indoor step-by-step turn-by-turn routing is layerable on the live airport digital twin.'
    }


# WebSockets
@app.websocket('/ws/live')
async def ws_live(ws: WebSocket):
    await ws.accept()
    CLIENTS.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        CLIENTS.discard(ws)
    except Exception:
        CLIENTS.discard(ws)


# PWA & Capacitor Config Endpoints
@app.get('/manifest.webmanifest')
def get_manifest():
    return FileResponse(FRONT / 'manifest.webmanifest', media_type='application/manifest+json')

@app.get('/sw.js')
def get_sw():
    return FileResponse(FRONT / 'sw.js', media_type='application/javascript')

@app.get('/capacitor.config.json')
def get_capacitor_config():
    cfg = BASE / 'capacitor.config.json'
    if cfg.exists():
        return FileResponse(cfg, media_type='application/json')
    return {'appId': 'ai.yatraflow.app', 'appName': 'YatraFlow', 'webDir': 'frontend'}


# Static Files
@app.get('/')
def home():
    return FileResponse(FRONT / 'index.html')

@app.get('/{path:path}')
def static_handler(path: str):
    requested = (FRONT / path).resolve()
    if str(requested).startswith(str(FRONT.resolve())) and requested.exists() and requested.is_file():
        return FileResponse(requested)
    return FileResponse(FRONT / 'index.html')
