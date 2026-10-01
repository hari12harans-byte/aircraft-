# YatraFlow — Integrated Airport Connection Copilot

This build is based on the uploaded AI Airport Connection Guardian project and has been reworked into **YatraFlow**.

## Major changes
- Removed glassmorphism and ambient/glass UI effects.
- Replaced the interface with a professional aviation operations design.
- Added a single integrated passenger journey instead of disconnected feature cards.
- Added passenger identity/journey profile.
- Added baggage tracking and baggage recovery model.
- Added ground transport input/tracking model.
- Added accessibility / CARE engine.
- Added assistance requests.
- Added emergency workflow with India 112.
- Added airport contacts/accessibility APIs.
- Added notification store.
- Added simulation event engine.
- Added operations dashboard and analytics.
- Added PWA/offline shell.
- Added voice copilot.
- Added optional Supabase configuration.
- Kept real aviation integration provider-based.
- Clearly labels LIVE / DEMO / DIGITAL TWIN sources.

## Run
### Windows
Double-click `run.bat`, or:

```powershell
python -m uvicorn backend.main:app --reload
```

Open:
`http://127.0.0.1:8000`

Demo account:
- Email: demo@yatraflow.ai
- Password: YatraFlow@123

## Live providers
Set `AVIATIONSTACK_API_KEY` for authorized live flight status.

The existing Open-Meteo and OpenSky integrations remain provider-based.

## Supabase
The project is Supabase-ready through:
- SUPABASE_URL
- SUPABASE_ANON_KEY
- SUPABASE_SERVICE_ROLE_KEY

The current local build uses SQLite for its local demo/auth store so it can run immediately. Supabase should be used as the production database/realtime layer after credentials and schema/RLS are configured.

## Important limitations
- The supplied CSV/demo flights are schedule/reference data, not live telemetry.
- GPS is not precise indoor gate positioning.
- Real baggage tracking requires an airline/airport baggage provider.
- Real transport dispatch requires a transport provider or airport feed.
- Automatic rebooking requires airline/OTA authorization and must always require passenger confirmation.

## Main APIs
- /api/health
- /api/state
- /api/platform/overview
- /api/passenger/profile
- /api/flights
- /api/flights/search
- /api/connection/setup
- /api/position
- /api/scenario
- /api/baggage
- /api/transport
- /api/assistance
- /api/emergency
- /api/notifications
- /api/simulation/event
- /api/analytics
- /api/airport/contacts
- /api/airport/accessibility
- /api/system/status
- /api/docs

## Antigravity
Open this repository in Antigravity and first run the project. Then ask the agent to audit the code before making further changes.

## Major UI update
- Animated aircraft hero with moving clouds.
- Black/dark aviation sky hero while the rest of the product remains professional light.
- Mobile hamburger navigation with three-line menu.
- Real OpenStreetMap embed with device-location support.
- Browser notification permission + in-app alert center.
- Polling detects connection-risk changes and surfaces alerts.
- Existing backend notification records are surfaced in the UI.

### Real map note
The current real-map layer uses OpenStreetMap's embeddable map. For airport gate-level indoor navigation, connect an airport-approved indoor mapping/positioning provider. Do not represent the public map as precise indoor positioning.

### Notification note
Browser notifications require user permission and HTTPS in production. In-app notifications work without browser permission.
