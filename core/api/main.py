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

    # For MVP, return mock layers. In real implementation, scan data/outputs/{module_id}/
    # This is a placeholder - actual implementation would read from filesystem
    return []


@app.get("/modules/{module_id}/timeseries")
async def get_timeseries(module_id: str) -> list[TimeSeriesPoint]:
    """Return time series points for a deployed module."""
    # Check if module is deployed
    deployed_ids = module_loader.get_deployed_modules()
    if module_id not in deployed_ids:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not deployed")

    # For MVP, return mock time series. In real implementation, read from GeoParquet
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
