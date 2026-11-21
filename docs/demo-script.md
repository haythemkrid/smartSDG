# Demo script (5 min) — build backward from this
1. (0:30) Problem: repeatable satellite SDG monitoring.
2. (1:30) HydroWatch on Sidi Salem: map layer, time series, metrics vs reference.
3. (1:00) Reproducibility: rerun gives same metrics hash; `dvc repro` skips unchanged stages.
4. (1:30) LIVE: SoilGuard exists on disk but is undeployed. Show the app without it; run
   `make deploy-module MODULE=soilguard`; refresh: it appears with no change to core/.
   Optional if time: edit one manifest field live and redeploy.
5. (0:30) Roadmap: more AOIs/governorates, real SoilGuard science, alerting.
Be explicit that SoilGuard is a prepared skeleton and that HydroWatch's science is a prototype (known limitations in docs/11-spike-review.md).
Demo safety: run `make run-pipeline MODULE=hydrowatch` BEFORE the event and serve the cached outputs; the live demo must not depend on Planetary Computer or Open-Meteo being reachable. Fallback: pre-recorded capture (TODO(haythem)).
