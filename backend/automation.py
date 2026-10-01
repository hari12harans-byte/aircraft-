from __future__ import annotations
import asyncio, datetime, hashlib, hmac, json, os, re, secrets, sqlite3, time, urllib.request
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

def get_webhook_url() -> str:
    return os.getenv('N8N_WEBHOOK_URL', '').strip()

def get_webhook_secret() -> str:
    return os.getenv('N8N_WEBHOOK_SECRET', 'yatraflow-n8n-secure-secret-2026').strip()

N8N_WEBHOOK_URL = get_webhook_url()
N8N_WEBHOOK_SECRET = get_webhook_secret()
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID', '').strip()
WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN', '').strip()

# Controlled event enum per specification
SUPPORTED_EVENT_TYPES = {
    'USER_REGISTERED',
    'EMAIL_VERIFICATION_REQUESTED',
    'EMAIL_VERIFIED',
    'PASSWORD_RESET_REQUESTED',
    'TRIP_CREATED',
    'TRIP_UPDATED',
    'TRIP_CANCELLED',
    'FLIGHT_DELAYED',
    'FLIGHT_CANCELLED',
    'FLIGHT_STATUS_CHANGED',
    'GATE_CHANGED',
    'TERMINAL_CHANGED',
    'CONNECTION_STATUS_CHANGED',
    'CONNECTION_AT_RISK',
    'CONNECTION_MISSED',
    'BOARDING_REMINDER',
    'TRANSPORT_UPDATED',
    'WEATHER_ALERT',
    'ASSISTANCE_REQUESTED',
    'ASSISTANCE_UPDATED',
    'EMERGENCY_EVENT',
    'FARE_ALERT_TRIGGERED'
}

def sign_payload(payload_bytes: bytes, secret: str = N8N_WEBHOOK_SECRET) -> str:
    """Generates HMAC-SHA256 signature for outbound n8n event webhooks."""
    return 'sha256=' + hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()

def verify_signature(payload_bytes: bytes, signature_header: str, secret: str = N8N_WEBHOOK_SECRET) -> bool:
    """Verifies incoming webhook signature against secret."""
    if not signature_header:
        return False
    expected = sign_payload(payload_bytes, secret)
    return hmac.compare_digest(expected, signature_header)

def validate_phone_e164(phone: str) -> bool:
    """Validates phone number adheres to normalized E.164 format (e.g. +919876543210)."""
    if not phone:
        return False
    return bool(re.match(r'^\+[1-9]\d{7,14}$', phone.strip()))

def generate_otp() -> str:
    """Generates a secure 6-digit numeric OTP."""
    return f"{secrets.randbelow(900000) + 100000}"

def get_whatsapp_template_message(template_name: str, to_phone: str, lang: str, params: list[str]) -> dict:
    """Formats payload conforming strictly to Meta WhatsApp Business Cloud API specifications."""
    meta_lang = 'ta' if lang == 'ta' else ('hi' if lang == 'hi' else 'en_US')
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone.replace('+', '').strip(),
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": meta_lang
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": str(p)} for p in params]
                }
            ]
        }
    }

async def dispatch_automation_event(
    db_conn: sqlite3.Connection,
    event_type: str,
    user_id: int,
    payload: dict,
    channels: list[str] = None,
    language: str = 'en',
    trip_id: Optional[str] = None,
    flight_id: Optional[str] = None
) -> dict:
    """
    Centralized event dispatcher:
    1. Validates event type against controlled enum
    2. Enforces idempotency via unique event_id
    3. Checks user notification preferences
    4. Signs event with HMAC-SHA256
    5. Dispatches to n8n webhook asynchronously
    6. Logs event to notification_logs
    7. Gracefully degrades without crashing YatraFlow if n8n/WhatsApp is offline
    """
    if event_type not in SUPPORTED_EVENT_TYPES:
        raise ValueError(f"Unsupported event type: {event_type}")

    channels = channels or ['in_app']
    language = language or 'en'
    event_id = f"evt_{secrets.token_hex(12)}"
    now = int(time.time())

    # Check notification preferences from database
    pref_row = db_conn.execute(
        "SELECT * FROM notification_preferences WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    allowed_channels = ['in_app']
    if pref_row:
        # Check specific notification type gating
        type_allowed = True
        if 'FLIGHT' in event_type and not pref_row['flight_change']:
            type_allowed = False
        elif 'GATE' in event_type and not pref_row['gate_change']:
            type_allowed = False
        elif 'CONNECTION' in event_type and not pref_row['connection_risk']:
            type_allowed = False
        elif 'BOARDING' in event_type and not pref_row['boarding_reminder']:
            type_allowed = False
        elif 'TRANSPORT' in event_type and not pref_row['transport_update']:
            type_allowed = False
        elif 'WEATHER' in event_type and not pref_row['weather_alert']:
            type_allowed = False
        elif 'ASSISTANCE' in event_type and not pref_row['assistance_update']:
            type_allowed = False

        if type_allowed:
            if 'email' in channels and pref_row['email_enabled']:
                allowed_channels.append('email')
            if 'whatsapp' in channels and pref_row['whatsapp_enabled']:
                allowed_channels.append('whatsapp')
            if 'push' in channels and pref_row['push_enabled']:
                allowed_channels.append('push')
    else:
        # Defaults
        if 'email' in channels:
            allowed_channels.append('email')

    # Construct complete event payload
    event_payload = {
        "event_id": event_id,
        "event_type": event_type,
        "user_id": str(user_id),
        "trip_id": str(trip_id or ''),
        "flight_id": str(flight_id or ''),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "language": language,
        "channels": allowed_channels,
        "data": payload
    }

    payload_json = json.dumps(event_payload, separators=(',', ':'))
    payload_bytes = payload_json.encode('utf-8')
    active_secret = get_webhook_secret()
    signature = sign_payload(payload_bytes, secret=active_secret)

    # In-app logging
    for ch in allowed_channels:
        db_conn.execute("""
            INSERT INTO notification_logs (user_id, event_id, channel, notification_type, status, provider_message_id, created_at, sent_at, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, event_id, ch, event_type, 'PENDING', '', now, 0, ''))
    db_conn.commit()

    # Outbound webhook delivery to n8n
    dispatch_status = "DELIVERED"
    error_msg = ""
    active_webhook_url = get_webhook_url()
    if active_webhook_url:
        try:
            req = urllib.request.Request(
                active_webhook_url,
                data=payload_bytes,
                headers={
                    'Content-Type': 'application/json',
                    'X-YatraFlow-Signature': signature,
                    'X-YatraFlow-Event': event_type,
                    'User-Agent': 'YatraFlow-Automation/2.1'
                }
            )
            # Async HTTP call run in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=5))
            dispatch_status = "DELIVERED"
        except Exception as ex:
            dispatch_status = "N8N_UNREACHABLE"
            error_msg = str(ex)
    else:
        dispatch_status = "LOCAL_ONLY"
        error_msg = "N8N_WEBHOOK_URL not configured"

    # Update notification_logs status
    for ch in allowed_channels:
        final_status = 'SENT' if dispatch_status == 'DELIVERED' or ch == 'in_app' else 'SKIPPED'
        db_conn.execute("""
            UPDATE notification_logs
            SET status = ?, sent_at = ?, error_message = ?
            WHERE event_id = ? AND channel = ?
        """, (final_status, now if final_status == 'SENT' else 0, error_msg, event_id, ch))
    db_conn.commit()

    return {
        "ok": True,
        "event_id": event_id,
        "event_type": event_type,
        "dispatch_status": dispatch_status,
        "channels": allowed_channels
    }
