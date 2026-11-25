-- VayuMesh: Seed Data Note
-- Official stations (Chikkamagaluru Kalyana Nagara KSPCB), demo users, and
-- virtual IoT sensor fleets are seeded via scripts/seed_official_stations.py
-- so API keys are cryptographically hashed with API_KEY_PEPPER from .env.
SELECT 'Use scripts/seed_official_stations.py to seed users and HMAC-hashed sensors.' AS info;
