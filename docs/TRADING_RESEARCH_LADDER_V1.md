# Trading Research Ladder V1

One page. How trading structure advances without burning credits.

## Ladder (never skip)

```
0. Freeze defects / shortlist attention
1. Identity / isolation feasibility (code)
2. MT5 isolation diagnostic (long window, density)
3. Prereg habitat vs signal  →  exploratory on exposed (NOT_PROMOTABLE)
4. Confirmatory forward under SAME prereg (after diagnostic end date)
5. Only then: discuss SUPPORTED / live — still NO-GO until costs+power clear
```

## EA book (credit-safe, not validated edge)

`InpBookMode=NXS_BOOK_EDGE_SHORTLIST` enforces the shortlist below in the live
EA (`docs/EDGE_BOOK_MODE_V1.md`). Remediation / candidate status is not a
production GO.

## Live shortlist

`FVG_CONT`, `LIQ_SWEEP`, `ORDER_BLOCK`, `BREAKOUT_ACC`, `Z_SCORE_BREAKOUT`, `EMA_PULLBACK`

## Current position (2026-10-20)

| Strategy | Step | Status |
|---|---|---|
| LIQ_SWEEP | 4 confirmatory | `INSUFFICIENT_EVIDENCE` (n=0, short window) — parked |
| FVG_CONT | 4 confirmatory | 7.31–7.33 done → **7.34** `INSUFFICIENT_EVIDENCE` (OPENED=8, not live-ready) |

## Routing

1. Deterministic scripts / unittest  
2. Local PC-MT5 for Tester  
3. Premium agent only for scientific adjudication / multi-file after local fail  

## Forbidden

Live/prop, promoting from exploratory, Python PF when exit ≠ MQL5, parallel agents on the same Tester, 3-week confirmatory as if it could hit min_n=30.
