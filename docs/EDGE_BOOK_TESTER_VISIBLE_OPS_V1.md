# Edge Book — Strategy Tester visible operations (XMGlobal)

Date: 2026-11-08 (Europe/Rome)  
Account: **345277936** on **XMGlobal-MT5 10** (demo, Strategy Tester)  
Expert: `Experts\EdgeBookShortlist01\NEXUS_EA_v2.ex5`

## Result (user-visible)

| Metric | Value |
|---|---|
| Symbol / TF | GOLD H4 |
| Window | 2026.07.01 → 2026.10.19 |
| Total trades | **8** |
| Deals | **16** |
| Net profit | **+46.07 USD** |
| Final balance | 10046.07 |
| CERT | `PASS` generated=264 blocked=256 opened=8 |

Report (left open with `ShutdownTerminal=0`):  
`...\Terminal\7F8EC41F...\nxs_edge_book_fvg_visible_20260701_20261019.htm`

Trade log (Common Files): `NEXUS_trades.csv` — also copied to `docs/evidence/`.

## Root cause of earlier 0-trade runs

`InpUseMaxTotalDD=true` reconciled the Tester’s synthetic initial `DEAL_TYPE_BALANCE` (deposit 10000) as `UNVERIFIED_BALANCE_FLOW_TICKET_1`, set `g_maxDDRecoveryRequired`, and blocked every new entry (`PROTECTIONS` on all decision ticks).

Fix in `NXS_Protections.mqh`: Strategy Tester / Optimization seed deposits advance the capital-flow cursor without locking. Live/demo terminals unchanged.

## Config

`MQL5/Profiles/NEXUS_EDGE_BOOK_FVG_VISIBLE_GOLD.ini`  
Research Mode + selector `8` (FVG_CONT) on the Edge Book build — visibility / operability proof, **not** a production edge claim.
