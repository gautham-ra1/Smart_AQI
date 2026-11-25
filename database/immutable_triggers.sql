-- VayuMesh: Constraint 3 — Immutable Append-Only raw_readings Trigger
-- Any UPDATE or DELETE attempt on raw_readings raises a PostgreSQL exception.

CREATE OR REPLACE FUNCTION prevent_raw_mutation() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'raw_readings is append-only and immutable (attempted % on id=%)', TG_OP, OLD.id
        USING ERRCODE = 'check_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_immutable_raw_readings ON raw_readings;

CREATE TRIGGER trg_immutable_raw_readings
BEFORE UPDATE OR DELETE ON raw_readings
FOR EACH ROW EXECUTE FUNCTION prevent_raw_mutation();
