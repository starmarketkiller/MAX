# Edge Book Mode V1

Date: 2026-11-08.

## What this is

`InpBookMode = NXS_BOOK_EDGE_SHORTLIST` is a **credit-safe trading book** for
`NEXUS_EA_v2`. It limits new opens to the research shortlist and hard-denies
scientifically `FAILED` / `DEFECT_BLOCKED` strategies outside Research Mode.

It is **not** a validated production edge. Registry and Phase 7 still say
Production = **NO-GO**. Remediation ≠ edge. Confirmatory forwards remain
`INSUFFICIENT_EVIDENCE` / `FORWARD_REQUIRED`.

## Shortlist (attention + opens)

`FVG_CONT`, `LIQ_SWEEP`, `ORDER_BLOCK`, `BREAKOUT_ACC`, `Z_SCORE_BREAKOUT`,
`EMA_PULLBACK`

Source: `docs/EDGE_CREDIT_SAFE_OPERATING_LOOP_V1.md`.

## Hard deny (even in `NXS_BOOK_FULL`)

`MACD`, `RSI_DIV`, `CRT`, `BB_SQUEEZE`, `TSI`, `SH_BMS_RTO`, `SH_BMS_RTO_V2`,
`SILVER_BULLET`

Research Mode isolation may still open these for measurement.

## Wiring

| Piece | Role |
|---|---|
| `InpBookMode` | Tester-visible book switch (default `FULL`) |
| `NXS_EdgeBook.mqh` | Allow / deny by `stratName` |
| `NXS_OpenTrade` / `NXR_OpenTrade` | Gate before exposure creation |
| `NXS_CommonExposurePreflight` | Unchanged; still required |
| `scripts/edge_freeze_check.py` | Registry ↔ EA default alignment |

## How to use

1. Load `MQL5/Profiles/NEXUS_EDGE_SHORTLIST_GOLD.set` (or set `InpBookMode=1`).
2. Keep `InpUseStrategyProfiles=true`, Institutional Core off, Data Collection off.
3. Demo / Tester only until a registry status becomes live-supported.
4. Run `python scripts/edge_freeze_check.py` after any default / registry change.

## Explicit non-claims

- No new strategy logic.
- No claim that Phase 7 PF figures survive live costs / regime shift.
- No LIVE arming (`InpLiveTradingAuthorized` stays operator-controlled).
- No second queue, second orchestrator, or C01–C20 changes.
