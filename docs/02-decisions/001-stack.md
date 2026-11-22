# ADR-001 — Technology stack
Status: ACCEPTED (reflects actual implementation)

- Python >=3.11 (pyproject.toml: `requires-python = ">=3.11"`); Python 3.11 used in CI/dev
- Package manager: pip (via pyproject.toml + uv for locking); **DEVIATION**: original layout mentioned Python 3.13, but 3.11 is the minimum supported and used
- FastAPI ✔, Pydantic v2 ✔ (schemas.py), MLflow ✔, DVC ✔, pystac-client ✔, rasterio ✔
- planetary-computer (signing), rioxarray/xarray (array handling on top of rasterio), geopandas + GeoParquet
- Frontend: Streamlit + Leafmap/MapLibre ✔
- Docker Compose ✔; pytest, ruff

## Rejected
- Google Earth Engine (not self-hostable, licence/auth friction)
- Airflow/Prefect (too heavy for the MVP; DVC stages suffice)
- A custom JS frontend (Streamlit is faster to deliver in 3 days)

## Consequences
File-based, offline-testable; the only external dependency at runtime is Planetary Computer at ingestion.

## Added after reading the spike
scikit-learn ✔ (RandomForest), pandas ✔, numpy ✔, requests ✔ (Open-Meteo). `rasterio` ✔ is the raster reader; rioxarray is optional.

## Deviations from original layout
- **Python version**: Original layout (AGENTS.md) specified Python 3.13; actual implementation uses `>=3.11` with 3.11 as the tested version. This provides broader compatibility while keeping modern Python features.
- **Package manager**: Original layout implied uv as primary; implementation uses pip with uv.lock for reproducible installs. pyproject.toml is the source of truth.
