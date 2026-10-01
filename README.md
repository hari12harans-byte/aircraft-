# YatraFlow — Intelligent Airport Connection Companion & Travel Super-App

**YatraFlow** is a comprehensive, mobile-first aviation and travel super-app built with **FastAPI**, **Vanilla HTML/CSS/JS**, and **Leaflet / OpenStreetMap**, featuring real-time flight telemetry, indoor terminal navigation, multi-modal ground transport, and an omnichannel event/notification architecture (In-app, Email, WhatsApp).

---

## 🌟 27 Core Modules

| # | Module | Implementation & Provider | Status State |
|---|---|---|---|
| 1 | **Flights** | Comprehensive schedule database & Aviationstack provider abstraction | `LIVE` / `DEMO` |
| 2 | **Flight Search** | Multi-corridor search with origin, destination, date, cabin, and sorting | `LIVE` / `DEMO` |
| 3 | **Flight Status** | Live tracker with multi-stage journey timeline & historical OTP | `LIVE` / `DEMO` |
| 4 | **Live Aircraft Tracking** | Real-time ADS-B transponder telemetry via **OpenSky Network** | `LIVE` / `DEMO` |
| 5 | **My Trips** | Active, upcoming, and past journey management with DB persistence | `LIVE` |
| 6 | **Connection Intelligence** | Connection Guardian engine: MCT analysis, baggage risk, crowd model | `LIVE` |
| 7 | **Airport Live Map** | Interactive **Leaflet** + **OpenStreetMap** with custom airport layer | `LIVE` |
| 8 | **Current Location** | High-precision HTML5 Geolocation API with accuracy indicator | `LIVE` / `DEMO` |
| 9 | **Gate Navigation** | Turn-by-turn indoor routing using Dijkstra graph algorithms | `LIVE` |
| 10 | **Terminal Navigation** | Inter-terminal transfer guides (T1, T2, T3) with shuttle & metro timings | `LIVE` |
| 11 | **Hotels** | Transit hotel & hourly sleeping pod directory with direct booking inquiry | `DEMO` (Commercial-ready) |
| 12 | **Ground Transport** | Multi-modal hub (Metro Express, Inter-Terminal Shuttle, Uber/Ola, Prepaid) | `LIVE` / `DEMO` |
| 13 | **Bus Tracking** | Live airport express feeder bus lines (Delhi DTC, Bengaluru BMTC, Chennai MTC) with GPS route stops | `DEMO` (Telemetry Simulation) |
| 14 | **Weather** | Real-time atmospheric conditions, humidity, wind & flight impact via **Open-Meteo** | `LIVE` / `DEMO` |
| 15 | **Notifications** | In-app notification center with read/unread tracking and real-time updates | `LIVE` |
| 16 | **Email** | Responsive, tri-lingual HTML email templates (English, Tamil, Hindi) | `LIVE` / `DEMO` |
| 17 | **WhatsApp** | Meta WhatsApp Business Cloud API payload generator with OTP verification | `LIVE` / `DEMO` |
| 18 | **Google Account** | Google OAuth 2.0 authentication integration with instant 1-click test mode | `LIVE` / `DEMO` |
| 19 | **Google Calendar** | 1-click Google Calendar direct web URL + RFC 5545 `.ics` file generator | `LIVE` |
| 20 | **Voice Assistant** | Multilingual Web Speech API voice companion with voice synthesis | `LIVE` |
| 21 | **English / Tamil / Hindi** | Complete tri-lingual interface and notification template engine | `LIVE` |
| 22 | **Emergency Assistance** | One-tap National 112 emergency hotline confirmation & airport security CISF contacts | `LIVE` |
| 23 | **Travel Timeline** | Interactive stage-by-stage progression (Boarding, Airborne, Landed, Baggage) | `LIVE` |
| 24 | **Saved Trips** | LocalStorage + SQLite/Supabase synchronization for offline resilience | `LIVE` |
| 25 | **Fare Alerts Architecture** | 14-day price trend analysis, drop predictor, and custom target price alerts | `LIVE` / `DEMO` |
| 26 | **PWA Installation** | Progressive Web App manifest, offline service worker cache shell | `LIVE` |
| 27 | **Android / Capacitor Readiness** | Fully configured `capacitor.config.json` with hardware back-button handling | `LIVE` |

---

## 🚀 Free & Open Data Providers

YatraFlow prioritizes free, open, and legally accessible data sources:
- **OpenSky Network**: Live ADS-B transponder telemetry of active aircraft in airport corridors.
- **Open-Meteo**: Free weather forecasts, wind speeds, and precipitation tracking without API keys.
- **OpenStreetMap & Leaflet**: Free tile map layer with interactive pins and zoom controls.
- **Supabase**: PostgreSQL database, Auth, and Realtime sync (`data/schema.sql` provided).
- **FastAPI**: High-performance asynchronous Python backend.
- **n8n**: Webhook event automation workflows for multi-channel messaging (`n8n/` directory).
- **Google OAuth**: Open identity standard for secure authentication.

---

## 🛡️ Strict Provider Status Engine

Every module explicitly reports its operating state:
- **`LIVE`**: Active external API feed successfully acquired (e.g. OpenSky transponder signals, Open-Meteo weather).
- **`DEMO`**: High-fidelity reference data / simulator operating (e.g. simulated transit bus GPS, schedule database).
- **`UNAVAILABLE`**: Network failure or upstream provider outage gracefully handled.

*YatraFlow never presents demo data as live data.*

---

## 💻 Quick Start

### 1. Requirements
- Python 3.10+
- Modern Web Browser (Chrome, Edge, Firefox, Safari)

### 2. Run the Server
#### On Windows:
Double-click `run.bat` or execute in PowerShell:
```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

#### On Linux / macOS:
```bash
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 3. Open Application
Navigate to `http://127.0.0.1:8000`

**Demo Account Credentials:**
- **Email:** `demo@yatraflow.ai`
- **Password:** `YatraFlow@123`
*(Or click "Use demo account" on the sign-in screen)*

---

## 🧪 Automated Test Suite
To verify all module suites:
```powershell
python test_suite.py
```

---

## 📱 Mobile & PWA Installation
- **PWA**: Click the "Install YatraFlow" badge or use browser prompt to add to Home Screen.
- **Capacitor (Android)**: Run `npx cap sync android` to build native APK.
