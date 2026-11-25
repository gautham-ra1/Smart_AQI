-- VayuMesh: Performance & Geospatial Indexes

CREATE INDEX IF NOT EXISTS idx_sensors_city_type ON sensors (city, sensor_type);
CREATE INDEX IF NOT EXISTS idx_sensors_status ON sensors (status);
CREATE INDEX IF NOT EXISTS idx_sensors_owner ON sensors (owner_id);

CREATE INDEX IF NOT EXISTS idx_raw_readings_sensor_time ON raw_readings (sensor_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_raw_readings_recorded_at ON raw_readings (recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_trust_logs_sensor_time ON trust_logs (sensor_id, evaluated_at DESC);
CREATE INDEX IF NOT EXISTS idx_trust_logs_reading_id ON trust_logs (reading_id);

CREATE INDEX IF NOT EXISTS idx_aqi_grids_city_mode_time ON aqi_grids (city, mode, computed_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs (created_at DESC);
