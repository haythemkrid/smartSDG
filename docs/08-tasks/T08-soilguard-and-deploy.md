# T08 — SoilGuard demo module and deploy-module  [MVP]
**Depends on:** T02, T03
**Goal:** SoilGuard skeleton (undeployed) and `make deploy-module`.
**Read first:** ADR-002 #6, docs/demo-script.md, docs/04-modules/soilguard.md
**Files:** modules/soilguard/{manifest.yaml, module.py}, core/registry/module_loader.py (deploy function), Makefile
**Acceptance criteria:**
- [ ] Before deploy: SoilGuard absent from GET /modules
- [ ] After `make deploy-module MODULE=soilguard`: manifest validated, MLflow registration done, listed in GET /modules, `git diff core/` unchanged except the loader's deploy function already present from this task
- [ ] Whole deploy takes under 1 minute (time it)
**Out of scope:** real salinity science
