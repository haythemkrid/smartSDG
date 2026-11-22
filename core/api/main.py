"""FastAPI application serving deployed SDG modules dynamically."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from core.registry.module_loader import ModuleLoader
from core.sdk.schemas import GeoLayer, TimeSeriesPoint

app = FastAPI(
    title="SmartSDG Core Engine API",
    description="API for SDG monitoring modules in Tunisia",
    version="0.1.0",
)

# Module loader instance
module_loader = ModuleLoader()


@app.get("/modules")
async def list_modules() -> list[dict[str, Any]]:
    """List all deployed modules with their metadata."""
    deployed_ids = module_loader.get_deployed_modules()
    manifests = module_loader.discover_modules()

    result = []
    for module_id in deployed_ids:
        if module_id in manifests:
            manifest = manifests[module_id]
            result.append(
                {
                    "id": manifest.id,
                    "version": manifest.version,
                    "title": manifest.title,
                    "sdg": manifest.sdg,
                    "sensors": manifest.sensors,
                    "indices": manifest.indices,
                    "aoi_id": manifest.aoi_id,
                    "temporal_resolution": manifest.temporal_resolution,
                    "spatial_resolution_m": manifest.spatial_resolution_m,
                    "outputs": [{"name": o.name, "type": o.type} for o in manifest.outputs],
                }
            )
    return result


@app.get("/modules/{module_id}/layers")
async def list_layers(module_id: str) -> list[GeoLayer]:
    """List all exported layers (COG/GeoParquet/GeoJSON) for a deployed module."""
    # Check if module is deployed
    deployed_ids = module_loader.get_deployed_modules()
    if module_id not in deployed_ids:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not deployed")

    # Scan data/outputs/{module_id}/ for exported layers
    import os
    from pathlib import Path

    outputs_dir = Path(f"data/outputs/{module_id}")
    if not outputs_dir.exists():
        return []

    layers = []
    for run_dir in sorted(outputs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        for file_path in run_dir.iterdir():
            if file_path.is_file():
                kind = "cog" if file_path.suffix in [".tif", ".tiff"] else "geoparquet"
                layers.append(
                    GeoLayer(
                        module_id=module_id,
                        name=file_path.stem,
                        kind=kind,
                        path=str(file_path),
                        time=None,
                        bbox=None,
                    )
                )
    return layers


@app.get("/modules/{module_id}/timeseries")
async def get_timeseries(module_id: str) -> list[TimeSeriesPoint]:
    """Return time series points for a deployed module."""
    # Check if module is deployed
    deployed_ids = module_loader.get_deployed_modules()
    if module_id not in deployed_ids:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not deployed")

    # Get AOI ID from manifest
    manifests = module_loader.discover_modules()
    manifest = manifests.get(module_id)
    aoi_id = manifest.aoi_id if manifest else None

    # Read time series from GeoParquet in data/outputs/{module_id}/
    import pandas as pd
    from pathlib import Path
    from datetime import date

    outputs_dir = Path(f"data/outputs/{module_id}")
    if not outputs_dir.exists():
        return []

    # Find the most recent run directory
    run_dirs = sorted([d for d in outputs_dir.iterdir() if d.is_dir()])
    if not run_dirs:
        return []

    latest_run = run_dirs[-1]
    ts_files = list(latest_run.glob("*timeseries*.parquet"))
    if not ts_files:
        return []

    try:
        df = pd.read_parquet(ts_files[0])
        # Convert to TimeSeriesPoint format
        points = []
        for _, row in df.iterrows():
            # Find metric column (non-quarter, non-geometry columns)
            metric_cols = [c for c in df.columns if c not in ["quarter", "geometry"]]
            for metric in metric_cols:
                # Parse quarter string like "2024-Q1" to date (first day of quarter)
                quarter_str = str(row["quarter"])
                if "-Q" in quarter_str:
                    year, q = quarter_str.split("-Q")
                    month = (int(q) - 1) * 3 + 1
                    time_date = date(int(year), month, 1)
                else:
                    time_date = date.today()

                val = row[metric]
                points.append(
                    TimeSeriesPoint(
                        module_id=module_id,
                        aoi_id=aoi_id,
                        time=time_date,
                        metric=metric,
                        value=float(val) if pd.notna(val) else 0.0,
                    )
                )
        return points
    except Exception:
        return []


@app.get("/modules/{module_id}/runs")
async def list_runs(module_id: str) -> list[dict[str, Any]]:
    """List all runs for a deployed module."""
    # Check if module is deployed
    deployed_ids = module_loader.get_deployed_modules()
    if module_id not in deployed_ids:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not deployed")

    # For MVP, return empty list. In real implementation, read from MLflow or filesystem
    return []


@app.get("/modules/{module_id}/layers/{layer_name}")
async def get_layer(module_id: str, layer_name: str) -> FileResponse:
    """Serve a specific layer file (COG/GeoParquet/GeoJSON)."""
    # Check if module is deployed
    deployed_ids = module_loader.get_deployed_modules()
    if module_id not in deployed_ids:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not deployed")

    # For MVP, return 404. In real implementation, serve from data/outputs/{module_id}/
    raise HTTPException(status_code=404, detail=f"Layer '{layer_name}' not found")


# Health check endpoint
@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
