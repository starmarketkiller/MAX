# Macro event gate — NFP/CPI/FOMC (`MEG-NFP-CPI-FOMC-001`)

Preregistered research experiment (NEXUS Cloud Strategy Research 01, top-3).

**Evidence ceiling:** `EXPLORATORY_ONLY`. Power Gate V1.4 cannot certify `POWER_READY` today. This package **never** claims `VALIDATED`.

**Phase 1 only:** non-directional microstructure. Does **not** trade surprise direction.

## Hypothesis

In the window **5 minutes before → 30 minutes after** scheduled NFP, CPI, and FOMC statement releases, XAUUSD **mean bid-ask spread** and **mid-price range** are strictly higher than the **same America/New_York local clock** on matched non-event weekdays, with stable sign across two discovery windows and without single-year concentration.

## Calendar prerequisite (blocking)

A sourced CSV with **pre-release** timestamps is required. Schema = `macro_calendar_v1.release_time.REQUIRED_COLUMNS`. How to obtain/store:

1. Read `../macro_calendar_v1/SOURCES.md` (BLS / Fed / optional MT5 export).
2. One row per publication: event, reference_period, release_date_local, release_time_local, local_timezone, source_url, retrieved_at_utc.
3. Store under `data/` (gitignored) on the research PC — e.g. `data/nfp_cpi_fomc_sourced.csv`.
4. `fixtures/sample_events_synthetic.csv` is **SYNTHETIC_FIXTURE** for CI only; the runner refuses it unless `--allow-synthetic-calendar`.

Forecast/consensus may be empty for phase 1. Directional phase 2 needs a **new** `hypothesis_id` plus licensed pre-release consensus.

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
| `combined_discoveries` | union; applies F1–F3 |
| `internal_validation` | 2025-11-04 → 2026-02-04 (one-shot after discoveries) |

## Data (research PC)

- Calendar CSV (above).
- M15 bid/ask bars covering the splits (from Phase 7 ticks or export). Cloud agents do **not** have these files.

## Run on PC

```bash
cd server/research_scripts
pip install -r ../requirements-dev.txt

python -m macro_event_gate_v1.run_experiment --split discovery_a \
  --calendar-csv /path/to/nfp_cpi_fomc.csv --bars-csv /path/to/xauusd_m15.csv
python -m macro_event_gate_v1.run_experiment --split discovery_b \
  --calendar-csv /path/to/nfp_cpi_fomc.csv --bars-csv /path/to/xauusd_m15.csv
python -m macro_event_gate_v1.run_experiment --split combined_discoveries \
  --calendar-csv /path/to/nfp_cpi_fomc.csv --bars-csv /path/to/xauusd_m15.csv

# only after combined decision is EXPLORATORY_PROMISING (frozen params)
python -m macro_event_gate_v1.run_experiment --split internal_validation \
  --calendar-csv /path/to/nfp_cpi_fomc.csv --bars-csv /path/to/xauusd_m15.csv
```

Outputs: `macro_event_gate_v1/data/runs/<split>_<ts>/` (gitignored).

## Falsifiers (preregistered)

1. **F1** — neither `spread_delta` nor `range_delta` has month-block CI95 with low > 0 on A∪B  
2. **F2** — one calendar year > 50% of sum of positive yearly mean `spread_delta`  
3. **F3** — sign of the primary elevated metric differs between discovery_a and discovery_b  

## Anti-scope

No SMC/CRT/Elliott hunt; no re-enable of FAILED/DEFECT strategies; no live MQL5 wiring; no registry `VALIDATED` promotion; do **not** continue `SD-TOKYO-LONDON-001` or `TG-12M-GATE-001` (both FAIL).

## Context

Candidate #1 session drift and #2 trend 12m gate closed FAIL — this is B1 candidate #3 only.
