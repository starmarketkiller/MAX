# Strategy Registry Reconciliation

PR6 replaces the independent backend, frontend, and EA strategy lists with the
canonical contract in `contracts/strategy-registry.json`.

## Reconciled inventory

- 42 canonical records.
- 38 live EA strategies.
- 37 numbered selector entries plus `THREE_BAR_DELIVERY_BREAK`, which is live
  but not selectable through the legacy numeric selector.
- 40 research/backtest implementations.
- `ELLIOTT` and `THREE_BAR_DELIVERY_BREAK` are explicitly marked as not
  implemented in research.
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
frontend and MQL adapters expose the canonical live inventory, and automated
tests compare both adapters against the source contract to prevent drift.

EA runtime names ending in `_NXR` are normalized to their canonical strategy
identifier before validation.
