# Trading Research Ladder V1

One page. How trading structure advances without burning credits.

## Ladder (never skip)

```
0. Freeze defects / shortlist attention
1. Identity / isolation feasibility (code)
2. MT5 isolation diagnostic (long window, density)
3. Prereg habitat vs signal  →  exploratory on exposed (NOT_PROMOTABLE)
4. Density gate ALLOW (scripts/confirmatory_density_gate.py) BEFORE confirmatory
5. Confirmatory forward under SAME prereg — isolation_ok required (raw CSV == OPENED)
6. Only then: discuss SUPPORTED / live — still NO-GO until costs+power clear
```

## Live shortlist

`FVG_CONT`, `LIQ_SWEEP`, `ORDER_BLOCK`, `BREAKOUT_ACC`, `Z_SCORE_BREAKOUT`, `EMA_PULLBACK`

## Current position (2026-10-20)

| Strategy | Step | Status |
|---|---|---|
| LIQ_SWEEP | 5 confirmatory | `INSUFFICIENT_EVIDENCE` — **parked** |
| FVG_CONT | 5 confirmatory | `INSUFFICIENT_EVIDENCE` (n_B=3) + CSV contamination lesson — **parked** |
| Measure stack | 7.35 | Harness preflight + MQL5 reset fallback + density gate — **active** |

**Do not start another shortlist strategy confirmatory until density gate ALLOW and a clean isolation_ok collect.**

## Routing

1. Deterministic scripts / unittest / density gate  
2. Local PC-MT5 for Tester (after EA recompile for Logging.mqh) — see `server/research_scripts/phase7/phase7_35_isolation_measure_hardening/RUNBOOK_MEASURE_HARDENING_WINDOWS.md`  

3. Premium agent only for scientific adjudication / multi-file after local fail  

## Forbidden

Live/prop, promoting from exploratory, Python PF when exit ≠ MQL5, parallel agents on the same Tester, confirmatory windows with expected n_B &lt; min_n, treating window-filtered CSV match as isolation proof.
