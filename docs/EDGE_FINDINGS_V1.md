# Edge findings V1 (2026-11-08 Europe/Rome)

## Verdict

**No validated production edge exists.** Closest signal: **FVG_CONT** — only shortlist name that is both Phase-7 sample-ready and net-positive in the latest XMGlobal book decomposition.

## Evidence ranking

| Rank | Strategy | Scientific status | Latest quantitative signal | Verdict |
|---|---|---|---|---|
| 1 | FVG_CONT | CANDIDATE; fwd INSUFFICIENT_EVIDENCE; defect REMEDIATED | Phase 7.32: n=82, mean R≈0.30, SAMPLE_READY_FOR_EDGE_PREREG. Phase 7.34 confirmatory: n=8, mean R≈0.25, INSUFFICIENT. Ops shortlist 2026.07–10: **+139 / +3.64R on 27 closes** | STRONGEST_CANDIDATE |
| 2 | BREAKOUT_ACC | FORWARD_REQUIRED; CI includes 0 | Ops: +54 on n=2 | WEAK / underpowered |
| 3 | LIQ_SWEEP | CANDIDATE; fwd NEGATIVE_INSUFFICIENT | Phase 7.30 OPENED=0. Ops: −128 on 11 | WEAK / regime-conditional |
| 4 | ORDER_BLOCK | FORWARD_REQUIRED | Ops: 0 opens | WEAK |
| 5 | Z_SCORE_BREAKOUT | CANDIDATE | Ops: 0 opens | WEAK |
| 6 | EMA_PULLBACK | CANDIDATE (registry) | Ops: **−1007 on 9 closes** | ANTI-EDGE this window — default OFF |

FAILED / DEFECT_BLOCKED: MACD, RSI_DIV, CRT, BB_SQUEEZE, TSI, SH_BMS_RTO*, SILVER_BULLET.

## What “found” means

- Found = best remaining hypothesis with positive diagnostic expectancy, **not** LIVE GO.
- Full shortlist book lost **−988 USD** because EMA_PULLBACK (+ LIQ_SWEEP) ate FVG gains.
- Next step: FVG_CONT only, Research OFF, BookMode SHORTLIST, powered forward sample — not the 6-name soup.

## Sources

- `contracts/edge-validation-registry.json`
- `docs/EDGE_CREDIT_SAFE_OPERATING_LOOP_V1.md`
- `server/research_scripts/phase7/phase7_32_fvg_cont_isolation_diagnostic/diagnostic_result_v1.json`
- `server/research_scripts/phase7/phase7_34_fvg_cont_confirmatory/confirmatory_forward_result_v1.json`
- `docs/evidence/NEXUS_trades_edge_shortlist_ops.csv`

## Confirmation (FVG-only ops, Research OFF)

Same window GOLD H4 2026.07.01–2026.10.19, account 345277936:

| Config | Trades | Net |
|---|---|---|
| EDGE_SHORTLIST soup (6 names) | 41 | **-987.99** |
| FVG_CONT only (selector=8, BookMode=1, Research=false) | **20** | **+76.73** |

Artifacts: docs/evidence/nxs_edge_fvg_only_ops_20260701_20261019.htm, MQL5/Profiles/NEXUS_EDGE_FVG_ONLY_OPS_GOLD.ini.

Still not LIVE GO (n=20 underpowered vs Power Gate). Directionally: isolate FVG_CONT; keep EMA_PULLBACK off.

## Ranking concurrence

Independent ranking agrees: FVG_CONT strongest; no VALIDATED; next = powered confirmatory selector=8 OPENED>=30. See EDGE_FVG_POWERED_FORWARD_NEXT_V1.md.
