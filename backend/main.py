from __future__ import annotations
import asyncio, hashlib, hmac, json, math, os, secrets, sqlite3, time, urllib.parse, urllib.request, datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response, Cookie, Header, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

BASE = Path(__file__).resolve().parent.parent
load_dotenv(BASE / '.env')

FRONT = BASE / 'frontend'; DATA = BASE / 'data'; DATA.mkdir(exist_ok=True)
DB = DATA / 'guardian.db'
VERSION = '2.1.0'
SESSION_TTL = 8 * 60 * 60
SECURE_COOKIE = os.getenv('COOKIE_SECURE', '0') == '1'
AVIATIONSTACK_KEY = os.getenv('AVIATIONSTACK_API_KEY', '').strip()
OPEN_METEO_ENABLED = os.getenv('OPEN_METEO_ENABLED', '1') != '0'
REFRESH_SECONDS = max(30, int(os.getenv('REFRESH_SECONDS', '60')))
OPEN_SKY_ENABLED = os.getenv('OPEN_SKY_ENABLED', '1') != '0'
AIRPORT_BBOXES = {
    'DEL': {'lamin': 28.30, 'lomin': 76.80, 'lamax': 28.85, 'lomax': 77.45},
    'MAA': {'lamin': 12.85, 'lomin': 80.05, 'lamax': 13.25, 'lomax': 80.35},
    'BOM': {'lamin': 18.90, 'lomin': 72.75, 'lamax': 19.30, 'lomax': 73.15},
    'BLR': {'lamin': 13.05, 'lomin': 77.55, 'lamax': 13.35, 'lomax': 77.85},
}
_OPEN_SKY_CACHE: dict[str, tuple[float, dict]] = {}
OPEN_SKY_CACHE_TTL = 15
OPEN_SKY_BBOX = AIRPORT_BBOXES['DEL']

SUPABASE_URL = os.getenv('SUPABASE_URL', '').strip()
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '').strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '').strip()
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000').strip()

LIVE_FLIGHTS: list[dict] = []
LIVE_FLIGHTS_UPDATED = 0

app = FastAPI(title='YatraFlow', version=VERSION, docs_url='/api/docs', redoc_url=None)

# Dynamic CORS setup supporting local development, API_BASE_URL, and production env
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

app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
RATE: dict[str, list[float]] = {}
CLIENTS: set[WebSocket] = set()

# Demo data is intentionally transparent: it is synthetic airport/operational data for a complete local demo.
FLIGHTS = [
    {'id':'6E604','airline':'IndiGo','number':'6E 604','from':'MAA','to':'DEL','from_name':'Chennai','to_name':'Delhi','dep':'08:10','arr':'11:05','terminal':'T1','gate':'A04','status':'On time','delay':0},
    {'id':'AI201','airline':'Air India','number':'AI 201','from':'DEL','to':'LHR','from_name':'Delhi','to_name':'London','dep':'11:55','arr':'16:40','terminal':'T3','gate':'B12','status':'On time','delay':0},
    {'id':'6E6817','airline':'IndiGo','number':'6E 6817','from':'MAA','to':'BOM','from_name':'Chennai','to_name':'Mumbai','dep':'10:25','arr':'12:20','terminal':'T2','gate':'C07','status':'On time','delay':0},
    {'id':'AI642','airline':'Air India','number':'AI 642','from':'BOM','to':'DEL','from_name':'Mumbai','to_name':'Delhi','dep':'13:10','arr':'15:20','terminal':'T2','gate':'D08','status':'On time','delay':0},
    {'id':'6E112','airline':'IndiGo','number':'6E 112','from':'DEL','to':'BLR','from_name':'Delhi','to_name':'Bengaluru','dep':'12:20','arr':'15:10','terminal':'T1','gate':'A11','status':'On time','delay':0},
]

# Delhi-style indoor digital twin used for the prototype. Nodes represent passenger-accessible zones.
ZONES = {
    'A04': {'name':'Gate A04','x':18,'y':67,'terminal':'T3','type':'gate'},
    'Security': {'name':'Security','x':43,'y':52,'terminal':'T3','type':'security'},
    'Immigration': {'name':'Immigration','x':55,'y':35,'terminal':'T3','type':'immigration'},
    'Baggage': {'name':'Baggage Hall','x':74,'y':64,'terminal':'T3','type':'baggage'},
    'B12': {'name':'Gate B12','x':84,'y':27,'terminal':'T3','type':'gate'},
    'Ground': {'name':'Ground Transport','x':80,'y':84,'terminal':'T3','type':'ground'},
    'HelpDesk': {'name':'Connection Desk','x':57,'y':72,'terminal':'T3','type':'support'},
}
ROUTES = {
    'A04': {'Security':7,'HelpDesk':8}, 'Security':{'A04':7,'Immigration':5,'HelpDesk':5},
    'Immigration':{'Security':5,'B12':9,'Baggage':7}, 'Baggage':{'Immigration':7,'B12':8,'Ground':5},
    'B12':{'Immigration':9,'Baggage':8,'Ground':6}, 'HelpDesk':{'A04':8,'Security':5,'Ground':6},
    'Ground':{'B12':6,'Baggage':5,'HelpDesk':6}
}

class Login(BaseModel): email: EmailStr; password: str = Field(min_length=1, max_length=128)
class Register(BaseModel): name: str = Field(min_length=2, max_length=80); email: EmailStr; password: str = Field(min_length=8, max_length=128)
class Setup(BaseModel): inbound_id: str; outbound_id: str; passenger_zone: str = 'A04'; bags: int = Field(default=1, ge=0, le=8); immigration: bool = False
class Position(BaseModel): zone: str
class Scenario(BaseModel): delay: int = Field(default=0, ge=0, le=240); gate_change: Optional[str] = None; baggage_delay: int = Field(default=0, ge=0, le=60); crowd: int = Field(default=50, ge=0, le=100)


def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def limit(key: str, n=20, window=60):
    now=time.time(); vals=[x for x in RATE.get(key,[]) if now-x<window]
    if len(vals)>=n: raise HTTPException(429,'Too many requests. Try again shortly.')
    vals.append(now); RATE[key]=vals

def hash_pw(pw,salt=None):
    salt=salt or secrets.token_bytes(16); return hashlib.scrypt(pw.encode(),salt=salt,n=2**14,r=8,p=1,dklen=32).hex(),salt.hex()
def verify_pw(pw,h,s): return hmac.compare_digest(hashlib.scrypt(pw.encode(),salt=bytes.fromhex(s),n=2**14,r=8,p=1,dklen=32).hex(),h)
def th(t): return hashlib.sha256(t.encode()).hexdigest()

def init_db():
    c=db(); c.executescript('''
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,password_hash TEXT NOT NULL,salt TEXT NOT NULL,created_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL,csrf TEXT NOT NULL,created_at INTEGER NOT NULL,expires_at INTEGER NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS connection_sessions(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,inbound_id TEXT NOT NULL,outbound_id TEXT NOT NULL,zone TEXT NOT NULL,bags INTEGER NOT NULL,immigration INTEGER NOT NULL,scenario TEXT NOT NULL,created_at INTEGER NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);

    CREATE TABLE IF NOT EXISTS passenger_profiles(user_id INTEGER PRIMARY KEY,phone TEXT DEFAULT '',pnr TEXT DEFAULT '',flight_id TEXT DEFAULT '',accessibility TEXT DEFAULT '[]',language TEXT DEFAULT 'English',simple_mode INTEGER DEFAULT 0,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS bags(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,tag TEXT NOT NULL,status TEXT NOT NULL,last_location TEXT NOT NULL,updated_at INTEGER NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS transport(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,vehicle_no TEXT NOT NULL,route TEXT NOT NULL,pickup TEXT NOT NULL,destination TEXT NOT NULL,lat REAL DEFAULT 0,lon REAL DEFAULT 0,eta INTEGER DEFAULT 0,status TEXT DEFAULT 'AVAILABLE',updated_at INTEGER NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS assistance_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,type TEXT NOT NULL,priority TEXT NOT NULL,status TEXT NOT NULL,location TEXT NOT NULL,notes TEXT DEFAULT '',created_at INTEGER NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS emergency_events(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,type TEXT NOT NULL,status TEXT NOT NULL,location TEXT NOT NULL,created_at INTEGER NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,type TEXT NOT NULL,title TEXT NOT NULL,message TEXT NOT NULL,read INTEGER DEFAULT 0,created_at INTEGER NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS simulation_events(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,event_type TEXT NOT NULL,payload TEXT NOT NULL,created_at INTEGER NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    '''); c.commit(); c.close()

def session_row(token):
    if not token: raise HTTPException(401,'Please sign in again.')
    c=db(); r=c.execute('SELECT s.*,u.email,u.name FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?',(th(token),int(time.time()))).fetchone(); c.close()
    if not r: raise HTTPException(401,'Your session has expired. Please sign in again.')
    return r

def csrf_ok(s,h):
    if not h or not hmac.compare_digest(h,s['csrf']): raise HTTPException(403,'Security check failed. Refresh the page.')
def set_cookie(resp,token): resp.set_cookie('yatraflow_session',token,httponly=True,secure=SECURE_COOKIE,samesite='lax',max_age=SESSION_TTL,path='/')
def new_session(uid):
    token=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(24); now=int(time.time()); c=db(); c.execute('INSERT INTO sessions VALUES(?,?,?,?,?)',(th(token),uid,csrf,now,now+SESSION_TTL)); c.execute('DELETE FROM sessions WHERE expires_at<?',(now,)); c.commit(); c.close(); return token,csrf

def http_json(url,timeout=8):
    req=urllib.request.Request(url,headers={'User-Agent':'AirportConnectionYatraFlow/1.0'})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read().decode())

def _iso_minutes(value: str | None) -> str:
    if not value:
        return ''
    return value[11:16] if len(value) >= 16 else value

def _map_aviationstack(x: dict) -> dict:
    f=x.get('flight',{}); dep=x.get('departure',{}); arr=x.get('arrival',{}); live=x.get('live') or {}
    number=f.get('iata') or f.get('number') or '—'
    return {
        'id': f"live-{f.get('icao') or number}-{x.get('flight_date') or ''}",
        'airline': (x.get('airline') or {}).get('name') or 'Unknown',
        'number': number,
        'from': dep.get('iata') or dep.get('icao') or '—',
        'to': arr.get('iata') or arr.get('icao') or '—',
        'from_name': dep.get('airport') or dep.get('iata') or '—',
        'to_name': arr.get('airport') or arr.get('iata') or '—',
        'dep': _iso_minutes(dep.get('scheduled') or dep.get('estimated')),
        'arr': _iso_minutes(arr.get('scheduled') or arr.get('estimated')),
        'terminal': dep.get('terminal') or arr.get('terminal') or '—',
        'gate': dep.get('gate') or arr.get('gate') or '—',
        'status': x.get('flight_status') or 'unknown',
        'delay': int(round((dep.get('delay') or 0))),
        'scheduled_departure': dep.get('scheduled'),
        'estimated_departure': dep.get('estimated'),
        'scheduled_arrival': arr.get('scheduled'),
        'estimated_arrival': arr.get('estimated'),
        'latitude': live.get('latitude'),
        'longitude': live.get('longitude'),
        'altitude_m': live.get('altitude'),
        'speed_kmh': round((live.get('speed_horizontal') or 0) * 1.852, 1) if live.get('speed_horizontal') else None,
        'source': 'Aviationstack',
        'updated': int(time.time())
    }

def flight_data(query: str = ''):
    global LIVE_FLIGHTS, LIVE_FLIGHTS_UPDATED
    if not AVIATIONSTACK_KEY:
        return {
            'success': False,
            'provider': 'aviationstack',
            'error': 'AviationStack unavailable',
            'items': FLIGHTS,
            'live': False,
            'source': 'Demo airport data',
            'message': 'Set AVIATIONSTACK_API_KEY for live flight-status polling.',
            'updated': int(time.time())
        }
    try:
        params = {'access_key': AVIATIONSTACK_KEY, 'limit': 100}
        q = query.strip().upper()
        if q:
            params['flight_iata'] = q
        else:
            params['dep_iata'] = 'DEL'
        query_str = urllib.parse.urlencode(params)

        d = None
        last_error = None
        for proto in ('https', 'http'):
            try:
                d = http_json(f'{proto}://api.aviationstack.com/v1/flights?{query_str}', 12)
                if isinstance(d, dict):
                    break
            except Exception as ex:
                last_error = ex
                continue

        if not d and last_error:
            raise last_error

        if not isinstance(d, dict):
            raise ValueError('Invalid response received from provider')

        if 'error' in d and isinstance(d['error'], dict):
            raw_err = d['error'].get('info') or d['error'].get('message') or d['error'].get('code') or 'AviationStack API error'
            clean_err = str(raw_err).replace(AVIATIONSTACK_KEY, '[REDACTED]')
            return {
                'success': False,
                'provider': 'aviationstack',
                'error': 'AviationStack unavailable',
                'message': clean_err or 'AviationStack reported an issue; using cached/demo flight data.',
                'items': LIVE_FLIGHTS or FLIGHTS,
                'live': bool(LIVE_FLIGHTS),
                'source': 'Aviationstack cache' if LIVE_FLIGHTS else 'Demo airport data',
                'updated': LIVE_FLIGHTS_UPDATED or int(time.time())
            }

        items = [_map_aviationstack(x) for x in d.get('data', []) if isinstance(x, dict)]
        if items:
            LIVE_FLIGHTS = items
            LIVE_FLIGHTS_UPDATED = int(time.time())
            return {
                'success': True,
                'provider': 'aviationstack',
                'items': items,
                'live': True,
                'source': 'Aviationstack',
                'updated': LIVE_FLIGHTS_UPDATED
            }
        return {
            'success': True,
            'provider': 'aviationstack',
            'items': FLIGHTS,
            'live': False,
            'source': 'Aviationstack',
            'message': 'Provider returned no matching flights.',
            'updated': int(time.time())
        }
    except Exception as e:
        clean_err = str(e).replace(AVIATIONSTACK_KEY, '[REDACTED]') if AVIATIONSTACK_KEY else ''
        return {
            'success': False,
            'provider': 'aviationstack',
            'error': 'AviationStack unavailable',
            'message': clean_err or 'Live provider unavailable; using transparent demo data.',
            'items': LIVE_FLIGHTS or FLIGHTS,
            'live': bool(LIVE_FLIGHTS),
            'source': 'Aviationstack cache' if LIVE_FLIGHTS else 'Demo airport data',
            'updated': LIVE_FLIGHTS_UPDATED or int(time.time())
        }

def open_sky(airport: str = 'DEL') -> dict:
    if not OPEN_SKY_ENABLED:
        return {'success': False, 'provider': 'opensky', 'items': [], 'live': False, 'source': 'disabled', 'airport': airport, 'updated': int(time.time())}

    now = time.time()
    cached = _OPEN_SKY_CACHE.get(airport)
    if cached and (now - cached[0] < OPEN_SKY_CACHE_TTL):
        return cached[1]

    try:
        bbox = AIRPORT_BBOXES.get(airport, AIRPORT_BBOXES['DEL'])
        q = urllib.parse.urlencode(bbox)
        d = http_json('https://opensky-network.org/api/states/all?' + q, 10)
        rows = []
        stamp = d.get('time') if isinstance(d, dict) else None
        for x in (d.get('states') or [] if isinstance(d, dict) else []):
            if len(x) < 12:
                continue
            rows.append({
                'icao24': x[0],
                'callsign': (x[1] or '').strip(),
                'longitude': x[5],
                'latitude': x[6],
                'altitude_m': x[7],
                'on_ground': bool(x[8]),
                'velocity_ms': x[9],
                'heading': x[10],
                'vertical_rate_ms': x[11],
                'updated_at': datetime.datetime.fromtimestamp(stamp, datetime.timezone.utc).isoformat() if stamp else None
            })
        result = {'success': True, 'provider': 'opensky', 'items': rows, 'live': bool(rows), 'source': 'OpenSky Network', 'airport': airport, 'updated': int(time.time())}
        _OPEN_SKY_CACHE[airport] = (now, result)
        return result
    except Exception as e:
        if cached:
            return cached[1]
        return {'success': False, 'provider': 'opensky', 'error': 'OpenSky unavailable', 'items': [], 'live': False, 'source': 'OpenSky Network', 'airport': airport, 'updated': int(time.time())}

def weather():
    if not OPEN_METEO_ENABLED: return {'live':False,'source':'disabled'}
    try:
        q=urllib.parse.urlencode({'latitude':28.5562,'longitude':77.1000,'current':'temperature_2m,precipitation,wind_speed_10m,weather_code','timezone':'Asia/Kolkata'})
        d=http_json('https://api.open-meteo.com/v1/forecast?'+q); cur=d.get('current',{})
        return {'live':True,'source':'Open-Meteo','temperature':cur.get('temperature_2m'),'precipitation':cur.get('precipitation'),'wind':cur.get('wind_speed_10m'),'code':cur.get('weather_code'),'updated':int(time.time())}
    except Exception as e: return {'live':False,'source':'unavailable','error':str(e)}

def get_session_state(uid):
    c=db(); r=c.execute('SELECT * FROM connection_sessions WHERE user_id=? ORDER BY id DESC LIMIT 1',(uid,)).fetchone(); c.close()
    if not r: return None
    try: scenario=json.loads(r['scenario'])
    except: scenario={}
    return {'id':r['id'],'inbound_id':r['inbound_id'],'outbound_id':r['outbound_id'],'zone':r['zone'],'bags':r['bags'],'immigration':bool(r['immigration']),'scenario':scenario}

def flight_by_id(fid):
    hit = next((f for f in LIVE_FLIGHTS if f['id']==fid), None)
    if hit:
        return hit
    hit = next((f for f in FLIGHTS if f['id']==fid), None)
    if hit:
        return hit
    if fid.startswith('live-') and AVIATIONSTACK_KEY:
        parts=fid.split('-')
        if len(parts) >= 2:
            q=parts[1]
            try:
                rows=flight_data(q).get('items',[])
                return next((f for f in rows if f.get('id')==fid or f.get('number','').replace(' ','').upper()==q.replace(' ','')), None)
            except Exception:
                return None
    return None

def minutes(hm):
    if not hm:
        raise ValueError('Missing flight time')
    raw=hm[11:16] if len(hm)>=16 and hm[4]=='-' else hm[:5]
    h,m=map(int,raw.split(':')); return h*60+m

def safe_minutes(hm, fallback=0):
    try: return minutes(hm)
    except Exception: return fallback

def connection_engine(inbound,outbound,zone,bags,immigration,scenario):
    inbound=dict(inbound); outbound=dict(outbound)
    delay=int(scenario.get('delay',0)); baggage_delay=int(scenario.get('baggage_delay',0)); crowd=int(scenario.get('crowd',50)); gate_change=scenario.get('gate_change')
    inbound_arr=safe_minutes(inbound.get('arr'), 0)
    outbound_dep=safe_minutes(outbound.get('dep'), inbound_arr + 60)
    # Handle connections that cross midnight.
    if outbound_dep <= inbound_arr:
        outbound_dep += 24*60
    inbound['arrival_minutes']=inbound_arr+delay
    outbound_gate=gate_change or outbound.get('gate','B12') or 'B12'
    boarding_close=outbound_dep-15
    available=max(0,boarding_close-inbound['arrival_minutes'])
    # Base transfer components in minutes. Crowd changes walking/security slightly.
    walk=ROUTES.get(zone,{}).get(outbound_gate, 15)
    if walk is None: walk=15
    walk=round(walk*(1+max(0,crowd-50)/250),1)
    security=8 + round(max(0,crowd-50)/25)
    immigration_time=10 if immigration else 0
    baggage=10 + baggage_delay if bags else 0
    buffer=5
    required=walk+security+immigration_time+baggage+buffer
    margin=available-required
    risk=max(0,min(99, round(50 - margin*3.4 + crowd*.18 + (10 if bags else 0))))
    if margin >= 12: level='SAFE'
    elif margin >= 0: level='TIGHT'
    elif margin >= -10: level='AT RISK'
    else: level='LIKELY MISSED'
    actions=[]
    if level in ('AT RISK','LIKELY MISSED'):
        actions=['Proceed directly to the connection route','Avoid non-essential airport stops']
        if bags: actions.append('Check baggage transfer status at the connection desk')
        if immigration: actions.append('Use the fastest available immigration lane')
        actions.append('Prepare airline connection support / rebooking options')
    else: actions=['Continue to the assigned gate','Keep boarding pass ready','Watch for gate or delay updates']
    return {'bags':bags,'immigration':immigration,'level':level,'risk':risk,'available_minutes':available,'required_minutes':round(required,1),'margin_minutes':round(margin,1),'walk_minutes':walk,'security_minutes':security,'immigration_minutes':immigration_time,'baggage_minutes':baggage,'buffer_minutes':buffer,'outbound_gate':outbound_gate,'boarding_close':f"{outbound.get('dep','—')} - 15 min",'actions':actions,'inbound_delay':delay,'crowd':crowd,'baggage_status':'At risk' if baggage_delay>10 else 'Transfer expected','message':{'SAFE':'Your connection has a healthy time buffer.','TIGHT':'Your connection is possible, but avoid delays.','AT RISK':'Your connection is at risk. Follow the rescue plan.','LIKELY MISSED':'The current transfer window is insufficient; recovery should be prepared.'}[level]}

def graph_route(start,goal):
    if start==goal:return [start],0
    dist={k:math.inf for k in ZONES}; prev={}; dist[start]=0; seen=set()
    while len(seen)<len(ZONES):
        u=min((k for k in ZONES if k not in seen),key=lambda k:dist[k],default=None)
        if u is None or dist[u]==math.inf:break
        seen.add(u)
        for v,w in ROUTES.get(u,{}).items():
            nd=dist[u]+w
            if nd<dist[v]: dist[v]=nd; prev[v]=u
    if goal not in prev and goal!=start:return [start,goal],15
    path=[]; x=goal
    while x!=start:path.append(x);x=prev[x]
    path.append(start);path.reverse();return path,round(dist[goal],1)

def state_payload(uid):
    s=get_session_state(uid)
    if not s:
        s={'inbound_id':'6E604','outbound_id':'AI201','zone':'A04','bags':1,'immigration':False,'scenario':{'delay':0,'gate_change':None,'baggage_delay':0,'crowd':50}}
    inbound=flight_by_id(s['inbound_id']) or FLIGHTS[0]; outbound=flight_by_id(s['outbound_id']) or FLIGHTS[1]
    # Live flight records drive the connection engine when available; the airport digital twin remains deterministic.
    engine=connection_engine(inbound,outbound,s['zone'],s['bags'],s['immigration'],s['scenario'])
    path,eta=graph_route(s['zone'],engine['outbound_gate'])
    rec=engine.copy(); rec['route']=path; rec['route_eta']=eta
    scenario_view={**s['scenario'],'bags':s['bags'],'immigration':s['immigration']}
    airport_code = outbound.get('from') or inbound.get('to') or 'DEL'
    sky = open_sky(airport_code if airport_code in AIRPORT_BBOXES else 'DEL')
    return {'inbound':inbound,'outbound':outbound,'engine':rec,'position':ZONES.get(s['zone'],ZONES['A04']),'zone':s['zone'],'zones':ZONES,'route_edges':ROUTES,'scenario':scenario_view,'weather':weather(),'airspace':sky,'flights':(LIVE_FLIGHTS or FLIGHTS),'source':{'flights':'Aviationstack' if (LIVE_FLIGHTS and AVIATIONSTACK_KEY) else ('Aviationstack unavailable' if AVIATIONSTACK_KEY else 'Demo airport data'),'airspace':'OpenSky Network' if sky.get('live') else 'OpenSky standby','weather':'Open-Meteo','indoor':'Airport Digital Twin demo','baggage':'Demo operational feed','ground':'Demo transport feed'},'updated':{'flights':LIVE_FLIGHTS_UPDATED,'weather':int(time.time()),'airspace':sky.get('updated',int(time.time()))}}

@app.middleware('http')
async def security(request,call_next):
    r=await call_next(request)
    r.headers.update({'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'strict-origin-when-cross-origin','Permissions-Policy':'geolocation=(self),camera=(),microphone=()','Content-Security-Policy':"default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-src 'self' https://www.openstreetmap.org; connect-src 'self' ws: wss: https://api.open-meteo.com https://api.aviationstack.com http://api.aviationstack.com https://opensky-network.org; frame-ancestors 'none'"})
    if request.url.path.startswith('/api/'):r.headers['Cache-Control']='no-store'
    return r

@app.on_event('startup')
async def startup():
    init_db(); c=db();
    if not c.execute('SELECT id FROM users WHERE email=?',('demo@yatraflow.ai',)).fetchone():
        h,s=hash_pw('YatraFlow@123'); c.execute('INSERT INTO users(email,name,password_hash,salt,created_at) VALUES(?,?,?,?,?)',('demo@yatraflow.ai','Demo Traveller',h,s,int(time.time()))); c.commit()
    c.close(); asyncio.create_task(broadcast_loop())
    if AVIATIONSTACK_KEY:
        try: await asyncio.to_thread(flight_data)
        except Exception: pass

async def broadcast(msg):
    for ws in list(CLIENTS):
        try: await ws.send_json(msg)
        except: CLIENTS.discard(ws)

async def broadcast_loop():
    while True:
        await asyncio.sleep(REFRESH_SECONDS)
        try:
            fd = await asyncio.to_thread(flight_data) if AVIATIONSTACK_KEY else {'items':FLIGHTS,'live':False,'source':'Demo airport data','updated':int(time.time())}
            sky = await asyncio.to_thread(open_sky, 'DEL')
            w = await asyncio.to_thread(weather)
            await broadcast({'type':'heartbeat','time':int(time.time()),'weather':w,'flights':fd,'airspace':sky})
        except Exception:
            pass

@app.get('/api/health')
def health(): return {'ok':True,'app':'YatraFlow','version':VERSION,'live_flight_provider':bool(AVIATIONSTACK_KEY),'weather_provider':OPEN_METEO_ENABLED}

@app.post('/api/register')
def register(p:Register,request:Request,response:Response):
    limit('register:'+str(request.client.host),5,300); email=p.email.lower().strip()
    if not(any(x.islower() for x in p.password) and any(x.isupper() for x in p.password) and any(x.isdigit() for x in p.password)): raise HTTPException(400,'Use uppercase, lowercase and a number.')
    h,s=hash_pw(p.password); c=db()
    try: cur=c.execute('INSERT INTO users(email,name,password_hash,salt,created_at) VALUES(?,?,?,?,?)',(email,p.name.strip(),h,s,int(time.time()))); c.commit();uid=cur.lastrowid
    except sqlite3.IntegrityError: c.close(); raise HTTPException(409,'An account with this email already exists.')
    c.close();tok,csrf=new_session(uid);set_cookie(response,tok);return {'ok':True,'csrf':csrf}

@app.post('/api/login')
def login(p:Login,request:Request,response:Response):
    limit('login:'+str(request.client.host),10,300);c=db();r=c.execute('SELECT * FROM users WHERE email=?',(p.email.lower().strip(),)).fetchone();c.close()
    if not r or not verify_pw(p.password,r['password_hash'],r['salt']):raise HTTPException(401,'Email or password is incorrect.')
    tok,csrf=new_session(r['id']);set_cookie(response,tok);return {'ok':True,'csrf':csrf}

@app.post('/api/logout')
def logout(response:Response,token:Optional[str]=Cookie(default=None,alias='yatraflow_session')):
    if token:
        c=db();c.execute('DELETE FROM sessions WHERE token_hash=?',(th(token),));c.commit();c.close()
    response.delete_cookie('yatraflow_session',path='/');return {'ok':True}

@app.get('/api/state')
def state(token:Optional[str]=Cookie(default=None,alias='yatraflow_session')):
    s=session_row(token);return {'user':{'name':s['name'],'email':s['email'],'csrf':s['csrf']},'state':state_payload(s['user_id'])}

@app.post('/api/connection/setup')
def setup(p:Setup,token:Optional[str]=Cookie(default=None,alias='yatraflow_session'),x_csrf:Optional[str]=Header(default=None,alias='X-CSRF-Token')):
    s=session_row(token);csrf_ok(s,x_csrf)
    if p.inbound_id==p.outbound_id:raise HTTPException(400,'Choose two different flights.')
    if not flight_by_id(p.inbound_id) or not flight_by_id(p.outbound_id):raise HTTPException(404,'Flight not found.')
    if p.passenger_zone not in ZONES:raise HTTPException(400,'Unknown airport zone.')
    scenario={'delay':0,'gate_change':None,'baggage_delay':0,'crowd':50}
    c=db();c.execute('INSERT INTO connection_sessions(user_id,inbound_id,outbound_id,zone,bags,immigration,scenario,created_at) VALUES(?,?,?,?,?,?,?,?)',(s['user_id'],p.inbound_id,p.outbound_id,p.passenger_zone,p.bags,int(p.immigration),json.dumps(scenario),int(time.time())));c.commit();c.close()
    return {'ok':True,'state':state_payload(s['user_id'])}

@app.post('/api/position')
def position(p:Position,token:Optional[str]=Cookie(default=None,alias='yatraflow_session'),x_csrf:Optional[str]=Header(default=None,alias='X-CSRF-Token')):
    s=session_row(token);csrf_ok(s,x_csrf)
    if p.zone not in ZONES:raise HTTPException(400,'Unknown airport zone.')
    c=db();r=c.execute('SELECT id FROM connection_sessions WHERE user_id=? ORDER BY id DESC LIMIT 1',(s['user_id'],)).fetchone()
    if not r:raise HTTPException(400,'Set up a connection first.')
    c.execute('UPDATE connection_sessions SET zone=? WHERE id=?',(p.zone,r['id']));c.commit();c.close();return {'ok':True,'state':state_payload(s['user_id'])}

@app.post('/api/scenario')
def scenario(p:Scenario,token:Optional[str]=Cookie(default=None,alias='yatraflow_session'),x_csrf:Optional[str]=Header(default=None,alias='X-CSRF-Token')):
    s=session_row(token);csrf_ok(s,x_csrf);c=db();r=c.execute('SELECT * FROM connection_sessions WHERE user_id=? ORDER BY id DESC LIMIT 1',(s['user_id'],)).fetchone()
    if not r: raise HTTPException(400,'Set up a connection first.')
    old=json.loads(r['scenario']); merged={**old,**p.model_dump(exclude_none=True)}
    c.execute('UPDATE connection_sessions SET scenario=? WHERE id=?',(json.dumps(merged),r['id']));c.commit();c.close();return {'ok':True,'state':state_payload(s['user_id'])}

@app.get('/api/flights')
def flights(token:Optional[str]=Cookie(default=None,alias='yatraflow_session')):
    session_row(token);return flight_data()

@app.get('/api/flights/search')
def flight_search(q:str='',token:Optional[str]=Cookie(default=None,alias='yatraflow_session')):
    session_row(token)
    return flight_data(q)

@app.get('/api/airspace')
def airspace(airport: str = 'DEL', token: Optional[str] = Cookie(default=None, alias='yatraflow_session')):
    session_row(token)
    return open_sky(airport if airport in AIRPORT_BBOXES else 'DEL')


# ---------------- GPS live position ----------------

class GPSIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    accuracy: float = Field(default=0, ge=0, le=100000)

@app.post('/api/position/gps')
def update_gps(p:GPSIn, token:Optional[str]=Cookie(default=None,alias='yatraflow_session'), x_csrf:Optional[str]=Header(default=None,alias='X-CSRF-Token')):
    s=auth_user(token); csrf_ok(s,x_csrf)
    # Keep GPS as a transient location signal. The existing position engine remains authoritative for demo gate zones.
    return {'ok':True,'state':state_payload(s['user_id']),'gps':{'lat':p.lat,'lon':p.lon,'accuracy':p.accuracy,'updated_at':int(time.time())}}

# ---------------- YatraFlow integrated platform APIs ----------------

class ProfileIn(BaseModel):
    phone: str = Field(default='', max_length=30)
    pnr: str = Field(default='', max_length=30)
    flight_id: str = Field(default='', max_length=80)
    accessibility: list[str] = Field(default_factory=list, max_length=12)
    language: str = Field(default='English', max_length=30)
    simple_mode: bool = False

class BagIn(BaseModel):
    tag: str = Field(min_length=2, max_length=40)
    status: str = Field(default='CHECKED_IN', max_length=30)
    last_location: str = Field(default='Check-in', max_length=100)

class TransportIn(BaseModel):
    vehicle_no: str = Field(min_length=1, max_length=30)
    route: str = Field(default='Airport Shuttle', max_length=100)
    pickup: str = Field(default='Terminal', max_length=100)
    destination: str = Field(default='Gate / Parking', max_length=100)
    lat: float = 0
    lon: float = 0
    eta: int = Field(default=10, ge=0, le=300)

class AssistanceIn(BaseModel):
    type: str = Field(min_length=2, max_length=50)
    priority: str = Field(default='NORMAL', max_length=20)
    location: str = Field(default='Current location', max_length=100)
    notes: str = Field(default='', max_length=300)

class EmergencyIn(BaseModel):
    type: str = Field(default='GENERAL', max_length=40)
    location: str = Field(default='Current location', max_length=100)

class SimulateIn(BaseModel):
    event_type: str = Field(min_length=2, max_length=50)
    value: int = Field(default=0, ge=0, le=240)

def auth_user(token):
    return session_row(token)

def write_notification(uid, typ, title, message):
    c=db()
    c.execute('INSERT INTO notifications(user_id,type,title,message,read,created_at) VALUES(?,?,?,?,0,?)',
              (uid,typ,title,message,int(time.time())))
    c.commit(); c.close()

@app.get('/api/platform/overview')
def platform_overview(token:Optional[str]=Cookie(default=None,alias='yatraflow_session')):
    s=auth_user(token); uid=s['user_id']
    state = state_payload(uid)
    c=db()
    counts = {
        'assistance': c.execute("SELECT COUNT(*) FROM assistance_requests WHERE user_id=? AND status!='RESOLVED'",(uid,)).fetchone()[0],
        'emergency': c.execute("SELECT COUNT(*) FROM emergency_events WHERE user_id=? AND status!='CLOSED'",(uid,)).fetchone()[0],
        'notifications': c.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND read=0",(uid,)).fetchone()[0],
        'bags': c.execute("SELECT COUNT(*) FROM bags WHERE user_id=?",(uid,)).fetchone()[0],
        'transport': c.execute("SELECT COUNT(*) FROM transport WHERE user_id=?",(uid,)).fetchone()[0],
    }
    c.close()
    return {
        'product':'YatraFlow',
        'version':VERSION,
        'state':state,
        'modules':{
            'flight_monitoring':'LIVE' if AVIATIONSTACK_KEY else 'DEMO',
            'connection_engine':'LIVE ENGINE',
            'navigation':'DIGITAL TWIN',
            'passenger_location':'DEVICE GPS',
            'baggage':'DEMO OPERATIONAL FEED',
            'ground_transport':'DEMO / USER INPUT',
            'gate_coordination':'SIMULATION READY',
            'recovery':'DECISION ENGINE',
            'ai_orchestration':'EVENT ENGINE',
            'voice_copilot':'BROWSER VOICE',
            'accessibility':'CARE ENGINE',
            'emergency':'112 + AIRPORT CONFIG',
            'offline':'PWA',
            'analytics':'LOCAL AGGREGATES'
        },
        'counts':counts,
        'updated':int(time.time())
    }

@app.get('/api/passenger/profile')
def get_profile(token:Optional[str]=Cookie(default=None,alias='yatraflow_session')):
    s=auth_user(token); c=db()
    r=c.execute('SELECT * FROM passenger_profiles WHERE user_id=?',(s['user_id'],)).fetchone()
    c.close()
    if not r:
        return {'profile':{'phone':'','pnr':'','flight_id':'','accessibility':[],'language':'English','simple_mode':False}}
    d=dict(r); d['accessibility']=json.loads(d.get('accessibility') or '[]'); d['simple_mode']=bool(d['simple_mode'])
    return {'profile':d}

@app.post('/api/passenger/profile')
def save_profile(p:ProfileIn, token:Optional[str]=Cookie(default=None,alias='yatraflow_session'), x_csrf:Optional[str]=Header(default=None,alias='X-CSRF-Token')):
    s=auth_user(token); csrf_ok(s,x_csrf); now=int(time.time()); c=db()
    c.execute("""INSERT INTO passenger_profiles(user_id,phone,pnr,flight_id,accessibility,language,simple_mode,created_at,updated_at)
                 VALUES(?,?,?,?,?,?,?,?,?)
                 ON CONFLICT(user_id) DO UPDATE SET phone=excluded.phone,pnr=excluded.pnr,flight_id=excluded.flight_id,accessibility=excluded.accessibility,language=excluded.language,simple_mode=excluded.simple_mode,updated_at=excluded.updated_at""",
              (s['user_id'],p.phone,p.pnr,p.flight_id,json.dumps(p.accessibility),p.language,int(p.simple_mode),now,now))
    c.commit(); c.close(); return {'ok':True}

@app.get('/api/baggage')
def get_baggage(token:Optional[str]=Cookie(default=None,alias='yatraflow_session')):
    s=auth_user(token); c=db(); rows=[dict(r) for r in c.execute('SELECT * FROM bags WHERE user_id=? ORDER BY id DESC',(s['user_id'],)).fetchall()]; c.close()
    if not rows:
        rows=[{'id':0,'tag':'DEMO-1042','status':'TRANSFER','last_location':'Transfer belt 3','updated_at':int(time.time())}]
    return {'items':rows,'source':'DEMO OPERATIONAL FEED'}

@app.post('/api/baggage')
def add_bag(p:BagIn, token:Optional[str]=Cookie(default=None,alias='yatraflow_session'), x_csrf:Optional[str]=Header(default=None,alias='X-CSRF-Token')):
    s=auth_user(token); csrf_ok(s,x_csrf); c=db()
    c.execute('INSERT INTO bags(user_id,tag,status,last_location,updated_at) VALUES(?,?,?,?,?)',(s['user_id'],p.tag,p.status.upper(),p.last_location,int(time.time())))
    c.commit(); c.close(); return {'ok':True}

@app.get('/api/transport')
def get_transport(token:Optional[str]=Cookie(default=None,alias='yatraflow_session')):
    s=auth_user(token); c=db(); rows=[dict(r) for r in c.execute('SELECT * FROM transport WHERE user_id=? ORDER BY id DESC',(s['user_id'],)).fetchall()]; c.close()
    if not rows:
        rows=[{'id':0,'vehicle_no':'TN-01-AX-2048','route':'Airport Shuttle','pickup':'T2 Arrivals','destination':'T1','lat':13.0827,'lon':80.2707,'eta':8,'status':'AVAILABLE','updated_at':int(time.time())}]
    return {'items':rows,'source':'DEMO / USER INPUT'}

@app.post('/api/transport')
def add_transport(p:TransportIn, token:Optional[str]=Cookie(default=None,alias='yatraflow_session'), x_csrf:Optional[str]=Header(default=None,alias='X-CSRF-Token')):
    s=auth_user(token); csrf_ok(s,x_csrf); c=db()
    c.execute('INSERT INTO transport(user_id,vehicle_no,route,pickup,destination,lat,lon,eta,status,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
              (s['user_id'],p.vehicle_no,p.route,p.pickup,p.destination,p.lat,p.lon,p.eta,'AVAILABLE',int(time.time())))
    c.commit(); c.close(); return {'ok':True}

@app.get('/api/assistance')
def get_assistance(token:Optional[str]=Cookie(default=None,alias='yatraflow_session')):
    s=auth_user(token); c=db(); rows=[dict(r) for r in c.execute('SELECT * FROM assistance_requests WHERE user_id=? ORDER BY id DESC LIMIT 20',(s['user_id'],)).fetchall()]; c.close()
    return {'items':rows}

@app.post('/api/assistance')
def request_assistance(p:AssistanceIn, token:Optional[str]=Cookie(default=None,alias='yatraflow_session'), x_csrf:Optional[str]=Header(default=None,alias='X-CSRF-Token')):
    s=auth_user(token); csrf_ok(s,x_csrf); c=db(); now=int(time.time())
    cur=c.execute('INSERT INTO assistance_requests(user_id,type,priority,status,location,notes,created_at) VALUES(?,?,?,?,?,?,?)',
                  (s['user_id'],p.type.upper(),p.priority.upper(),'OPEN',p.location,p.notes,now)); rid=cur.lastrowid; c.commit(); c.close()
    write_notification(s['user_id'],'ASSISTANCE','Assistance requested',f'{p.type} assistance request #{rid} is open.')
    return {'ok':True,'request_id':rid}

@app.get('/api/emergency')
def emergency_status(token:Optional[str]=Cookie(default=None,alias='yatraflow_session')):
    s=auth_user(token); c=db(); rows=[dict(r) for r in c.execute('SELECT * FROM emergency_events WHERE user_id=? ORDER BY id DESC LIMIT 10',(s['user_id'],)).fetchall()]; c.close()
    return {'emergency_number':'112','airport_security':'Airport-specific contact configured by deployment','items':rows}

@app.post('/api/emergency')
def create_emergency(p:EmergencyIn, token:Optional[str]=Cookie(default=None,alias='yatraflow_session'), x_csrf:Optional[str]=Header(default=None,alias='X-CSRF-Token')):
    s=auth_user(token); csrf_ok(s,x_csrf); c=db(); now=int(time.time())
    cur=c.execute('INSERT INTO emergency_events(user_id,type,status,location,created_at) VALUES(?,?,?,?,?)',(s['user_id'],p.type.upper(),'OPEN',p.location,now))
    rid=cur.lastrowid; c.commit(); c.close()
    write_notification(s['user_id'],'EMERGENCY','Emergency workflow started',f'Event #{rid}. Emergency number: 112.')
    return {'ok':True,'event_id':rid,'emergency_number':'112','message':'Confirm the phone call on your device when ready.'}

@app.get('/api/notifications')
def notifications(token:Optional[str]=Cookie(default=None,alias='yatraflow_session')):
    s=auth_user(token); c=db(); rows=[dict(r) for r in c.execute('SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 30',(s['user_id'],)).fetchall()]; c.close()
    return {'items':rows}

@app.post('/api/notifications/read')
def notifications_read(token:Optional[str]=Cookie(default=None,alias='yatraflow_session'), x_csrf:Optional[str]=Header(default=None,alias='X-CSRF-Token')):
    s=auth_user(token); csrf_ok(s,x_csrf); c=db(); c.execute('UPDATE notifications SET read=1 WHERE user_id=?',(s['user_id'],)); c.commit(); c.close(); return {'ok':True}

@app.post('/api/simulation/event')
def simulation_event(p:SimulateIn, token:Optional[str]=Cookie(default=None,alias='yatraflow_session'), x_csrf:Optional[str]=Header(default=None,alias='X-CSRF-Token')):
    s=auth_user(token); csrf_ok(s,x_csrf); typ=p.event_type.upper(); now=int(time.time())
    # Reuse the same connection scenario engine used by the dashboard.
    if typ in ('FLIGHT_DELAY','DELAY'):
        result = scenario(Scenario(delay=p.value), token, x_csrf)
    elif typ in ('BAGGAGE_DELAY','BAG_DELAY'):
        result = scenario(Scenario(baggage_delay=p.value), token, x_csrf)
    elif typ == 'CROWD':
        result = scenario(Scenario(crowd=min(100,p.value)), token, x_csrf)
    else:
        result = {'ok':True,'state':state_payload(s['user_id'])}
    c=db(); c.execute('INSERT INTO simulation_events(user_id,event_type,payload,created_at) VALUES(?,?,?,?)',(s['user_id'],typ,json.dumps(p.model_dump()),now)); c.commit(); c.close()
    write_notification(s['user_id'],'SIMULATION',f'Simulated {typ}',f'Simulation value: {p.value}')
    return result

@app.get('/api/analytics')
def analytics(token:Optional[str]=Cookie(default=None,alias='yatraflow_session')):
    s=auth_user(token); c=db()
    open_assist=c.execute("SELECT COUNT(*) FROM assistance_requests WHERE user_id=? AND status='OPEN'",(s['user_id'],)).fetchone()[0]
    emergencies=c.execute("SELECT COUNT(*) FROM emergency_events WHERE user_id=?",(s['user_id'],)).fetchone()[0]
    simulations=c.execute("SELECT COUNT(*) FROM simulation_events WHERE user_id=?",(s['user_id'],)).fetchone()[0]
    bags=c.execute("SELECT COUNT(*) FROM bags WHERE user_id=?",(s['user_id'],)).fetchone()[0]
    c.close()
    return {'metrics':{'connection_monitoring':1,'open_assistance':open_assist,'emergency_events':emergencies,'bags_tracked':bags,'simulations_run':simulations,'notifications':0},
            'note':'Operational analytics are based on the local/demo event store until a production telemetry provider is connected.'}

@app.get('/api/airport/contacts')
def airport_contacts():
    return {
        'airport':'DEL / MAA',
        'emergency':'112',
        'security':'044-22563240',
        'assistance':'Airport Passenger Assistance Desk (24/7)',
        'transit_hotel':{
            'name':'Holiday Inn Express / Plaza Premium Transit Hotel',
            'terminal':'Terminal 3 (Airside & Landside)',
            'phone':'+91-11-45252000',
            'booking':'Direct transit desk or online'
        },
        'ground_transport':{
            'bus':'Delhi Airport Express Shuttle / Route 47A / DTC Airport Link',
            'metro':'Airport Express Metro (Orange Line)',
            'taxi':'Official Prepaid Taxi / Uber / Ola Pickup Zone'
        },
        'source':'Deployment-configured directory'
    }

@app.get('/api/airport/hotels')
def airport_hotels():
    return {
        'airport':'DEL',
        'hotels':[
            {'name':'Holiday Inn Express New Delhi Airport T3','type':'Airside Transit Hotel','location':'T3 Inside Security','contact':'+91-11-45252000'},
            {'name':'Plaza Premium Transit Hotel','type':'Transit Rest Lounge & Hotel','location':'T3 Domestic & International','contact':'+91-11-49638700'},
            {'name':'Aerocity Airport Transit Hub','type':'Airport Hotel Hub (Radisson/Aloft)','location':'Aerocity (Free 5-min shuttle)','contact':'+91-11-46050101'}
        ]
    }

@app.get('/api/airport/accessibility')
def airport_accessibility():
    return {
        'wheelchair_routes':True,'elevator_routing':True,'accessible_restrooms':True,
        'visual_alerts':True,'audio_navigation':True,'simple_mode':True,
        'language_support':['English','Tamil','Hindi'],
        'note':'Precise indoor accessibility routing requires airport-approved indoor positioning data.'
    }

@app.get('/api/system/status')
def system_status():
    return {
        'app':'YatraFlow','version':VERSION,'api':'online',
        'providers':{
            'aviation': 'configured' if AVIATIONSTACK_KEY else 'demo',
            'weather':'enabled' if OPEN_METEO_ENABLED else 'disabled',
            'airspace':'enabled' if OPEN_SKY_ENABLED else 'disabled',
            'supabase':'configured' if SUPABASE_URL and SUPABASE_ANON_KEY else 'not configured'
        },
        'limitations':[
            'Static demo flights are not live telemetry.',
            'Indoor gate positioning requires airport-approved BLE/Wi-Fi/UWB data.',
            'Baggage and ground feeds remain demo/user-input until provider credentials are connected.'
        ]
    }


@app.websocket('/ws/live')
async def ws_live(ws:WebSocket):
    await ws.accept();CLIENTS.add(ws)
    try:
        while True: await ws.receive_text()
    except WebSocketDisconnect: CLIENTS.discard(ws)
    except Exception: CLIENTS.discard(ws)

@app.get('/')
def home():return FileResponse(FRONT/'index.html')
@app.get('/{path:path}')
def static(path:str):
    requested=(FRONT/path).resolve()
    if str(requested).startswith(str(FRONT.resolve())) and requested.exists() and requested.is_file():
        return FileResponse(requested)
    return FileResponse(FRONT/'index.html')
