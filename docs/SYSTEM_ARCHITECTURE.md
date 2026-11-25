# VayuMesh — Backend Technical Design & Architecture (Chikkamagaluru Pilot)

Aligned with `Backend_Document_Template.docx` and `Hyperlocal AQI Sensor Fusion Plan.pdf`.

## 1. System Overview
| Item | Details |
| :--- | :--- |
| **Backend Responsibility** | Authenticates users and IoT devices, enforces per-key rate limits and physical sanity checks, stores immutable raw telemetry in PostgreSQL, applies Western Ghats hygrometric pre-calibration, runs Two-Tier Adaptive EWMA trust scoring, computes 50×50 Trust-Weighted IDW and Trust-Aware Ordinary Kriging grids, serves CPCB/MoHFW health advisories, and broadcasts live updates via Socket.io. |
| **Primary Actors / Roles** | `Public` (unauthenticated map/advisory viewer), `citizen` (personal health cohort & map), `sensor_owner` (registers sensors, views one-time HMAC API keys, tracks readings), `admin` (manages official stations, injects synthetic faults, replays historical grids, inspects trust & audit logs). |
| **Main Entities** | `users`, `sensors`, `raw_readings` (immutable), `trust_logs`, `aqi_grids`, `advisories`, `audit_logs`. |

## 2. Key Architecture Decisions
| ID | Decision | Reason | Trade-off |
| :--- | :--- | :--- | :--- |
| **AD-01** | FastAPI + NumPy/SciPy modular monolith | In-process vectorized TW-IDW (~3 ms) and Trust-Aware Kriging (~6–21 ms) with Pydantic v2 validation. | CPU-bound Kriging shares the API process (mitigated by grid caching). |
| **AD-02** | PostgreSQL append-only `raw_readings` trigger | `trg_immutable_raw_readings` blocks `UPDATE`/`DELETE` at the DB engine level for auditable replay. | Derived trust/grid states live in separate tables (`trust_logs`, `aqi_grids`). |
| **AD-03** | Redis sliding-window rate limiter + local fallback | Enforces 12 req/min per hashed API key (`HTTP 429`) in production and degrades cleanly to in-memory sliding window locally. | In-memory fallback is single-process only. |
| **AD-04** | HTML5 Canvas `ImageOverlay` over `Leaflet.heat` | Renders calibrated CPCB PM2.5 contours + Kriging uncertainty opacity rather than misleading point density. | Custom canvas renderer instead of plugin default. |

## 3. Core Business Rules
- **BR-01 (Immutability)**: `raw_readings` cannot be updated or deleted (`prevent_raw_mutation()` trigger).
- **BR-02 (Hashed API Keys)**: Only `HMAC-SHA256(API_KEY_PEPPER, raw_key)` (64-char hex) is stored; raw key is returned once.
- **BR-03 (Rate Limiting & Sanity)**: 12 req/min/key (`429`); `pm25 ∈ [0, 1000]`, `rh_pct ∈ [0, 100]`, India GPS (`lat 6.5–37.5, lon 68.0–97.5`) (`422`).
- **BR-04 (Monsoon RH Pre-Calibration)**: Above `75% RH`, raw PM2.5 is damped via `raw / (1 + 0.008 * (RH - 75)^1.5)` before trust evaluation while raw readings remain untouched.
- **BR-05 (Two-Tier Adaptive Trust)**: Official CAAQMS = `1.0`. Citizen/mobile/institutional nodes ∈ `[0.05, 0.90]` via EWMA (`α = 0.25`): Tier 1 Reference-Anchored (`≤ 5 km` from Kalyana Nagara) or Tier 2 Peer-Consensus MAD (`> 5 km`, `≥ 3` peers within 4 km, e.g. Aldur corridor). `< 0.20` → `quarantined`.
- **BR-06 (Kriging Fallback)**: Automatically falls back to TW-IDW if active sensors `< 5`.
- **BR-07 (CPCB & MoHFW Grounding)**: Exact India CPCB NAQI PM2.5 breakpoints + MoHFW/NCDC cohort rules.
