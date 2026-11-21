"""Pydantic schemas. SOURCE OF TRUTH until T02 copies it verbatim to core/sdk/schemas.py.
Do not modify without human approval."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class AOI(BaseModel):
    """Area of interest loaded from configs/tunisia_aois.geojson. geometry: GeoJSON, EPSG:4326."""

    id: str
    name: str
    geometry: dict[str, Any]


class OutputSpec(BaseModel):
    name: str
    type: Literal["cog", "geoparquet", "geojson"]


class ModuleManifest(BaseModel):
    """Content of modules/<id>/manifest.yaml."""

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    title: str
    sdg: list[int] = Field(min_length=1)  # each 1..17
    sensors: list[str] = Field(min_length=1)
    indices: list[str] = []
    aoi_id: str  # id of a feature in configs/tunisia_aois.geojson
    temporal_resolution: str | None = None
    spatial_resolution_m: float | None = None
    params: dict[str, Any] = {}  # module-specific parameters
    outputs: list[OutputSpec] = Field(min_length=1)


class GeoLayer(BaseModel):
    """One exported artifact the API can serve."""

    module_id: str
    name: str
    kind: Literal["cog", "geoparquet", "geojson"]
    path: Path
    time: date | None = None
    bbox: tuple[float, float, float, float] | None = None


class TimeSeriesPoint(BaseModel):
    module_id: str
    aoi_id: str | None = None
    time: date
    metric: str
    value: float
