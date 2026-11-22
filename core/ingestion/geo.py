"""CRS and window reading helpers. Single entry point for reprojection/windowing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from numpy.typing import NDArray
from rasterio.crs import CRS
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds


class NoDataError(ValueError):
    """Raised when no data is found for a query."""

    pass


def get_utm_crs_from_bounds(bounds: tuple[float, float, float, float]) -> CRS:
    """
    Determine UTM CRS from WGS84 bounds (lon/lat).

    Args:
        bounds: (min_lon, min_lat, max_lon, max_lat) in EPSG:4326

    Returns:
        UTM CRS object
    """
    min_lon, min_lat, max_lon, max_lat = bounds
    center_lon = (min_lon + max_lon) / 2
    center_lat = (min_lat + max_lat) / 2

    # UTM zone calculation
    zone = int((center_lon + 180) / 6) + 1
    hemisphere = "north" if center_lat >= 0 else "south"

    return CRS.from_string(
        f"EPSG:326{zone:02d}" if hemisphere == "north" else f"EPSG:327{zone:02d}"
    )


def reproject_bounds(
    bounds: tuple[float, float, float, float],
    src_crs: CRS | str,
    dst_crs: CRS | str,
) -> tuple[float, float, float, float]:
    """
    Reproject bounds from source CRS to destination CRS.

    Args:
        bounds: (min_x, min_y, max_x, max_y) in src_crs
        src_crs: Source CRS
        dst_crs: Destination CRS

    Returns:
        Bounds in dst_crs
    """
    return transform_bounds(src_crs, dst_crs, *bounds)


def read_window(
    href: str,
    bounds: tuple[float, float, float, float],
    bounds_crs: CRS | str,
    target_resolution: float | None = None,
) -> tuple[NDArray[Any], rasterio.Affine, CRS]:
    """
    Read a raster window from a COG/GeoTIFF href.

    Handles bands at different resolutions by reading at native resolution
    and optionally resampling to target_resolution.

    Args:
        href: Raster file URL (COG or local path)
        bounds: (min_x, min_y, max_x, max_y) in bounds_crs
        bounds_crs: CRS of the bounds
        target_resolution: Optional target resolution in meters. If provided,
            resamples to this resolution. If None, reads at native resolution.

    Returns:
        Tuple of (data_array, transform, crs)
    """
    with rasterio.open(href) as src:
        src_crs = src.crs
        src_transform = src.transform
        src_res = src.res[0]  # Assume square pixels

        # Reproject bounds to source CRS if needed
        if bounds_crs != src_crs:
            bounds = reproject_bounds(bounds, bounds_crs, src_crs)

        # Calculate window in source CRS
        window = from_bounds(*bounds, transform=src_transform)

        # Read data at native resolution
        data = src.read(1, window=window)
        win_transform = src.window_transform(window)

        # Resample if target_resolution is specified and different from native
        if target_resolution is not None and abs(src_res - target_resolution) > 1e-6:
            from rasterio.enums import Resampling
            from rasterio.warp import reproject

            # Calculate output shape
            height = int(window.height * src_res / target_resolution)
            width = int(window.width * src_res / target_resolution)

            out_data = np.empty((height, width), dtype=data.dtype)
            out_transform = rasterio.Affine(
                target_resolution,
                win_transform.b,
                win_transform.c,
                win_transform.d,
                -target_resolution,
                win_transform.f,
            )

            reproject(
                source=data,
                destination=out_data,
                src_transform=win_transform,
                src_crs=src_crs,
                dst_transform=out_transform,
                dst_crs=src_crs,
                resampling=Resampling.nearest,
            )
            return out_data, out_transform, src_crs

        return data, win_transform, src_crs


def read_window_matching(
    href: str,
    reference_transform: rasterio.Affine,
    reference_crs: CRS,
    reference_shape: tuple[int, int],
    resampling: str = "nearest",
) -> NDArray[Any]:
    """
    Read a raster window to match a reference grid exactly.

    Used for reading SCL (20m) to match B03/B08 (10m) grid.

    Args:
        href: Raster file URL
        reference_transform: Target transform
        reference_crs: Target CRS
        reference_shape: Target (height, width)
        resampling: Resampling method ('nearest', 'bilinear', etc.)

    Returns:
        Data array resampled to reference grid
    """
    from rasterio.enums import Resampling
    from rasterio.warp import reproject

    resampling_method = getattr(Resampling, resampling)

    with rasterio.open(href) as src:
        out_data = np.empty(reference_shape, dtype=src.dtypes[0])
        reproject(
            source=rasterio.band(src, 1),
            destination=out_data,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=reference_transform,
            dst_crs=reference_crs,
            resampling=resampling_method,
        )
        return out_data


def write_cog(
    data: NDArray[Any],
    transform: rasterio.Affine,
    crs: CRS,
    path: Path,
    dtype: str = "uint8",
    nodata: int | float | None = None,
) -> None:
    """
    Write a Cloud Optimized GeoTIFF (COG).

    Args:
        data: 2D or 3D array (bands, height, width) or (height, width)
        transform: Affine transform
        crs: CRS object
        path: Output path
        dtype: Output data type
        nodata: Nodata value
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if data.ndim == 2:
        data = data[np.newaxis, ...]

    height, width = data.shape[-2:]
    count = data.shape[0]

    profile = {
        "driver": "COG",
        "height": height,
        "width": width,
        "count": count,
        "dtype": dtype,
        "crs": crs,
        "transform": transform,
        "compress": "deflate",
        "blocksize": 512,
        "overview_resampling": "nearest",
    }

    if nodata is not None:
        profile["nodata"] = nodata

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)
