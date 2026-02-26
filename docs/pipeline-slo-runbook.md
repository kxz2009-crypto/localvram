# Pipeline SLO Runbook

This runbook defines how LocalVRAM tracks pipeline stability SLO for benchmark collection and publish.

## 1) Source and output

- Source: `src/data/pipeline-status.json`
- SLO snapshot: `src/data/pipeline-slo.json`
- Status page: `/en/status/pipeline-status/`

## 2) Build snapshot

```bash
python scripts/build-pipeline-slo.py
```

Optional flags:

```bash
python scripts/build-pipeline-slo.py --target-success-rate 95 --window-days 7,28 --workflow-keys weekly_benchmark,publish_benchmark_artifact
```

## 3) SLO definition

- Primary SLO: 28-day success rate `>= 95%` for:
  - `weekly_benchmark`
  - `publish_benchmark_artifact`
- Weekly report window: rolling 7 days.
- Failure taxonomy source: `failure_class` in `pipeline-status.json` history.

## 4) Operational usage

When SLO is not met:

1. Open `/en/status/pipeline-status/`.
2. Check 28-day failure top class per workflow.
3. Prioritize fixes by highest failure frequency.
4. Re-run workflow and verify SLO trend improves in next runs.

## 5) CI integration

- `weekly-benchmark.yml` rebuilds `pipeline-slo.json` after weekly status snapshot update.
- `publish-benchmark-artifact.yml` rebuilds SLO before quality gate and again after publish final status update.
- `daily-content.yml` rebuilds SLO to keep status pages and quality checks aligned.
