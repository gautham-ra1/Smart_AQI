"""Cross-platform Cloud PostGIS Schema & Trigger Installer (Neon / Supabase / Render / Local).

Runs pure asyncpg SQL so teammates on Windows or Mac can initialize a fresh
cloud PostGIS database in one command without needing the psql CLI.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402

POSTGIS_UPGRADE_SQL = """
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS postgis;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sensors' AND column_name = 'location'
    ) THEN
        ALTER TABLE sensors ADD COLUMN location GEOGRAPHY(Point, 4326);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'raw_readings' AND column_name = 'location'
    ) THEN
        ALTER TABLE raw_readings ADD COLUMN location GEOGRAPHY(Point, 4326);
    END IF;

    UPDATE sensors
    SET location = ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography
    WHERE location IS NULL;

    UPDATE raw_readings
    SET location = ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography
    WHERE location IS NULL;

    CREATE INDEX IF NOT EXISTS idx_sensors_location_gist ON sensors USING GIST (location);
    CREATE INDEX IF NOT EXISTS idx_raw_readings_location_gist ON raw_readings USING GIST (location);
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'PostGIS not installed on this server (%): using lat/lon columns.', SQLERRM;
END $$;
"""

POSTGIS_SYNC_TRIGGER_SQL = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') THEN
        CREATE OR REPLACE FUNCTION sync_geography_point() RETURNS TRIGGER AS $fn$
        BEGIN
            NEW.location := ST_SetSRID(ST_MakePoint(NEW.lon, NEW.lat), 4326)::geography;
            RETURN NEW;
        END;
        $fn$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_sensors_sync_geo ON sensors;
        CREATE TRIGGER trg_sensors_sync_geo
        BEFORE INSERT OR UPDATE OF lat, lon ON sensors
        FOR EACH ROW EXECUTE FUNCTION sync_geography_point();

        DROP TRIGGER IF EXISTS trg_raw_readings_sync_geo ON raw_readings;
        CREATE TRIGGER trg_raw_readings_sync_geo
        BEFORE INSERT ON raw_readings
        FOR EACH ROW EXECUTE FUNCTION sync_geography_point();
    END IF;
END $$;
"""


async def init_cloud_db() -> None:
    db_dir = ROOT / "database"
    sql_files = ["extensions.sql", "schema.sql", "indexes.sql", "immutable_triggers.sql"]

    async with engine.begin() as conn:
        raw_conn = await conn.get_raw_connection()
        asyncpg_conn = raw_conn.driver_connection

        for fname in sql_files:
            content = (db_dir / fname).read_text(encoding="utf-8")
            await asyncpg_conn.execute(content)
            print(f"[OK] Applied database/{fname}")

        await asyncpg_conn.execute(POSTGIS_UPGRADE_SQL)
        await asyncpg_conn.execute(POSTGIS_SYNC_TRIGGER_SQL)

        ext_res = await conn.execute(
            text("SELECT extname, extversion FROM pg_extension WHERE extname IN ('postgis', 'pgcrypto')")
        )
        exts = ext_res.fetchall()
        print(f"[OK] Active extensions: {exts}")

    await engine.dispose()
    print("[DONE] Cloud database schema, PostGIS geography columns, and immutable trigger initialized.")


if __name__ == "__main__":
    asyncio.run(init_cloud_db())
