# VayuMesh — 7:00 PM Technical Interview Live Demo Playbook

## Quick Start (3 Terminals)

### Terminal 1 — Start FastAPI + Socket.io Backend
```bash
cd /Users/gauthamrajykotian/Smart_AQI/backend
.venv/bin/uvicorn app.main:socket_app --reload --port 8000
```
- Swagger API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### Terminal 2 — Start React + Leaflet Canvas Frontend
```bash
cd /Users/gauthamrajykotian/Smart_AQI/frontend
npm run dev
```
- Live Chikkamagaluru Map UI: `http://localhost:5173`

### Terminal 3 — Run Virtual IoT Devices & Live Proofs
```bash
cd /Users/gauthamrajykotian/Smart_AQI

# 1. Stream all 13 Chikkamagaluru Virtual IoT Devices (official + institutional + mobile + monsoon fog + outer peer cluster)
backend/.venv/bin/python scripts/generate_synthetic_sensors.py --url http://localhost:8000 --interval 6

# 2. Prove persistent fault decay (0.75 -> 0.05 in 10 ticks) from a rogue virtual device
backend/.venv/bin/python scripts/simulate_faulty_sensor.py --mode drift --ticks 10 --bias 150

# 3. Prove Redis/sliding-window HTTP 429 rate limiting (>12 req/min)
backend/.venv/bin/python scripts/simulate_faulty_sensor.py --mode burst

# 4. Prove structured HTTP 422 physical sanity checks (PM2.5=2500, London GPS, RH=140%)
backend/.venv/bin/python scripts/simulate_faulty_sensor.py --mode malformed

# 5. Run full 12-test automated verification suite (including PostgreSQL immutability trigger!)
cd backend && PYTHONPATH=. .venv/bin/pytest tests/ -v
```

## Demo Credentials
- **Admin**: `admin@vayumesh.in` / `Admin@123`
- **Sensor Owner**: `owner@vayumesh.in` / `Owner@123`
- **Citizen (Asthma Cohort)**: `citizen@vayumesh.in` / `Citizen@123`

## 5-Minute Interview Walkthrough Order
1. **Live Map (`localhost:5173`)**: Point out the **HTML5 Canvas** CPCB contour overlay (not `Leaflet.heat`), the **Kalyana Nagara KSPCB official anchor** (blue), the **Mullayanagiri 90% RH Fog Node** (raw 45 → corrected ~30.7 µg/m³, trust preserved > 0.80), and the **Aldur Road outer cluster** running `peer_mad` (>5 km from official station).
2. **Toggle Fast TW-IDW vs. Precision Kriging (+ Uncertainty Opacity)**: Highlight `< 10 ms` compute time on 2,500 cells.
3. **Click "Admin Demo Login" → "Inject Fault (+150 µg/m³)"**: Watch the EWMA Trust Trajectory chart drop smoothly `0.75 → 0.05` (`quarantined`) while the Kriging heatmap suppresses the false hotspot.
4. **Click "Recompute from Logs"**: Explain `trg_immutable_raw_readings` in PostgreSQL guaranteeing raw data is never mutated.
5. **Switch Cohort (`Asthma` vs `Outdoor Worker` vs `General`)**: Show India CPCB NAQI + MoHFW/NCDC N95 guidance and medical disclaimer.
