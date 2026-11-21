import pystac_client
import planetary_computer
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
import numpy as np
import pandas as pd

class Sentinel2IngestionPipeline:
    """
    Handles Sentinel-2 L2A imagery search, UTM coordinate projection,
    NDWI computation, and pixel-level SCL cloud/shadow masking.
    """
    def __init__(self, bbox, max_cloud=15):
        self.bbox = bbox
        self.max_cloud = max_cloud
        self.catalog = pystac_client.Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=planetary_computer.sign_inplace,
        )

    def fetch_scenes(self, start_date, end_date):
        search = self.catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=self.bbox,
            datetime=f"{start_date}/{end_date}",
            query={"eo:cloud_cover": {"lt": self.max_cloud}},
        )
        return sorted(list(search.items()), key=lambda x: x.datetime)

    def ingest_time_series(self, start_date="2023-01-01", end_date="2026-11-01"):
        items = self.fetch_scenes(start_date, end_date)
        records = []
        seen_quarters = set()

        for item in items:
            quarter = f"{item.datetime.year}-Q{(item.datetime.month - 1)//3 + 1}"
            if quarter in seen_quarters:
                continue

            try:
                green_href = item.assets["B03"].href
                nir_href = item.assets["B08"].href
                scl_href = item.assets["SCL"].href

                with rasterio.open(green_href) as src_g, \
                     rasterio.open(nir_href) as src_n, \
                     rasterio.open(scl_href) as src_s:

                    utm_bounds = transform_bounds("EPSG:4326", src_g.crs, *self.bbox)
                    window = from_bounds(*utm_bounds, transform=src_g.transform)

                    green = src_g.read(1, window=window).astype("float32")
                    nir = src_n.read(1, window=window).astype("float32")
                    scl = src_s.read(1, window=window)

                    win_transform = src_g.window_transform(window)
                    crs = src_g.crs

                denom = green + nir
                ndwi = np.where(denom == 0, 0, (green - nir) / denom)
                cloud_mask = np.isin(scl, [3, 8, 9, 10])

                seen_quarters.add(quarter)
                records.append({
                    "date": item.datetime.strftime("%Y-%m-%d"),
                    "quarter": quarter,
                    "ndwi": ndwi,
                    "cloud_mask": cloud_mask,
                    "transform": win_transform,
                    "crs": crs
                })
            except Exception as e:
                print(f"Skipping scene {item.id}: {e}")

        return records
