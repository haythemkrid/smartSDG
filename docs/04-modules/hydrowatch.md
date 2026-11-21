# HydroWatch (SDG 6, 13) — FULL

Source of truth: the spike `hydrowatch_repo/` (ingestion.py, features.py, model.py, main.py).
Defects found in it: docs/11-spike-review.md. Parameter values: `modules/hydrowatch/manifest.yaml`
and `configs/pipeline_default.yaml`.

## What the spike does
1. Search Sentinel-2 L2A on Planetary Computer for the Sidi Salem bbox, 2023-01-01 to 2026-11-01,
   scene cloud cover < 15 %. Keep the earliest scene of each calendar quarter.
2. Per scene: read B03, B08, SCL in the bbox window; NDWI = (B03 − B08)/(B03 + B08) (0 where the
   denominator is 0); cloud mask = SCL in {3, 8, 9, 10}.
3. Water mask: RandomForest pixel classifier (features: NDWI and its two spatial gradients), trained
   once on the first scene with weak labels `ndwi > 0.05` (20 000 sampled pixels), applied to every
   scene; cloud pixels forced to 0. Area (ha) = water pixels × 0.01.
4. Weather (Open-Meteo archive): quarterly precipitation sums at 3 Medjerda-basin points, weighted
   0.45/0.35/0.20; quarterly mean temperature at the Béja point.
5. Features: lag_1_area, weighted_catchment_precip_mm, lag_1_catchment_precip_mm, mean_temp_c,
   sin_q, cos_q (quarter as a cycle). Target: water_area_ha.
6. Train a RandomForestRegressor on quarters before 2026-Q1; walk-forward recursive prediction over
   2026 quarters (each prediction feeds the next lag). Report MAE (ha) and MAPE (%).

## Mapping to BaseSDGModule
| Spike code | Method | Notes |
|---|---|---|
| `fetch_scenes` + first-per-quarter selection; `fetch_catchment_weather` | `ingest` | returns `{"items": [...], "weather": DataFrame}`; saves the hashed STAC query; weather fetch cached as a fixture-able file; weather client lives in `modules/hydrowatch/weather.py` |
| band reading, NDWI, SCL mask | `compute_indices` | returns per-scene records `{date, quarter, ndwi, cloud_mask, transform, crs}` (ADR-002 #10); NDWI via `indices.py`, windowing via `geo.py` |
| pixel RF fit + area series + `build_ml_dataset` + forecaster fit | `train` | artifact `{"pixel_clf", "forecaster", "train_cutoff"}`; shared helper `_segment_scenes` produces the area series the forecaster needs (ADR-002 #11) |
| pixel RF inference + recursive backtest | `infer` | predictions `{"records", "area_ts", "backtest"}` |
| `run_backtest` metrics | `evaluate` | MAE (ha), MAPE (%), per-quarter error_pct; reference = satellite-derived area of the test quarters. No external ground truth exists yet |
| (new) | `export_layers` | water-mask COG per quarter (from the records' transform and crs); area time series as GeoParquet with the AOI geometry |

## Honest scope of the results
The mask is validated against its own weak labels, and the forecast against satellite-derived areas
with oracle weather and a handful of rows. Say so in outputs and in the demo. An external reference
(dam fill levels) is a stretch goal, see 10-known-unknowns.md.

## Migration rule
The spike is migrated as-is, defects included. Purpose: demonstrate the platform, not improve the science. T00b (fixes) is stretch.
