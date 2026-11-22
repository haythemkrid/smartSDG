"""Core ingestion package for STAC search, spectral indices, and geospatial utilities."""

from __future__ import annotations

from core.ingestion.geo import (
    NoDataError,
    get_utm_crs_from_bounds,
    read_window,
    read_window_matching,
    reproject_bounds,
    write_cog,
)
from core.ingestion.indices import (
    cloud_mask_from_scl,
    mndwi,
    ndbi,
    ndwi,
)
from core.ingestion.stac_client import (
    STACClient,
    load_bands,
)

__all__ = [
    # indices
    "ndwi",
    "mndwi",
    "ndbi",
    "cloud_mask_from_scl",
    # geo
    "NoDataError",
    "get_utm_crs_from_bounds",
    "reproject_bounds",
    "read_window",
    "read_window_matching",
    "write_cog",
    # stac_client
    "STACClient",
    "load_bands",
]
