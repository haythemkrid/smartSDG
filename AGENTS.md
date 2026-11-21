# AGENTS.md — SmartSDG Core Engine

Read this file fully before any task. Read other docs only when told to (table below).

## What this project is
SmartSDG Core Engine is a plug-and-play platform to monitor SDG indicators in Tunisia from
satellite data. Domain modules (HydroWatch, UrbanPulse, SoilGuard) implement ONE contract
(`BaseSDGModule`); the core ingests, versions, serves them through an API and shows them on a map.
Deadline: hackathon 2026-11-24/25. Scope = MVP (docs/00-overview.md).

## Repository layout (source of truth for file locations)
```
smartsdg-core-engine/
├── Makefile                    # setup, run-pipeline, deploy-module, up (+ test, lint)
├── docker-compose.yml          # API, MLflow, frontend, orchestrator
├── pyproject.toml
├── dvc.yaml                    # [addition] pipeline stages
├── configs/
│   ├── tunisia_aois.geojson    # AOIs: Sidi Salem dam, Grand Tunis, Oasis
│   └── pipeline_default.yaml   # global params (dates, cloud cap, resolution)
├── core/
│   ├── sdk/{base_module.py, schemas.py}      # CONTRACT (protected)
│   ├── ingestion/stac_client.py              # STAC search/load (+ geo.py, indices.py: additions)
│   ├── registry/module_loader.py             # discovery + MLflow registration
│   └── api/main.py                           # FastAPI
├── modules/{hydrowatch,urbanpulse,soilguard}/{manifest.yaml, module.py}
├── frontend/app.py             # Streamlit + Leafmap/MapLibre
├── data/{raw,processed,outputs}
├── tests/                      # [addition] fixtures/, golden/
└── docs/                       # these docs
```
Legacy: `hydrowatch_repo/` (spike: ingestion/features/model/main). Read-only reference until task T00.
Files marked [addition] are not in the original tree; they are approved here and explained in
docs/02-decisions/002-layout-and-contract.md. Any other new top-level file needs human approval.

## Stack (docs/02-decisions/001-stack.md; do not substitute)
Python 3.13 · pystac-client + planetary-computer · rasterio (+ rioxarray/xarray) · geopandas/GeoParquet
· Pydantic v2 · FastAPI · MLflow · DVC · Streamlit + Leafmap · Docker Compose · pytest · ruff.

## Commands (docs/09-runbook.md)
```
make setup                         # create env, install deps
make run-pipeline MODULE=hydrowatch
make deploy-module MODULE=soilguard
make up                            # docker compose up (API, MLflow, frontend, orchestrator)
make test                          # offline pytest   [addition]
make lint                          # ruff             [addition]
```
A command that does not exist yet is created in task T01. Do not invent alternatives.

## Conventions
- Type hints everywhere; docstrings on public functions; code and comments in English.
- CRS/reprojection only through `core/ingestion/geo.py`. Index math only through `core/ingestion/indices.py`.
- Parameters: global in `configs/pipeline_default.yaml`, per-module in `manifest.yaml` (`params`).
  No magic numbers in code. Randomness seeded from params.
- Modules never import other modules. The core never imports a concrete module (use module_loader).
- Tests are offline (fixtures in tests/fixtures/).
- Outputs: rasters COG, tables GeoParquet, under `data/outputs/<module_id>/<run_id>/`.

## Hard rules
1. NEVER edit `core/sdk/` or `docs/03-contracts/` without asking the human.
2. NEVER invent data, collection IDs, thresholds, AOI polygons, spectral formulas or dataset URLs.
   A fact marked `TODO(haythem)` or absent from the docs means STOP and ask.
3. NEVER add a dependency or change the stack without an ADR and human approval.
4. Do not build anything under "Non-goals" (docs/00-overview.md).
5. Do not delete or rewrite `hydrowatch_repo/` outside T00, and only with human approval.
6. One task at a time; touch only the files listed in the task card.
7. HydroWatch science (indices, thresholds, models, features) is migrated as-is. Do not fix or improve it unless the human explicitly starts T00b.

## Where to read what
| When | Read |
|---|---|
| Any task | its card in docs/08-tasks/ + the "Read first" files |
| Touching sdk/modules | docs/03-contracts/, docs/04-modules/<module>.md |
| Touching data/STAC | docs/05-data.md |
| Touching pipeline/deploy | docs/06-pipeline.md, ADR-002 |
| Writing tests | docs/07-testing.md |
| Unsure about a fact | docs/10-known-unknowns.md |
| Touching HydroWatch or the spike | docs/04-modules/hydrowatch.md, docs/11-spike-review.md |

## Definition of done
- [ ] Every acceptance criterion of the card passes (commands/tests)
- [ ] `make test` and `make lint` pass
- [ ] Only listed files touched (or justified)
- [ ] Docs updated if behaviour/commands changed
- [ ] Short note: what changed, what remains, new unknowns added to docs/10-known-unknowns.md
