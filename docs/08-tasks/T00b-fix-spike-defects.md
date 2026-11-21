# T00b — Fix spike defects  [STRETCH — NOT in MVP. Do not start unless the human explicitly asks]
**Depends on:** T00, human approval per finding (unknown #4, #5)
**Goal:** Apply findings from docs/11-spike-review.md one at a time, in this order: #1 SCL alignment,
#2 reflectance offset, #3 cloud policy, #8, #9, #11. Each fix is its own commit.
**Files:** modules/hydrowatch/module.py, core/ingestion/geo.py, core/ingestion/indices.py, tests/test_alignment.py, tests/golden/
**Acceptance criteria (per fix):**
- [ ] A test fails before the fix and passes after
- [ ] Golden file updated in the same commit, with the metric change reported in the note
- [ ] Docs (04-modules/hydrowatch.md, 11-spike-review.md) updated: finding marked fixed
**Out of scope:** findings #4, #5, #6, #7, #10 are labelling or policy decisions for the human
