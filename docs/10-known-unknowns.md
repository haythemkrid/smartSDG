# 10 — Known unknowns (STOP and ask; never invent)

## Resolved
- Orchestrator = a DVC runner (container running `dvc repro`, triggered by `make run-pipeline`); not a scheduler.
- AOI file did not exist; Sidi Salem created from the spike's bbox.
- Collection, cloud cap, time window, SCL classes, water threshold, model hyperparameters: now in configs and the manifest.
- Spike code reviewed: docs/11-spike-review.md.

## Open
1. External ground truth for HydroWatch (dam fill levels). The spike has none: its metrics compare the
   forecast to satellite-derived area. Stretch goal; hand-typed CSV from the human if found.
2. One full output of the original spike (`python main.py | tee spike_run.txt`, with runtime): still useful to prove the migration reproduces it and to precompute demo artifacts.
3. EPSG actually used by the tile (spike keeps native CRS).
4. Spike defects: decided NOT to fix for the demo (stretch T00b). No confirmation run needed.
5. (merged into 4)
6. Source of the catchment weights 0.45/0.35/0.20; Open-Meteo terms/attribution.
7. Polygons for Grand Tunis and Oasis; reservoir outline for Sidi Salem if "reservoir area" is claimed.
8. SoilGuard: salinity index and sensors (skeleton until defined). UrbanPulse thermal source (skeleton).
9. Governorate boundary source and licence.
10. ADR-002 items awaiting confirmation (#3, #4, #6, #10, #11, #12).
