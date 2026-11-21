# 11 — Spike review (hydrowatch_repo)

Findings from reading the code. "Verify" = I could not run it (no network to Planetary Computer);
the human or agent must confirm before acting. Policy (human decision): the goal is to demonstrate the platform,
not to improve the pipeline. The spike is migrated as-is; these findings are known limitations to state
honestly in the demo. Fixes are stretch (T00b) and only on explicit request.

| # | Severity | Finding | Proposed handling |
|---|---|---|---|
| 1 | High (verify) | `scl` is read with a window computed from the B03 (10 m) transform, but SCL is delivered at 20 m. The pixel window lands on the wrong ground area (about 2x offset and extent), so the cloud mask is misaligned with NDWI. | Read SCL with its own transform, upsample (nearest) to the 10 m grid in `geo.py`. Check: print `src.res` for B03/B08/SCL. |
| 2 | High (verify) | NDWI uses raw DN. For products processed with baseline 04.00 or later, reflectance has a 1000 DN offset (scale 1/10000). Uncorrected, NDWI is compressed and the `0.05` weak-label threshold is tied to raw DN. | Apply scale/offset from the asset's `raster:bands` metadata, then re-tune or re-justify the threshold. Check `s2:processing_baseline` on items. |
| 3 | Medium | Cloud/shadow pixels are set to 0 (non-water) and area is not normalised, so cloudy scenes bias the area low. | Record `valid_fraction` per scene; decide: drop scenes under a coverage floor, or scale area. Human decision. |
| 4 | Medium | The "backtest" uses the observed same-quarter precipitation and temperature as inputs. That is a hindcast with oracle weather, not a forecast. | Label it "hindcast" in outputs and docs, or feed forecasted weather. |
| 5 | Medium | Tiny sample: up to 12 training rows (2023-Q1 to 2025-Q4) and up to 4 test rows; `2026-Q4` is partial (end date 2026-11-01), so its rain total is partial. | Report n with every metric; use complete quarters only (human decision). |
| 6 | Medium | Pixel RF is trained on its own weak labels (`ndwi > 0.05`, features derived from NDWI): it approximates the threshold. No independent water label exists, so mask accuracy is unvalidated. | State it as such. Optional sanity check: overlap with SCL water class (6). |
| 7 | Medium | One scene per quarter = earliest acceptable scene by date, so the acquisition date inside a quarter varies. | Keep for baseline; decide on a fixed day-of-quarter or composite later. |
| 8 | Low | `merge(...).fillna(0)` turns missing weather into 0 mm; `bfill()` on lag features makes the first row's lag equal to its own value. | Fail loudly on missing weather; drop the first row instead of back-filling. |
| 9 | Low | `requests.get(...).json()["daily"]` has no timeout or status check; an API error raises `KeyError`. Open-Meteo usage terms/attribution not yet checked. | Timeout, status check, response cached as fixture. |
| 10 | Low | The bbox is a rectangle: "water area" counts river and any other water in it, not only the reservoir. | Name the metric `water_area_in_aoi_ha`, or provide a reservoir polygon. |
| 11 | Low | Hard-coded: pixel area `0.01` ha (only valid at 10 m), catchment weights 0.45/0.35/0.20 (no source), `sys.path.append` hack, empty `scenes` crashes later. | Derive pixel area from the transform; weights to params (done); raise `NoDataError`. |
