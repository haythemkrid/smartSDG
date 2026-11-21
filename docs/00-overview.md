# 00 — Overview

## Goal
A modular, reproducible engine for SDG monitoring in Tunisia where a new domain module is deployed
without touching the core.

## Modules
| Module | SDG | Role in MVP | Status |
|---|---|---|---|
| HydroWatch | 6 (13) | Pilot 1: water surface at Sidi Salem (quarterly) + area hindcast for 2026 | FULL |
| UrbanPulse | 11 | Pilot 2: urban sprawl and heat islands | SKELETON (contract-compliant, minimal/synthetic output) |
| SoilGuard | 15 | Live-demo template: soil salinisation and oases | SKELETON, kept undeployed until the demo |

## MVP (must work on demo day)
1. SDK (`BaseSDGModule`, Pydantic schemas) + module loader + manifest validation
2. STAC client (Planetary Computer) with saved, hashed queries
3. HydroWatch end to end on the Sidi Salem AOI
4. FastAPI exposing deployed modules dynamically
5. Streamlit map that discovers modules from the API
6. `make deploy-module MODULE=soilguard` live: SoilGuard appears with no core change
7. `make up` brings the stack up with Docker Compose

## Non-goals (do NOT build)
- All 24 governorates processed (AOIs come from configs/tunisia_aois.geojson only)
- Automatic satellite-pass triggers, alerting, auth, multi-tenancy
- Real UrbanPulse/SoilGuard science (skeletons only, unless the human promotes them)
- Improving the HydroWatch pipeline: the spike is migrated AS-IS to demonstrate the platform. Its defects are documented (docs/11-spike-review.md), not fixed
- Custom deep-learning infrastructure (threshold or simple classifier is enough)

## Success criteria
- Same params → same outputs (hash-identical metrics)
- Deploying SoilGuard changes zero lines in `core/`
- HydroWatch backtest metrics (MAE in ha, MAPE in %) are reported with their limits (docs/11-spike-review.md)
