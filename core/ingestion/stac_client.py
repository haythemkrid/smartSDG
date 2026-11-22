"""STAC search and load client. Saves queries for reproducibility."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import planetary_computer
import pystac
import pystac_client

from core.ingestion.geo import NoDataError
from core.sdk.schemas import AOI


class STACClient:
    """Client for searching and loading STAC items from Planetary Computer."""

    def __init__(
        self,
        stac_url: str = "https://planetarycomputer.microsoft.com/api/stac/v1",
        collection: str = "sentinel-2-l2a",
    ) -> None:
        self.stac_url = stac_url
        self.collection = collection
        self._catalog: pystac_client.Client | None = None

    @property
    def catalog(self) -> pystac_client.Client:
        """Lazy initialization of STAC catalog."""
        if self._catalog is None:
            self._catalog = pystac_client.Client.open(
                self.stac_url,
                modifier=planetary_computer.sign_inplace,
            )
        return self._catalog

    def search(
        self,
        aoi: AOI,
        date_range: tuple[date, date],
        collections: list[str] | None = None,
        max_cloud: int = 15,
    ) -> pystac.ItemCollection:
        """
        Search STAC catalog for items matching criteria.

        Args:
            aoi: Area of interest with geometry in EPSG:4326
            date_range: (start_date, end_date)
            collections: List of collection IDs (default: self.collection)
            max_cloud: Maximum cloud cover percentage (scene-level)

        Returns:
            ItemCollection of matching items

        Raises:
            NoDataError: If no items found
        """
        if collections is None:
            collections = [self.collection]

        # Convert AOI geometry to bbox for STAC search
        # The geometry is a GeoJSON polygon; we need bbox
        coords = aoi.geometry["coordinates"][0]  # Assume single polygon
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        bbox = [min(lons), min(lats), max(lons), max(lats)]

        start_date, end_date = date_range
        datetime_str = f"{start_date.isoformat()}/{end_date.isoformat()}"

        query = {
            "eo:cloud_cover": {"lt": max_cloud},
        }

        search = self.catalog.search(
            collections=collections,
            bbox=bbox,
            datetime=datetime_str,
            query=query,
        )

        items = list(search.items())

        if not items:
            raise NoDataError(
                f"No items found for AOI {aoi.id}, date range {date_range}, "
                f"collections {collections}, max_cloud {max_cloud}"
            )

        # Save query for reproducibility
        self._save_query(aoi, date_range, collections, max_cloud, items)

        return pystac.ItemCollection(items)

    def select_first_per_quarter(self, items: pystac.ItemCollection) -> list[pystac.Item]:
        """
        Select the earliest acceptable scene per calendar quarter.

        Args:
            items: ItemCollection from search

        Returns:
            List of selected items, one per quarter
        """
        # Group by quarter
        quarters: dict[str, list[pystac.Item]] = {}

        for item in items:
            dt = item.datetime
            if dt is None:
                continue
            quarter = f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"
            if quarter not in quarters:
                quarters[quarter] = []
            quarters[quarter].append(item)

        # Select earliest item per quarter
        selected = []
        for quarter in sorted(quarters.keys()):
            quarter_items = sorted(quarters[quarter], key=lambda x: x.datetime)
            selected.append(quarter_items[0])

        return selected

    def _save_query(
        self,
        aoi: AOI,
        date_range: tuple[date, date],
        collections: list[str],
        max_cloud: int,
        items: list[pystac.Item],
    ) -> str:
        """
        Save STAC query with hash for reproducibility.

        Returns:
            SHA256 hash of the query
        """
        query_data = {
            "aoi_id": aoi.id,
            "aoi_geometry": aoi.geometry,
            "date_range": [d.isoformat() for d in date_range],
            "collections": collections,
            "max_cloud": max_cloud,
            "item_ids": [item.id for item in items],
            "item_datetimes": [
                item.datetime.isoformat() if item.datetime else None for item in items
            ],
        }

        # Create deterministic hash
        query_json = json.dumps(query_data, sort_keys=True)
        query_hash = hashlib.sha256(query_json.encode()).hexdigest()[:16]

        # Save to data/raw/queries/
        query_dir = Path("data/raw/queries")
        query_dir.mkdir(parents=True, exist_ok=True)

        query_file = query_dir / f"{query_hash}.json"
        with open(query_file, "w") as f:
            json.dump(query_data, f, indent=2)

        return query_hash


def load_bands(
    item: pystac.Item,
    band_names: list[str],
    aoi: AOI,
    target_resolution: float | None = None,
) -> dict[str, tuple]:
    """
    Load multiple bands from a STAC item, clipped to AOI.

    Args:
        item: STAC item
        band_names: List of band asset keys (e.g., ["B03", "B08", "SCL"])
        aoi: Area of interest for clipping
        target_resolution: Optional target resolution in meters

    Returns:
        Dict mapping band_name -> (data_array, transform, crs)
    """
    from core.ingestion.geo import read_window, read_window_matching

    # Get bounds from AOI geometry
    coords = aoi.geometry["coordinates"][0]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    bounds = (min(lons), min(lats), max(lons), max(lats))

    results = {}
    reference_transform = None
    reference_crs = None
    reference_shape = None

    for band_name in band_names:
        if band_name not in item.assets:
            raise ValueError(f"Band {band_name} not found in item {item.id}")

        href = item.assets[band_name].href

        if target_resolution is not None:
            # Read all bands at target resolution
            data, transform, crs = read_window(href, bounds, "EPSG:4326", target_resolution)
        else:
            # Read at native resolution
            data, transform, crs = read_window(href, bounds, "EPSG:4326")

            # First band becomes reference for matching resolution
            if reference_transform is None:
                reference_transform = transform
                reference_crs = crs
                reference_shape = data.shape
            else:
                # Resample to match reference (for SCL at 20m -> 10m)
                data = read_window_matching(
                    href, reference_transform, reference_crs, reference_shape
                )
                transform = reference_transform
                crs = reference_crs

        results[band_name] = (data, transform, crs)

    return results
