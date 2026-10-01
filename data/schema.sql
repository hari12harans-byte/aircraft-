-- ==============================================================================
-- YatraFlow Supabase / PostgreSQL Production Database Schema
-- Version 2.2.0
-- Compatible with Supabase Database, Auth, Realtime and Row Level Security (RLS)
-- ==============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Users Table
CREATE TABLE IF NOT EXISTS public.users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    salt VARCHAR(255) NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    google_id VARCHAR(255) DEFAULT NULL,
    google_email VARCHAR(255) DEFAULT NULL,
    google_avatar TEXT DEFAULT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT DEFAULT NULL
);

-- 2. Sessions Table
CREATE TABLE IF NOT EXISTS public.sessions (
    token_hash VARCHAR(64) PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    csrf VARCHAR(64) NOT NULL,
    created_at BIGINT NOT NULL,
    expires_at BIGINT NOT NULL
);

-- 3. Passenger Profiles Table
CREATE TABLE IF NOT EXISTS public.passenger_profiles (
    user_id BIGINT PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    phone VARCHAR(32) DEFAULT '',
    pnr VARCHAR(32) DEFAULT '',
    flight_id VARCHAR(64) DEFAULT '',
    country VARCHAR(4) DEFAULT 'IN',
    timezone VARCHAR(64) DEFAULT 'Asia/Kolkata',
    language VARCHAR(16) DEFAULT 'en',
    simple_mode BOOLEAN DEFAULT FALSE,
    accessibility JSONB DEFAULT '[]'::jsonb,
    onboarded BOOLEAN DEFAULT FALSE,
    whatsapp_enabled BOOLEAN DEFAULT FALSE,
    whatsapp_verified BOOLEAN DEFAULT FALSE,
    whatsapp_number VARCHAR(32) DEFAULT '',
    email_notifications_enabled BOOLEAN DEFAULT TRUE,
    google_connected BOOLEAN DEFAULT FALSE,
    last_lat DOUBLE PRECISION DEFAULT 0.0,
    last_lon DOUBLE PRECISION DEFAULT 0.0,
    last_accuracy DOUBLE PRECISION DEFAULT 0.0,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL
);

-- 4. Connection Sessions Table
CREATE TABLE IF NOT EXISTS public.connection_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    inbound_id VARCHAR(64) NOT NULL,
    outbound_id VARCHAR(64) NOT NULL,
    zone VARCHAR(32) NOT NULL,
    bags INTEGER NOT NULL DEFAULT 1,
    immigration BOOLEAN NOT NULL DEFAULT FALSE,
    scenario JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at BIGINT NOT NULL
);

-- 5. Saved Trips Table
CREATE TABLE IF NOT EXISTS public.trips (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    inbound_id VARCHAR(64) NOT NULL,
    outbound_id VARCHAR(64) NOT NULL,
    trip_date VARCHAR(32) NOT NULL,
    status VARCHAR(32) DEFAULT 'CONFIRMED',
    calendar_event_id VARCHAR(255) DEFAULT '',
    created_at BIGINT NOT NULL,
    updated_at BIGINT DEFAULT NULL
);

-- 6. Baggage Tracking Table
CREATE TABLE IF NOT EXISTS public.bags (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    tag VARCHAR(64) NOT NULL,
    status VARCHAR(64) NOT NULL,
    last_location VARCHAR(255) NOT NULL,
    updated_at BIGINT NOT NULL
);

-- 7. Ground Transport Table
CREATE TABLE IF NOT EXISTS public.transport (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    vehicle_no VARCHAR(64) NOT NULL,
    route VARCHAR(255) NOT NULL,
    pickup VARCHAR(255) NOT NULL,
    destination VARCHAR(255) NOT NULL,
    lat DOUBLE PRECISION DEFAULT 0.0,
    lon DOUBLE PRECISION DEFAULT 0.0,
    eta INTEGER DEFAULT 0,
    status VARCHAR(64) DEFAULT 'AVAILABLE',
    updated_at BIGINT NOT NULL
);

-- 8. Assistance Requests Table
CREATE TABLE IF NOT EXISTS public.assistance_requests (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    type VARCHAR(64) NOT NULL,
    priority VARCHAR(32) NOT NULL DEFAULT 'NORMAL',
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    location VARCHAR(255) NOT NULL,
    notes TEXT DEFAULT '',
    created_at BIGINT NOT NULL
);

-- 9. Emergency Events Table
CREATE TABLE IF NOT EXISTS public.emergency_events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    location VARCHAR(255) NOT NULL,
    created_at BIGINT NOT NULL
);

-- 10. Notifications Table
CREATE TABLE IF NOT EXISTS public.notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    type VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    read BOOLEAN DEFAULT FALSE,
    created_at BIGINT NOT NULL
);

-- 11. User Notification Preferences Table
CREATE TABLE IF NOT EXISTS public.notification_preferences (
    user_id BIGINT PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    email_enabled BOOLEAN DEFAULT TRUE,
    whatsapp_enabled BOOLEAN DEFAULT FALSE,
    push_enabled BOOLEAN DEFAULT TRUE,
    flight_change BOOLEAN DEFAULT TRUE,
    gate_change BOOLEAN DEFAULT TRUE,
    connection_risk BOOLEAN DEFAULT TRUE,
    boarding_reminder BOOLEAN DEFAULT TRUE,
    transport_update BOOLEAN DEFAULT TRUE,
    weather_alert BOOLEAN DEFAULT TRUE,
    assistance_update BOOLEAN DEFAULT TRUE,
    travel_summary BOOLEAN DEFAULT FALSE,
    updated_at BIGINT NOT NULL
);

-- 12. Notification Logs (Audit & Idempotency Store)
CREATE TABLE IF NOT EXISTS public.notification_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    event_id VARCHAR(64) NOT NULL,
    channel VARCHAR(32) NOT NULL,
    notification_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    provider_message_id VARCHAR(255) DEFAULT '',
    created_at BIGINT NOT NULL,
    sent_at BIGINT DEFAULT 0,
    error_message TEXT DEFAULT ''
);

-- 13. Verification & Password Reset Tokens
CREATE TABLE IF NOT EXISTS public.verification_tokens (
    token_hash VARCHAR(64) PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    token_type VARCHAR(32) NOT NULL, -- 'EMAIL_VERIFY', 'PASSWORD_RESET'
    created_at BIGINT NOT NULL,
    expires_at BIGINT NOT NULL,
    used BOOLEAN DEFAULT FALSE
);

-- 14. WhatsApp OTP Verifications
CREATE TABLE IF NOT EXISTS public.whatsapp_otps (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    phone VARCHAR(32) NOT NULL,
    otp_hash VARCHAR(64) NOT NULL,
    attempts INTEGER DEFAULT 0,
    verified BOOLEAN DEFAULT FALSE,
    created_at BIGINT NOT NULL,
    expires_at BIGINT NOT NULL
);

-- Indexes for High Performance
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON public.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_connection_user_id ON public.connection_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_logs_user ON public.notification_logs(user_id, event_id);
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON public.notifications(user_id, read);
CREATE INDEX IF NOT EXISTS idx_tokens_lookup ON public.verification_tokens(token_hash, expires_at);
CREATE INDEX IF NOT EXISTS idx_trips_user ON public.trips(user_id);

-- Enable Row Level Security (RLS)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.passenger_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.connection_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bags ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transport ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assistance_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.emergency_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_logs ENABLE ROW LEVEL SECURITY;
