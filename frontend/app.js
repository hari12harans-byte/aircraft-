
const $=s=>document.querySelector(s);
const esc=x=>String(x??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const state={screen:'auth',tab:'dashboard',csrf:'',user:null,data:null,profile:null,overview:null,authMode:'login',listening:false,alerts:[],menuOpen:false};
const demo={email:'demo@yatraflow.ai',password:'YatraFlow@123'};

async function api(path,opt={}){
  const o={credentials:'include',...opt,headers:{'Content-Type':'application/json',...(opt.headers||{})}};
  if(o.body&&typeof o.body!=='string')o.body=JSON.stringify(o.body);
  const r=await fetch(path,o); let d={}; try{d=await r.json()}catch{}
  if(!r.ok)throw new Error(d.detail||'Request failed'); return d;
}
function toast(msg){const x=$('#toast');x.textContent=msg;x.classList.add('show');clearTimeout(window.__toast);window.__toast=setTimeout(()=>x.classList.remove('show'),2800)}
function csrfHeaders(){return {'X-CSRF-Token':state.csrf}}
function badge(level){let c=level==='SAFE'?'safe':level==='TIGHT'?'tight':level==='AT RISK'?'risk':'missed';return `<span class="badge ${c}">${esc(level)}</span>`}

function auth(){
 return `<div class="auth">
  <section class="auth-left"><div class="eyebrow" style="color:#dcecff">INTELLIGENT AIRPORT OPERATIONS</div>
   <h1>YatraFlow keeps your journey connected.</h1>
   <p>One platform for flight intelligence, connection risk, airport navigation, baggage, ground transport, accessibility, emergency assistance and recovery.</p>
   <div class="feature-list"><div>✈ Flight & connection intelligence</div><div>⌖ Airport route & location</div><div>🧳 Baggage intelligence</div><div>♿ CARE accessibility engine</div><div>🆘 Emergency & assistance</div><div>◉ Voice Copilot</div></div>
  </section>
  <section class="auth-right"><div class="auth-box"><div class="logo"><span class="logo-mark">✈</span> YatraFlow</div>
   <div class="auth-tabs"><button class="${state.authMode==='login'?'active':''}" data-auth="login">Sign in</button><button class="${state.authMode==='register'?'active':''}" data-auth="register">Create account</button></div>
   ${state.authMode==='login'?`<form id="authForm"><label>Email<input id="email" type="email" required value="${demo.email}"></label><label style="margin-top:12px">Password<input id="password" type="password" required value="${demo.password}"></label><button class="primary" style="width:100%;margin-top:15px">Continue</button><button type="button" class="secondary" id="demo" style="width:100%;margin-top:8px">Use demo account</button></form>`:
   `<form id="authForm"><label>Name<input id="name" required></label><label style="margin-top:12px">Email<input id="email" type="email" required></label><label style="margin-top:12px">Password<input id="password" type="password" minlength="8" required></label><button class="primary" style="width:100%;margin-top:15px">Create account</button></form>`}
   <div id="authmsg"></div><div class="footer-note">Demo data is clearly marked. Connect authorized providers for production live feeds.</div>
  </div></section>
 </div>`
}

const navItems=[['dashboard','Dashboard','⌂'],['journey','Journey','✈'],['airport','Airport Twin','⌖'],['recovery','Recovery','↻'],['care','CARE & Safety','♿'],['operations','Operations','◉']];
function shell(){
 return `<div class="app">
  <header class="topbar"><div class="logo"><span class="logo-mark">✈</span> YatraFlow</div>
   <nav class="nav">${navItems.map(n=>`<button class="${state.tab===n[0]?'active':''}" data-tab="${n[0]}">${n[2]} ${n[1]}</button>`).join('')}</nav>
   <div class="top-actions"><div class="live"><span class="live-dot"></span> System online</div>
   <button class="icon-btn alert-bell" id="alertBell" title="Notifications">🔔${state.alerts.length?`<span class="alert-count">${Math.min(9,state.alerts.length)}</span>`:''}</button>
   <button class="icon-btn" data-tab="settings">⚙</button><button class="icon-btn" id="logout">↪</button><button class="hamburger" id="hamburger">☰</button></div>
  </header>
  <div class="drawer-backdrop ${state.menuOpen?'open':''}" id="drawerBackdrop"></div>
  <aside class="drawer ${state.menuOpen?'open':''}" id="drawer"><div class="drawer-head"><div class="logo"><span class="logo-mark">✈</span> YatraFlow</div><button class="icon-btn" id="closeDrawer">×</button></div><div class="drawer-nav">${navItems.concat([['settings','Settings','⚙']]).map(n=>`<button class="${state.tab===n[0]?'active':''}" data-tab="${n[0]}">${n[2]} &nbsp; ${n[1]}</button>`).join('')}</div><div class="footer-note">All navigation is mobile optimized.</div></aside>
  <div class="alert-center">${state.alerts.map((a,i)=>`<div class="alert-item ${a.level||''}"><button data-dismiss-alert="${i}">×</button><strong>${esc(a.title)}</strong><span>${esc(a.message)}</span></div>`).join('')}</div>
  <main class="page">${renderSection()}</main>
  <nav class="mobile-bottom">${navItems.slice(0,5).map(n=>`<button class="${state.tab===n[0]?'active':''}" data-tab="${n[0]}">${n[2]}<br>${n[1]}</button>`).join('')}</nav>
  <button class="voice" id="voiceBtn" title="Voice Copilot">🎙</button>
  <button class="sos" id="sosBtn" title="Emergency assistance">SOS</button>
 </div>`
}
function renderSection(){
 if(state.tab==='dashboard')return dashboard();
 if(state.tab==='journey')return journey();
 if(state.tab==='airport')return airport();
 if(state.tab==='recovery')return recovery();
 if(state.tab==='care')return care();
 if(state.tab==='operations')return operations();
 return settings();
}
function pageHead(k,sub,action=''){return `<div class="page-head"><div><div class="eyebrow">${k}</div><h1>${sub}</h1></div>${action}</div>`}

function getActiveAirTrack(d){
  if(!d) return null;
  const lf = (d.outbound?.latitude && d.outbound?.longitude) ? d.outbound :
             (d.inbound?.latitude && d.inbound?.longitude) ? d.inbound : null;
  if(lf){
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
  if(!items.length) return null;

  const f1 = (d.inbound?.number||'').replace(/\s+/g,'').toUpperCase();
  const f2 = (d.outbound?.number||'').replace(/\s+/g,'').toUpperCase();
  const matched = items.find(x => {
    const c = (x.callsign||'').replace(/\s+/g,'').toUpperCase();
    return c && (c === f1 || c === f2 || (f1.length>2 && c.includes(f1)) || (f2.length>2 && c.includes(f2)));
  });

  if(matched){
    return {
      callsign: matched.callsign,
      flight: d.outbound?.number || matched.callsign,
      airline: d.outbound?.airline || 'Monitored Flight',
      lat: Number(matched.latitude),
      lon: Number(matched.longitude),
      alt: matched.altitude_m,
      speed: Math.round((matched.velocity_ms || 0) * 3.6),
      heading: matched.heading,
      source: 'OpenSky Radar (Live Transponder Match)',
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
    source: 'OpenSky Radar (' + (d.airspace?.airport || 'DEL') + ' Corridor)',
    isExact: false
  };
}

function dashboard(){
 const d=state.data,e=d?.engine||{};
 const track=getActiveAirTrack(d);
 const planeRotate = (track && track.heading !== null && track.heading !== undefined)
   ? Math.max(-20, Math.min(20, ((track.heading % 90) - 45)))
   : -7;

 return `<section class="sky-hero"><div class="sky"><div class="cloud c1"></div><div class="cloud c2"></div><div class="cloud c3"></div></div>
 <div class="sky-copy"><div class="eyebrow">YATRAFLOW FLIGHT INTELLIGENCE</div>
 ${track ? `
   <div class="flight-chip live"><span class="live-dot"></span> LIVE RADAR · ${esc(track.callsign)} · ${track.lat.toFixed(4)}°N, ${track.lon.toFixed(4)}°E</div>
   <h1>Your journey, monitored with real-time flight telemetry.</h1>
   <p>Real transponder signals received from live airspace radar. Tracking coordinates, speed, connection risk, baggage and alerts from one passenger command center.</p>
   <div class="telemetry-bar">
     <div class="telemetry-item"><span>COORDINATES</span><strong>${track.lat.toFixed(4)}°, ${track.lon.toFixed(4)}°</strong></div>
     <div class="telemetry-item"><span>ALTITUDE</span><strong>${track.alt ? Math.round(track.alt) + ' m' : 'En route'}</strong></div>
     <div class="telemetry-item"><span>GROUND SPEED</span><strong>${track.speed ? track.speed + ' km/h' : '—'}</strong></div>
     ${track.heading !== null && track.heading !== undefined ? `<div class="telemetry-item"><span>HEADING</span><strong>${Math.round(track.heading)}°</strong></div>` : ''}
     <div class="telemetry-item"><span>RADAR SOURCE</span><strong class="green-text">${esc(track.source)}</strong></div>
   </div>
 ` : `
   <div class="flight-chip"><span class="standby-dot"></span> RADAR STANDBY · ${esc(d?.outbound?.number||'6E 604')} · Scheduled</div>
   <h1>Your journey, monitored from takeoff to connection.</h1>
   <p>Track flight status, connection risk, airport movement, baggage and alerts from one passenger command center.</p>
   <div class="hud-standby">Awaiting live transponder contact in terminal airspace. Real coordinates will display upon radar acquisition (synthetic coordinates disabled).</div>
 `}
 <div class="actions" style="margin-top:16px"><button class="primary" data-tab="airport">Open real map</button><button class="secondary" data-action="refresh">Refresh flight</button></div></div>
 <div class="aircraft-wrap"><div class="trail"></div><div class="aircraft" style="transform:rotate(${planeRotate}deg)"><div class="plane-body"></div><div class="plane-nose"></div><div class="plane-tail"></div><div class="wing"></div><div class="wing bottom"></div><div class="engine"></div><div class="window-row"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div></div></div></section>
 ${pageHead('LIVE JOURNEY','Connection Guardian',`<button class="primary" data-action="refresh">↻ Refresh</button>`)}
 <section class="hero"><div><div class="eyebrow">CURRENT JOURNEY</div><h1>${esc(d?.inbound?.number||'6E 604')} → ${esc(d?.outbound?.number||'AI 201')}</h1><p>${esc(d?.inbound?.from_name||'Chennai')} → ${esc(d?.inbound?.to_name||'Delhi')} → ${esc(d?.outbound?.to_name||'London')} · Passenger at <strong>${esc(d?.position?.name||'Gate A04')}</strong></p><div class="actions"><button class="soft" data-tab="journey">Edit journey</button><button class="secondary" data-tab="airport">Open airport map</button></div></div><div class="hero-side">${badge(e.level||'SAFE')}<strong class="risk-number">${e.risk||0}%</strong><span class="small">connection risk</span></div></section>
 <section class="metrics"><div class="metric"><span>Time available</span><strong>${e.available_minutes??'—'} min</strong></div><div class="metric"><span>Time required</span><strong>${e.required_minutes??'—'} min</strong></div><div class="metric"><span>Connection margin</span><strong>${e.margin_minutes??'—'} min</strong></div><div class="metric"><span>Boarding closes</span><strong>${esc(e.boarding_close||'—')}</strong></div></section>
 <div class="grid"><section class="card"><div class="card-head"><div><div class="eyebrow">AI DECISION ENGINE</div><h2>${badge(e.level||'SAFE')}</h2></div><span class="status-pill ${d?.source?.flights==='Aviationstack'?'live':''}">${d?.source?.flights==='Aviationstack'?'LIVE':'DEMO'}</span></div><p>${esc(e.message||'Set up a journey to start monitoring.')}</p><div><div class="small">Walking · ${e.walk_minutes??0} min</div><div class="progress"><i style="width:${Math.min(100,(e.walk_minutes||0)*5)}%"></i></div><div class="small">Security · ${e.security_minutes??0} min</div><div class="progress"><i style="width:${Math.min(100,(e.security_minutes||0)*7)}%"></i></div><div class="small">Baggage · ${e.baggage_minutes??0} min</div><div class="progress"><i style="width:${Math.min(100,(e.baggage_minutes||0)*5)}%"></i></div></div></section>
 <section class="card"><div class="card-head"><div><div class="eyebrow">ACTION ORCHESTRATOR</div><h2>What to do next</h2></div><span class="status-pill">EVENT ENGINE</span></div><div class="list">${(e.actions||[]).map(a=>`<div class="list-row"><span>${esc(a)}</span><span>›</span></div>`).join('')}</div><div class="actions"><button class="primary" data-tab="recovery">Open recovery</button><button class="secondary" data-tab="care">Get assistance</button></div></section></div>
 <div class="grid three"><section class="card"><div class="eyebrow">FLIGHT</div><h2>${esc(d?.inbound?.number||'—')}</h2><p>${esc(d?.inbound?.airline||'—')} · ${esc(d?.inbound?.status||'Unknown')}</p><span class="status-pill">${esc(d?.inbound?.gate||'Gate —')}</span></section><section class="card"><div class="eyebrow">BAGGAGE</div><h2 id="bagSummary">Loading…</h2><p>Bag-level tracking and transfer risk</p><button class="soft" data-tab="care">Open baggage</button></section><section class="card"><div class="eyebrow">GROUND TRANSPORT</div><h2 id="transportSummary">Loading…</h2><p>Vehicle, route and ETA</p><button class="soft" data-tab="care">Open transport</button></section></div>`
}

function journey(){
 const flights=state.overview?.state?.flights||state.data?.flights||[];
 return `${pageHead('JOURNEY BUILDER','Plan and monitor your connection')}
 <div class="grid"><section class="card"><div class="eyebrow">PASSENGER IDENTITY</div><h2>Associate your journey</h2><div class="form-grid"><label>PNR / booking reference<input id="pnr" value="${esc(state.profile?.pnr||'')}"></label><label>Flight number<input id="flightId" value="${esc(state.profile?.flight_id||'')}"></label><label>Phone<input id="phone" value="${esc(state.profile?.phone||'')}"></label><label>Language<select id="language"><option>English</option><option>Tamil</option><option>Hindi</option></select></label></div><div class="actions"><button class="primary" data-action="saveProfile">Save journey identity</button></div></section>
 <section class="card"><div class="eyebrow">CONNECTION SETUP</div><h2>Choose flights</h2><div class="form-grid"><label>Inbound<select id="inbound">${flights.map((f,i)=>`<option value="${esc(f.id)}" ${i===0?'selected':''}>${esc(f.number)} · ${esc(f.from_name)} → ${esc(f.to_name)}</option>`).join('')}</select></label><label>Connecting flight<select id="outbound">${flights.map((f,i)=>`<option value="${esc(f.id)}" ${i===1?'selected':''}>${esc(f.number)} · ${esc(f.from_name)} → ${esc(f.to_name)}</option>`).join('')}</select></label></div><label style="margin-top:12px"><input id="immigration" type="checkbox" style="width:auto;margin-right:7px"> Immigration required</label><div class="actions"><button class="primary" data-action="setupConnection">Start monitoring</button></div></section></div>
 <section class="card"><div class="eyebrow">JOURNEY LOGIC</div><div class="route"><div class="route-node"><div class="route-dot">1</div><div class="small">Arrive</div></div><div class="route-line"></div><div class="route-node"><div class="route-dot">2</div><div class="small">Security</div></div><div class="route-line"></div><div class="route-node"><div class="route-dot">3</div><div class="small">Gate</div></div><div class="route-line"></div><div class="route-node"><div class="route-dot">4</div><div class="small">Board</div></div></div><p>YatraFlow recalculates the connection whenever delay, crowd, baggage, gate or passenger-location conditions change.</p></section>`
}

function airport(){
 const d=state.data||{}, z=d.zones||{};
 const track=getActiveAirTrack(d);
 const showPlane=state.mapTarget==='aircraft' && track;
 const lat=showPlane ? track.lat : (d.position?.lat||28.5562);
 const lon=showPlane ? track.lon : (d.position?.lon||77.1000);
 const zones=Object.entries(z);
 const mapUrl=`https://www.openstreetmap.org/export/embed.html?bbox=${lon-0.045}%2C${lat-0.035}%2C${lon+0.045}%2C${lat+0.035}&layer=mapnik&marker=${lat}%2C${lon}`;
 return `${pageHead('AIRPORT DIGITAL TWIN','Live airport map',`<button class="primary" data-action="locate">⌖ Detect my location</button>`)}
 <section class="card"><div class="card-head"><div><div class="eyebrow">REAL MAP</div><h2>OpenStreetMap navigation base</h2></div><span class="status-pill live">MAP ONLINE</span></div>
 <div class="map-live"><div class="map-overlay"><strong>${showPlane ? '✈ Live Aircraft: ' + esc(track.callsign) : esc(d.position?.name||'Current location')}</strong><small>${showPlane ? 'Showing real-time transponder coordinates in corridor: ' + lat.toFixed(4) + '°, ' + lon.toFixed(4) + '°' : 'Map center uses passenger location. Indoor routing layers over terminal base.'}</small></div><iframe title="YatraFlow real map" src="${mapUrl}" loading="lazy"></iframe></div>
 <div class="actions">
   <button class="${!showPlane?'primary':'secondary'}" data-action="${showPlane?'focusPassenger':'locate'}">⌖ Passenger location</button>
   ${track ? `<button class="${showPlane?'primary':'secondary'}" data-action="${showPlane?'focusPassenger':'focusAircraft'}">✈ ${showPlane?'Back to passenger':'Track live aircraft ('+esc(track.callsign)+')'}</button>` : ''}
   <button class="secondary" data-action="openMap">Open full map</button>
 </div></section>
 <div class="grid"><section class="card"><div class="eyebrow">INDOOR ROUTE</div><h2>Airport digital twin</h2><p>Gate and accessible routing remain layered over the real map when airport indoor data is available.</p><div class="actions">${zones.filter(([k,v])=>v.type==='gate').map(([k,v])=>`<button class="soft" data-zone="${esc(k)}">${esc(v.name)}</button>`).join('')}</div></section>
 <section class="card"><div class="eyebrow">LOCATION INTELLIGENCE</div><h2>${esc(d.position?.name||'Current location')}</h2><p>GPS provides outdoor position. BLE/Wi-Fi/UWB can be connected for precise indoor gate navigation.</p><div class="kpis"><div class="kpi"><span>Route ETA</span><strong>${d.engine?.route_eta||'—'} min</strong></div><div class="kpi"><span>Destination</span><strong>${esc(d.engine?.outbound_gate||'—')}</strong></div><div class="kpi"><span>Coordinates</span><strong>${lat.toFixed(4)}, ${lon.toFixed(4)}</strong></div></div></section></div>
 <section class="card" style="margin-top:12px"><div class="card-head"><div><div class="eyebrow">TERMINAL AIRSPACE RADAR</div><h2>Live aircraft in corridor (OpenSky Network)</h2></div><span class="status-pill ${d.airspace?.live?'live':''}">${d.airspace?.live?'RADAR LIVE':'STANDBY'}</span></div>
 <p>Live transponder telemetry from ADS-B receivers. Coordinates, altitudes and speeds are real-time broadcast signals.</p>
 <div class="list">${(d.airspace?.items||[]).slice(0,5).map(x=>`<div class="list-row"><span><strong>✈ ${esc(x.callsign||x.icao24)}</strong> &nbsp;<small class="mono">${Number(x.latitude).toFixed(4)}°N, ${Number(x.longitude).toFixed(4)}°E</small></span><span><small>ALT ${Math.round(x.altitude_m||0)}m · SPD ${Math.round((x.velocity_ms||0)*3.6)} km/h</small></span></div>`).join('')||'<div class="small">No transponder signals detected in local radar cell right now.</div>'}</div></section>`;
}
function recovery(){
 const e=state.data?.engine||{}, atRisk=['AT RISK','LIKELY MISSED'].includes(e.level);
 return `${pageHead('RECOVERY ENGINE','Protect the journey')}
 <div class="alert ${atRisk?'red':'green'}"><strong>${atRisk?'Connection requires recovery planning':'Connection currently has a viable buffer'}</strong><br>${esc(e.message||'')}</div>
 <div class="grid three"><div class="action-card"><strong>Alternative flight</strong><p>Show available later-flight options when a live provider is connected.</p><button class="soft" data-action="recoveryOption" style="margin-top:10px">Find options</button></div><div class="action-card"><strong>Ground transfer</strong><p>Coordinate airport shuttle/taxi/metro after a missed connection.</p><button class="soft" data-tab="care" style="margin-top:10px">View transport</button></div><div class="action-card"><strong>Human support</strong><p>Request airline/airport assistance instead of silently failing.</p><button class="soft" data-action="assistance" style="margin-top:10px">Request help</button></div></div>
 <section class="card"><div class="eyebrow">BAGGAGE RECOVERY</div><h2>Keep passenger and bag on the same recovery plan</h2><p>YatraFlow flags transfer risk and exposes the next handling action. Actual airline baggage rerouting requires an authorized baggage provider.</p><div class="actions"><button class="primary" data-action="bagStatus">Check baggage</button><button class="secondary" data-action="transportStatus">Check transport</button></div></section>`
}

function care(){
 return `${pageHead('CARE + SAFETY','Inclusive assistance')}
 <div class="grid three"><section class="card"><div class="eyebrow">CARE ENGINE</div><h2>Accessibility profile</h2><div class="list">${['WHEELCHAIR','LOW_VISION','HEARING','SPEECH_ASSIST','ELDERLY','SIMPLE_MODE'].map(x=>`<label class="list-row"><span>${x.replaceAll('_',' ')}</span><input type="checkbox" class="access" value="${x}" ${state.profile?.accessibility?.includes(x)?'checked':''} style="width:auto"></label>`).join('')}</div><button class="primary" data-action="saveAccess" style="margin-top:12px">Apply accessibility</button></section>
 <section class="card"><div class="eyebrow">BAGGAGE</div><h2>Bag tracking</h2><div id="bags">Loading…</div><div class="actions"><button class="soft" data-action="addDemoBag">Add bag</button></div></section>
 <section class="card"><div class="eyebrow">GROUND TRANSPORT</div><h2>Vehicle tracking</h2><div id="transport">Loading…</div><div class="actions"><button class="soft" data-action="addDemoTransport">Add vehicle</button></div></section></div>
 <section class="card"><div class="eyebrow">ASSISTANCE</div><h2>Get a human when you need one</h2><div class="grid three" style="margin:0">${['WHEELCHAIR','VISUAL','HEARING','SPEECH','ELDERLY','I AM LOST'].map(x=>`<button class="big-action secondary" data-assist="${x}"><span><strong>${x}</strong><small>Airport assistance request</small></span>→</button>`).join('')}</div></section>
 <section class="card"><div class="eyebrow">EMERGENCY</div><h2>Immediate support</h2><p>India emergency number: <strong>112</strong>. Calls require your confirmation on the device.</p><div class="actions"><button class="danger" data-action="emergency">Start emergency workflow</button><button class="secondary" data-action="security">Airport security contact</button><button class="secondary" data-action="lost">I'm lost</button></div></section>`
}

function operations(){
 const c=state.overview?.counts||{};
 return `${pageHead('OPERATIONS','Airport command center',`<button class="primary" data-action="refresh">↻ Refresh</button>`)}
 <div class="metrics"><div class="metric"><span>Open assistance</span><strong>${c.assistance??0}</strong></div><div class="metric"><span>Emergency events</span><strong>${c.emergency??0}</strong></div><div class="metric"><span>Bags tracked</span><strong>${c.bags??0}</strong></div><div class="metric"><span>Unread alerts</span><strong>${c.notifications??0}</strong></div></div>
 <div class="grid"><section class="card"><div class="eyebrow">MODULE STATUS</div><h2>YatraFlow services</h2><div class="list">${Object.entries(state.overview?.modules||{}).map(([k,v])=>`<div class="list-row"><span>${k.replaceAll('_',' ')}</span><span class="status-pill ${String(v).includes('LIVE')?'live':''}">${esc(v)}</span></div>`).join('')}</div></section>
 <section class="card"><div class="eyebrow">SIMULATION CONTROL</div><h2>Test the entire event pipeline</h2><p>Simulation events use the same connection engine and notification path as the demo monitoring flow.</p><div class="actions">${[['FLIGHT_DELAY',15],['FLIGHT_DELAY',30],['BAGGAGE_DELAY',20],['CROWD',90]].map(x=>`<button class="secondary" data-sim="${x[0]}" data-value="${x[1]}">${x[0].replace('_',' ')} +${x[1]}</button>`).join('')}<button class="danger" data-action="emergency">Simulate emergency</button></div></section></div>
 <section class="card"><div class="eyebrow">ANALYTICS</div><h2>Operational metrics</h2><div id="analytics">Loading…</div></section>`
}
function settings(){
 return `${pageHead('SETTINGS','Passenger preferences')}
 <div class="grid"><section class="card"><div class="eyebrow">PROFILE</div><h2>Preferences</h2><div class="form-grid"><label>Language<select id="setLanguage"><option>English</option><option>Tamil</option><option>Hindi</option></select></label><label>Simple mode<select id="setSimple"><option value="0">Standard</option><option value="1">Simple / first-time flyer</option></select></label></div><button class="primary" data-action="saveSettings" style="margin-top:14px">Save preferences</button></section>
 <section class="card"><div class="eyebrow">SYSTEM</div><h2>Data & providers</h2><div class="list"><div class="list-row"><span>Flight data</span><strong>${state.overview?.modules?.flight_monitoring||'DEMO'}</strong></div><div class="list-row"><span>Weather</span><strong>${state.overview?.modules?.weather||'Open-Meteo'}</strong></div><div class="list-row"><span>Supabase</span><strong>${state.overview?.modules?.supabase||'Optional'}</strong></div></div><p class="footer-note">Never place service-role credentials in frontend code. Demo feeds are explicitly labelled.</p></section></div>`
}

async function load(){
 try{
  const d=await api('/api/state'); state.user=d.user; state.csrf=d.user.csrf; state.data=d.state;
  state.overview=await api('/api/platform/overview'); state.profile=(await api('/api/passenger/profile')).profile;
  state.screen='app'; render(); await loadExtras();
 }catch(e){state.screen='auth';render(); if(e.message!=='Please sign in again.')toast(e.message)}
}
async function loadExtras(){
 if(state.tab==='dashboard'){try{const b=await api('/api/baggage');$('#bagSummary').textContent=b.items[0]?.status||'No bag';const t=await api('/api/transport');$('#transportSummary').textContent=t.items[0]?.vehicle_no||'No vehicle'}catch{}}
 if(state.tab==='care'){try{const b=await api('/api/baggage');$('#bags').innerHTML=b.items.map(x=>`<div class="list-row"><span><strong>${esc(x.tag)}</strong><br><small>${esc(x.last_location)}</small></span>${badge(x.status==='TRANSFER'?'TIGHT':'SAFE')}</div>`).join('')}catch{};try{const t=await api('/api/transport');$('#transport').innerHTML=t.items.map(x=>`<div class="list-row"><span><strong>${esc(x.vehicle_no)}</strong><br><small>${esc(x.route)}</small></span><strong>${x.eta} min</strong></div>`).join('')}catch{}}
 if(state.tab==='operations'){try{const a=await api('/api/analytics');$('#analytics').innerHTML=`<div class="kpis">${Object.entries(a.metrics).map(([k,v])=>`<div class="kpi"><span>${k.replaceAll('_',' ')}</span><strong>${v}</strong></div>`).join('')}</div><p>${esc(a.note)}</p>`}catch{}}
}

function addAlert(title,message,level=''){
 state.alerts.unshift({title,message,level,ts:Date.now()});
 if(state.alerts.length>5)state.alerts.length=5;
 if('Notification' in window && Notification.permission==='granted'){try{new Notification(`YatraFlow: ${title}`,{body:message})}catch{}}
 render();
}
async function pollAlerts(){
 if(state.screen!=='app')return;
 try{
  const d=await api('/api/state'); const old=state.data?.engine?.level, now=d.state?.engine?.level;
  state.data=d.state;
  if(old && now && old!==now){
    const level=now.includes('MISSED')?'red':now.includes('RISK')?'amber':'green';
    addAlert('Connection status changed',`Your connection is now ${now}. ${d.state?.engine?.message||''}`,level);
  }
  const n=await api('/api/notifications');
  const unread=(n.items||[]).filter(x=>!x.read);
  if(unread.length && !state.alerts.length){
    unread.slice(0,3).forEach(x=>state.alerts.push({title:x.title,message:x.message,level:x.type==='EMERGENCY'?'red':'amber'}));
    render();
  }
 }catch{}
}
function requestNotificationPermission(){
 try{
  if('Notification' in window && Notification.permission==='default'){
   const p = Notification.requestPermission();
   if(p && typeof p.then==='function') p.catch(()=>{});
  }
 }catch(e){}
}

function render(){ $('#app').innerHTML=state.screen==='auth'?auth():shell(); bind(); if(state.screen==='app')loadExtras() }
function navigate(tab){state.tab=tab;state.menuOpen=false;render()}
function bind(){
 document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>navigate(b.dataset.tab));
 document.querySelectorAll('[data-auth]').forEach(b=>b.onclick=()=>{state.authMode=b.dataset.auth;render()});
 const form=$('#authForm'); if(form)form.onsubmit=async e=>{e.preventDefault();try{const reg=state.authMode==='register';const body=reg?{name:$('#name').value,email:$('#email').value,password:$('#password').value}:{email:$('#email').value,password:$('#password').value};const d=await api(reg?'/api/register':'/api/login',{method:'POST',body});state.csrf=d.csrf||'';await load()}catch(x){$('#authmsg').innerHTML=`<div class="alert red">${esc(x.message)}</div>`}};
 const demoBtn=$('#demo');if(demoBtn)demoBtn.onclick=()=>{state.authMode='login';render();$('#email').value=demo.email;$('#password').value=demo.password;$('#authForm').requestSubmit()};
 const logout=$('#logout');if(logout)logout.onclick=async()=>{await api('/api/logout',{method:'POST'});location.reload()};
 const hb=$('#hamburger');if(hb)hb.onclick=()=>{state.menuOpen=true;render()};
 const cb=$('#closeDrawer');if(cb)cb.onclick=()=>{state.menuOpen=false;render()};
 const db=$('#drawerBackdrop');if(db)db.onclick=()=>{state.menuOpen=false;render()};
 const bell=$('#alertBell');if(bell)bell.onclick=()=>{state.alerts=[];render()};
 document.querySelectorAll('[data-dismiss-alert]').forEach(b=>b.onclick=()=>{state.alerts.splice(Number(b.dataset.dismissAlert),1);render()});
 document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>action(b.dataset.action));
 document.querySelectorAll('[data-zone]').forEach(b=>b.onclick=async()=>{try{const d=await api('/api/position',{method:'POST',headers:csrfHeaders(),body:{zone:b.dataset.zone}});state.data=d.state;toast('Passenger location updated');render()}catch(e){toast(e.message)}});
 document.querySelectorAll('[data-assist]').forEach(b=>b.onclick=()=>requestAssist(b.dataset.assist));
 document.querySelectorAll('[data-sim]').forEach(b=>b.onclick=()=>simulate(b.dataset.sim,Number(b.dataset.value)));
 const vb=$('#voiceBtn');if(vb)vb.onclick=voice;
 const sos=$('#sosBtn');if(sos)sos.onclick=()=>action('emergency');
}
async function action(a){
 try{
  if(a==='refresh'){const d=await api('/api/state');state.data=d.state;state.overview=await api('/api/platform/overview');toast('Journey refreshed');render()}
  if(a==='setupConnection'){const d=await api('/api/connection/setup',{method:'POST',headers:csrfHeaders(),body:{inbound_id:$('#inbound').value,outbound_id:$('#outbound').value,passenger_zone:'A04',bags:1,immigration:$('#immigration').checked}});state.data=d.state;addAlert('Connection monitoring started','YatraFlow is now monitoring your journey.','green');navigate('dashboard')}
  if(a==='saveProfile'){await saveProfile();toast('Journey identity saved')}
  if(a==='saveAccess'){const selected=[...document.querySelectorAll('.access:checked')].map(x=>x.value);await saveProfile(selected);toast('Accessibility profile applied')}
  if(a==='saveSettings'){await saveProfile(state.profile?.accessibility||[]);toast('Preferences saved')}
  if(a==='locate'){if(!navigator.geolocation)return toast('Location is not available in this browser');navigator.geolocation.getCurrentPosition(async p=>{try{const d=await api('/api/position/gps',{method:'POST',headers:csrfHeaders(),body:{lat:p.coords.latitude,lon:p.coords.longitude,accuracy:p.coords.accuracy||0}});state.data=d.state||state.data;toast('Live location updated');render()}catch(e){toast(`GPS received: ${p.coords.latitude.toFixed(3)}, ${p.coords.longitude.toFixed(3)}`)}},()=>toast('Location permission was denied'))}
  if(a==='emergency'){const d=await api('/api/emergency',{method:'POST',headers:csrfHeaders(),body:{type:'GENERAL',location:state.data?.position?.name||'Current location'}});toast(`Emergency workflow ${d.event_id} created. Call 112 only after confirmation.`);window.location.href='tel:112'}
  if(a==='security'){const d=await api('/api/airport/contacts');toast(`Airport security: ${d.security}`)}
  if(a==='lost'){await requestAssist('I AM LOST')}
  if(a==='assistance')await requestAssist('GENERAL')
  if(a==='bagStatus'){const d=await api('/api/baggage');toast(`Bag ${d.items[0]?.tag||''}: ${d.items[0]?.status||'unknown'}`)}
  if(a==='transportStatus'){const d=await api('/api/transport');toast(`${d.items[0]?.vehicle_no||'Transport'} · ETA ${d.items[0]?.eta??'—'} min`)}
  if(a==='addDemoBag'){await api('/api/baggage',{method:'POST',headers:csrfHeaders(),body:{tag:`DEMO-${Math.floor(1000+Math.random()*8999)}`,status:'TRANSFER',last_location:'Transfer belt 3'}});render()}
  if(a==='addDemoTransport'){await api('/api/transport',{method:'POST',headers:csrfHeaders(),body:{vehicle_no:'TN-01-AX-2048',route:'Airport Shuttle',pickup:'T2 Arrivals',destination:'T1',eta:8}});render()}
  if(a==='openMap'){window.open(`https://www.openstreetmap.org/?mlat=${state.data?.position?.lat||13.0827}&mlon=${state.data?.position?.lon||80.2707}#map=15/${state.data?.position?.lat||13.0827}/${state.data?.position?.lon||80.2707}`,'_blank')}
  if(a==='focusAircraft'){state.mapTarget='aircraft';render();toast('Map centered on live aircraft transponder')}
  if(a==='focusPassenger'){state.mapTarget='passenger';render();toast('Map centered on passenger location')}
  if(a==='recoveryOption')toast('Recovery options are provider-dependent; no automatic rebooking is performed without passenger confirmation.')
 }catch(e){toast(e.message||'Action failed')}
}
async function saveProfile(accessibility=state.profile?.accessibility||[]){
 const d=await api('/api/passenger/profile',{method:'POST',headers:csrfHeaders(),body:{phone:$('#phone')?.value||state.profile?.phone||'',pnr:$('#pnr')?.value||state.profile?.pnr||'',flight_id:$('#flightId')?.value||state.profile?.flight_id||'',accessibility,language:$('#language')?.value||$('#setLanguage')?.value||state.profile?.language||'English',simple_mode:$('#setSimple')?.value==='1'||state.profile?.simple_mode||false}});
 state.profile={...(state.profile||{}),accessibility};return d;
}
async function requestAssist(type){try{await api('/api/assistance',{method:'POST',headers:csrfHeaders(),body:{type,priority:type==='I AM LOST'?'HIGH':'NORMAL',location:state.data?.position?.name||'Current location'}});toast(`${type} assistance request submitted`)}catch(e){toast(e.message)}}
async function simulate(type,value){try{const d=await api('/api/simulation/event',{method:'POST',headers:csrfHeaders(),body:{event_type:type,value}});state.data=d.state;state.overview=await api('/api/platform/overview');addAlert('Simulation alert',`${type} event applied to the journey engine.`,type.includes('DELAY')?'amber':'red');}catch(e){toast(e.message)}}

function voice(){
 const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!SpeechRecognition)return toast('Voice input is not supported here. Try Chrome or Edge.');
 if(state.listening)return;
 const r=new SpeechRecognition();r.lang=(state.profile?.language||'English')==='Tamil'?'ta-IN':(state.profile?.language||'English')==='Hindi'?'hi-IN':'en-IN';r.interimResults=false;r.maxAlternatives=1;state.listening=true;$('#voiceBtn')?.classList.add('listening');toast('Listening…');
 r.onresult=e=>handleIntent(e.results[0][0].transcript);
 r.onerror=()=>{state.listening=false;$('#voiceBtn')?.classList.remove('listening');toast('Voice input was not understood')};
 r.onend=()=>{state.listening=false;$('#voiceBtn')?.classList.remove('listening')};r.start();
}
function handleIntent(q){
 q=q.toLowerCase();let answer='';
 if(q.includes('flight')||q.includes('status'))answer=`Your monitored flight is ${state.data?.outbound?.number||'not set'} and the connection risk is ${state.data?.engine?.level||'unknown'}.`;
 else if(q.includes('connection')||q.includes('make it'))answer=`You have ${state.data?.engine?.margin_minutes??'unknown'} minutes of connection margin.`;
 else if(q.includes('gate')||q.includes('way')){navigate('airport');answer='Opening your airport route.'}
 else if(q.includes('bag')){navigate('care');answer='Opening baggage tracking.'}
 else if(q.includes('bus')||q.includes('transport')){navigate('care');answer='Opening ground transport.'}
 else if(q.includes('wheelchair')||q.includes('help')){navigate('care');answer='Opening assistance options.'}
 else if(q.includes('emergency')||q.includes('danger')){action('emergency');answer='Starting the emergency workflow.'}
 else if(q.includes('lost')){action('lost');answer='Submitting a lost passenger assistance request.'}
 else answer='I can help with flight status, connection risk, gate navigation, baggage, transport, accessibility and emergency assistance.';
 toast(answer);if('speechSynthesis'in window){speechSynthesis.cancel();speechSynthesis.speak(new SpeechSynthesisUtterance(answer))}
}

if('serviceWorker' in navigator){navigator.serviceWorker.register('/sw.js').catch(()=>{});}
window.addEventListener('online',()=>toast('Connection restored'));
window.addEventListener('offline',()=>toast('Offline mode: cached app shell remains available.'));
render();
requestNotificationPermission();
load();
setInterval(pollAlerts,15000);
