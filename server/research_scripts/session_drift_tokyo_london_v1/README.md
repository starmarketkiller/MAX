# Session drift Tokyo→London (`SD-TOKYO-LONDON-001`)

Preregistered research experiment (NEXUS Cloud Strategy Research 01, top-1).

**Evidence ceiling:** `EXPLORATORY_ONLY`. Power Gate V1.4 cannot certify `POWER_READY` today. This package **never** claims `VALIDATED`.

## Hypothesis

Long XAUUSD from Tokyo cash open (Asia/Tokyo 09:00) to London cash open (Europe/London 08:00), priced **ask→bid**, beats a duration-scaled generic gold rise, with stable sign across two discovery windows and without single-year concentration.

## Excluded windows (runner refuses overlap)

| Window | Reason |
|---|---|
| 2022-02-04 → 2023-02-03 | Consumed holdout |
| 2026-02-04 → 2026-09-16 | Phase 7 sealed holdout |

## Splits

| Split | UTC |
|---|---|
| `discovery_a` | 2023-02-04 → 2024-08-04 |
| `discovery_b` | 2024-08-04 → 2025-11-04 |
| `combined_discoveries` | union; applies F1–F4 |
| `internal_validation` | 2025-11-04 → 2026-02-04 (one-shot after discoveries) |

## Data (research PC only)

Phase 7 Dukascopy ticks (gitignored):

`server/research_scripts/phase7/data_cache_new_period/decoded/YYYY/YYYY-MM-DD.csv.gz`

Cloud agents do **not** have these files. Unit tests use synthetic bars only.

## Run on PC

```bash
cd server/research_scripts
pip install -r ../requirements-dev.txt

# smoke (10 days): proves tick read + bar build + session matching
python -m session_drift_tokyo_london_v1.run_experiment --split discovery_a --smoke-days 10

# full discoveries
python -m session_drift_tokyo_london_v1.run_experiment --split discovery_a
python -m session_drift_tokyo_london_v1.run_experiment --split discovery_b
python -m session_drift_tokyo_london_v1.run_experiment --split combined_discoveries

# only after combined decision is EXPLORATORY_PROMISING (frozen params)
python -m session_drift_tokyo_london_v1.run_experiment --split internal_validation
```

Optional: pre-aggregated M15 bid/ask CSV via `--bars-csv path.csv` (columns: `start`, `open`, `ask_open`, …).

Outputs: `session_drift_tokyo_london_v1/data/runs/<split>_<ts>/` (gitignored) — `summary.json`, `events.csv`.

## Falsifiers (preregistered)

1. **F1** — month-block CI95 for mean net USD includes ≤ 0  
2. **F2** — mean delta vs duration-scaled Tokyo→Tokyo generic gold ≤ 0  
3. **F3** — one calendar year > 50% of sum of positive yearly means  
4. **F4** — sign(mean) differs between discovery_a and discovery_b  

## Anti-scope

No SMC/CRT/Elliott hunt; no re-enable of FAILED/DEFECT strategies; no live MQL5 wiring; no registry `VALIDATED` promotion from this run.
