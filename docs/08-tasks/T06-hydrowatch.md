# T06 — HydroWatch end to end + DVC  [MVP]
**Depends on:** T00, T02, T05
**Goal:** Full module, dvc.yaml, MLflow logging, COG/GeoParquet outputs.
**Read first:** 04-modules/hydrowatch.md, 06-pipeline.md, 07-testing.md
**Acceptance criteria:**
- [ ] Baseline golden test (T00) still passes, or the change is explained by an approved T00b fix
- [ ] Second `dvc repro` with unchanged params reruns nothing
- [ ] Layers and time series visible through the API and the map
- [ ] Outputs precomputed under data/outputs/hydrowatch/ so the demo works offline
**Out of scope:** extra AOIs, SAR
