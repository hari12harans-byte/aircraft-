# YatraFlow — Modular n8n Automation Workflows

This directory contains production-ready, modular n8n workflow definitions for YatraFlow's external email, WhatsApp, and Google integrations.

## Architecture

```text
YatraFlow FastAPI Backend
        │ (Signed Webhook: HMAC SHA-256)
        ▼
   n8n Webhook Router
        │
        ├── 01 - Email Verification
        ├── 02 - Password Reset
        ├── 03 - Welcome Email
        ├── 04 - Trip Confirmation
        ├── 05 - Flight Change Notification
        ├── 06 - Gate Change Notification
        ├── 07 - Connection Risk Alert (WhatsApp + Email)
        ├── 08 - Boarding Reminder (Scheduled / Timezone Aware)
        ├── 09 - Transport Update
        ├── 10 - Weather Alert
        ├── 11 - Assistance Update
        ├── 12 - WhatsApp OTP Verification
        ├── 13 - WhatsApp Cloud API Router (Meta Graph API)
        └── 14 - Daily / Pre-Travel Summary
```

## Security & Idempotency

1. **HMAC-SHA256 Signature Verification**:
   - YatraFlow signs every outbound automation webhook with `X-YatraFlow-Signature: sha256=...` using `N8N_WEBHOOK_SECRET`.
   - Workflows verify this signature before processing payloads.
2. **Idempotency**:
   - Every event includes a unique `event_id`. Workflows check against previous deliveries to guarantee zero duplicate emails or WhatsApp messages.
3. **No Passwords or Service Secrets**:
   - Payloads strictly exclude passwords, Supabase service-role keys, and raw OAuth tokens.

## How to Import into n8n

1. Open your n8n instance (e.g. `http://localhost:5678` or your hosted n8n Cloud).
2. Go to **Workflows** -> **Import from File...**
3. Select any `.json` file from this directory.
4. Set up your SMTP / SendGrid credentials for Email, Meta Cloud API for WhatsApp, and Google OAuth credentials.
5. In YatraFlow's `.env`, configure:
   ```env
   N8N_WEBHOOK_URL=http://your-n8n-host:5678/webhook/yatraflow-events
   N8N_WEBHOOK_SECRET=yatraflow-n8n-secure-secret-2026
   ```
