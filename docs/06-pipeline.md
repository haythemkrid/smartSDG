# 06 — Pipeline

| Stage | Input | Output | Rule |
|---|---|---|---|
| ingest | AOI, dates, collections, cloud cap (+ weather for HydroWatch) | `data/raw/queries/<hash>.json`, items, weather | query hashed and saved; weather responses cached |
| preprocess | items | masked, reprojected dataset | via core/ingestion/geo.py only |
| indices | dataset | dataset + indices | formulas from core/ingestion/indices.py |
| train/infer | dataset, params | model, predictions | seeded |
| evaluate | predictions, reference | metrics.json | logged to MLflow |
| export | predictions | COG + GeoParquet (incl. time series) | under data/outputs/<id>/<run_id>/ |
| register | artifacts, metrics | MLflow run | Staging → Production is manual |

Parameters: pipeline_default.yaml < manifest params < CLI overrides (ADR-002).
Orchestration: the `orchestrator` compose service is a DVC runner. Root `dvc.yaml`, one stage chain per module; `make run-pipeline MODULE=<id>` wraps it.
Deployment: `make deploy-module MODULE=<id>` (ADR-002 #6). Spike migration: T00.
