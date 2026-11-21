# 05 — Data

Facts from the spike unless marked TODO(haythem).

## Planetary Computer (Sentinel-2 L2A)
| Item | Value |
|---|---|
| STAC URL | https://planetarycomputer.microsoft.com/api/stac/v1 (signed with `planetary_computer.sign_inplace`) |
| Collection | `sentinel-2-l2a` |
| Bands | B03 (green), B08 (NIR), SCL (scene classification) |
| Cloud filter | `eo:cloud_cover < 15` (scene level) |
| Time window | 2023-01-01 to 2026-11-01 |
| Selection | earliest acceptable scene per calendar quarter (`YYYY-Qn`) |
| Cloud/shadow classes (SCL) | 3, 8, 9, 10 |
| Grid | B03/B08 10 m; **SCL is 20 m** (see 11-spike-review.md #1) |
| CRS | the tile's native UTM (spike does not reproject). TODO(haythem): confirm EPSG by running; expected UTM 32N for this AOI |
| Pixel area | 0.01 ha at 10 m |
| Reflectance scaling | spike uses raw DN (see 11-spike-review.md #2) |

## AOIs (`configs/tunisia_aois.geojson`)
The file did not exist. It now contains `sidi_salem`: bbox [9.355, 36.585, 9.455, 36.655]
(lon/lat, from the spike), a rectangle and not the reservoir outline.
Grand Tunis (UrbanPulse) and Oasis (SoilGuard): TODO(haythem), supply polygons; agents must never invent them.

## Open-Meteo Historical Weather (HydroWatch ancillary data)
| Item | Value |
|---|---|
| URL | https://archive-api.open-meteo.com/v1/archive, `timezone=Africa/Tunis` |
| Precipitation | `daily=precipitation_sum` at (36.28, 7.95), (36.45, 8.44), (36.62, 9.40); summed per quarter |
| Temperature | `daily=temperature_2m_mean` at (36.62, 9.40); mean per quarter |
| Weights | 0.45 / 0.35 / 0.20, source unknown (TODO(haythem)) |
| Terms | TODO(haythem): check usage terms and attribution before publishing |

## Formulas
- NDWI = (B03 − B08) / (B03 + B08), 0 where the denominator is 0
- MNDWI = (B03 − B11) / (B03 + B11) and NDBI = (B11 − B08) / (B11 + B08): not used by the spike; B11 is 20 m
- SoilGuard salinity index: TODO(haythem). Do not pick one.

## Layout
```
data/raw/queries/<sha256>.json     # saved STAC queries; data/raw/weather/<sha256>.json for weather responses
data/processed/<module_id>/<run_id>/
data/outputs/<module_id>/<run_id>/ # water_mask_<YYYY-Qn>.tif (COG), area_timeseries.parquet, metrics.json
```
`run_id` = short hash of (merged params + query hash + code version).
