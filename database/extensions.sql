-- VayuMesh: PostgreSQL Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- PostGIS is enabled automatically in PostGIS containers (docker-compose.yml).
-- On vanilla PostgreSQL without PostGIS installed, the DO block skips cleanly.
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS postgis;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'PostGIS extension not available locally; falling back to lat/lon double precision columns.';
END $$;
