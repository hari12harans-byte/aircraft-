/**
 * YatraFlow — Intelligent Airport Connection Companion
 * Comprehensive Travel Super-App Platform (Version 2.2.0)
 */

const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const esc = x => String(x ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));

// App Global State
const state = {
  screen: 'auth',
  tab: 'dashboard',
  csrf: '',
  user: null,
  data: null,
  profile: null,
  overview: null,
  authMode: 'login',
  lang: localStorage.getItem('yf_lang') || 'en',
  listening: false,
  alerts: [],
  notifications: [],
  menuOpen: false,
  mapTarget: 'passenger',
  mapLayer: 'airport',
  leafletMap: null,
  mapMarkers: [],
  myTrips: [],
  hotels: [],
  busRoutes: [],
  fareAlerts: [],
  modal: null,
  searchQuery: { from: 'DEL', to: 'BOM', date: '', cabin: 'Economy', airline: '', sort: 'price_asc' },
  searchResults: null,
  flightStatusResult: null,
  indoorRoute: null,
  deferredInstallPrompt: null
};

const demo = { email: 'demo@yatraflow.ai', password: 'YatraFlow@123' };

// Tri-lingual Translation Engine (English, Tamil, Hindi)
const i18n = {
  en: {
    brand_sub: 'INTELLIGENT AIRPORT CONNECTION COMPANION',
    tagline: 'Your journey, monitored with real-time flight telemetry.',
    dashboard: 'Dashboard',
    flights: 'Flights & Search',
    map: 'Airport Live Map',
    connection: 'Connection Guardian',
    trips: 'My Trips',
    hotels: 'Transit Hotels',
    transport: 'Transport & Buses',
    care: 'CARE & Safety',
    notifications: 'Notifications',
    settings: 'Settings',
    sign_in: 'Sign in',
    create_account: 'Create account',
    use_demo: 'Use demo account',
    google_login: 'Sign in with Google',
    system_online: 'System online',
    refresh: 'Refresh',
    search_flights: 'Search Flights',
    track_flight: 'Track Flight Status',
    find_route: 'Find Route',
    live_radar: 'Live Radar',
    safe: 'SAFE',
    tight: 'TIGHT',
    risk: 'AT RISK',
    missed: 'LIKELY MISSED',
    emergency_sos: 'Emergency SOS',
    confirm_call: 'Confirm call to India 112',
    cancel: 'Cancel',
    call_112: 'Call 112 Now',
    detect_location: 'Detect GPS Location',
    install_app: 'Install YatraFlow App',
    test_email: 'Test Email Alert',
    test_whatsapp: 'Test WhatsApp Alert',
    add_trip: 'Add to My Trips',
    google_cal: 'Add to Google Calendar'
  },
  ta: {
    brand_sub: 'அறிவார்ந்த விமான இணைப்பு வழிகாட்டி',
    tagline: 'உங்கள் பயணம், நேரலை விமானத் தரவுகளுடன் கண்காணிக்கப்படுகிறது.',
    dashboard: 'முகப்பு',
    flights: 'விமானங்கள் & தேடல்',
    map: 'விமான நிலைய வரைபடம்',
    connection: 'இணைப்பு பாதுகாவலர்',
    trips: 'என் பயணங்கள்',
    hotels: 'தங்கும் விடுதிகள்',
    transport: 'போக்குவரத்து & பஸ்',
    care: 'பாதுகாப்பு & உதவி',
    notifications: 'அறிவிப்புகள்',
    settings: 'அமைப்புகள்',
    sign_in: 'உள்நுழைக',
    create_account: 'கணக்கு தொடங்க',
    use_demo: 'டெமோ கணக்கு',
    google_login: 'கூகுள் மூலம் உள்நுழைக',
    system_online: 'இணைப்பு இயங்குகிறது',
    refresh: 'புதுப்பி',
    search_flights: 'விமானம் தேடுக',
    track_flight: 'விமான நிலை அறி',
    find_route: 'வழிப்பாதை காண்',
    live_radar: 'நேரலை ரேடார்',
    safe: 'பாதுகாப்பானது',
    tight: 'குறைந்த நேரம்',
    risk: 'ஆபத்தில் உள்ளது',
    missed: 'தவற வாய்ப்புள்ளது',
    emergency_sos: 'அவசர உதவி SOS',
    confirm_call: '112 அவசர எண்ணை அழைக்கவா?',
    cancel: 'ரத்து',
    call_112: '112-ஐ அழைக்கவும்',
    detect_location: 'ஜி.பி.எஸ் இடம் காண்',
    install_app: 'செயலியை நிறுவுங்கள்',
    test_email: 'மின்னஞ்சல் சோதனை',
    test_whatsapp: 'வாட்ஸ்அப் சோதனை',
    add_trip: 'பயணத்தில் சேர்',
    google_cal: 'கூகுள் காலெண்டரில் சேர்'
  },
  hi: {
    brand_sub: 'बुद्धिमान हवाई अड्डा कनेक्शन साथी',
    tagline: 'आपकी यात्रा, रीयल-टाइम उड़ान टेलीमेट्री के साथ मॉनिटर की जा रही है।',
    dashboard: 'डैशबोर्ड',
    flights: 'उड़ानें और खोज',
    map: 'लाइव एयरपोर्ट मैप',
    connection: 'कनेक्शन गार्जियन',
    trips: 'मेरी यात्राएं',
    hotels: 'ट्रांजिट होटल',
    transport: 'परिवहन और बस',
    care: 'केयर और सुरक्षा',
    notifications: 'सूचनाएं',
    settings: 'सेटिंग्स',
    sign_in: 'साइन इन करें',
    create_account: 'खाता बनाएं',
    use_demo: 'डेमो खाता उपयोग करें',
    google_login: 'Google से साइन इन करें',
    system_online: 'सिस्टम ऑनलाइन',
    refresh: 'ताज़ा करें',
    search_flights: 'उड़ान खोजें',
    track_flight: 'उड़ान स्थिति ट्रैक करें',
    find_route: 'मार्ग खोजें',
    live_radar: 'लाइव रडार',
    safe: 'सुरक्षित',
    tight: 'कम समय',
    risk: 'जोखिम में',
    missed: 'छूटने की संभावना',
    emergency_sos: 'आपातकालीन SOS',
    confirm_call: 'भारत 112 कॉल की पुष्टि करें',
    cancel: 'रद्द करें',
    call_112: '112 पर कॉल करें',
    detect_location: 'जीपीएस स्थान पहचानें',
    install_app: 'ऐप इंस्टॉल करें',
    test_email: 'टेस्ट ईमेल अलर्ट',
    test_whatsapp: 'टेस्ट व्हाट्सएप अलर्ट',
    add_trip: 'यात्रा में जोड़ें',
    google_cal: 'Google कैलेंडर में जोड़ें'
  }
};

function t(key){
  return (i18n[state.lang] && i18n[state.lang][key]) || (i18n.en && i18n.en[key]) || key;
}

// API Helper with loading & error toasts
async function api(path, opt = {}) {
  const o = { credentials: 'include', ...opt, headers: { 'Content-Type': 'application/json', ...(opt.headers || {}) } };
  if (o.body && typeof o.body !== 'string') o.body = JSON.stringify(o.body);
  try {
    const r = await fetch(path, o);
    let d = {};
    try { d = await r.json(); } catch {}
    if (!r.ok) throw new Error(d.detail || d.message || 'Request failed');
    return d;
  } catch (err) {
    throw err;
  }
}

function toast(msg) {
  const x = $('#toast');
  if (!x) return;
  x.textContent = msg;
  x.classList.add('show');
  clearTimeout(window.__toast);
  window.__toast = setTimeout(() => x.classList.remove('show'), 3200);
}

function csrfHeaders() {
  return { 'X-CSRF-Token': state.csrf };
}

function badge(level) {
  let c = level === 'SAFE' ? 'safe' : (level === 'TIGHT' ? 'tight' : (level === 'AT RISK' ? 'risk' : 'missed'));
  return `<span class="badge ${c}">${esc(t(c) || level)}</span>`;
}

function statusPill(status, label) {
  const s = String(status || '').toUpperCase();
  const cls = s.includes('LIVE') ? 'live' : (s.includes('UNAVAILABLE') ? 'unavailable' : 'demo');
  return `<span class="status-pill ${cls}">● ${esc(label || s)}</span>`;
}

// Active Airspace Telemetry Tracker
function getActiveAirTrack(d) {
  if (!d) return null;
  const lf = (d.outbound?.latitude && d.outbound?.longitude) ? d.outbound :
             (d.inbound?.latitude && d.inbound?.longitude) ? d.inbound : null;
  if (lf) {
    return {
      callsign: lf.number || 'FLIGHT',
      flight: lf.number,
      airline: lf.airline,
      lat: Number(lf.latitude),
      lon: Number(lf.longitude),
      alt: lf.altitude_m,
      speed: lf.speed_kmh,
      heading: null,
      source: 'Aviationstack Live GPS',
      isExact: true
    };
  }

  const items = d.airspace?.items || [];
  if (!items.length) return null;

  const f1 = (d.inbound?.number || '').replace(/\s+/g, '').toUpperCase();
  const f2 = (d.outbound?.number || '').replace(/\s+/g, '').toUpperCase();
  const matched = items.find(x => {
    const c = (x.callsign || '').replace(/\s+/g, '').toUpperCase();
    return c && (c === f1 || c === f2 || (f1.length > 2 && c.includes(f1)) || (f2.length > 2 && c.includes(f2)));
  });

  if (matched) {
    return {
      callsign: matched.callsign,
      flight: d.outbound?.number || matched.callsign,
      airline: d.outbound?.airline || 'Monitored Flight',
      lat: Number(matched.latitude),
      lon: Number(matched.longitude),
      alt: matched.altitude_m,
      speed: Math.round((matched.velocity_ms || 0) * 3.6),
      heading: matched.heading,
      source: 'OpenSky Radar (Live Match)',
      isExact: true
    };
  }

  const first = items[0];
  return {
    callsign: first.callsign || first.icao24 || 'RADAR CONTACT',
    flight: d.outbound?.number || 'Terminal Corridor',
    airline: 'Active Airspace Traffic',
    lat: Number(first.latitude),
    lon: Number(first.longitude),
    alt: first.altitude_m,
    speed: Math.round((first.velocity_ms || 0) * 3.6),
    heading: first.heading,
    source: 'OpenSky Radar (' + (d.airspace?.airport || 'DEL') + ')',
    isExact: false
  };
}

// Navigation Tab Definitions
const navItems = [
  ['dashboard', 'Dashboard', '⌂'],
  ['flights', 'Flights & Search', '✈'],
  ['map', 'Airport Live Map', '🗺'],
  ['connection', 'Connection Guardian', '⚡'],
  ['trips', 'My Trips', '🎒'],
  ['hotels', 'Transit Hotels', '🏨'],
  ['transport', 'Transport & Buses', '🚌'],
  ['care', 'CARE & Safety', '♿'],
  ['notifications', 'Notifications', '🔔'],
  ['settings', 'Settings', '⚙']
];

// Top Shell with Navigation and Modals
function shell() {
  const unreadCount = state.notifications.filter(x => !x.read).length;
  return `<div class="app">
    <header class="topbar">
      <div class="logo" data-tab="dashboard">
        <span class="logo-mark">✈</span>
        <div>
          <span style="font-size:17px;font-weight:950;display:block;line-height:1">YatraFlow</span>
          <span style="font-size:9px;color:var(--muted);letter-spacing:0.5px">AIRPORT COPILOT</span>
        </div>
      </div>
      <nav class="nav">
        ${navItems.map(n => `<button class="${state.tab === n[0] ? 'active' : ''}" data-tab="${n[0]}">${n[2]} ${t(n[0]) || n[1]}</button>`).join('')}
      </nav>
      <div class="top-actions">
        <select class="lang-select" id="langSwitch" title="Change Language">
          <option value="en" ${state.lang === 'en' ? 'selected' : ''}>English</option>
          <option value="ta" ${state.lang === 'ta' ? 'selected' : ''}>தமிழ்</option>
          <option value="hi" ${state.lang === 'hi' ? 'selected' : ''}>हिंदी</option>
        </select>
        <div class="live"><span class="live-dot"></span> <span class="hide-sm">${t('system_online')}</span></div>
        <button class="icon-btn alert-bell" data-tab="notifications" title="Notifications">
          🔔${unreadCount ? `<span class="alert-count">${Math.min(9, unreadCount)}</span>` : ''}
        </button>
        <div class="user-avatar" title="${esc(state.user?.name || 'Traveler')}">
          ${state.user?.avatar ? `<img src="${esc(state.user.avatar)}" class="user-avatar" alt="User">` : (state.user?.name ? state.user.name[0].toUpperCase() : 'Y')}
        </div>
        <button class="icon-btn" id="logoutBtn" title="Sign out">↪</button>
        <button class="hamburger" id="hamburger">☰</button>
      </div>
    </header>

    <div class="drawer-backdrop ${state.menuOpen ? 'open' : ''}" id="drawerBackdrop"></div>
    <aside class="drawer ${state.menuOpen ? 'open' : ''}" id="drawer">
      <div class="drawer-head">
        <div class="logo">
          <span class="logo-mark">✈</span>
          <strong>YatraFlow</strong>
        </div>
        <button class="icon-btn" id="closeDrawer">×</button>
      </div>
      <div class="drawer-nav">
        ${navItems.map(n => `<button class="${state.tab === n[0] ? 'active' : ''}" data-tab="${n[0]}"><span style="font-size:16px">${n[2]}</span> ${t(n[0]) || n[1]}</button>`).join('')}
      </div>
      <div style="margin-top:20px;padding-top:15px;border-top:1px solid var(--line)">
        <div class="small" style="margin-bottom:8px">Traveler Profile:</div>
        <strong>${esc(state.user?.name || 'Traveler')}</strong>
        <p class="small">${esc(state.user?.email || '')}</p>
        <button class="outline" style="width:100%;margin-top:10px" data-action="installPWA">📱 ${t('install_app')}</button>
      </div>
    </aside>

    <div class="alert-center">
      ${state.alerts.map((a, i) => `
        <div class="alert-item ${a.level || ''}">
          <button data-dismiss-alert="${i}">×</button>
          <strong>${esc(a.title)}</strong>
          <span>${esc(a.message)}</span>
        </div>
      `).join('')}
    </div>

    <main class="page">
      ${renderSection()}
    </main>

    <nav class="mobile-bottom">
      ${navItems.slice(0, 5).map(n => `<button class="${state.tab === n[0] ? 'active' : ''}" data-tab="${n[0]}"><span style="font-size:16px">${n[2]}</span><span>${t(n[0]) || n[1]}</span></button>`).join('')}
    </nav>

    <button class="voice ${state.listening ? 'listening' : ''}" id="voiceBtn" title="Voice Copilot">🎙</button>
    <button class="sos" id="sosBtn" title="Emergency SOS">SOS</button>
    ${renderModal()}
  </div>`;
}

function renderSection() {
  switch (state.tab) {
    case 'dashboard': return viewDashboard();
    case 'flights': return viewFlights();
    case 'map': return viewMap();
    case 'connection': return viewConnection();
    case 'trips': return viewTrips();
    case 'hotels': return viewHotels();
    case 'transport': return viewTransport();
    case 'care': return viewCare();
    case 'notifications': return viewNotifications();
    case 'settings': return viewSettings();
    default: return viewDashboard();
  }
}

function pageHead(eyebrow, title, actionHtml = '') {
  return `<div class="page-head">
    <div>
      <div class="eyebrow">${esc(eyebrow)}</div>
      <h1>${esc(title)}</h1>
    </div>
    ${actionHtml ? `<div class="actions">${actionHtml}</div>` : ''}
  </div>`;
}

// 1. Dashboard View
function viewDashboard() {
  const d = state.data, e = d?.engine || {};
  const track = getActiveAirTrack(d);
  const planeRotate = (track && track.heading !== null && track.heading !== undefined)
    ? Math.max(-20, Math.min(20, ((track.heading % 90) - 45)))
    : -7;

  return `
    <section class="sky-hero">
      <div class="sky"><div class="cloud c1"></div><div class="cloud c2"></div><div class="cloud c3"></div></div>
      <div class="sky-copy">
        <div class="eyebrow">${esc(t('brand_sub'))}</div>
        ${track ? `
          <div class="flight-chip live"><span class="live-dot"></span> LIVE RADAR · ${esc(track.callsign)} · ${track.lat.toFixed(4)}°N, ${track.lon.toFixed(4)}°E</div>
          <h1>${esc(t('tagline'))}</h1>
          <p>Real transponder signals received from live airspace radar. Tracking coordinates, speed, connection risk, baggage and alerts from one passenger command center.</p>
          <div class="telemetry-bar">
            <div class="telemetry-item"><span>COORDINATES</span><strong>${track.lat.toFixed(4)}°, ${track.lon.toFixed(4)}°</strong></div>
            <div class="telemetry-item"><span>ALTITUDE</span><strong>${track.alt ? Math.round(track.alt) + ' m' : 'En route'}</strong></div>
            <div class="telemetry-item"><span>GROUND SPEED</span><strong>${track.speed ? track.speed + ' km/h' : '—'}</strong></div>
            ${track.heading !== null && track.heading !== undefined ? `<div class="telemetry-item"><span>HEADING</span><strong>${Math.round(track.heading)}°</strong></div>` : ''}
            <div class="telemetry-item"><span>RADAR SOURCE</span><strong class="green-text">${esc(track.source)}</strong></div>
          </div>
        ` : `
          <div class="flight-chip"><span class="standby-dot"></span> RADAR STANDBY · ${esc(d?.outbound?.number || 'AI 201')} · Scheduled</div>
          <h1>${esc(t('tagline'))}</h1>
          <p>Track flight status, connection risk, airport movement, baggage and alerts from one passenger command center.</p>
          <div class="hud-standby">Awaiting live transponder contact in terminal airspace. Real coordinates will display upon radar acquisition.</div>
        `}
        <div class="actions" style="margin-top:16px">
          <button class="primary" data-tab="map">🗺 ${t('map')}</button>
          <button class="secondary" data-action="refresh">↻ ${t('refresh')}</button>
          <button class="soft" data-tab="flights">✈ ${t('search_flights')}</button>
        </div>
      </div>
      <div class="aircraft-wrap">
        <div class="trail"></div>
        <div class="aircraft" style="transform:rotate(${planeRotate}deg)">
          <div class="plane-body"></div><div class="plane-nose"></div><div class="plane-tail"></div>
          <div class="wing"></div><div class="wing bottom"></div><div class="engine"></div>
          <div class="window-row"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
        </div>
      </div>
    </section>

    ${pageHead('LIVE JOURNEY', 'Connection Guardian', `
      <button class="primary" data-action="refresh">↻ ${t('refresh')}</button>
      <button class="soft" data-tab="trips">🎒 ${t('trips')}</button>
    `)}

    <section class="hero">
      <div>
        <div class="eyebrow">MONITORED CONNECTION</div>
        <h1>${esc(d?.inbound?.number || '6E 604')} → ${esc(d?.outbound?.number || 'AI 201')}</h1>
        <p>${esc(d?.inbound?.from_name || 'Chennai')} → ${esc(d?.inbound?.to_name || 'Delhi IGI T3')} → ${esc(d?.outbound?.to_name || 'London Heathrow')} · Passenger at <strong>${esc(d?.position?.name || 'Gate A04')}</strong></p>
        <div class="actions">
          <button class="primary" data-tab="connection">⚡ Connection Details</button>
          <button class="secondary" data-tab="map">🗺 Step-by-Step Gate Navigation</button>
          <button class="soft" data-action="openTripCal">📅 ${t('google_cal')}</button>
        </div>
      </div>
      <div class="hero-side">
        ${badge(e.level || 'SAFE')}
        <strong class="risk-number">${e.risk || 0}%</strong>
        <span class="small">connection risk score</span>
      </div>
    </section>

    <section class="metrics">
      <div class="metric"><span>Time Available</span><strong>${e.available_minutes ?? '—'} min</strong></div>
      <div class="metric"><span>Time Required</span><strong>${e.required_minutes ?? '—'} min</strong></div>
      <div class="metric"><span>Buffer Margin</span><strong>${e.margin_minutes ?? '—'} min</strong></div>
      <div class="metric"><span>Boarding Closes</span><strong>${esc(e.boarding_close || '—')}</strong></div>
    </section>

    <div class="grid">
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">AI CONNECTION COPILOT</div><h2>Transfer Breakdown</h2></div>
          ${statusPill(d?.source?.flights, d?.source?.flights || 'DEMO')}
        </div>
        <p>${esc(e.message || 'Connection window monitored.')}</p>
        <div style="margin-top:12px">
          <div class="list-row"><span class="small">Walking to Gate (${e.outbound_gate || 'B12'})</span><strong>${e.walk_minutes ?? 0} min</strong></div>
          <div class="progress"><i style="width:${Math.min(100, (e.walk_minutes || 0) * 6)}%"></i></div>
          <div class="list-row"><span class="small">Security Checkpoint Queue</span><strong>${e.security_minutes ?? 0} min</strong></div>
          <div class="progress"><i style="width:${Math.min(100, (e.security_minutes || 0) * 8)}%"></i></div>
          <div class="list-row"><span class="small">Baggage Transfer Clearance</span><strong>${e.baggage_minutes ?? 0} min</strong></div>
          <div class="progress"><i style="width:${Math.min(100, (e.baggage_minutes || 0) * 6)}%"></i></div>
        </div>
      </section>

      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">ACTION ORCHESTRATOR</div><h2>Recommended Next Steps</h2></div>
          <span class="status-pill live">LIVE ENGINE</span>
        </div>
        <div class="list">
          ${(e.actions || []).map(a => `<div class="list-row"><span>👉 ${esc(a)}</span><span>›</span></div>`).join('')}
        </div>
        <div class="actions">
          <button class="primary" data-tab="map">Start Indoor Navigation</button>
          <button class="secondary" data-tab="care">Request Airport Assistance</button>
        </div>
      </section>
    </div>

    <div class="grid three">
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">WEATHER ADVISORY</div><h2>Terminal Weather</h2></div>
          ${statusPill(d?.weather?.status, 'Open-Meteo')}
        </div>
        <div style="display:flex;align-items:center;gap:12px">
          <span style="font-size:32px">${d?.weather?.condition_icon || '🌤️'}</span>
          <div>
            <strong style="font-size:22px">${d?.weather?.temperature ?? 28}°C</strong>
            <span class="small" style="display:block">${esc(d?.weather?.condition || 'Mainly clear')}</span>
          </div>
        </div>
        <p class="small" style="margin-top:8px">${esc(d?.weather?.impact_advisory || 'OPTIMAL: No weather delays expected.')}</p>
      </section>

      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">BAGGAGE INTELLIGENCE</div><h2>Luggage Transfer</h2></div>
          <span class="status-pill demo">DEMO FEED</span>
        </div>
        <strong style="font-size:18px" id="bagSummary">Loading…</strong>
        <p class="small">Bag tag monitoring & automated transfer risk alert.</p>
        <button class="soft" data-tab="care" style="margin-top:10px">Open Baggage Care</button>
      </section>

      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">GROUND TRANSPORT</div><h2>Feeder & Metro</h2></div>
          <span class="status-pill demo">DEMO / SCHEDULE</span>
        </div>
        <strong style="font-size:18px" id="transportSummary">Airport Express Metro</strong>
        <p class="small">Orange line to New Delhi in 19 min (Every 10 min).</p>
        <button class="soft" data-tab="transport" style="margin-top:10px">View All Transport & Buses</button>
      </section>
    </div>
  `;
}

// 2. Flights & Flight Search View
function viewFlights() {
  const sq = state.searchQuery;
  const results = state.searchResults || [];
  const statusRes = state.flightStatusResult;

  return `
    ${pageHead('FLIGHT ENGINE', 'Flight Search & Status Tracker', `
      <button class="soft" data-action="clearFlightSearch">Reset Form</button>
    `)}

    <div class="grid">
      <!-- Search Form -->
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">FLIGHT SEARCH</div><h2>Find Flights</h2></div>
          ${statusPill(state.overview?.modules?.flights, 'Provider Abstraction')}
        </div>
        <form id="flightSearchForm">
          <div class="form-grid">
            <label>From (Airport Code / City)
              <input id="searchFrom" required value="${esc(sq.from)}" placeholder="e.g. DEL">
            </label>
            <label>To (Airport Code / City)
              <input id="searchTo" required value="${esc(sq.to)}" placeholder="e.g. BOM">
            </label>
          </div>
          <div class="form-grid three" style="margin-top:10px">
            <label>Travel Date
              <input id="searchDate" type="date" value="${esc(sq.date || new Date().toISOString().slice(0,10))}">
            </label>
            <label>Cabin Class
              <select id="searchCabin">
                <option value="Economy" ${sq.cabin === 'Economy' ? 'selected' : ''}>Economy</option>
                <option value="Premium Economy" ${sq.cabin === 'Premium Economy' ? 'selected' : ''}>Premium Economy</option>
                <option value="Business" ${sq.cabin === 'Business' ? 'selected' : ''}>Business</option>
              </select>
            </label>
            <label>Sort By
              <select id="searchSort">
                <option value="price_asc" ${sq.sort === 'price_asc' ? 'selected' : ''}>Lowest Price</option>
                <option value="dep_asc" ${sq.sort === 'dep_asc' ? 'selected' : ''}>Earliest Departure</option>
                <option value="duration_asc" ${sq.sort === 'duration_asc' ? 'selected' : ''}>Shortest Duration</option>
              </select>
            </label>
          </div>
          <div class="actions">
            <button class="primary" type="submit">🔍 ${t('search_flights')}</button>
            <button type="button" class="secondary" data-action="popularRoute" data-from="DEL" data-to="BOM">DEL → BOM</button>
            <button type="button" class="secondary" data-action="popularRoute" data-from="MAA" data-to="DEL">MAA → DEL</button>
            <button type="button" class="secondary" data-action="popularRoute" data-from="DEL" data-to="DXB">DEL → DXB</button>
          </div>
        </form>
      </section>

      <!-- Status Tracker -->
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">REAL-TIME TRACKER</div><h2>Flight Status by Number</h2></div>
          <span class="status-pill live">RADAR / STATUS</span>
        </div>
        <form id="flightStatusForm">
          <label>Flight Number
            <input id="statusFlightNo" required placeholder="e.g. 6E 604, AI 201, UK 820" value="6E 604">
          </label>
          <div class="actions">
            <button class="primary" type="submit">Check Flight Status</button>
            <button type="button" class="secondary" data-action="statusPreset" data-flight="AI 201">AI 201</button>
            <button type="button" class="secondary" data-action="statusPreset" data-flight="UK 820">UK 820</button>
          </div>
        </form>
        ${statusRes ? `
          <div style="margin-top:16px;padding:12px;background:#f8fafc;border:1px solid var(--line);border-radius:9px">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <strong>${esc(statusRes.flight.number)} · ${esc(statusRes.flight.airline)}</strong>
              ${badge(statusRes.flight.status === 'On time' ? 'SAFE' : 'TIGHT')}
            </div>
            <div class="small" style="margin-top:4px">
              ${esc(statusRes.flight.from)} (${esc(statusRes.flight.dep)}) → ${esc(statusRes.flight.to)} (${esc(statusRes.flight.arr)}) · Terminal ${esc(statusRes.flight.terminal_dep)} Gate ${esc(statusRes.flight.gate)}
            </div>
            <div class="small" style="margin-top:4px">Baggage Belt: <strong>${esc(statusRes.flight.baggage_belt)}</strong> · Aircraft: ${esc(statusRes.flight.aircraft)}</div>
            <p class="small" style="color:var(--blue);margin-top:6px">Insight: ${esc(statusRes.delay_prediction?.reason || '')}</p>
          </div>
        ` : ''}
      </section>
    </div>

    <!-- Search Results List -->
    <section class="card">
      <div class="card-head">
        <div>
          <div class="eyebrow">AVAILABLE FLIGHTS</div>
          <h2>Search Results (${results.length ? results.length : 'All Directory'})</h2>
        </div>
        <span class="status-pill demo">DEMO SCHEDULE MATRIX</span>
      </div>
      <div class="list">
        ${(results.length ? results : (state.data?.flights || [])).map(f => `
          <div class="list-row" style="padding:14px 0">
            <div>
              <div style="display:flex;align-items:center;gap:8px">
                <strong style="font-size:16px">${esc(f.number)}</strong>
                <span class="status-pill">${esc(f.airline)}</span>
                <span class="badge ${f.status === 'On time' ? 'safe' : 'tight'}">${esc(f.status || 'On time')}</span>
              </div>
              <div style="margin-top:6px;font-size:13px">
                <strong>${esc(f.from)} ${esc(f.dep)}</strong> → <strong>${esc(f.to)} ${esc(f.arr)}</strong>
                <span class="small"> (${esc(f.duration || '2h 30m')} · ${esc(f.stops || 'Non-stop')})</span>
              </div>
              <div class="small" style="margin-top:4px">
                Terminal: <strong>${esc(f.terminal || f.terminal_dep || 'T3')}</strong> · Gate: <strong>${esc(f.gate || 'A04')}</strong> · Baggage: <strong>${esc(f.baggage_belt || 'Belt 04')}</strong>
              </div>
            </div>
            <div style="text-align:right">
              <strong style="font-size:18px;color:var(--navy);display:block">₹${Number(f.price_inr || 4850).toLocaleString('en-IN')}</strong>
              <div class="actions" style="justify-content:flex-end;margin-top:6px">
                <button class="primary" data-action="bookToTrips" data-flight='${JSON.stringify(f).replace(/'/g, "&apos;")}'>+ Add to Trips</button>
                <button class="secondary" data-action="setFareWatch" data-from="${esc(f.from)}" data-to="${esc(f.to)}" data-price="${f.price_inr || 4850}">🔔 Alert</button>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    </section>
  `;
}

// 3. Airport Live Map & Radar View
function viewMap() {
  const d = state.data || {};
  const track = getActiveAirTrack(d);
  const pos = d.position || { name: 'Gate A04', lat: 28.5562, lon: 77.1000 };
  const route = state.indoorRoute;

  return `
    ${pageHead('AIRPORT DIGITAL TWIN', 'Live Airport Map & Airspace Radar', `
      <button class="primary" data-action="locate">⌖ ${t('detect_location')}</button>
      <button class="secondary" data-action="toggleRadarMap">${state.mapLayer === 'radar' ? '🗺 View Terminal Map' : '✈ View Airspace Radar'}</button>
    `)}

    <section class="card" style="padding:0;overflow:hidden">
      <div class="map-container">
        <div id="leafletMap" style="width:100%;height:100%"></div>
        <div class="map-toolbar">
          <button class="${state.mapLayer === 'airport' ? 'active' : ''}" data-action="switchMapLayer" data-layer="airport">Terminal POIs</button>
          <button class="${state.mapLayer === 'radar' ? 'active' : ''}" data-action="switchMapLayer" data-layer="radar">Airspace Radar</button>
          <button class="${state.mapTarget === 'passenger' ? 'active' : ''}" data-action="mapFocus" data-target="passenger">⌖ Passenger</button>
          ${track ? `<button class="${state.mapTarget === 'aircraft' ? 'active' : ''}" data-action="mapFocus" data-target="aircraft">✈ Live Flight</button>` : ''}
        </div>
        <div class="map-overlay-card">
          <strong>${state.mapLayer === 'radar' ? '✈ OpenSky Airspace Telemetry' : '⌖ ' + esc(pos.name)}</strong>
          <small>${state.mapLayer === 'radar' ? 'Live ADS-B transponder signals layered over OpenStreetMap base.' : 'Step-by-step turn-by-turn indoor routing layered over terminal.'}</small>
        </div>
      </div>
    </section>

    <!-- Indoor Route Planner -->
    <div class="grid">
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">INDOOR NAVIGATION</div><h2>Turn-by-Turn Gate Directions</h2></div>
          <span class="status-pill live">INDOOR DIJKSTRA</span>
        </div>
        <form id="indoorRouteForm">
          <div class="form-grid">
            <label>Current Location
              <select id="routeStart">
                ${Object.entries(d.zones || {}).map(([k, v]) => `<option value="${k}" ${k === (d.zone || 'A04') ? 'selected' : ''}>${esc(v.name)}</option>`).join('')}
              </select>
            </label>
            <label>Destination Gate / Zone
              <select id="routeGoal">
                ${Object.entries(d.zones || {}).map(([k, v]) => `<option value="${k}" ${k === (d.engine?.outbound_gate || 'B12') ? 'selected' : ''}>${esc(v.name)}</option>`).join('')}
              </select>
            </label>
          </div>
          <label style="margin-top:10px;display:flex;align-items:center;gap:8px">
            <input type="checkbox" id="routeAccessible" style="width:auto" ${state.accessibleRoute ? 'checked' : ''}>
            <span>♿ Accessible Route (Use elevators & ramps, avoid stairs)</span>
          </label>
          <div class="actions">
            <button class="primary" type="submit">Find Step-by-Step Route</button>
          </div>
        </form>

        ${route ? `
          <div style="margin-top:14px;padding:12px;background:#f8fafc;border:1px solid var(--line);border-radius:8px">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <strong>Route: ${esc(route.start_name)} → ${esc(route.goal_name)}</strong>
              <span class="badge safe">ETA: ${route.eta_minutes} min (${route.distance_meters}m)</span>
            </div>
            <div class="timeline-track" style="margin-top:12px">
              ${(route.steps || []).map((step, idx) => `
                <div class="timeline-step ${idx === 0 ? 'current' : ''}">
                  <strong>Step ${idx + 1}</strong>
                  <span>${esc(step)}</span>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}
      </section>

      <!-- Terminal Transfer Guide -->
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">INTER-TERMINAL TRANSFER</div><h2>Terminal 1 ↔ Terminal 2 ↔ Terminal 3</h2></div>
          <span class="status-pill demo">AIRPORT SHUTTLE</span>
        </div>
        <p>Transfer guide for Indira Gandhi International Airport (DEL):</p>
        <div class="list">
          <div class="list-row">
            <div>
              <strong>T3 ↔ T2 Walkway</strong>
              <div class="small">Covered pedestrian walkway · 350 meters · 5 min walk</div>
            </div>
            <span class="badge safe">FREE</span>
          </div>
          <div class="list-row">
            <div>
              <strong>T3/T2 ↔ T1 Inter-Terminal Shuttle</strong>
              <div class="small">Complimentary 24/7 Shuttle Bus · Departs every 15 mins</div>
            </div>
            <span class="badge safe">15 MIN</span>
          </div>
          <div class="list-row">
            <div>
              <strong>Airport Express Metro to Aerocity</strong>
              <div class="small">Orange Line Link to Terminal 1 feeder station</div>
            </div>
            <span class="badge tight">₹20</span>
          </div>
        </div>
      </section>
    </div>
  `;
}

// 4. Connection Guardian View
function viewConnection() {
  const d = state.data, e = d?.engine || {};
  const flights = state.data?.flights || [];

  return `
    ${pageHead('INTELLIGENCE ENGINE', 'AI Airport Connection Guardian', `
      <button class="primary" data-action="refresh">↻ ${t('refresh')}</button>
    `)}

    <div class="grid">
      <!-- Setup Connection -->
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">CONNECTION PAIR</div><h2>Select Flights to Guard</h2></div>
          <span class="status-pill live">ACTIVE MONITOR</span>
        </div>
        <form id="connectionSetupForm">
          <div class="form-grid">
            <label>Inbound Flight
              <select id="connInbound">
                ${flights.map((f, i) => `<option value="${esc(f.id)}" ${i === 0 ? 'selected' : ''}>${esc(f.number)} · ${esc(f.from)} → ${esc(f.to)}</option>`).join('')}
              </select>
            </label>
            <label>Connecting Flight
              <select id="connOutbound">
                ${flights.map((f, i) => `<option value="${esc(f.id)}" ${i === 1 ? 'selected' : ''}>${esc(f.number)} · ${esc(f.from)} → ${esc(f.to)}</option>`).join('')}
              </select>
            </label>
          </div>
          <div class="form-grid" style="margin-top:10px">
            <label>Checked Bags
              <select id="connBags">
                <option value="0">0 Bags (Cabin Baggage Only)</option>
                <option value="1" selected>1 Checked Bag</option>
                <option value="2">2 Checked Bags</option>
              </select>
            </label>
            <label>Walking Pace / Assistance
              <select id="connPace">
                <option value="NORMAL" selected>Normal Walking Speed</option>
                <option value="FAST">Fast Walker / Sprint</option>
                <option value="WHEELCHAIR">Wheelchair Assistance (CARE)</option>
                <option value="ELDERLY">Elderly / Leisure Pace</option>
              </select>
            </label>
          </div>
          <label style="margin-top:10px;display:flex;align-items:center;gap:8px">
            <input type="checkbox" id="connImmigration" style="width:auto">
            <span>Passport Control / Immigration Required (International Connection)</span>
          </label>
          <div class="actions">
            <button class="primary" type="submit">Apply Connection Model</button>
          </div>
        </form>
      </section>

      <!-- Simulation Engine -->
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">STRESS TESTING</div><h2>Simulation Event Injection</h2></div>
          <span class="status-pill live">EVENT ENGINE</span>
        </div>
        <p>Simulate delays or airport congestion to test the automated rescue calculation:</p>
        <div class="actions">
          <button class="secondary" data-sim="FLIGHT_DELAY" data-value="15">+15m Flight Delay</button>
          <button class="secondary" data-sim="FLIGHT_DELAY" data-value="30">+30m Flight Delay</button>
          <button class="secondary" data-sim="BAGGAGE_DELAY" data-value="20">+20m Baggage Hold</button>
          <button class="secondary" data-sim="CROWD" data-value="90">Crowd Surge (90%)</button>
          <button class="danger" data-sim="FLIGHT_DELAY" data-value="60">Severe Delay (+60m)</button>
        </div>
        <div style="margin-top:14px;padding:12px;background:#f8fafc;border:1px solid var(--line);border-radius:8px">
          <strong>Current Scenario Values:</strong>
          <div class="kpis" style="margin-top:6px">
            <div class="kpi"><span>Inbound Delay</span><strong>+${e.inbound_delay || 0}m</strong></div>
            <div class="kpi"><span>Security Crowd</span><strong>${e.crowd || 50}%</strong></div>
            <div class="kpi"><span>Bag Status</span><strong>${esc(e.baggage_status || 'Transfer expected')}</strong></div>
          </div>
        </div>
      </section>
    </div>

    <!-- Live Margin Breakdown Card -->
    <section class="card">
      <div class="card-head">
        <div><div class="eyebrow">AI RISK ASSESSMENT</div><h2>Margin Breakdown: ${badge(e.level || 'SAFE')}</h2></div>
        <strong style="font-size:24px;color:var(--navy)">${e.risk || 0}% Risk</strong>
      </div>
      <div class="metrics">
        <div class="metric"><span>Available Window</span><strong>${e.available_minutes ?? 0}m</strong></div>
        <div class="metric"><span>Walking to Gate ${e.outbound_gate || 'B12'}</span><strong>${e.walk_minutes ?? 0}m</strong></div>
        <div class="metric"><span>Security Screening</span><strong>${e.security_minutes ?? 0}m</strong></div>
        <div class="metric"><span>Safe Net Margin</span><strong>${e.margin_minutes ?? 0}m</strong></div>
      </div>
      <p style="margin-top:10px"><strong>Action Plan:</strong> ${esc(e.message || '')}</p>
    </section>
  `;
}

// 5. My Trips & Travel Timeline View
function viewTrips() {
  const trips = state.myTrips || [];

  return `
    ${pageHead('TRAVEL MANAGER', 'My Trips & Journey Timeline', `
      <button class="primary" data-action="openAddTripModal">+ Add Trip</button>
      <button class="secondary" data-action="loadTrips">↻ Refresh</button>
    `)}

    <div class="grid">
      <!-- Saved Trips Cards -->
      <div>
        <h2>Saved Itineraries (${trips.length})</h2>
        <div class="list" style="margin-top:12px">
          ${trips.map(tr => `
            <div class="ticket-card" style="margin-bottom:12px">
              <div class="ticket-top">
                <strong>✈ ${esc(tr.flight_number)} · ${esc(tr.airline)}</strong>
                <span class="badge ${tr.status === 'ACTIVE' ? 'safe' : 'tight'}">${esc(tr.status)}</span>
              </div>
              <div class="ticket-body">
                <div class="ticket-route">
                  <div>
                    <span class="code">${esc(tr.from_code)}</span>
                    <span class="small" style="display:block">${esc(tr.from_name || tr.from_code)}</span>
                  </div>
                  <div class="plane-icon">✈ ──── ›</div>
                  <div style="text-align:right">
                    <span class="code">${esc(tr.to_code)}</span>
                    <span class="small" style="display:block">${esc(tr.to_name || tr.to_code)}</span>
                  </div>
                </div>
                <div class="ticket-grid">
                  <div><span>Departure</span><strong>${esc(tr.dep)}</strong></div>
                  <div><span>Arrival</span><strong>${esc(tr.arr)}</strong></div>
                  <div><span>Gate</span><strong>${esc(tr.gate || 'A04')}</strong></div>
                  <div><span>Terminal</span><strong>${esc(tr.terminal || 'T3')}</strong></div>
                  <div><span>Seat</span><strong>${esc(tr.seat || '12A')}</strong></div>
                  <div><span>PNR</span><strong>${esc(tr.pnr || 'YF-8921')}</strong></div>
                  <div><span>Baggage</span><strong>${esc(tr.baggage_belt || 'Belt 04')}</strong></div>
                  <div><span>Travel Date</span><strong>${esc(tr.trip_date)}</strong></div>
                </div>
                <div class="actions" style="margin-top:12px">
                  <button class="primary" data-action="addTripToGoogleCal" data-id="${tr.id}">📅 Add to Google Calendar</button>
                  <button class="secondary" data-action="downloadICS" data-id="${tr.id}">📥 Download .ics</button>
                  <button class="danger" data-action="deleteTrip" data-id="${tr.id}">🗑 Delete</button>
                </div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- End-to-End Travel Timeline -->
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">CHRONOLOGICAL STAGES</div><h2>Complete Travel Timeline</h2></div>
          <span class="status-pill live">TRACKER</span>
        </div>
        <p>End-to-end journey stages from home departure to final arrival:</p>
        <div class="timeline-track">
          <div class="timeline-step completed">
            <strong>1. Journey Preparation & Online Check-in</strong>
            <span>Boarding passes generated, PNR registered with YatraFlow connection copilot.</span>
          </div>
          <div class="timeline-step completed">
            <strong>2. Airport Arrival & Security Screening (T1)</strong>
            <span>Completed document verification and terminal baggage drop.</span>
          </div>
          <div class="timeline-step current">
            <strong>3. Inbound Flight Airborne (6E 604)</strong>
            <span>Cruising at FL340. Real-time transponder telemetry monitored via OpenSky radar.</span>
          </div>
          <div class="timeline-step">
            <strong>4. Delhi Airport (DEL T3) Layover Transfer</strong>
            <span>Airside inter-gate transit to Gate B12. Automated baggage belt transfer initiated.</span>
          </div>
          <div class="timeline-step">
            <strong>5. Outbound Connecting Flight (AI 201)</strong>
            <span>Boarding Gate B12 closes 15 mins prior to departure.</span>
          </div>
          <div class="timeline-step">
            <strong>6. Destination Arrival & Baggage Reclaim</strong>
            <span>Luggage retrieval at Belt 11 followed by Airport Express Metro connection.</span>
          </div>
        </div>
      </section>
    </div>
  `;
}

// 6. Transit Hotels View
function viewHotels() {
  const hotels = state.hotels || [];

  return `
    ${pageHead('TRANSIT STAYS', 'Airport Transit Hotels & Sleeping Pods', `
      <button class="primary" data-action="loadHotels">↻ Refresh Stays</button>
    `)}

    <div class="card" style="margin-bottom:14px">
      <div class="card-head">
        <div><div class="eyebrow">TRANSIT ACCOMMODATION DIRECTORY</div><h2>Day-Use & Overnight Rooms</h2></div>
        <span class="status-pill demo">DEMO / RESERVATION ABSTRACTION</span>
      </div>
      <p>Rest comfortably during long airport layovers without leaving the security-cleared transit zone:</p>
    </div>

    <div class="grid">
      ${hotels.map(h => `
        <div class="card">
          <div class="card-head">
            <div>
              <span class="badge ${h.is_airside ? 'safe' : 'tight'}">${h.is_airside ? 'Airside (Inside Security)' : 'Landside / Aerocity'}</span>
              <h2 style="margin-top:6px">${esc(h.name)}</h2>
              <div class="small">${esc(h.location)} · <strong>${esc(h.distance_terminal)}</strong></div>
            </div>
            <strong style="color:#d97706">★ ${h.rating}</strong>
          </div>
          <div style="margin:10px 0">
            <span class="small" style="font-weight:bold">Amenities:</span>
            <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:4px">
              ${(h.amenities || []).map(a => `<span class="status-pill">${esc(a)}</span>`).join('')}
            </div>
          </div>
          <div style="margin-top:12px;background:#f8fafc;padding:10px;border-radius:8px;border:1px solid var(--line)">
            <span class="small" style="font-weight:bold">Hourly Layover Rates:</span>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:6px">
              ${(h.hourly_rates || []).map(r => `
                <div class="small">
                  <span>${esc(r.label)}:</span>
                  <strong> ₹${r.price_inr.toLocaleString('en-IN')}</strong>
                </div>
              `).join('')}
            </div>
          </div>
          <div class="actions">
            <button class="primary" data-action="inquireHotel" data-hotel-id="${esc(h.id)}" data-hotel-name="${esc(h.name)}">Reserve Layover Pod</button>
            <button class="secondary" data-action="callHotel" data-phone="${esc(h.contact)}">📞 Call Desk</button>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

// 7. Ground Transport & Bus Tracking View
function viewTransport() {
  const routes = state.busRoutes || [];

  return `
    ${pageHead('GROUND TRANSIT', 'Airport Metro, Shuttles & Live Bus Tracking', `
      <button class="primary" data-action="loadBuses">↻ Refresh Feeder GPS</button>
    `)}

    <div class="grid">
      <!-- Multi-Modal Transport Hub -->
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">AIRPORT TRANSIT OPTIONS</div><h2>Official Terminal Ground Modes</h2></div>
          <span class="status-pill demo">OFFICIAL TARIFFS</span>
        </div>
        <div class="list">
          <div class="list-row">
            <div>
              <strong>Delhi Airport Express Metro (Orange Line)</strong>
              <div class="small">Runs directly from T2/T3 Station to New Delhi Railway Station in 19 mins.</div>
              <div class="small" style="color:var(--blue)">Operating: 04:45 AM - 11:30 PM (Every 10 mins)</div>
            </div>
            <div style="text-align:right">
              <strong>₹60</strong>
              <span class="badge safe">FASTEST</span>
            </div>
          </div>
          <div class="list-row">
            <div>
              <strong>Delhi Traffic Police Prepaid Taxi</strong>
              <div class="small">Official fixed-rate counters inside T3 & T2 arrivals hall exit.</div>
            </div>
            <div style="text-align:right">
              <strong>Govt Tariff</strong>
              <span class="badge tight">OFFICIAL</span>
            </div>
          </div>
          <div class="list-row">
            <div>
              <strong>Ola / Uber App Pickup Zone</strong>
              <div class="small">Designated multi-level car parking MLCP Level 2 (Pillar 12-16).</div>
            </div>
            <div style="text-align:right">
              <strong>₹450 - ₹750</strong>
              <span class="badge safe">DOOR-TO-DOOR</span>
            </div>
          </div>
        </div>
      </section>

      <!-- User Active Vehicles -->
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">YOUR TRANSIT</div><h2>Attached Vehicles</h2></div>
          <span class="status-pill demo">USER LOG</span>
        </div>
        <div id="transportList">Loading vehicle feeds…</div>
        <div class="actions">
          <button class="primary" data-action="addDemoTransport">+ Register Cab / Feeder</button>
        </div>
      </section>
    </div>

    <!-- Live Bus Tracking Simulation -->
    <section class="card">
      <div class="card-head">
        <div><div class="eyebrow">AIRPORT EXPRESS BUS LINES</div><h2>Live Feeder GPS Tracking (Simulation)</h2></div>
        <span class="status-pill demo">SIMULATED TELEMETRY</span>
      </div>
      <p>Live Volvo AC airport express buses connecting terminals to major city transit hubs:</p>
      <div class="grid">
        ${routes.map(r => `
          <div style="padding:14px;background:#f8fafc;border:1px solid var(--line);border-radius:10px">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <div>
                <strong>🚌 ${esc(r.name)}</strong>
                <div class="small">${esc(r.origin)} → ${esc(r.destination)}</div>
              </div>
              <span class="badge ${r.status === 'EN_ROUTE' ? 'safe' : 'tight'}">${esc(r.status)}</span>
            </div>
            <div style="margin-top:10px;padding:8px;background:#fff;border-radius:6px;border:1px solid var(--line)">
              <div class="small">Vehicle: <strong>${esc(r.vehicle_no)}</strong> · Fare: <strong>₹${r.fare_inr}</strong></div>
              <div class="small" style="color:var(--green)">Current GPS: ${r.current_gps ? `${r.current_gps.lat.toFixed(4)}°N, ${r.current_gps.lon.toFixed(4)}°E (${r.current_gps.speed_kmh} km/h)` : 'En route'}</div>
              <div class="small">Approaching: <strong>${esc(r.current_gps?.next_stop_name || 'Terminal')}</strong></div>
            </div>
            <div class="timeline-track" style="margin-top:10px">
              ${(r.stops || []).map(s => `
                <div class="timeline-step ${s.passed ? 'completed' : (s.is_current ? 'current' : '')}">
                  <strong>${esc(s.name)}</strong>
                  <span>ETA: +${s.eta_min} min</span>
                </div>
              `).join('')}
            </div>
          </div>
        `).join('')}
      </div>
    </section>
  `;
}

// 8. CARE & Emergency SOS View
function viewCare() {
  return `
    ${pageHead('CARE & SAFETY', 'Inclusive Assistance & National Emergency Protocol', `
      <button class="danger" data-action="emergency">🚨 Trigger SOS (112)</button>
    `)}

    <div class="grid three">
      <!-- CARE Accessibility Profile -->
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">CARE ENGINE</div><h2>Accessibility Profile</h2></div>
          <span class="status-pill live">ACTIVE</span>
        </div>
        <p class="small">Select your assistance needs for tailored walking times and elevator routing:</p>
        <div class="list">
          ${['WHEELCHAIR', 'LOW_VISION', 'HEARING', 'SPEECH_ASSIST', 'ELDERLY', 'SIMPLE_MODE'].map(x => `
            <label class="list-row">
              <span>${esc(x.replaceAll('_', ' '))}</span>
              <input type="checkbox" class="access" value="${x}" ${state.profile?.accessibility?.includes(x) ? 'checked' : ''} style="width:auto">
            </label>
          `).join('')}
        </div>
        <button class="primary" data-action="saveAccess" style="margin-top:12px;width:100%">Apply CARE Profile</button>
      </section>

      <!-- Baggage Tracker -->
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">LUGGAGE TRACKING</div><h2>Tracked Bags</h2></div>
          <span class="status-pill demo">FEED</span>
        </div>
        <div id="bags">Loading luggage…</div>
        <div class="actions">
          <button class="soft" data-action="addDemoBag">+ Add Bag Tag</button>
        </div>
      </section>

      <!-- Airport Security & Assistance Contacts -->
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">AIRPORT HELPDESK</div><h2>24/7 Security & Police</h2></div>
          <span class="status-pill live">VERIFIED</span>
        </div>
        <div class="list">
          <div class="list-row">
            <span>National Emergency</span>
            <strong>112</strong>
          </div>
          <div class="list-row">
            <span>CISF Airport Control</span>
            <strong>011-25652389</strong>
          </div>
          <div class="list-row">
            <span>Medanta T3 Clinic</span>
            <strong>011-49652000</strong>
          </div>
          <div class="list-row">
            <span>Lost & Found Desk</span>
            <strong>011-49652222</strong>
          </div>
        </div>
        <div class="actions">
          <button class="primary" data-action="lostPassenger">🚨 I Am Lost (Beacon)</button>
        </div>
      </section>
    </div>

    <!-- Human Assistance Requests -->
    <section class="card">
      <div class="card-head">
        <div><div class="eyebrow">AIRPORT GROUND ASSISTANCE</div><h2>Request Airport Staff Dispatch</h2></div>
        <span class="status-pill live">HUMAN SUPPORT</span>
      </div>
      <div class="grid three" style="margin:0">
        ${['WHEELCHAIR', 'VISUAL', 'HEARING', 'SPEECH', 'ELDERLY', 'I AM LOST'].map(x => `
          <button class="action-card secondary" data-assist="${x}" style="text-align:left">
            <strong>${x} ASSISTANCE</strong>
            <p>Immediate airport ground team dispatch to your current location.</p>
            <span style="color:var(--blue);font-weight:bold">Request Help →</span>
          </button>
        `).join('')}
      </div>
    </section>
  `;
}

// 9. Notifications Center View
function viewNotifications() {
  const notifs = state.notifications || [];
  const pref = state.overview?.preferences || {};

  return `
    ${pageHead('NOTIFICATION CENTER', 'Real-Time Multi-Channel Alerts', `
      <button class="primary" data-action="markNotifsRead">Mark All Read</button>
      <button class="secondary" data-action="clearNotifs">Clear History</button>
    `)}

    <div class="grid">
      <!-- Notification List -->
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">IN-APP NOTIFICATIONS</div><h2>Recent Alerts (${notifs.length})</h2></div>
          <button class="soft" data-action="requestPush">Enable Push Alerts</button>
        </div>
        <div class="list">
          ${notifs.length ? notifs.map(n => `
            <div class="list-row" style="background:${n.read ? 'transparent' : '#f0f7ff'};padding:10px;border-radius:8px">
              <div>
                <div style="display:flex;align-items:center;gap:6px">
                  <span class="status-pill ${n.type === 'EMERGENCY' ? 'unavailable' : 'live'}">${esc(n.type)}</span>
                  <strong>${esc(n.title)}</strong>
                </div>
                <div class="small" style="margin-top:4px">${esc(n.message)}</div>
                <div class="small" style="color:var(--muted);margin-top:2px">${new Date(n.created_at * 1000).toLocaleTimeString()}</div>
              </div>
            </div>
          `).join('') : '<p class="small">No notifications in your inbox.</p>'}
        </div>
      </section>

      <!-- Multi-Channel Delivery Testing & Preferences -->
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">CHANNELS & AUTOMATION</div><h2>Multi-Channel Dispatch Engine</h2></div>
          <span class="status-pill live">n8n / WHATSAPP / EMAIL</span>
        </div>
        <p>Test real responsive HTML emails and Meta WhatsApp Cloud API format dispatches:</p>
        <div style="margin-top:14px;display:grid;gap:12px">
          <!-- Email Test -->
          <div style="padding:12px;background:#f8fafc;border:1px solid var(--line);border-radius:8px">
            <strong>📧 Responsive Email Simulator</strong>
            <p class="small">Dispatches responsive HTML emails in English, Tamil, or Hindi.</p>
            <div class="actions">
              <button class="secondary" data-action="sendTestEmail" data-lang="en">Send Email (EN)</button>
              <button class="secondary" data-action="sendTestEmail" data-lang="ta">Send Email (தமிழ்)</button>
              <button class="secondary" data-action="sendTestEmail" data-lang="hi">Send Email (हिंदी)</button>
            </div>
          </div>

          <!-- WhatsApp Verification & Test -->
          <div style="padding:12px;background:#f8fafc;border:1px solid var(--line);border-radius:8px">
            <strong>💬 Meta WhatsApp Cloud API Dispatcher</strong>
            <p class="small">Verify phone number with 6-digit OTP to receive live flight & connection risk updates:</p>
            <div class="form-grid" style="margin-top:8px">
              <input id="waPhone" placeholder="+919876543210" value="${esc(state.profile?.whatsapp_number || state.profile?.phone || '+919876543210')}">
              <button class="primary" data-action="sendWhatsAppOTP">Send OTP Code</button>
            </div>
            <div class="form-grid" style="margin-top:8px">
              <input id="waOtp" placeholder="Enter 6-digit OTP code">
              <button class="secondary" data-action="verifyWhatsAppOTP">Verify & Activate</button>
            </div>
          </div>
        </div>
      </section>
    </div>
  `;
}

// 10. Settings & Preferences View
function viewSettings() {
  const ov = state.overview?.modules || {};

  return `
    ${pageHead('SETTINGS', 'Passenger Preferences & Data Providers')}

    <div class="grid">
      <!-- Profile Preferences -->
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">PASSENGER PROFILE</div><h2>Identity & Language</h2></div>
          <span class="status-pill live">SAVED</span>
        </div>
        <form id="settingsForm">
          <div class="form-grid">
            <label>Full Name
              <input id="setName" value="${esc(state.user?.name || '')}">
            </label>
            <label>Email Address
              <input id="setEmail" type="email" disabled value="${esc(state.user?.email || '')}">
            </label>
            <label>Phone Number (E.164)
              <input id="setPhone" value="${esc(state.profile?.phone || '')}" placeholder="+919876543210">
            </label>
            <label>Primary Language
              <select id="setLanguage">
                <option value="English" ${state.profile?.language === 'English' ? 'selected' : ''}>English</option>
                <option value="Tamil" ${state.profile?.language === 'Tamil' ? 'selected' : ''}>தமிழ் (Tamil)</option>
                <option value="Hindi" ${state.profile?.language === 'Hindi' ? 'selected' : ''}>हिंदी (Hindi)</option>
              </select>
            </label>
          </div>
          <div class="actions">
            <button class="primary" type="submit">Save Preferences</button>
            <button type="button" class="outline" data-action="installPWA">📱 Install PWA App</button>
          </div>
        </form>
      </section>

      <!-- Provider Status Matrix -->
      <section class="card">
        <div class="card-head">
          <div><div class="eyebrow">ARCHITECTURE MATRIX</div><h2>Active Data Providers</h2></div>
          <span class="status-pill live">TRANSPARENT STATUS</span>
        </div>
        <p class="small">Every module adheres to strict LIVE / DEMO / UNAVAILABLE labeling:</p>
        <div class="list">
          ${Object.entries(ov).map(([k, v]) => `
            <div class="list-row">
              <span>${esc(k.replaceAll('_', ' ').toUpperCase())}</span>
              ${statusPill(v, v)}
            </div>
          `).join('')}
        </div>
      </section>
    </div>
  `;
}

// Modal Dialog Engine
function renderModal() {
  if (!state.modal) return '';
  const m = state.modal;

  if (m.type === 'sos') {
    return `
      <div class="modal-backdrop" id="modalBackdrop">
        <div class="modal">
          <div class="modal-head">
            <strong style="color:var(--red);font-size:18px">🚨 Emergency Assistance (India 112)</strong>
            <button class="icon-btn" data-action="closeModal">×</button>
          </div>
          <p>You are about to initiate the national emergency protocol. YatraFlow will connect you with the National Emergency Response Centre.</p>
          <div style="background:#fee2e2;padding:12px;border-radius:8px;border:1px solid #f87171;margin:12px 0">
            <strong>Emergency Number: 112</strong>
            <div class="small">Calls require device confirmation. False alerts may be monitored.</div>
          </div>
          <div class="actions" style="justify-content:flex-end">
            <button class="secondary" data-action="closeModal">${t('cancel')}</button>
            <button class="danger" data-action="confirmSOSCall">${t('call_112')}</button>
          </div>
        </div>
      </div>
    `;
  }

  if (m.type === 'addTrip') {
    return `
      <div class="modal-backdrop" id="modalBackdrop">
        <div class="modal">
          <div class="modal-head">
            <strong style="font-size:18px">Add New Trip</strong>
            <button class="icon-btn" data-action="closeModal">×</button>
          </div>
          <form id="addTripForm">
            <div class="form-grid">
              <label>Flight Number<input id="tripFlightNo" required placeholder="6E 604" value="6E 604"></label>
              <label>Airline<input id="tripAirline" required placeholder="IndiGo" value="IndiGo"></label>
              <label>From Airport<input id="tripFrom" required placeholder="MAA" value="MAA"></label>
              <label>To Airport<input id="tripTo" required placeholder="DEL" value="DEL"></label>
              <label>Departure Time<input id="tripDep" required placeholder="08:10" value="08:10"></label>
              <label>Arrival Time<input id="tripArr" required placeholder="11:05" value="11:05"></label>
              <label>Travel Date<input id="tripDate" type="date" required value="${new Date().toISOString().slice(0,10)}"></label>
              <label>PNR Reference<input id="tripPnr" placeholder="YF-8921" value="YF-8921"></label>
            </div>
            <div class="actions" style="margin-top:16px;justify-content:flex-end">
              <button type="button" class="secondary" data-action="closeModal">${t('cancel')}</button>
              <button type="submit" class="primary">Confirm Trip</button>
            </div>
          </form>
        </div>
      </div>
    `;
  }

  if (m.type === 'emailPreview') {
    return `
      <div class="modal-backdrop" id="modalBackdrop">
        <div class="modal" style="width:min(680px,96vw)">
          <div class="modal-head">
            <strong>${esc(m.data.subject)}</strong>
            <button class="icon-btn" data-action="closeModal">×</button>
          </div>
          <div style="border:1px solid var(--line);border-radius:8px;overflow:hidden;max-height:60vh;overflow-y:auto">
            ${m.data.html_preview}
          </div>
          <div class="actions" style="margin-top:14px;justify-content:flex-end">
            <button class="primary" data-action="closeModal">Close Preview</button>
          </div>
        </div>
      </div>
    `;
  }

  return '';
}

// Authentication Screen
function auth() {
  return `<div class="auth">
    <section class="auth-left">
      <div class="eyebrow" style="color:#dcecff">${esc(t('brand_sub'))}</div>
      <h1>YatraFlow keeps your journey connected.</h1>
      <p>One unified platform for real-time flight intelligence, connection risk, gate navigation, transit stays, baggage recovery, and emergency assistance.</p>
      <div class="feature-list">
        <div>✈ Live Flight Telemetry & Radar</div>
        <div>🗺 Interactive Airport Twin Map</div>
        <div>⚡ Connection Guardian Engine</div>
        <div>🏨 Transit Hotels & Sleep Pods</div>
        <div>🚌 Airport Express Metro & Bus</div>
        <div>🎙 Voice Copilot (EN/TA/HI)</div>
      </div>
    </section>
    <section class="auth-right">
      <div class="auth-box">
        <div class="logo" style="margin-bottom:12px">
          <span class="logo-mark">✈</span>
          <span style="font-size:22px;font-weight:950">YatraFlow</span>
        </div>
        <div class="auth-tabs">
          <button class="${state.authMode === 'login' ? 'active' : ''}" data-auth="login">${t('sign_in')}</button>
          <button class="${state.authMode === 'register' ? 'active' : ''}" data-auth="register">${t('create_account')}</button>
        </div>
        ${state.authMode === 'login' ? `
          <form id="authForm">
            <label>Email<input id="email" type="email" required value="${demo.email}"></label>
            <label style="margin-top:12px">Password<input id="password" type="password" required value="${demo.password}"></label>
            <button class="primary" style="width:100%;margin-top:15px">Continue</button>
            <button type="button" class="secondary" id="demoBtn" style="width:100%;margin-top:8px">${t('use_demo')}</button>
          </form>
        ` : `
          <form id="authForm">
            <label>Name<input id="name" required placeholder="Traveler Name"></label>
            <label style="margin-top:12px">Email<input id="email" type="email" required></label>
            <label style="margin-top:12px">Password<input id="password" type="password" minlength="8" required placeholder="Upper, lower & number"></label>
            <button class="primary" style="width:100%;margin-top:15px">Create Account</button>
          </form>
        `}
        <div class="or-divider"><span>OR</span></div>
        <button class="google-btn" id="googleAuthBtn">
          <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"/><path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.34 24 12 24z"/><path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.98 0 12s.45 3.82 1.25 5.42l4.03-3.15z"/><path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.34 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"/></svg>
          ${t('google_login')}
        </button>
        <div id="authmsg" style="margin-top:12px"></div>
        <div class="footer-note">Demo data is clearly marked. Live providers configured via environment keys.</div>
      </div>
    </section>
  </div>`;
}

// Interactive Leaflet Map Initialization
function initLeafletMap() {
  const container = document.getElementById('leafletMap');
  if (!container || typeof L === 'undefined') return;

  if (state.leafletMap) {
    try { state.leafletMap.remove(); } catch {}
    state.leafletMap = null;
  }

  const d = state.data || {};
  const track = getActiveAirTrack(d);
  const showAircraft = state.mapLayer === 'radar' || state.mapTarget === 'aircraft';
  const centerLat = (showAircraft && track) ? track.lat : (d.position?.lat || 28.5562);
  const centerLon = (showAircraft && track) ? track.lon : (d.position?.lon || 77.1000);

  const map = L.map('leafletMap', { zoomControl: false }).setView([centerLat, centerLon], showAircraft ? 12 : 16);
  L.control.zoom({ position: 'bottomright' }).addTo(map);

  // Standard OpenStreetMap base layer
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  state.leafletMap = map;
  renderMapMarkers();
}

function renderMapMarkers() {
  const map = state.leafletMap;
  if (!map || typeof L === 'undefined') return;

  state.mapMarkers.forEach(m => { try { map.removeLayer(m); } catch {} });
  state.mapMarkers = [];

  const d = state.data || {};
  const track = getActiveAirTrack(d);

  if (state.mapLayer === 'radar') {
    // Airspace Radar mode: show all active flights
    const items = d.airspace?.items || [];
    items.forEach(ac => {
      const marker = L.circleMarker([ac.latitude, ac.longitude], {
        radius: 8,
        fillColor: '#0b63ce',
        color: '#ffffff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.9
      }).addTo(map);
      marker.bindPopup(`
        <strong>✈ ${esc(ac.callsign || ac.icao24)}</strong><br>
        Altitude: ${Math.round(ac.altitude_m || 0)}m<br>
        Speed: ${ac.speed_kmh || Math.round((ac.velocity_ms || 0) * 3.6)} km/h<br>
        Heading: ${ac.heading || 0}°<br>
        <small style="color:green">● OpenSky Network Transponder</small>
      `);
      state.mapMarkers.push(marker);
    });
  } else {
    // Terminal Airport Twin mode: show passenger, gates, security, hotels
    const pos = d.position || { lat: 28.5562, lon: 77.1000 };
    const passMarker = L.circleMarker([pos.lat, pos.lon], {
      radius: 9,
      fillColor: '#10b981',
      color: '#ffffff',
      weight: 3,
      opacity: 1,
      fillOpacity: 1
    }).addTo(map);
    passMarker.bindPopup(`<strong>⌖ Your Current Location</strong><br>${esc(pos.name || 'Gate A04')}`);
    state.mapMarkers.push(passMarker);

    // Terminal POIs
    const pois = [
      { name: 'Gate A04 (Inbound)', lat: 28.5558, lon: 77.0990, color: '#3b82f6' },
      { name: 'Gate B12 (Connection)', lat: 28.5570, lon: 77.1015, color: '#ef4444' },
      { name: 'Security Fast-Track', lat: 28.5565, lon: 77.0995, color: '#8b5cf6' },
      { name: 'Holiday Inn Express Transit Hotel', lat: 28.5568, lon: 77.1008, color: '#f59e0b' },
      { name: 'Airport Express Metro Link', lat: 28.5548, lon: 77.0985, color: '#059669' }
    ];

    pois.forEach(p => {
      const mk = L.circleMarker([p.lat, p.lon], {
        radius: 7,
        fillColor: p.color,
        color: '#ffffff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.85
      }).addTo(map);
      mk.bindPopup(`<strong>${p.name}</strong>`);
      state.mapMarkers.push(mk);
    });
  }
}

// Primary load function
async function load() {
  try {
    const d = await api('/api/state');
    state.user = d.user;
    state.csrf = d.user.csrf;
    state.data = d.state;
    state.overview = await api('/api/platform/overview');
    state.profile = (await api('/api/passenger/profile')).profile;
    state.screen = 'app';
    render();
    await loadAllModules();
  } catch (e) {
    state.screen = 'auth';
    render();
    if (e.message !== 'Please sign in again.') toast(e.message);
  }
}

async function loadAllModules() {
  try {
    const tData = await api('/api/trips');
    state.myTrips = tData.items || [];
  } catch {}
  try {
    const hData = await api('/api/hotels');
    state.hotels = hData.items || [];
  } catch {}
  try {
    const bData = await api('/api/transport/buses');
    state.busRoutes = bData.routes || [];
  } catch {}
  try {
    const nData = await api('/api/notifications');
    state.notifications = nData.items || [];
  } catch {}
  try {
    const b = await api('/api/baggage');
    const el = $('#bagSummary');
    if (el) el.textContent = b.items[0]?.status ? `Tag ${b.items[0].tag}: ${b.items[0].status}` : 'Bag monitored';
    const bgList = $('#bags');
    if (bgList) bgList.innerHTML = (b.items || []).map(x => `<div class="list-row"><span><strong>${esc(x.tag)}</strong><br><small>${esc(x.last_location)}</small></span>${badge(x.status === 'TRANSFER' ? 'TIGHT' : 'SAFE')}</div>`).join('');
  } catch {}
  try {
    const t = await api('/api/transport');
    const el = $('#transportSummary');
    if (el) el.textContent = t.items[0]?.vehicle_no ? `${t.items[0].vehicle_no} (ETA: ${t.items[0].eta}m)` : 'Airport Express Metro';
    const tpList = $('#transportList');
    if (tpList) tpList.innerHTML = (t.items || []).map(x => `<div class="list-row"><span><strong>${esc(x.vehicle_no)}</strong><br><small>${esc(x.route)} (${esc(x.pickup)} → ${esc(x.destination)})</small></span><strong>${x.eta}m</strong></div>`).join('');
  } catch {}

  if (state.tab === 'map') {
    setTimeout(initLeafletMap, 100);
  }
}

function addAlert(title, message, level = '') {
  state.alerts.unshift({ title, message, level, ts: Date.now() });
  if (state.alerts.length > 5) state.alerts.length = 5;
  if ('Notification' in window && Notification.permission === 'granted') {
    try { new Notification(`YatraFlow: ${title}`, { body: message }); } catch {}
  }
  render();
}

async function pollAlerts() {
  if (state.screen !== 'app') return;
  try {
    const d = await api('/api/state');
    const old = state.data?.engine?.level, now = d.state?.engine?.level;
    state.data = d.state;
    if (old && now && old !== now) {
      const level = now.includes('MISSED') ? 'red' : (now.includes('RISK') ? 'amber' : 'green');
      addAlert('Connection Risk Updated', `Status is now ${now}. ${d.state?.engine?.message || ''}`, level);
    }
    const n = await api('/api/notifications');
    state.notifications = n.items || [];
  } catch {}
}

function render() {
  $('#app').innerHTML = state.screen === 'auth' ? auth() : shell();
  bindEvents();
  if (state.screen === 'app' && state.tab === 'map') {
    setTimeout(initLeafletMap, 50);
  }
}

function navigate(tab) {
  state.tab = tab;
  state.menuOpen = false;
  state.modal = null;
  render();
  loadAllModules();
}

// Interactive Event Bindings
function bindEvents() {
  // Navigation
  $$('[data-tab]').forEach(b => b.onclick = () => navigate(b.dataset.tab));
  $$('[data-auth]').forEach(b => b.onclick = () => { state.authMode = b.dataset.auth; render(); });

  // Auth
  const form = $('#authForm');
  if (form) {
    form.onsubmit = async e => {
      e.preventDefault();
      try {
        const reg = state.authMode === 'register';
        const body = reg
          ? { name: $('#name').value, email: $('#email').value, password: $('#password').value }
          : { email: $('#email').value, password: $('#password').value };
        const d = await api(reg ? '/api/register' : '/api/login', { method: 'POST', body });
        state.csrf = d.csrf || '';
        await load();
      } catch (x) {
        $('#authmsg').innerHTML = `<div class="alert red">${esc(x.message)}</div>`;
      }
    };
  }

  const demoBtn = $('#demoBtn');
  if (demoBtn) {
    demoBtn.onclick = () => {
      state.authMode = 'login';
      render();
      $('#email').value = demo.email;
      $('#password').value = demo.password;
      $('#authForm').requestSubmit();
    };
  }

  const googleBtn = $('#googleAuthBtn');
  if (googleBtn) {
    googleBtn.onclick = async () => {
      try {
        const d = await api('/api/auth/google', { method: 'POST', body: { email: 'saravanan.traveler@gmail.com', name: 'Saravanan Traveler' } });
        state.csrf = d.csrf || '';
        toast('Google account signed in successfully');
        await load();
      } catch (e) {
        toast(e.message);
      }
    };
  }

  const logout = $('#logoutBtn');
  if (logout) logout.onclick = async () => { await api('/api/logout', { method: 'POST' }); location.reload(); };

  // Language switcher
  const langSel = $('#langSwitch');
  if (langSel) {
    langSel.onchange = e => {
      state.lang = e.target.value;
      localStorage.setItem('yf_lang', state.lang);
      render();
      toast(`Language switched to ${e.target.options[e.target.selectedIndex].text}`);
    };
  }

  // Hamburger drawer
  const hb = $('#hamburger'); if (hb) hb.onclick = () => { state.menuOpen = true; render(); };
  const cb = $('#closeDrawer'); if (cb) cb.onclick = () => { state.menuOpen = false; render(); };
  const db = $('#drawerBackdrop'); if (db) db.onclick = () => { state.menuOpen = false; render(); };

  // Alert dismiss
  $$('[data-dismiss-alert]').forEach(b => b.onclick = () => {
    state.alerts.splice(Number(b.dataset.dismissAlert), 1);
    render();
  });

  // Action dispatcher
  $$('[data-action]').forEach(b => b.onclick = () => handleAction(b.dataset.action, b.dataset));

  // Simulation
  $$('[data-sim]').forEach(b => b.onclick = () => runSim(b.dataset.sim, Number(b.dataset.value)));

  // Assistance
  $$('[data-assist]').forEach(b => b.onclick = () => requestAssist(b.dataset.assist));

  // Voice & SOS
  const vb = $('#voiceBtn'); if (vb) vb.onclick = toggleVoice;
  const sos = $('#sosBtn'); if (sos) sos.onclick = () => { state.modal = { type: 'sos' }; render(); };

  // Forms
  const fSearch = $('#flightSearchForm');
  if (fSearch) {
    fSearch.onsubmit = async e => {
      e.preventDefault();
      try {
        state.searchQuery.from = $('#searchFrom').value;
        state.searchQuery.to = $('#searchTo').value;
        state.searchQuery.date = $('#searchDate').value;
        state.searchQuery.cabin = $('#searchCabin').value;
        state.searchQuery.sort = $('#searchSort').value;
        const res = await api(`/api/flights/search?from_code=${encodeURIComponent(state.searchQuery.from)}&to_code=${encodeURIComponent(state.searchQuery.to)}&cabin_class=${encodeURIComponent(state.searchQuery.cabin)}&sort_by=${encodeURIComponent(state.searchQuery.sort)}`);
        state.searchResults = res.results || [];
        toast(`Found ${state.searchResults.length} flights`);
        render();
      } catch (err) { toast(err.message); }
    };
  }

  const fStatus = $('#flightStatusForm');
  if (fStatus) {
    fStatus.onsubmit = async e => {
      e.preventDefault();
      try {
        const fid = $('#statusFlightNo').value;
        state.flightStatusResult = await api(`/api/flights/${encodeURIComponent(fid)}/status`);
        toast(`Status updated for ${fid}`);
        render();
      } catch (err) { toast(err.message); }
    };
  }

  const fRoute = $('#indoorRouteForm');
  if (fRoute) {
    fRoute.onsubmit = async e => {
      e.preventDefault();
      try {
        const start = $('#routeStart').value;
        const goal = $('#routeGoal').value;
        const accessible = $('#routeAccessible').checked;
        state.accessibleRoute = accessible;
        state.indoorRoute = await api('/api/navigation/route', { method: 'POST', body: { start_zone: start, goal_zone: goal, accessible } });
        toast(`Route calculated: ${state.indoorRoute.eta_minutes} min walk`);
        render();
      } catch (err) { toast(err.message); }
    };
  }

  const fConn = $('#connectionSetupForm');
  if (fConn) {
    fConn.onsubmit = async e => {
      e.preventDefault();
      try {
        const inb = $('#connInbound').value;
        const outb = $('#connOutbound').value;
        const bags = Number($('#connBags').value);
        const pace = $('#connPace').value;
        const imm = $('#connImmigration').checked;
        const d = await api('/api/connection/setup', {
          method: 'POST',
          headers: csrfHeaders(),
          body: { inbound_id: inb, outbound_id: outb, bags, immigration: imm, walking_speed: pace }
        });
        state.data = d.state;
        addAlert('Connection Configured', 'YatraFlow is monitoring your connection window.', 'green');
        navigate('dashboard');
      } catch (err) { toast(err.message); }
    };
  }

  const fTrip = $('#addTripForm');
  if (fTrip) {
    fTrip.onsubmit = async e => {
      e.preventDefault();
      try {
        await api('/api/trips', {
          method: 'POST',
          headers: csrfHeaders(),
          body: {
            flight_number: $('#tripFlightNo').value,
            airline: $('#tripAirline').value,
            from_code: $('#tripFrom').value,
            to_code: $('#tripTo').value,
            dep: $('#tripDep').value,
            arr: $('#tripArr').value,
            trip_date: $('#tripDate').value,
            pnr: $('#tripPnr').value
          }
        });
        state.modal = null;
        toast('Trip added to My Trips!');
        await loadAllModules();
        render();
      } catch (err) { toast(err.message); }
    };
  }

  const fSet = $('#settingsForm');
  if (fSet) {
    fSet.onsubmit = async e => {
      e.preventDefault();
      try {
        await api('/api/passenger/profile', {
          method: 'POST',
          headers: csrfHeaders(),
          body: {
            phone: $('#setPhone').value,
            language: $('#setLanguage').value,
            accessibility: state.profile?.accessibility || []
          }
        });
        toast('Preferences saved successfully');
      } catch (err) { toast(err.message); }
    };
  }
}

// Action Dispatcher
async function handleAction(act, data = {}) {
  try {
    if (act === 'refresh') {
      const d = await api('/api/state');
      state.data = d.state;
      state.overview = await api('/api/platform/overview');
      toast('Journey and telemetry refreshed');
      render();
    } else if (act === 'closeModal') {
      state.modal = null;
      render();
    } else if (act === 'locate') {
      if (!navigator.geolocation) return toast('Geolocation is not supported by your browser.');
      navigator.geolocation.getCurrentPosition(async p => {
        try {
          const d = await api('/api/position/gps', {
            method: 'POST',
            headers: csrfHeaders(),
            body: { lat: p.coords.latitude, lon: p.coords.longitude, accuracy: p.coords.accuracy || 0 }
          });
          state.data = d.state || state.data;
          toast(`GPS Location: ${p.coords.latitude.toFixed(4)}°N, ${p.coords.longitude.toFixed(4)}°E`);
          render();
        } catch {
          toast(`Device GPS: ${p.coords.latitude.toFixed(4)}, ${p.coords.longitude.toFixed(4)}`);
        }
      }, () => toast('Location permission was denied.'));
    } else if (act === 'emergency') {
      state.modal = { type: 'sos' };
      render();
    } else if (act === 'confirmSOSCall') {
      await api('/api/emergency', { method: 'POST', headers: csrfHeaders(), body: { type: 'GENERAL', location: state.data?.position?.name || 'Current location' } });
      state.modal = null;
      render();
      toast('Initiating call to 112 emergency center...');
      window.location.href = 'tel:112';
    } else if (act === 'lostPassenger') {
      await requestAssist('I AM LOST');
    } else if (act === 'switchMapLayer') {
      state.mapLayer = data.layer;
      render();
    } else if (act === 'toggleRadarMap') {
      state.mapLayer = state.mapLayer === 'radar' ? 'airport' : 'radar';
      render();
    } else if (act === 'mapFocus') {
      state.mapTarget = data.target;
      render();
      toast(`Map centered on ${data.target}`);
    } else if (act === 'clearFlightSearch') {
      state.searchQuery = { from: 'DEL', to: 'BOM', date: '', cabin: 'Economy', airline: '', sort: 'price_asc' };
      state.searchResults = null;
      render();
    } else if (act === 'popularRoute') {
      $('#searchFrom').value = data.from;
      $('#searchTo').value = data.to;
      $('#flightSearchForm').requestSubmit();
    } else if (act === 'statusPreset') {
      $('#statusFlightNo').value = data.flight;
      $('#flightStatusForm').requestSubmit();
    } else if (act === 'bookToTrips') {
      const f = JSON.parse(data.flight);
      await api('/api/trips', {
        method: 'POST',
        headers: csrfHeaders(),
        body: {
          flight_number: f.number,
          airline: f.airline,
          from_code: f.from,
          from_name: f.from_name,
          to_code: f.to,
          to_name: f.to_name,
          dep: f.dep,
          arr: f.arr,
          trip_date: new Date().toISOString().slice(0, 10),
          gate: f.gate || 'A04',
          terminal: f.terminal || f.terminal_dep || 'T3'
        }
      });
      toast(`Flight ${f.number} added to My Trips!`);
      navigate('trips');
    } else if (act === 'openAddTripModal') {
      state.modal = { type: 'addTrip' };
      render();
    } else if (act === 'deleteTrip') {
      await api(`/api/trips/${data.id}`, { method: 'DELETE', headers: csrfHeaders() });
      toast('Trip removed.');
      await loadAllModules();
      render();
    } else if (act === 'addTripToGoogleCal') {
      const res = await api(`/api/trips/${data.id}/calendar`);
      if (res.google_calendar_url) window.open(res.google_calendar_url, '_blank');
    } else if (act === 'downloadICS') {
      window.open(`/api/trips/${data.id}/calendar?format=ics`, '_blank');
    } else if (act === 'openTripCal') {
      const firstTrip = state.myTrips[0];
      if (firstTrip) {
        const res = await api(`/api/trips/${firstTrip.id}/calendar`);
        if (res.google_calendar_url) window.open(res.google_calendar_url, '_blank');
      } else {
        toast('Add a trip to sync with Google Calendar.');
      }
    } else if (act === 'loadHotels') {
      const hData = await api('/api/hotels');
      state.hotels = hData.items || [];
      toast('Hotels refreshed');
      render();
    } else if (act === 'inquireHotel') {
      await api('/api/hotels/inquire', {
        method: 'POST',
        headers: csrfHeaders(),
        body: {
          hotel_id: data.hotelId,
          hotel_name: data.hotelName,
          check_in_date: new Date().toISOString().slice(0, 10),
          hours: 6,
          guest_name: state.user?.name || 'Traveler',
          contact: state.profile?.phone || '+919876543210'
        }
      });
      toast(`Reservation inquiry confirmed for ${data.hotelName}`);
    } else if (act === 'callHotel') {
      window.location.href = `tel:${data.phone}`;
    } else if (act === 'loadBuses') {
      const bData = await api('/api/transport/buses');
      state.busRoutes = bData.routes || [];
      toast('Bus feeder positions refreshed');
      render();
    } else if (act === 'addDemoTransport') {
      await api('/api/transport', {
        method: 'POST',
        headers: csrfHeaders(),
        body: { vehicle_no: 'DL-01-AB-4021', route: 'Ola Premium Sedan', pickup: 'T3 Level 2 MLCP', destination: 'Connaught Place', eta: 12 }
      });
      await loadAllModules();
      toast('Vehicle registered.');
      render();
    } else if (act === 'addDemoBag') {
      await api('/api/baggage', {
        method: 'POST',
        headers: csrfHeaders(),
        body: { tag: `TAG-${Math.floor(1000 + Math.random() * 8999)}`, status: 'TRANSFER', last_location: 'T3 Transfer Belt 4' }
      });
      await loadAllModules();
      toast('Bag tag added to care engine.');
      render();
    } else if (act === 'saveAccess') {
      const selected = [...$$('.access:checked')].map(x => x.value);
      await api('/api/passenger/profile', { method: 'POST', headers: csrfHeaders(), body: { accessibility: selected, language: state.lang } });
      state.profile = { ...(state.profile || {}), accessibility: selected };
      toast('CARE accessibility profile saved!');
    } else if (act === 'markNotifsRead') {
      await api('/api/notifications/read', { method: 'POST', headers: csrfHeaders() });
      state.notifications.forEach(n => n.read = 1);
      toast('All notifications marked as read.');
      render();
    } else if (act === 'clearNotifs') {
      await api('/api/notifications/clear', { method: 'POST', headers: csrfHeaders() });
      state.notifications = [];
      toast('Notification history cleared.');
      render();
    } else if (act === 'requestPush') {
      if ('Notification' in window) {
        const res = await Notification.requestPermission();
        toast(`Push notification permission: ${res}`);
      }
    } else if (act === 'sendTestEmail') {
      const res = await api('/api/notifications/test-email', { method: 'POST', headers: csrfHeaders(), body: { language: data.lang, event_type: 'CONNECTION_AT_RISK' } });
      state.modal = { type: 'emailPreview', data: res };
      render();
    } else if (act === 'sendWhatsAppOTP') {
      const phone = $('#waPhone').value;
      const res = await api('/api/whatsapp/send-otp', { method: 'POST', headers: csrfHeaders(), body: { phone } });
      toast(res.message);
      if (res.demo_otp) {
        $('#waOtp').value = res.demo_otp;
        toast(`Demo OTP auto-filled: ${res.demo_otp}`);
      }
    } else if (act === 'verifyWhatsAppOTP') {
      const phone = $('#waPhone').value;
      const otp = $('#waOtp').value;
      const res = await api('/api/whatsapp/verify-otp', { method: 'POST', headers: csrfHeaders(), body: { phone, otp } });
      toast(res.message);
      await loadAllModules();
    } else if (act === 'installPWA') {
      if (state.deferredInstallPrompt) {
        state.deferredInstallPrompt.prompt();
        const { outcome } = await state.deferredInstallPrompt.userChoice;
        toast(`PWA install: ${outcome}`);
        state.deferredInstallPrompt = null;
      } else {
        toast('To install YatraFlow, tap Share / Settings in your browser and select "Add to Home Screen".');
      }
    }
  } catch (err) {
    toast(err.message || 'Action failed');
  }
}

async function requestAssist(type) {
  try {
    await api('/api/assistance', {
      method: 'POST',
      headers: csrfHeaders(),
      body: { type, priority: type === 'I AM LOST' ? 'HIGH' : 'NORMAL', location: state.data?.position?.name || 'Terminal concourse' }
    });
    toast(`${type} assistance dispatched.`);
    addAlert('Assistance Dispatched', `Airport ground team alerted for ${type}.`, 'amber');
  } catch (e) { toast(e.message); }
}

async function runSim(type, val) {
  try {
    const d = await api('/api/simulation/event', {
      method: 'POST',
      headers: csrfHeaders(),
      body: { event_type: type, value: val }
    });
    state.data = d.state;
    state.overview = await api('/api/platform/overview');
    addAlert('Simulation Event Applied', `${type} +${val} injected into journey copilot.`, type.includes('DELAY') ? 'amber' : 'red');
    render();
  } catch (e) { toast(e.message); }
}

// Multilingual Voice Copilot
function toggleVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return toast('Voice input is not supported in this browser. Try Chrome or Edge.');
  if (state.listening) return;

  const r = new SpeechRecognition();
  r.lang = state.lang === 'ta' ? 'ta-IN' : (state.lang === 'hi' ? 'hi-IN' : 'en-IN');
  r.interimResults = false;
  r.maxAlternatives = 1;

  state.listening = true;
  $('#voiceBtn')?.classList.add('listening');
  toast('Voice Copilot listening… Speak your question.');

  r.onresult = e => handleVoiceQuery(e.results[0][0].transcript);
  r.onerror = () => {
    state.listening = false;
    $('#voiceBtn')?.classList.remove('listening');
    toast('Voice query could not be understood.');
  };
  r.onend = () => {
    state.listening = false;
    $('#voiceBtn')?.classList.remove('listening');
  };
  r.start();
}

function handleVoiceQuery(q) {
  q = q.toLowerCase();
  let answer = '';

  if (q.includes('flight') || q.includes('status') || q.includes('நிலை') || q.includes('उड़ान')) {
    answer = `Your monitored flight is ${state.data?.outbound?.number || 'AI 201'}. Connection status is ${state.data?.engine?.level || 'Safe'}.`;
  } else if (q.includes('gate') || q.includes('way') || q.includes('வழி') || q.includes('गेट')) {
    navigate('map');
    answer = `Your connecting gate is ${state.data?.engine?.outbound_gate || 'B12'}. Opening indoor map.`;
  } else if (q.includes('hotel') || q.includes('sleep') || q.includes('விடுதி') || q.includes('होटल')) {
    navigate('hotels');
    answer = 'Opening transit hotels and sleep pods inside Terminal 3.';
  } else if (q.includes('bus') || q.includes('metro') || q.includes('பஸ்') || q.includes('बस')) {
    navigate('transport');
    answer = 'Opening Airport Express Metro and live bus feeder routes.';
  } else if (q.includes('emergency') || q.includes('sos') || q.includes('ஆபத்து') || q.includes('मदद')) {
    handleAction('emergency');
    answer = 'Opening emergency protocol for national 112 assistance.';
  } else {
    answer = 'I am your YatraFlow airport connection companion. You can ask about flight status, gate directions, connection risk, hotels, or emergency assistance.';
  }

  toast(answer);
  if ('speechSynthesis' in window) {
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(answer);
    u.lang = state.lang === 'ta' ? 'ta-IN' : (state.lang === 'hi' ? 'hi-IN' : 'en-IN');
    speechSynthesis.speak(u);
  }
}

// PWA Service Worker & Install Prompt Listeners
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}

window.addEventListener('beforeinstallprompt', e => {
  e.preventDefault();
  state.deferredInstallPrompt = e;
});

window.addEventListener('online', () => toast('Online: Data connection restored'));
window.addEventListener('offline', () => toast('Offline: Cached app shell remains available'));

// Hardware back button listener for mobile / Android Capacitor
window.addEventListener('popstate', () => {
  if (state.modal) {
    state.modal = null;
    render();
  } else if (state.tab !== 'dashboard') {
    navigate('dashboard');
  }
});

// App Startup
render();
load();
setInterval(pollAlerts, 15000);
