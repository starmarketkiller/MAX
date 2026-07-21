# Strategy Registry Reconciliation

PR6 replaces the independent backend, frontend, and EA strategy lists with the
canonical contract in `contracts/strategy-registry.json`.

## Reconciled inventory

- 41 canonical records.
- 37 live EA strategies.
- `CISD` is retained as the research/runtime alias of the canonical
  `THREE_BAR_DELIVERY_BREAK` record, rather than counted twice.
- 40 research/backtest implementations.
- `ELLIOTT` is explicitly marked as not implemented in research.
- `SCALP_EMA`, `SCALP_BB_FADE`, `SCALP_RSI_SNAP`, and `SCALP_RANGE_BRK` are
  explicitly research-only.

## Research parity exceptions

The Python research engine is not a line-for-line implementation of the EA.
All implemented strategies are therefore classified as approximate unless the
current engine routes them through a proxy:

| Strategy | Research proxy |
| --- | --- |
| `LONDON_BO` | `BREAKOUT_ACC` |
| `RANGE_FADE` | `BOLLINGER` |
| `WEEKLY_EXP` | `BREAKOUT_ACC` |
| `LIQ_VOID` | `FVG_CONT` |
| `SH_BMS_RTO` | `OB_MIT` |
| `SMS_BMS_RTO` | `OB_MIT` |

## Enforcement

The backend loads and validates the contract at startup. Unknown identifiers
now fail validation instead of being silently removed or replaced. The
generator writes the frontend and MQL adapters, and automated tests compare
both adapters against the source contract to prevent drift.

EA runtime names ending in `_NXR` and the `CISD` alias are normalized to their
canonical strategy identifier before validation.
