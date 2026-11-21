# T03 — API  [MVP]
**Depends on:** T02
**Goal:** FastAPI serving deployed modules dynamically, tested with a mock module.
**Files:** core/api/main.py, tests/test_api.py, tests/fixtures/mock_module/
**Interface:** GET /modules, /modules/{id}/layers, /modules/{id}/timeseries (returns TimeSeriesPoint[]), /modules/{id}/runs
**Acceptance criteria:**
- [ ] `pytest tests/test_api.py` passes; OpenAPI at /docs
- [ ] A module added to deployed_modules.yaml appears without code change; an undeployed one does not
**Out of scope:** auth; running science on request
