# ADR-001 — Technology stack
Status: PROPOSED (items ✔ come from the human's layout; confirm the rest)

- Python 3.13 ✔ (cpython-313 bytecode in the spike); fall back to 3.12 only if a geo wheel is missing, and record it
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
