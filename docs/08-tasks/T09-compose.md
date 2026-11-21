# T09 — Docker Compose  [MVP-lite]
**Depends on:** T03, T04
**Goal:** `make up` starts the stack.
**Files:** docker-compose.yml, Dockerfile(s)
**Acceptance criteria:**
- [ ] API, MLflow and frontend start; frontend reaches the API; MLflow UI reachable
- [ ] `orchestrator` service = container that runs `dvc repro` for a module (`make run-pipeline` uses it); not a scheduler
**Out of scope:** production hardening
