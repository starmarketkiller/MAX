# 11. Backtest Capability Matrix

## Classification

The Python engine in `server/backtest.py` is a **RESEARCH_SIMULATOR**.

It is not currently a digital twin or live-validation source of truth.

## Evidence

The code explicitly describes strategy logic as Python re-implementations rather than 1:1 MQL5 copies.

## Capability matrix

| Capability | Live EA | Python research engine | Parity |
|---|---:|---:|---|
| Individual strategy signals | Yes | Yes, partly proxy-based | Approximate |
| InstitutionalCore aggregation | Yes | No | Missing |
| Strategy Chain | Yes | No | Missing |
| Multi-position portfolio | Yes | No; single global position | Missing |
| Grid Recovery | Yes | No | Missing |
| Pyramiding | Yes | No | Missing |
| Split management | Yes | Limited/general exits | Missing/approximate |
| Dynamic sizing by broker contract | Yes | No | Missing |
| Margin/leverage | Broker-aware | No | Missing |
| Spread/commission/slippage/swap | Live broker | Partial (31/07): optional `spread_price` (converted to R per-trade) and `commission_r` (flat R cost), both default 0.0 (unchanged behavior unless set); no slippage/swap model | Approximate |
| Full protection pipeline | Yes/partial wiring | No | Missing |
| News and correlation gates | Present live | No | Missing |
| Floating drawdown | Live | No; closed-equity only | Missing |
| Intrabar order sequencing | Broker/ticks | SL-first bar assumption | Approximate |
| True HTF filter | Multiple live systems | Same-TF SMA approximation | Approximate |
| End-of-data liquidation | N/A live | Open position may remain | Defect |
| Unknown strategy handling | Registry-dependent | Silent fallback to ADX_RSI | Defect |
| Synthetic data | N/A | Allowed fallback | Research only |

## Metric caveats

- reported “Sharpe” is based on trade R mean/std and is closer to SQN-like behavior than time-series Sharpe;
- profit factor can be null with no losses;
- constant positive-R series can produce zero due to zero standard deviation;
- drawdown ignores open-position floating loss;
- PnL is modeled from R × risk money, without broker contract details;
- MAE/MFE (`mae_r`/`mfe_r` per trade, `avg_loss_mae_r`/`near_miss_loss_pct`
  in the summary, added 31/07) are tracked from bar high/low while a
  position is open, on the ORIGINAL risk distance (not a moved BE/trailing
  stop) — the bar that triggers the stop is included in the MAE calculation
  for that trade, which can make MAE slightly exceed 1R (bar-based
  approximation, not intrabar-sequenced).

## Strategy parity caveats

Several research strategies map to proxies. Additional `SCALP_*` strategies exist only in Python. Elliott and live strategy coverage are not fully aligned.

## Required UI language

The frontend must label results as:

- `Research simulation`;
- data source (`Yahoo`, `Stooq`, `Synthetic`);
- parity level;
- ignored live features;
- exact engine version and configuration hash.

## Evolution path

1. Correct defects: unknown strategy error, force end liquidation, explicit data provenance.
2. Add realistic cost and broker model.
3. Add event-driven multi-position simulation.
4. Share strategy contracts and fixtures with EA.
5. Build targeted parity tests for selected strategies.
6. Only then introduce a separately named `Broker-Aware Validation Engine`.
