from __future__ import annotations
import os, time, urllib.request, urllib.parse, json
from typing import Any
from .base import BaseProvider, ProviderStatus

AIRPORT_COORDS = {
    'DEL': {'name': 'Indira Gandhi International, Delhi', 'lat': 28.5562, 'lon': 77.1000, 'tz': 'Asia/Kolkata'},
    'MAA': {'name': 'Chennai International Airport', 'lat': 12.9941, 'lon': 80.1709, 'tz': 'Asia/Kolkata'},
    'BOM': {'name': 'Chhatrapati Shivaji Maharaj Airport, Mumbai', 'lat': 19.0896, 'lon': 72.8656, 'tz': 'Asia/Kolkata'},
    'BLR': {'name': 'Kempegowda International Airport, Bengaluru', 'lat': 13.1986, 'lon': 77.7066, 'tz': 'Asia/Kolkata'},
    'HYD': {'name': 'Rajiv Gandhi International, Hyderabad', 'lat': 17.2403, 'lon': 78.4294, 'tz': 'Asia/Kolkata'},
    'CCU': {'name': 'Netaji Subhash Chandra Bose, Kolkata', 'lat': 22.6547, 'lon': 88.4467, 'tz': 'Asia/Kolkata'},
    'COK': {'name': 'Cochin International Airport', 'lat': 10.1520, 'lon': 76.3920, 'tz': 'Asia/Kolkata'},
    'GOI': {'name': 'Dabolim Airport, Goa', 'lat': 15.3808, 'lon': 73.8314, 'tz': 'Asia/Kolkata'},
    'LHR': {'name': 'London Heathrow Airport', 'lat': 51.4700, 'lon': -0.4543, 'tz': 'Europe/London'},
    'DXB': {'name': 'Dubai International Airport', 'lat': 25.2532, 'lon': 55.3657, 'tz': 'Asia/Dubai'},
    'SIN': {'name': 'Singapore Changi Airport', 'lat': 1.3644, 'lon': 103.9915, 'tz': 'Asia/Singapore'},
    'JFK': {'name': 'John F. Kennedy International, New York', 'lat': 40.6413, 'lon': -73.7781, 'tz': 'America/New_York'}
}

WEATHER_CODE_MAP = {
    0: ("Clear sky", "☀️", "OPTIMAL"),
    1: ("Mainly clear", "🌤️", "OPTIMAL"),
    2: ("Partly cloudy", "⛅", "OPTIMAL"),
    3: ("Overcast", "☁️", "NORMAL"),
    45: ("Foggy", "🌫️", "WEATHER DELAY RISK"),
    48: ("Depositing rime fog", "🌫️", "WEATHER DELAY RISK"),
    51: ("Light drizzle", "🌦️", "NORMAL"),
    53: ("Moderate drizzle", "🌦️", "NORMAL"),
    55: ("Dense drizzle", "🌧️", "MINOR TURBULENCE"),
    61: ("Slight rain", "🌧️", "NORMAL"),
    63: ("Moderate rain", "🌧️", "MINOR TURBULENCE"),
    65: ("Heavy rain", "🌧️", "WEATHER DELAY RISK"),
    71: ("Slight snow", "🌨️", "MINOR TURBULENCE"),
    80: ("Rain showers", "🌦️", "NORMAL"),
    95: ("Thunderstorm", "⛈️", "WEATHER DELAY RISK"),
    96: ("Thunderstorm with hail", "⛈️", "SEVERE DELAY RISK")
}

class WeatherProvider(BaseProvider):
    def __init__(self):
        self.enabled = os.getenv("OPEN_METEO_ENABLED", "1") != "0"
        super().__init__("Open-Meteo", is_configured=self.enabled)
        self.cache: dict[str, tuple[float, dict]] = {}
        self.cache_ttl = 300  # 5 minutes

    def get_weather(self, airport_code: str = 'DEL') -> dict[str, Any]:
        """Fetch live or cached weather for any airport."""
        code = airport_code.upper().strip()
        loc = AIRPORT_COORDS.get(code, AIRPORT_COORDS['DEL'])

        now = time.time()
        if code in self.cache and (now - self.cache[code][0] < self.cache_ttl):
            return self.cache[code][1]

        if not self.enabled:
            return self._demo_weather(code, loc, "Provider disabled in configuration")

        try:
            params = {
                'latitude': loc['lat'],
                'longitude': loc['lon'],
                'current': 'temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m',
                'hourly': 'temperature_2m,precipitation_probability,weather_code',
                'forecast_hours': 24,
                'timezone': loc['tz']
            }
            url = 'https://api.open-meteo.com/v1/forecast?' + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, headers={'User-Agent': 'YatraFlow-Aviation/2.2'})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            cur = data.get('current', {})
            code_num = cur.get('weather_code', 0)
            cond_desc, cond_icon, flight_impact = WEATHER_CODE_MAP.get(code_num, ("Fair", "⛅", "OPTIMAL"))

            hourly = data.get('hourly', {})
            sparkline = []
            temps = hourly.get('temperature_2m', [])[:8]
            times = hourly.get('time', [])[:8]
            for t_str, temp in zip(times, temps):
                sparkline.append({
                    'time': t_str[11:16] if len(t_str) >= 16 else t_str,
                    'temp': temp
                })

            result = {
                "success": True,
                "provider": "Open-Meteo",
                "status": ProviderStatus.LIVE.value,
                "is_live": True,
                "airport": code,
                "airport_name": loc['name'],
                "temperature": cur.get('temperature_2m', 28.0),
                "feels_like": cur.get('apparent_temperature', 29.5),
                "humidity": cur.get('relative_humidity_2m', 60),
                "wind_speed": cur.get('wind_speed_10m', 12.0),
                "wind_direction": cur.get('wind_direction_10m', 180),
                "precipitation": cur.get('precipitation', 0.0),
                "condition": cond_desc,
                "condition_icon": cond_icon,
                "flight_impact": flight_impact,
                "impact_advisory": f"{flight_impact}: No adverse weather delays expected for takeoff or landing." if flight_impact == "OPTIMAL" else f"{flight_impact}: Crosswinds or precipitation may cause brief approach holds.",
                "hourly_sparkline": sparkline,
                "updated_at": int(now)
            }
            self.cache[code] = (now, result)
            return result

        except Exception as e:
            return self._demo_weather(code, loc, str(e))

    def _demo_weather(self, code: str, loc: dict, error_msg: str) -> dict[str, Any]:
        return {
            "success": True,
            "provider": "Open-Meteo (Demo Fallback)",
            "status": ProviderStatus.DEMO.value,
            "is_live": False,
            "airport": code,
            "airport_name": loc['name'],
            "temperature": 27.5,
            "feels_like": 28.8,
            "humidity": 55,
            "wind_speed": 11.4,
            "wind_direction": 160,
            "precipitation": 0.0,
            "condition": "Mainly clear",
            "condition_icon": "🌤️",
            "flight_impact": "OPTIMAL",
            "impact_advisory": "OPTIMAL: Standard terminal weather conditions.",
            "hourly_sparkline": [
                {"time": "08:00", "temp": 24},
                {"time": "11:00", "temp": 28},
                {"time": "14:00", "temp": 31},
                {"time": "17:00", "temp": 29},
                {"time": "20:00", "temp": 26}
            ],
            "updated_at": int(time.time()),
            "message": f"Demo weather active ({error_msg})"
        }
