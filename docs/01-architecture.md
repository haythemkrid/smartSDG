# 01 — Architecture

```
frontend/app.py (Streamlit + Leafmap)   ← calls the API only
        │ REST / GeoJSON / COG
core/api/main.py (FastAPI)              ← serves DEPLOYED modules, reads run artifacts only
        │
core/registry/module_loader.py          ← discovers modules/*/manifest.yaml, validates, registers in MLflow
        │
modules/<id>/{manifest.yaml, module.py} ← each subclasses BaseSDGModule
        │
core/ingestion/stac_client.py           ← Planetary Computer STAC (Sentinel-1/2, Landsat)
```
Pipeline orchestration: DVC stages (`dvc.yaml`) per module; MLflow for runs and registry;
the `orchestrator` compose service is described in 10-known-unknowns.md #2.

## Dependency rules
sdk ← ingestion ← modules ; registry depends on sdk ; api depends on sdk + registry ;
frontend depends on the API only. Modules never import each other; the core never imports a
concrete module. The API never runs science code on a request.

## One run
ingest → preprocess → indices → train/infer → evaluate → export → register (docs/06-pipeline.md)
