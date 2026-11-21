# T02 — SDK and module loader  [MVP]
**Depends on:** T01
**Goal:** Copy the contract files verbatim into core/sdk/ and implement discovery/validation.
**Read first:** docs/03-contracts/*, ADR-002
**Files:** core/sdk/{base_module.py, schemas.py}, core/registry/module_loader.py, configs/deployed_modules.yaml,
tests/test_loader.py, tests/test_contract.py
**Acceptance criteria:**
- [ ] core/sdk files are byte-identical to docs/03-contracts (imports adjusted only)
- [ ] Loader scans `modules/*/manifest.yaml`, validates with ModuleManifest; invalid manifest → error naming the field
- [ ] Loader lists deployed modules from configs/deployed_modules.yaml
- [ ] Contract test passes for every module under modules/
**Out of scope:** API, MLflow registration (T08)
