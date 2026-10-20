# Phase 7.35 — Measure hardening (PC-MT5)

Hardening is already on branch `cursor/edge-freeze-credit-safe-loop-5198` (commit `b38fba2`).  
**No new strategy confirmatory** until density gate `ALLOW` and collect reports `isolation_ok: true`.

## 1. Sync + recompile EA

```powershell
cd C:\Users\User\ClaudeWork\MAX
git pull origin cursor/edge-freeze-credit-safe-loop-5198
```

In MetaEditor: open `MQL5\Experts\NEXUS_EA_v2.mq5` → **Compile** (F7).  
Confirm zero errors. The Logging fix needs a fresh `.ex5` before the next isolation/Tester run.

Smoke check after first Tester launch with `InpResetTradesLogOnInit=true`: Experts log should show either  
`NEXUS_trades.csv archiviato come …` or `copiato+cancellato …` — not a bare FileMove 5020 with no archive.

## 2. Density gate before any confirmatory

From repo root (example: FVG-style density ~2.5/mo, buy-share 0.4, 3.5 months):

```powershell
python scripts\confirmatory_density_gate.py --trades-per-month 2.5 --months 3.5 --min-n 30 --buy-share 0.4
```

- Exit **0** + `"verdict": "ALLOW"` → window length is eligible for confirmatory spend.  
- Exit **2** + `"REFUSE"` → extend the calendar window (see `months_needed_for_min_n_B`); do **not** launch confirmatory.

Worked example already locked: 2.5 × 3.5 × 0.4 ⇒ expected n_B ≈ 3.5 → **REFUSE** (~30 months needed at that rate).

## 3. Next isolation / confirmatory collect

Use the existing phase harness (`launch_*` then `collect_*`). Collect now fails closed if raw CSV closes ≠ certificate OPENED (`COLLECTED_ISOLATION_FAILED`). Window-filtered equality alone is **not** isolation proof.

```powershell
# After collect, inspect:
# reconciliation.isolation_ok must be true
# status must not be COLLECTED_ISOLATION_FAILED
```

## 4. Parked strategies

| Strategy | Status |
|---|---|
| LIQ_SWEEP | confirmatory `INSUFFICIENT_EVIDENCE` — parked |
| FVG_CONT | confirmatory `INSUFFICIENT_EVIDENCE` + CSV lesson — parked |

Resume a confirmatory only when **both** density gate ALLOW and a clean `isolation_ok` collect are in hand. Demo Tester only; no live/prop.
