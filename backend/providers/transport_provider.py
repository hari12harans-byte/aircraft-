from __future__ import annotations
import time, math
from typing import Any, Optional
from .base import BaseProvider, ProviderStatus

class TransportProvider(BaseProvider):
    def __init__(self):
        super().__init__("YatraFlow Transit & Feeder Engine", is_configured=False)

    OPTIONS = {
        "DEL": [
            {
                "id": "metro-del",
                "type": "METRO",
                "title": "Delhi Airport Express Metro (Orange Line)",
                "description": "Direct high-speed rail to New Delhi Railway Station in 19 minutes.",
                "station": "IGI Airport Metro Station (Direct underground link from T2 & T3)",
                "fare_inr": "₹60",
                "frequency": "Every 10-12 mins",
                "hours": "04:45 AM - 11:30 PM",
                "speed": "80 km/h",
                "eta_city": 19,
                "badge": "FASTEST"
            },
            {
                "id": "shuttle-del",
                "type": "SHUTTLE",
                "title": "DIAL Inter-Terminal Shuttle",
                "description": "Complimentary airside/landside transfer between T1, T2 and T3.",
                "station": "T3 Pillar 10 / T2 Arrivals / T1 Shuttles",
                "fare_inr": "Free (Show Flight Ticket)",
                "frequency": "Every 15-20 mins",
                "hours": "24/7 Operations",
                "speed": "35 km/h",
                "eta_city": 15,
                "badge": "FREE TRANSFER"
            },
            {
                "id": "cabs-del",
                "type": "CABS",
                "title": "Uber & Ola App Pickup Zone",
                "description": "Multi-Level Car Parking (MLCP) designated pickup lanes.",
                "station": "T3 Multi-Level Car Park Level 2 (Pillar 12-16) / T2 Parking P3",
                "fare_inr": "₹450 - ₹750 (to City Center)",
                "frequency": "Instant Dispatch (2-4 min wait)",
                "hours": "24/7 Operations",
                "speed": "Traffic dependent",
                "eta_city": 45,
                "badge": "DOOR-TO-DOOR"
            },
            {
                "id": "taxi-prepaid",
                "type": "PREPAID_TAXI",
                "title": "Delhi Traffic Police Official Prepaid Taxi",
                "description": "Government authorized booth inside arrivals terminal hall.",
                "station": "Inside T3 & T2 Arrivals Exit Gates",
                "fare_inr": "Fixed Official Tariff (Slip required)",
                "frequency": "Immediate queue",
                "hours": "24/7 Operations",
                "speed": "Standard cab",
                "eta_city": 45,
                "badge": "GOVT AUTHORIZED"
            }
        ],
        "MAA": [
            {
                "id": "metro-maa",
                "type": "METRO",
                "title": "Chennai Metro Blue Line",
                "description": "Direct connection to Chennai Central & Mount Road.",
                "station": "Airport Metro Station (Direct skywalk from T1 & T2)",
                "fare_inr": "₹40 - ₹50",
                "frequency": "Every 7-10 mins",
                "hours": "05:00 AM - 11:00 PM",
                "speed": "65 km/h",
                "eta_city": 32,
                "badge": "RECOMMENDED"
            },
            {
                "id": "shuttle-maa",
                "type": "SHUTTLE",
                "title": "AAI Electric Buggy Shuttle",
                "description": "Complimentary golf-cart buggy transfer between Domestic T1 & International T2.",
                "station": "Arrival concourse walk-through",
                "fare_inr": "Free",
                "frequency": "On Demand / Every 5 mins",
                "hours": "24/7 Operations",
                "speed": "15 km/h",
                "eta_city": 5,
                "badge": "FREE"
            }
        ],
        "BLR": [
            {
                "id": "bus-blr",
                "type": "BUS",
                "title": "BMTC Vayu Vajra Airport Express (Volvo AC)",
                "description": "Dedicated luxury Volvo buses connecting Kempegowda Airport to all parts of Bengaluru.",
                "station": "Airport Bus Bay 1 - 8 (Outside Terminal 1 & 2)",
                "fare_inr": "₹220 - ₹280",
                "frequency": "Every 15-30 mins",
                "hours": "24/7 Operations",
                "speed": "50 km/h",
                "eta_city": 60,
                "badge": "POPULAR"
            },
            {
                "id": "shuttle-blr",
                "type": "SHUTTLE",
                "title": "Kempegowda T1 <-> T2 Electric Shuttle Bus",
                "description": "Zero-emission electric buses running continuously between Terminals 1 and 2.",
                "station": "T1 Bay 4 / T2 Ground Transport Hall",
                "fare_inr": "Free for All Passengers",
                "frequency": "Every 7 mins",
                "hours": "24/7 Operations",
                "speed": "30 km/h",
                "eta_city": 10,
                "badge": "FREE"
            }
        ]
    }

    # Airport Express Bus Lines with real-world routes & simulated live tracking
    BUS_ROUTES = [
        {
            "route_id": "DTC-EXP4",
            "name": "DTC Airport Express 4",
            "city": "Delhi",
            "airport": "DEL",
            "origin": "ISBT Kashmere Gate",
            "destination": "IGI Airport Terminal 3",
            "fare_inr": 100,
            "vehicle_no": "DL-1PD-4082",
            "next_departure": "10 mins",
            "status": "EN_ROUTE",
            "stops": [
                {"name": "ISBT Kashmere Gate", "eta_min": 0, "lat": 28.6675, "lon": 77.2285, "passed": True},
                {"name": "New Delhi Railway Station (Ajmeri Gate)", "eta_min": 12, "lat": 28.6429, "lon": 77.2205, "passed": True},
                {"name": "Connaught Place (Palika Kendra)", "eta_min": 20, "lat": 28.6297, "lon": 77.2185, "passed": True},
                {"name": "Dhaula Kuan Interchange", "eta_min": 35, "lat": 28.5921, "lon": 77.1615, "passed": False, "is_current": True},
                {"name": "Aerocity Hospitality District", "eta_min": 45, "lat": 28.5492, "lon": 77.1215, "passed": False},
                {"name": "IGI Terminal 2 Arrivals", "eta_min": 52, "lat": 28.5560, "lon": 77.0980, "passed": False},
                {"name": "IGI Terminal 3 Ground Hub", "eta_min": 58, "lat": 28.5562, "lon": 77.1000, "passed": False}
            ]
        },
        {
            "route_id": "DTC-780",
            "name": "DTC Route 780 Express",
            "city": "Delhi",
            "airport": "DEL",
            "origin": "New Delhi Railway Station",
            "destination": "IGI Airport T2 / T3",
            "fare_inr": 50,
            "vehicle_no": "DL-1PD-2915",
            "next_departure": "4 mins",
            "status": "APPROACHING",
            "stops": [
                {"name": "New Delhi Station", "eta_min": 0, "lat": 28.6429, "lon": 77.2205, "passed": True},
                {"name": "Karol Bagh Metro", "eta_min": 10, "lat": 28.6450, "lon": 77.1900, "passed": True},
                {"name": "Dhaula Kuan", "eta_min": 25, "lat": 28.5921, "lon": 77.1615, "passed": True},
                {"name": "Mahipalpur Bypass", "eta_min": 38, "lat": 28.5430, "lon": 77.1320, "passed": False, "is_current": True},
                {"name": "IGI Airport T3 Arrivals", "eta_min": 46, "lat": 28.5562, "lon": 77.1000, "passed": False}
            ]
        },
        {
            "route_id": "BMTC-KIA9",
            "name": "BMTC Vayu Vajra KIA-9",
            "city": "Bengaluru",
            "airport": "BLR",
            "origin": "Majestic (Kempegowda Bus Station)",
            "destination": "Kempegowda International Airport T1 & T2",
            "fare_inr": 250,
            "vehicle_no": "KA-57-F-1204",
            "next_departure": "12 mins",
            "status": "EN_ROUTE",
            "stops": [
                {"name": "Majestic Bus Station", "eta_min": 0, "lat": 12.9772, "lon": 77.5713, "passed": True},
                {"name": "Mekhri Circle", "eta_min": 15, "lat": 13.0084, "lon": 77.5833, "passed": True},
                {"name": "Hebbal Flyover", "eta_min": 26, "lat": 13.0358, "lon": 77.5970, "passed": False, "is_current": True},
                {"name": "Yelahanka Bypass", "eta_min": 40, "lat": 13.1007, "lon": 77.5963, "passed": False},
                {"name": "Kempegowda Airport T1", "eta_min": 60, "lat": 13.1986, "lon": 77.7066, "passed": False},
                {"name": "Kempegowda Airport T2", "eta_min": 68, "lat": 13.2045, "lon": 77.7120, "passed": False}
            ]
        },
        {
            "route_id": "MTC-AIR1",
            "name": "MTC Airport Express Feeder",
            "city": "Chennai",
            "airport": "MAA",
            "origin": "Chennai Central Railway Station",
            "destination": "Chennai Airport T1 & T4",
            "fare_inr": 80,
            "vehicle_no": "TN-01-N-9842",
            "next_departure": "8 mins",
            "status": "EN_ROUTE",
            "stops": [
                {"name": "Chennai Central", "eta_min": 0, "lat": 13.0827, "lon": 80.2757, "passed": True},
                {"name": "LIC / Mount Road", "eta_min": 12, "lat": 13.0645, "lon": 80.2640, "passed": True},
                {"name": "Guindy Kathipara Junction", "eta_min": 28, "lat": 13.0067, "lon": 80.2030, "passed": False, "is_current": True},
                {"name": "Chennai Airport T1", "eta_min": 42, "lat": 12.9941, "lon": 80.1709, "passed": False}
            ]
        }
    ]

    def get_transport_options(self, airport: str = 'DEL') -> dict[str, Any]:
        """Get multi-modal ground transport options for an airport."""
        code = airport.upper().strip()
        opts = self.OPTIONS.get(code, self.OPTIONS['DEL'])
        return {
            "success": True,
            "provider": self.name,
            "status": ProviderStatus.DEMO.value,
            "is_live": False,
            "airport": code,
            "items": opts,
            "count": len(opts),
            "updated_at": int(time.time()),
            "message": "Ground transport schedules and official tariff matrix loaded."
        }

    def get_bus_routes(self, airport: str = 'DEL') -> dict[str, Any]:
        """Get live bus routes with simulated dynamic GPS telemetry along routes."""
        code = airport.upper().strip()
        routes = [r for r in self.BUS_ROUTES if r.get("airport") == code or not code]
        if not routes:
            routes = self.BUS_ROUTES

        # Calculate dynamic bus GPS location based on current time
        now = time.time()
        enriched_routes = []
        for r in routes:
            r_copy = dict(r)
            stops = r_copy["stops"]
            # Find current stop index
            curr_idx = next((i for i, s in enumerate(stops) if s.get("is_current")), 1)
            # Add dynamic simulated position
            curr_stop = stops[curr_idx]
            next_stop = stops[min(len(stops)-1, curr_idx+1)]
            
            # Smooth interpolation
            cycle = (now % 60) / 60.0
            live_lat = curr_stop["lat"] + (next_stop["lat"] - curr_stop["lat"]) * cycle
            live_lon = curr_stop["lon"] + (next_stop["lon"] - curr_stop["lon"]) * cycle
            
            r_copy["current_gps"] = {
                "lat": round(live_lat, 5),
                "lon": round(live_lon, 5),
                "heading": 210.0,
                "speed_kmh": 38,
                "current_stop_name": curr_stop["name"],
                "next_stop_name": next_stop["name"]
            }
            enriched_routes.append(r_copy)

        return {
            "success": True,
            "provider": "Airport Transit Feeder (Demo Simulation)",
            "status": ProviderStatus.DEMO.value,
            "is_live": False,
            "airport": code,
            "routes": enriched_routes,
            "count": len(enriched_routes),
            "updated_at": int(now),
            "message": "Airport Express Bus tracking operating in simulation mode. Live GTFS-RT feed can be connected when authorized by transit authority."
        }
