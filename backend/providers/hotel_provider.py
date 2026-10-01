from __future__ import annotations
import time
from typing import Any, Optional
from .base import BaseProvider, ProviderStatus

class HotelProvider(BaseProvider):
    def __init__(self):
        super().__init__("YatraFlow Transit Stays", is_configured=False)

    HOTELS_DATA = [
        {
            "id": "h-hie-t3",
            "name": "Holiday Inn Express New Delhi Airport T3",
            "airport": "DEL",
            "type": "Airside Transit Hotel",
            "location": "Terminal 3, Level 5, International / Domestic Departures",
            "is_airside": True,
            "requires_visa": False,
            "distance_terminal": "0 mins (Inside Security)",
            "hourly_rates": [
                {"hours": 3, "price_inr": 3200, "label": "3-Hour Shower & Nap"},
                {"hours": 6, "price_inr": 5400, "label": "6-Hour Layover Rest"},
                {"hours": 12, "price_inr": 8200, "label": "12-Hour Long Layover"},
                {"hours": 24, "price_inr": 11500, "label": "Overnight Stay"}
            ],
            "rating": 4.6,
            "reviews_count": 1840,
            "amenities": ["Rain Shower", "Free High-Speed Wi-Fi", "Work Desk", "Luggage Storage", "Complimentary Tea/Coffee", "Flight Info Display"],
            "contact": "+91-11-45252000",
            "image": "hotel_hie"
        },
        {
            "id": "h-plaza-t3",
            "name": "Plaza Premium Transit Hotel & Nap Pods",
            "airport": "DEL",
            "type": "Airside Sleeping Pods & Suites",
            "location": "Terminal 3, International Departures, Near Gate 15",
            "is_airside": True,
            "requires_visa": False,
            "distance_terminal": "0 mins (Inside Terminal)",
            "hourly_rates": [
                {"hours": 3, "price_inr": 2800, "label": "3-Hour Soundproof Pod"},
                {"hours": 6, "price_inr": 4600, "label": "6-Hour Private Studio"},
                {"hours": 12, "price_inr": 7200, "label": "12-Hour Suite Stay"}
            ],
            "rating": 4.4,
            "reviews_count": 920,
            "amenities": ["Soundproof Pod", "USB Quick Charge", "Private Shower", "Hot Buffet Access", "Eye Mask & Toiletries"],
            "contact": "+91-11-49638700",
            "image": "hotel_plaza"
        },
        {
            "id": "h-radisson-aero",
            "name": "Radisson Blu Plaza Delhi Airport",
            "airport": "DEL",
            "type": "Airport Luxury Hotel",
            "location": "NH-8, Mahipalpur (Near Aerocity Metro Station)",
            "is_airside": False,
            "requires_visa": True,
            "distance_terminal": "5 mins via Free Airport Shuttle",
            "hourly_rates": [
                {"hours": 6, "price_inr": 4800, "label": "Day-Use Deluxe Room"},
                {"hours": 24, "price_inr": 9200, "label": "Full Night Stay + Breakfast"}
            ],
            "rating": 4.7,
            "reviews_count": 3120,
            "amenities": ["Free Airport Shuttle 24/7", "Outdoor Pool", "Spa & Wellness", "24/7 Buffet Dining", "Soundproof Glazing"],
            "contact": "+91-11-26779191",
            "image": "hotel_radisson"
        },
        {
            "id": "h-ibis-aero",
            "name": "Ibis New Delhi Aerocity",
            "airport": "DEL",
            "type": "Smart Airport Transit Stay",
            "location": "Asset 9, Hospitality District, Aerocity",
            "is_airside": False,
            "requires_visa": True,
            "distance_terminal": "7 mins via Airport Express Metro",
            "hourly_rates": [
                {"hours": 6, "price_inr": 3500, "label": "6-Hour Layover Room"},
                {"hours": 24, "price_inr": 5800, "label": "Overnight Stay"}
            ],
            "rating": 4.3,
            "reviews_count": 2450,
            "amenities": ["Direct Metro Connectivity", "Free Wi-Fi", "Early Bird Breakfast from 4 AM", "Express Checkout"],
            "contact": "+91-11-43020202",
            "image": "hotel_ibis"
        },
        {
            "id": "h-snooze-maa",
            "name": "Snooze Hub & Transit Lounge Chennai",
            "airport": "MAA",
            "type": "Terminal Rest Pods",
            "location": "Chennai Airport T1 Domestic Concourse, Level 2",
            "is_airside": True,
            "requires_visa": False,
            "distance_terminal": "0 mins (Inside T1 Security)",
            "hourly_rates": [
                {"hours": 3, "price_inr": 1800, "label": "3-Hour Snooze Cube"},
                {"hours": 6, "price_inr": 3200, "label": "6-Hour Rest Pod"}
            ],
            "rating": 4.5,
            "reviews_count": 640,
            "amenities": ["Ergonomic Recliner/Bed", "Noise Cancellation", "Flight Wake-up Call", "Charging Station"],
            "contact": "+91-44-22560551",
            "image": "hotel_snooze"
        }
    ]

    def list_hotels(self, airport: str = 'DEL', airside_only: bool = False) -> dict[str, Any]:
        """List available transit and airport hotels with filters."""
        code = airport.upper().strip()
        matched = [h for h in self.HOTELS_DATA if h.get("airport") == code or not code]
        if not matched:
            matched = self.HOTELS_DATA

        if airside_only:
            matched = [h for h in matched if h.get("is_airside")]

        return {
            "success": True,
            "provider": self.name,
            "status": ProviderStatus.DEMO.value,
            "is_live": False,
            "airport": code,
            "items": matched,
            "count": len(matched),
            "updated_at": int(time.time()),
            "message": "Transit hotel and sleeping pod directory loaded. Commercial booking provider can be integrated via provider abstraction."
        }
