# FVG_CONT — next powered confirmatory

Date: 2026-11-08 (Europe/Rome)

## Ranking

FVG_CONT = STRONGEST_CANDIDATE. Zero VALIDATED. No LIVE GO.

## Power math

Density ~2.5 trades/month (Phase 7.34 runbook).  
Phase 7.34 OPENED=8 on 2026.07.01–2026.10.19.  
**min_n=30 ⇒ ~12 months clean forward** after the exploratory freeze.  
Do **not** reuse Phase 7.32 diagnostic (2023.10–2026.06) as confirmatory.

## Next allowed MT5

1. **Interim (launched):** selector=8, Research ON, 2026.07.01–2026.11.07 — expect still INSUFFICIENT.
2. **Powered gate:** accumulate from 2026.10.20 until OPENED≥30, then `analyze_confirmatory_forward.py`.

## Non-goals

No soup book for this claim. No EMA_PULLBACK re-enable. No registry LIVE promotion.
## Interim extension result (2026-11-08)

Window 2026.07.01-2026.11.07, selector=8, Research ON, account 345277936.
CERT opened=**11**, net **-81.96**, balance 9918.04.
Still **INSUFFICIENT** vs min_n=30. Does not overturn FVG as strongest candidate; does not support LIVE.
Artifact: docs/evidence/nxs_edge_fvg_conf_ext_20260701_20261107.htm

## Interim side split (arm B observational)

Same 11 trades from the HTML deals table (`interim_side_split_v1.json`):

| Arm | n | Money | mean R | sum R |
|---|---|---|---|---|
| A all | 11 | −82.45 | −0.04 | −0.46 |
| B BUY | 3 | **+76.44** | +0.67 | +2.00 |
| SELL drag | 8 | −158.89 | −0.31 | −2.46 |

Decision remains **INSUFFICIENT_EVIDENCE** (`n_B=3 << 30`). Directionally matches Phase 7.33 BUY-heavy habitat; SELL is the interim drag.

## BUY-only ops filter

`InpFvgContBuyOnly` (default **false**) drops FVG SELL after H1-aligned bear gap — same pattern as `InpBollingerBuyOnly`. Used only for Research-OFF ops hunts via `NEXUS_EDGE_FVG_BUY_ONLY_OPS_GOLD.ini`. Does **not** change confirmatory A recipe. Not LIVE GO.

### BUY-only ops result (2026-11-09 Europe/Rome)

Window 2026.07.01–2026.11.07, selector=8, Research OFF, `InpFvgContBuyOnly=true`, account 345277936.

| Metric | Value |
|---|---|
| Opens | **6 BUY / 0 SELL** |
| Net | **+70.15** |
| Wins | 3/6 |

Filter works (no SELL). Positive but still underpowered vs min_n=30. Not LIVE GO.
Artifacts: `docs/evidence/nxs_edge_fvg_buy_only_ops_20260701_20261107.htm`, `buy_only_ops_result_v1.json`.
