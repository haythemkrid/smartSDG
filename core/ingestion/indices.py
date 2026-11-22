"""Generic spectral index formulas. Used by modules via core/ingestion/indices.py."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def ndwi(green: NDArray[np.floating], nir: NDArray[np.floating]) -> NDArray[np.floating]:
    """
    Normalized Difference Water Index (NDWI).

    NDWI = (green - nir) / (green + nir)

    Returns 0 where denominator is 0.

    Args:
        green: Green band (B03 for Sentinel-2)
        nir: Near-infrared band (B08 for Sentinel-2)

    Returns:
        NDWI array with same shape as inputs
    """
    denom = green + nir
    return np.where(denom == 0, 0.0, (green - nir) / denom)


def mndwi(green: NDArray[np.floating], swir: NDArray[np.floating]) -> NDArray[np.floating]:
    """
    Modified Normalized Difference Water Index (MNDWI).

    MNDWI = (green - swir) / (green + swir)

    Returns 0 where denominator is 0.

    Args:
        green: Green band (B03 for Sentinel-2)
        swir: Short-wave infrared band (B11 for Sentinel-2)

    Returns:
        MNDWI array with same shape as inputs
    """
    denom = green + swir
    return np.where(denom == 0, 0.0, (green - swir) / denom)


def ndbi(swir: NDArray[np.floating], nir: NDArray[np.floating]) -> NDArray[np.floating]:
    """
    Normalized Difference Built-up Index (NDBI).

    NDBI = (swir - nir) / (swir + nir)

    Returns 0 where denominator is 0.

    Args:
        swir: Short-wave infrared band (B11 for Sentinel-2)
        nir: Near-infrared band (B08 for Sentinel-2)

    Returns:
        NDBI array with same shape as inputs
    """
    denom = swir + nir
    return np.where(denom == 0, 0.0, (swir - nir) / denom)


def cloud_mask_from_scl(scl: NDArray[np.integer], cloud_classes: list[int]) -> NDArray[np.bool_]:
    """
    Create cloud/shadow mask from Scene Classification Layer (SCL).

    Args:
        scl: SCL band array
        cloud_classes: List of SCL class values to mask (default: [3, 8, 9, 10])

    Returns:
        Boolean mask where True = cloud/shadow pixel
    """
    return np.isin(scl, cloud_classes)
