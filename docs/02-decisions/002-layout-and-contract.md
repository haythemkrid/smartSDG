# ADR-002 — Layout and contract resolutions
Status: PROPOSED. The human's tree is authoritative; these are the gaps I closed. Confirm or override.

1. **Contract = six methods** (ingest, compute_indices, train, infer, evaluate, export_layers) on
   `BaseSDGModule`. Time series are exported as a GeoParquet `GeoLayer`; the API converts rows to
   `TimeSeriesPoint`. No seventh method.
2. **Manifest file is `manifest.yaml`** validated by the Pydantic `ModuleManifest` (no JSON Schema file).
3. **Index math is separated from STAC access.** The tree puts "calcul d'indices" in `stac_client.py`.
   Decision: `stac_client.py` only searches/loads; generic formulas (NDWI, MNDWI, NDBI...) go in
   `core/ingestion/indices.py` (addition). Module-specific use of them stays in `module.py`.
4. **CRS helpers** in `core/ingestion/geo.py` (addition) so reprojection has a single entry point.
5. **Parameter precedence:** `configs/pipeline_default.yaml` < `manifest.yaml` `params` < CLI overrides.
6. **"Deployed" state.** `make deploy-module MODULE=<id>` validates the manifest, registers the module
   in MLflow, and adds the id to `configs/deployed_modules.yaml` (addition). The API serves only deployed
   modules. HydroWatch and UrbanPulse are deployed by default; SoilGuard is not, until the demo.
7. **DVC:** a root `dvc.yaml` (addition); `data/` is tracked by DVC pointers, not committed to git.
8. **No `_template` folder.** SoilGuard is the template and the live-demo module.
9. **Honest demo claim:** SoilGuard is pre-written, so the live moment shows deployment, not
   authoring from scratch. See docs/demo-script.md.

10. `compute_indices` may return per-scene records (numpy arrays + transform + crs) as the spike does; xarray is preferred but not required for the MVP.
11. HydroWatch is two-stage (pixel segmentation, then area forecasting). It stays inside six methods: `train` fits both models using the shared helper `_segment_scenes`; `infer` applies them. No contract change.
12. The area time series is exported as GeoParquet with the AOI geometry repeated per row, so the manifest output types stay cog / geoparquet / geojson.
13. `orchestrator` compose service = DVC runner (human answer).
