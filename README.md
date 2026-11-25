# VayuMesh — Hyperlocal AQI Heatmap with Adaptive Sensor Fusion (Chikkamagaluru Pilot)

Team Paradox (`AV26-97347C3AFB`) — Adaptive Three-Tier Sensor Fusion Engine built with **FastAPI + NumPy/SciPy**, **PostgreSQL**, **Redis**, **Socket.io**, and **React + Leaflet HTML5 Canvas**.

## What Is Implemented
- **Database (`database/`)**: Normalized PostgreSQL schema with `trg_immutable_raw_readings` (`BEFORE UPDATE OR DELETE` trigger enforcing append-only raw telemetry).
- **Core Engines (`backend/app/engines/`)**:
  - Hygrometric pre-calibration (`humidity_correction.py`) for Western Ghats monsoon fog (`RH > 75%`).
  - Two-Tier Adaptive Trust Engine (`trust_engine.py`): Tier 1 Reference-Anchored (`≤ 5 km`), Tier 2 Peer-Consensus MAD (`> 5 km`), EWMA (`α = 0.25`, `[0.05, 0.90]`).
  - Vectorized Trust-Weighted IDW (`idw_engine.py`) & Trust-Aware Ordinary Kriging (`kriging_engine.py`) with heteroscedastic measurement variance and `< 5` sensor fallback.
  - India CPCB NAQI PM2.5 Sub-Index (`aqi_engine.py`) & MoHFW/NCDC cohort advisories (`advisory_engine.py`).
- **Virtual IoT Device Simulators (`scripts/`)**: Real HTTP clients authenticating via `X-API-Key` for institutional anchors, mobile transit nodes (KSRTC bus & auto-rickshaw), 90% RH monsoon fog node, outer taluk peer cluster, and fault/burst/malformed test modes.
- **Live Map UI (`frontend/`)**: React + Leaflet HTML5 Canvas CPCB contour overlay, Kriging uncertainty opacity toggle, live Socket.io updates, Recharts EWMA trust trajectory, MoHFW advisory panel, and Admin Fault Injection / Recompute controls.

See [docs/DEMO_WORKFLOW.md](docs/DEMO_WORKFLOW.md) for quick-start commands and [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) for architecture details.
