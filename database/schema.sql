-- VayuMesh: Normalized Relational Schema (Chikkamagaluru-first, pan-India ready)

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'citizen'
        CHECK (role IN ('citizen', 'sensor_owner', 'admin')),
    health_profile TEXT NOT NULL DEFAULT 'general'
        CHECK (health_profile IN ('general', 'asthma', 'children', 'elderly', 'pregnant', 'outdoor_worker')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sensors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    city TEXT NOT NULL DEFAULT 'chikkamagaluru',
    api_key_hash CHAR(64) UNIQUE NOT NULL, -- HMAC-SHA256(API_KEY_PEPPER, raw_key)
    sensor_type TEXT NOT NULL
        CHECK (sensor_type IN ('official', 'citizen_fixed', 'institutional_node', 'mobile_fleet')),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'degraded', 'quarantined', 'revoked')),
    model_meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    trust_weight DOUBLE PRECISION NOT NULL DEFAULT 0.75
        CHECK (trust_weight >= 0.05 AND trust_weight <= 1.0),
    lat DOUBLE PRECISION NOT NULL CHECK (lat >= 6.5 AND lat <= 37.5),
    lon DOUBLE PRECISION NOT NULL CHECK (lon >= 68.0 AND lon <= 97.5),
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Strictly append-only immutable raw sensor readings (protected by trigger)
CREATE TABLE IF NOT EXISTS raw_readings (
    id BIGSERIAL PRIMARY KEY,
    sensor_id UUID NOT NULL REFERENCES sensors(id) ON DELETE RESTRICT,
    pm25_raw DOUBLE PRECISION NOT NULL CHECK (pm25_raw >= 0 AND pm25_raw <= 1000),
    pm10_raw DOUBLE PRECISION CHECK (pm10_raw IS NULL OR (pm10_raw >= 0 AND pm10_raw <= 2000)),
    rh_pct DOUBLE PRECISION NOT NULL DEFAULT 55.0 CHECK (rh_pct >= 0 AND rh_pct <= 100),
    temp_c DOUBLE PRECISION CHECK (temp_c IS NULL OR (temp_c >= -20 AND temp_c <= 65)),
    lat DOUBLE PRECISION NOT NULL CHECK (lat >= 6.5 AND lat <= 37.5),
    lon DOUBLE PRECISION NOT NULL CHECK (lon >= 68.0 AND lon <= 97.5),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Derived trust evaluation log (replayable from raw_readings)
CREATE TABLE IF NOT EXISTS trust_logs (
    id BIGSERIAL PRIMARY KEY,
    sensor_id UUID NOT NULL REFERENCES sensors(id) ON DELETE CASCADE,
    reading_id BIGINT NOT NULL REFERENCES raw_readings(id) ON DELETE RESTRICT,
    pm25_corrected DOUBLE PRECISION NOT NULL,
    prev_trust DOUBLE PRECISION NOT NULL,
    new_trust DOUBLE PRECISION NOT NULL,
    agreement_score DOUBLE PRECISION NOT NULL,
    tier_used TEXT NOT NULL
        CHECK (tier_used IN ('official', 'reference_anchored', 'peer_mad', 'isolated_prior')),
    reference_pm25 DOUBLE PRECISION,
    dist_ref_km DOUBLE PRECISION,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Derived interpolated AQI grids (replayable for any historical timestamp T)
CREATE TABLE IF NOT EXISTS aqi_grids (
    id BIGSERIAL PRIMARY KEY,
    city TEXT NOT NULL DEFAULT 'chikkamagaluru',
    mode TEXT NOT NULL CHECK (mode IN ('idw', 'kriging')),
    requested_mode TEXT NOT NULL CHECK (requested_mode IN ('idw', 'kriging')),
    grid_size INTEGER NOT NULL DEFAULT 50,
    bounds JSONB NOT NULL,
    grid_pm25 JSONB NOT NULL,
    grid_std_dev JSONB,
    active_sensor_count INTEGER NOT NULL DEFAULT 0,
    compute_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    source_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Advisory audit / alert history
CREATE TABLE IF NOT EXISTS advisories (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    city TEXT NOT NULL DEFAULT 'chikkamagaluru',
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    pm25_equiv DOUBLE PRECISION NOT NULL,
    aqi_pm25_equiv INTEGER NOT NULL,
    cpcb_band TEXT NOT NULL,
    health_profile TEXT NOT NULL,
    advisory_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Admin & security audit logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_email TEXT,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
