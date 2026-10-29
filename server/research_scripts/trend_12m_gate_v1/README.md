# Trend 12-month gate + vol sizing (`TG-12M-GATE-001`)

Preregistered research experiment (NEXUS Cloud Strategy Research 01, top-2).

**Evidence ceiling:** `EXPLORATORY_ONLY`. Power Gate V1.4 cannot certify `POWER_READY` today. This package **never** claims `VALIDATED`.

## Hypothesis

Gate daily XAUUSD exposure by the sign of the trailing 12-month return; optionally size by realized volatility. Selection among three preregistered variants only on public history **before 2019**. Winner must beat size-matched buy-and-hold on post-2019 confirmations (holdouts excluded).

## Excluded windows (runner refuses / day-filters)

| Window | Reason |
|---|---|
| 2022-02-04 → 2023-02-03 | Consumed holdout |
| 2026-02-04 → 2026-09-16 | Phase 7 sealed holdout |

## Splits

| Split | UTC dates |
|---|---|
| `selection` | … → 2018-12-31 (sole variant selection) |
| `confirmation_a` | 2019-01-01 → 2022-02-03 |
| `confirmation_b` | 2023-02-04 → 2025-11-04 |
| `combined_confirmations` | A∪B; applies F2–F4 on frozen winner |
| `internal_validation` | 2025-11-04 → 2026-02-04 (one-shot after discoveries) |

## Variants (K=3)

1. `LO_FLAT_UNIT` — long if r12>0 else flat; unit size vs unit BH  
2. `LO_FLAT_VOL` — long if r12>0 else flat; vol-target vs vol BH  
3. `LS_VOL` — sign(r12) × vol-target vs vol BH  

## Data (research PC)

Long daily CSV: `date,close` (optional OHLC). Tick Phase 7 alone is **not** sufficient (too short / post-2023).

## Run on PC

```bash
cd server/research_scripts
pip install -r ../requirements-dev.txt

python -m trend_12m_gate_v1.run_experiment --split selection --daily-csv /path/to/xauusd_daily.csv
python -m trend_12m_gate_v1.run_experiment --split confirmation_a --daily-csv /path/to/xauusd_daily.csv
python -m trend_12m_gate_v1.run_experiment --split confirmation_b --daily-csv /path/to/xauusd_daily.csv
python -m trend_12m_gate_v1.run_experiment --split combined_confirmations --daily-csv /path/to/xauusd_daily.csv

# only after combined decision is EXPLORATORY_PROMISING (frozen params)
python -m trend_12m_gate_v1.run_experiment --split internal_validation --daily-csv /path/to/xauusd_daily.csv
```

Outputs: `trend_12m_gate_v1/data/runs/<split>_<ts>/` (gitignored).

## Falsifiers

1. **F1** — no variant beats matched BH on selection after Bonferroni CI  
2. **F2** — winner CI95 excess on combined confirmations includes ≤ 0  
3. **F3** — one calendar year > 50% of sum of positive yearly excess means  
4. **F4** — sign(excess) differs between confirmation_a and confirmation_b  

## Anti-scope

No SMC/CRT/Elliott hunt; no re-enable of FAILED/DEFECT strategies; no live MQL5 wiring; no registry `VALIDATED` promotion; no selection on post-2018 data.

## Context

Candidate #1 session drift (`SD-TOKYO-LONDON-001`) closed FAIL/not promising on discovery_a — do **not** continue drift B.
