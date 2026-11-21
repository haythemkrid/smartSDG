# T00 — Adopt the spike  [MVP]
**Depends on:** T02 (contract), T05 (core/ingestion helpers), human's spike run output (unknown #2)
**Goal:** Migrate `hydrowatch_repo/` into `modules/hydrowatch/module.py` per the mapping table in
docs/04-modules/hydrowatch.md. BEHAVIOUR-PRESERVING: keep the known defects (docs/11-spike-review.md).
**Read first:** AGENTS.md, docs/03-contracts/*, docs/04-modules/hydrowatch.md, docs/05-data.md, docs/11-spike-review.md
**Files:** modules/hydrowatch/{module.py, weather.py}, tests/fixtures/*, tests/golden/hydrowatch_spike_baseline.json, tests/test_hydrowatch.py
(manifest.yaml and configs/ are already provided: do not change values)
**Acceptance criteria:**
- [ ] Module passes `tests/test_contract.py` and loads through `module_loader`
- [ ] On the fixtures, metrics match the spike baseline within tolerance (MAE, MAPE, per-quarter areas)
- [ ] All constants read from configs/manifest; no network in tests
- [ ] Each defect from 11-spike-review.md left untouched and listed in the PR note
- [ ] `hydrowatch_repo/` untouched
**Out of scope:** any fix (see T00b), new science
