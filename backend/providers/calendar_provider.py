from __future__ import annotations
import urllib.parse, datetime
from typing import Any, Optional
from .base import BaseProvider, ProviderStatus

class CalendarProvider(BaseProvider):
    def __init__(self):
        super().__init__("Google Calendar & iCal Engine", is_configured=True)

    def generate_calendar_links(
        self,
        flight_number: str,
        airline: str,
        from_code: str,
        from_name: str,
        to_code: str,
        to_name: str,
        dep_time: str,
        arr_time: str,
        date_str: Optional[str] = None,
        terminal: str = "T3",
        gate: str = "B12",
        pnr: str = ""
    ) -> dict[str, Any]:
        """
        Generates Google Calendar direct URL and raw RFC 5545 iCalendar (.ics) string.
        """
        today = date_str or datetime.date.today().isoformat()
        
        # Parse departure time
        try:
            dep_h, dep_m = map(int, dep_time.split(':')[:2])
        except Exception:
            dep_h, dep_m = 10, 0

        try:
            arr_h, arr_m = map(int, arr_time.split(':')[:2])
        except Exception:
            arr_h, arr_m = dep_h + 2, dep_m

        date_parts = list(map(int, today.split('-')[:3]))
        dep_dt = datetime.datetime(date_parts[0], date_parts[1], date_parts[2], dep_h, dep_m)
        
        # If arrival crosses midnight
        if arr_h < dep_h or (arr_h == dep_h and arr_m < dep_m):
            arr_dt = dep_dt + datetime.timedelta(days=1, hours=arr_h-dep_h, minutes=arr_m-dep_m)
        else:
            arr_dt = datetime.datetime(date_parts[0], date_parts[1], date_parts[2], arr_h, arr_m)

        # Format ISO UTC timestamp for Google Calendar (YYYYMMDDTHHMMSSZ)
        # Assuming local Asia/Kolkata (UTC+5:30) for calculation
        utc_offset = datetime.timedelta(hours=5, minutes=30)
        dep_utc = dep_dt - utc_offset
        arr_utc = arr_dt - utc_offset

        dates_param = f"{dep_utc.strftime('%Y%m%dT%H%M%SZ')}/{arr_utc.strftime('%Y%m%dT%H%M%SZ')}"
        
        title = f"Flight {flight_number}: {from_code} → {to_code} ({airline})"
        location = f"{from_name} ({from_code}) Terminal {terminal}, Gate {gate}"
        details = (
            f"Flight: {flight_number} ({airline})\n"
            f"PNR / Booking: {pnr or 'Confirmed'}\n"
            f"Route: {from_name} ({from_code}) → {to_name} ({to_code})\n"
            f"Terminal: {terminal} | Gate: {gate}\n"
            f"Departure: {dep_time} | Arrival: {arr_time}\n\n"
            f"Monitored live by YatraFlow Airport Connection Companion.\n"
            f"Open YatraFlow for gate navigation & connection alerts."
        )

        # Google Calendar Direct URL
        params = {
            "action": "TEMPLATE",
            "text": title,
            "dates": dates_param,
            "details": details,
            "location": location
        }
        google_url = "https://calendar.google.com/calendar/render?" + urllib.parse.urlencode(params)

        # RFC 5545 iCalendar ICS Content
        now_stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        uid = f"yatraflow-{flight_number.replace(' ','')}-{today.replace('-','')}@yatraflow.ai"
        
        ics_content = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "PRODID:-//YatraFlow//Airport Companion 2.2//EN\r\n"
            "CALSCALE:GREGORIAN\r\n"
            "METHOD:PUBLISH\r\n"
            "BEGIN:VEVENT\r\n"
            f"UID:{uid}\r\n"
            f"DTSTAMP:{now_stamp}\r\n"
            f"DTSTART:{dep_utc.strftime('%Y%m%dT%H%M%SZ')}\r\n"
            f"DTEND:{arr_utc.strftime('%Y%m%dT%H%M%SZ')}\r\n"
            f"SUMMARY:{title}\r\n"
            f"DESCRIPTION:{details.replace(chr(10), '\\n')}\r\n"
            f"LOCATION:{location}\r\n"
            "STATUS:CONFIRMED\r\n"
            "BEGIN:VALARM\r\n"
            "TRIGGER:-PT60M\r\n"
            "ACTION:DISPLAY\r\n"
            "DESCRIPTION:YatraFlow Boarding Reminder: Gate closes in 40 mins\r\n"
            "END:VALARM\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )

        return {
            "google_calendar_url": google_url,
            "ics_content": ics_content,
            "event_title": title,
            "dates_formatted": f"{dep_time} - {arr_time} ({today})",
            "location": location
        }
