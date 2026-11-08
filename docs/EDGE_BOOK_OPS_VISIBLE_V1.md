# Edge Book — operational EDGE_SHORTLIST on XMGlobal Tester

Date: 2026-11-08 (Europe/Rome)
Account: **345277936 / XMGlobal-MT5 10** (Strategy Tester UI left open)
Expert: `EdgeBookShortlist01\NEXUS_EA_v2`

## Goal

EA that **opens operations** under the real credit-safe book (`InpBookMode=1`, `InpResearchMode=false`), using the best shortlist the repo evidence supports.

## Result

| Field | Value |
|---|---|
| Mode | EDGE_SHORTLIST · Research OFF |
| Window | GOLD H4 2026.07.01–2026.10.19 |
| Trades | **41** (82 deals) |
| Net | **-987.99 USD** (final 9012.01) |
| Opens by stratName (CSV) | FVG_CONT 27, LIQ_SWEEP 11, EMA_PULLBACK 9, BREAKOUT_ACC 2 |

Terminal title still shows the linked demo account with Results populated.

## Honest edge status

This is **not** a validated production edge. The window is net-negative. Registry/Phase 7 remain NO-GO / CANDIDATE / FORWARD_REQUIRED. The EA now:

1. Runs the shortlist book for real (not Research bypass)
2. Opens trades on the linked Tester account
3. Hard-denies FAILED/DEFECT names outside Research

## Artifacts

- Report: `docs/evidence/nxs_edge_shortlist_ops_20260701_20261019.htm`
- Trades: `docs/evidence/NEXUS_trades_edge_shortlist_ops.csv`
- Ini: `MQL5/Profiles/NEXUS_EDGE_SHORTLIST_OPS_GOLD.ini`
