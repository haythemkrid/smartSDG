# 07 — Testing

- Offline only. Fixtures in `tests/fixtures/`: recorded STAC items, the 4 Open-Meteo responses, and
  small raster crops of B03, B08 and SCL (SCL at its native 20 m). Fixtures over 5 MB are DVC-tracked, not in git.
  TODO(haythem): choose the fixture scenes (suggest 3 to 4 quarters).
- Unit: NDWI on synthetic arrays; quarter labelling; weather aggregation on a recorded response.
- Contract: every `modules/*` passes `tests/test_contract.py`.
- Baseline (T00): `tests/golden/hydrowatch_spike_baseline.json` holds the spike's metrics on the fixtures,
  defects included. TODO(haythem): needs one full run output of the original spike.
- Alignment (T00b): synthetic test with a 10 m band and a 20 m SCL proving the mask lands on the right pixels.
  Marked `xfail` until finding #1 is fixed.
- API: TestClient with a mock module; only deployed modules listed.
- If a test needs the network, the design is wrong: ask.
