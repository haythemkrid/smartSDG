# T05 — STAC client and indices  [MVP]
**Depends on:** T01 (values are in configs/pipeline_default.yaml)
**Goal:** Search/load items; generic index formulas.
**Read first:** 05-data.md, ADR-002 #3 #4
**Files:** core/ingestion/{stac_client.py, geo.py, indices.py}, tests/test_stac.py, tests/test_indices.py, tests/fixtures/stac_*.json
**Interface:** `search(aoi: AOI, dates: tuple[date, date], collections: list[str], max_cloud: int) -> ItemCollection`
**Acceptance criteria:**
- [ ] Tests pass offline (recorded fixtures)
- [ ] Query saved to data/raw/queries/<sha256>.json; identical query → identical hash
- [ ] `NoDataError` on zero items; formulas match 05-data.md on synthetic arrays
**Also:** `geo.py` window reading must support bands of different resolutions (needed by T00b #1). `indices.py` holds NDWI/MNDWI/NDBI.
**Out of scope:** caching layer, SAR, weather (module-specific, see T00)
