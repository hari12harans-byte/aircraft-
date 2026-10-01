from __future__ import annotations
import os, time, urllib.request, urllib.parse, json, datetime
from typing import Any
from .base import BaseProvider, ProviderStatus

AIRPORT_BBOXES = {
    'DEL': {'lamin': 28.30, 'lomin': 76.80, 'lamax': 28.85, 'lomax': 77.45},
    'MAA': {'lamin': 12.75, 'lomin': 79.95, 'lamax': 13.25, 'lomax': 80.40},
    'BOM': {'lamin': 18.85, 'lomin': 72.60, 'lamax': 19.35, 'lomax': 73.15},
    'BLR': {'lamin': 12.95, 'lomin': 77.45, 'lamax': 13.45, 'lomax': 77.95},
    'HYD': {'lamin': 17.00, 'lomin': 78.15, 'lamax': 17.50, 'lomax': 78.65},
    'CCU': {'lamin': 22.40, 'lomin': 88.20, 'lamax': 22.90, 'lomax': 88.70},
    'COK': {'lamin': 9.90,  'lomin': 76.15, 'lamax': 10.40, 'lomax': 76.65},
    'GOI': {'lamin': 15.15, 'lomin': 73.60, 'lamax': 15.65, 'lomax': 74.10},
    'LHR': {'lamin': 51.25, 'lomin': -0.75, 'lamax': 51.70, 'lomax': -0.15},
    'DXB': {'lamin': 25.00, 'lomin': 55.10, 'lamax': 25.50, 'lomax': 55.60},
    'SIN': {'lamin': 1.15,  'lomin': 103.75,'lamax': 1.60,  'lomax': 104.25},
    'JFK': {'lamin': 40.40, 'lomin': -74.05,'lamax': 40.90, 'lomax': -73.50}
}

class RadarProvider(BaseProvider):
    def __init__(self):
        self.enabled = os.getenv("OPEN_SKY_ENABLED", "1") != "0"
        super().__init__("OpenSky Network", is_configured=self.enabled)
        self.cache: dict[str, tuple[float, dict]] = {}
        self.cache_ttl = 15  # 15 seconds

    def get_airspace(self, airport_code: str = 'DEL') -> dict[str, Any]:
        """Fetch real-time ADS-B transponder data from OpenSky Network."""
        code = airport_code.upper().strip()
        bbox = AIRPORT_BBOXES.get(code, AIRPORT_BBOXES['DEL'])

        now = time.time()
        if code in self.cache and (now - self.cache[code][0] < self.cache_ttl):
            return self.cache[code][1]

        if not self.enabled:
            return self._demo_radar(code, "OpenSky disabled in environment")

        try:
            q = urllib.parse.urlencode(bbox)
            url = f"https://opensky-network.org/api/states/all?{q}"
            req = urllib.request.Request(url, headers={'User-Agent': 'YatraFlow-ADS-B-Client/2.2'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            states = data.get('states') or []
            stamp = data.get('time')
            rows = []
            for s in states:
                if len(s) < 12 or s[5] is None or s[6] is None:
                    continue
                rows.append({
                    "icao24": s[0],
                    "callsign": (s[1] or '').strip(),
                    "origin_country": s[2],
                    "longitude": round(float(s[5]), 5),
                    "latitude": round(float(s[6]), 5),
                    "altitude_m": round(float(s[7])) if s[7] is not None else 0,
                    "on_ground": bool(s[8]),
                    "velocity_ms": round(float(s[9]), 1) if s[9] is not None else 0.0,
                    "speed_kmh": round(float(s[9]) * 3.6) if s[9] is not None else 0,
                    "heading": round(float(s[10]), 1) if s[10] is not None else 0.0,
                    "vertical_rate_ms": round(float(s[11]), 1) if s[11] is not None else 0.0,
                    "timestamp": datetime.datetime.fromtimestamp(stamp, datetime.timezone.utc).isoformat() if stamp else datetime.datetime.now(datetime.timezone.utc).isoformat()
                })

            if rows:
                result = {
                    "success": True,
                    "provider": "OpenSky Network",
                    "status": ProviderStatus.LIVE.value,
                    "is_live": True,
                    "airport": code,
                    "items": rows,
                    "total": len(rows),
                    "updated_at": int(now),
                    "message": f"Real ADS-B transponder telemetry acquired from {len(rows)} aircraft in {code} corridor."
                }
                self.cache[code] = (now, result)
                return result
            else:
                return self._demo_radar(code, "No transponder signals detected currently in local radar cell")

        except Exception as ex:
            return self._demo_radar(code, str(ex))

    def _demo_radar(self, code: str, reason: str) -> dict[str, Any]:
        """Provides realistic aircraft telemetry when OpenSky is offline or cell is quiet."""
        base_bbox = AIRPORT_BBOXES.get(code, AIRPORT_BBOXES['DEL'])
        mid_lat = (base_bbox['lamin'] + base_bbox['lamax']) / 2.0
        mid_lon = (base_bbox['lomin'] + base_bbox['lomax']) / 2.0

        demo_items = [
            {
                "icao24": "8005b1",
                "callsign": "IGO604",
                "origin_country": "India",
                "longitude": round(mid_lon - 0.06, 5),
                "latitude": round(mid_lat + 0.04, 5),
                "altitude_m": 2450,
                "on_ground": False,
                "velocity_ms": 115.0,
                "speed_kmh": 414,
                "heading": 135.0,
                "vertical_rate_ms": -4.2,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            },
            {
                "icao24": "8008c2",
                "callsign": "AIC201",
                "origin_country": "India",
                "longitude": round(mid_lon + 0.08, 5),
                "latitude": round(mid_lat - 0.05, 5),
                "altitude_m": 6800,
                "on_ground": False,
                "velocity_ms": 195.0,
                "speed_kmh": 702,
                "heading": 310.0,
                "vertical_rate_ms": 7.5,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            },
            {
                "icao24": "8004f3",
                "callsign": "VTI820",
                "origin_country": "India",
                "longitude": round(mid_lon + 0.02, 5),
                "latitude": round(mid_lat + 0.09, 5),
                "altitude_m": 4100,
                "on_ground": False,
                "velocity_ms": 150.0,
                "speed_kmh": 540,
                "heading": 225.0,
                "vertical_rate_ms": -3.0,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            },
            {
                "icao24": "896174",
                "callsign": "UAE511",
                "origin_country": "United Arab Emirates",
                "longitude": round(mid_lon - 0.12, 5),
                "latitude": round(mid_lat - 0.08, 5),
                "altitude_m": 9200,
                "on_ground": False,
                "velocity_ms": 220.0,
                "speed_kmh": 792,
                "heading": 285.0,
                "vertical_rate_ms": 1.2,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        ]

        return {
            "success": True,
            "provider": "OpenSky Network (Radar Standby / Demo)",
            "status": ProviderStatus.DEMO.value,
            "is_live": False,
            "airport": code,
            "items": demo_items,
            "total": len(demo_items),
            "updated_at": int(time.time()),
            "message": f"DEMO radar corridor active ({reason}). Live transponder signals will update when radar contact is made."
        }
