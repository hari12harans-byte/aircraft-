from __future__ import annotations
import time, random, datetime, math
from typing import Any, Optional
from .base import BaseProvider, ProviderStatus

class FareAlertProvider(BaseProvider):
    def __init__(self):
        super().__init__("YatraFlow Fare Watch Engine", is_configured=True)

    def get_route_price_trends(self, from_code: str, to_code: str) -> dict[str, Any]:
        """Returns 14-day price history and forecasted trend for route."""
        from_c = from_code.upper().strip()
        to_c = to_code.upper().strip()

        # Seed realistic base fare
        base_fares = {
            ("DEL", "BOM"): 4950,
            ("BOM", "DEL"): 5100,
            ("MAA", "DEL"): 4850,
            ("DEL", "MAA"): 4750,
            ("BLR", "DEL"): 4600,
            ("DEL", "BLR"): 4720,
            ("DEL", "DXB"): 21500,
            ("DEL", "LHR"): 38400,
            ("DEL", "SIN"): 26800,
            ("DEL", "JFK"): 62000
        }
        base = base_fares.get((from_c, to_c), 5200)

        # Generate realistic trend points
        today = datetime.date.today()
        trend_points = []
        for i in range(14, 0, -1):
            d = today - datetime.timedelta(days=i)
            # Fluctuation pattern
            fluctuation = int(base * 0.08 * math_sin(i * 0.6)) + (random.randint(-150, 150))
            trend_points.append({
                "date": d.strftime("%d %b"),
                "price": max(1999, base + fluctuation)
            })

        current_price = trend_points[-1]["price"]
        lowest_30d = min(p["price"] for p in trend_points) - 200
        average_fare = sum(p["price"] for p in trend_points) // len(trend_points)
        
        # Advice
        if current_price <= average_fare:
            advice = "Good time to book: Fares are currently lower than the 14-day average."
            trend = "FALLING"
        else:
            advice = "Fares are slightly elevated. Set a fare alert to track upcoming drops."
            trend = "RISING"

        return {
            "success": True,
            "provider": self.name,
            "status": ProviderStatus.DEMO.value,
            "route": f"{from_c} → {to_c}",
            "current_fare_inr": current_price,
            "lowest_30d_inr": lowest_30d,
            "average_fare_inr": average_fare,
            "trend": trend,
            "advice": advice,
            "history": trend_points,
            "updated_at": int(time.time())
        }

def math_sin(x: float) -> float:
    import math
    return math.sin(x)
