# Handoff — Edge Book Mode V1 (review distinta)

Branch: `cursor/edge-book-mode-v1-b2b8`  
PR: https://github.com/starmarketkiller/MAX/pull/79  
Base: `cursor/nexus-desktop-agent-plan-v11-b2b8`

## Cosa verificare

1. `InpBookMode=EDGE_SHORTLIST` apre solo lo shortlist credit-safe.
2. In `FULL`, `FAILED`/`DEFECT_BLOCKED` non aprono (hard-deny), salvo Research Mode.
3. Il gate è su `stratName`, non sull’enum `STRAT_*`.
4. `NXS_CommonExposurePreflight` non ha perso gate; il book è additivo.
5. Nessun claim di edge validato / LIVE / promozione registry oltre
   `INSUFFICIENT_EVIDENCE` per FVG_CONT 7.34.

## Percorsi coperto

| Percorso | Gate |
|---|---|
| `NXS_CollectRaw` | `NXS_EdgeBook_Allows` prima dell’esecuzione |
| `NXS_Profile_Enabled` | `NXS_EdgeBook_Allows` |
| `NXS_OpenTrade` / `NXR_OpenTrade` | book gate esplicito |
| Data Collection | book gate prima di `SafeBuy`/`SafeSell` |
| `NXS_CommonExposurePreflight` | book se `NXS_StrategyKnown(stratName)` (SL reclaim, ecc.) |
| WebBridge | telemetria effettiva = toggle ∧ book |

## Prove eseguite (locale)

- MetaEditor compile: 0 errors (2 warning preesistenti)
- `python scripts/edge_freeze_check.py`
- `pytest server/tests/test_edge_freeze_check_v1.py server/tests/test_edge_book_matrix_v1.py`

## Fuori scope / non fatto

- Strategy Tester forward su GOLD (manuale)
- Promozione a SUPPORTED / LIVE
- Riscrivere logica di segnale
- Merge / deploy / C01–C20
