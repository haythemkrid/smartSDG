# T01 — Project skeleton  [MVP]
**Depends on:** none
**Goal:** Tree, tooling and commands from AGENTS.md.
**Read first:** AGENTS.md, 01-architecture.md, ADR-001/002
**Files:** Makefile, pyproject.toml (configs/ and modules/hydrowatch/manifest.yaml are already provided: do not change values),
.gitignore, empty package dirs with `__init__.py`, tests/
**Acceptance criteria:**
- [ ] `make setup`, `make test`, `make lint` work from a clean checkout
- [ ] `make run-pipeline`, `make deploy-module`, `make up` exist and fail with a clear "not implemented yet" message
- [ ] Python 3.13 pinned; lockfile committed; `.gitignore` covers `__pycache__/`, `*.pyc`, `.venv/`, `mlruns/`, `data/*` (DVC pointers excepted)
**Out of scope:** any science code
