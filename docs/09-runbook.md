# 09 — Runbook

Created in T01 (Makefile). Until then they do not exist.
```
make setup
make run-pipeline MODULE=hydrowatch
make deploy-module MODULE=soilguard
make up
make test
make lint
make restore-demo     # restore demo outputs from demo_data/
make snapshot-demo    # snapshot current data/outputs/ to demo_data/
```

## Demo outputs

Demo outputs come from `demo_data/`; regenerate with `make run-pipeline`.

To verify demo data works:
```bash
rm -rf data/outputs && make restore-demo && make test
```

Troubleshooting (append as discovered): Planetary Computer signing, nodata handling, Python 3.13 wheels.
