# NEXUS — INVENTARIO CANONICO DELLE STRATEGIE

> Consegna 1 del `NEXUS_CLOUD_STRATEGY_WORK_PACKAGE_v1` (§27.1).
> **Documento analitico: non modifica alcun comportamento.**

| | |
|---|---|
| Data verifica | 2026-07-26 |
| Commit | `4465873` |
| Branch | `claude/strategy-work-package-v1` |
| Baseline congelata (STEP 0) | `4465873` |
| Strategie nel registro canonico | 41 (37 live, 4 research-only) |

## Fonti usate e loro stato

| Fonte | Percorso | Stato |
|---|---|---|
| Registro canonico | `contracts/strategy-registry.json` | letto |
| Generatore del registro | `contracts/generate_registry.py` | letto |
| Router e dispatch | `MQL5/Experts/NEXUS_EA_v2.mq5` | letto |
| Trigger MQL5 | `MQL5/Include/NEXUS_v1/NXS_Strategies*.mqh` | letto |
| Profili per strategia | `MQL5/Include/NEXUS_v1/NXS_StrategyProfiles.mqh` | letto |
| Interruttori | `MQL5/Include/NEXUS_v1/NXS_Inputs.mqh` | letto |
| Telemetria canonica | `MQL5/Include/NEXUS_v1/NXS_WebBridge.mqh` | letto |
| Motore di ricerca Python | `server/backtest.py` (`STRATEGIES`) | letto |
| Registro frontend | `frontend/src/contracts/strategyRegistry.js` | letto |
| Sweep isolato per strategia | `knowledge/strategy_database.json` | letto |
| Audit master | `docs/NEXUS_MASTER_PROJECT.md` | letto |
| **Corpus semantic audit** | `NEXUS_CORPUS_SEMANTIC_AUDIT_PRELIMINARY_v1.md` | **`SOURCE_GAP` — non presente nel repository** |
| **PDF e materiali di corso** | — | **`SOURCE_GAP` — non presenti nel repository** |

Le due lacune sono rilevanti: §7 chiede il confronto fra codice e **fonte originale
della strategia**. Senza i materiali concettuali, per le strategie SMC/ICT il
confronto è possibile solo fra *codice MQL5* e *codice Python*, non contro la
definizione d'origine. Ogni giudizio di fedeltà concettuale in questa consegna è
quindi limitato — dove lo è, è marcato.

## Nota metodologica sui dati di sweep

`knowledge/strategy_database.json` — round `results/reports/sweep37 (file stats piu' recente per passata)`,
baseline `e6ce816 / branch baseline-post-infra-audit`.

> PF/WR/expectancy del round corrente: strategia ISOLATA, lotto fisso 0.01, DataCollectionMode - misurano il comportamento del trigger, non il P&L di portafoglio

**Solo 9 strategie su 37 hanno dati di sweep completati.**
Le altre 28 non hanno mai prodotto una passata isolata: per loro non
esiste alcuna misura di comportamento del trigger.

---

## Tabella di corrispondenza (§27.2)

Legenda colonne: **Sel** = indice di isolamento nel codice · **Reg** = indice nel
registro canonico · **MQL5** = interruttore · **Py** = funzione nel motore di
ricerca · **Prof** = profilo parametrico presente · **FE** = visibile nel frontend
· **Sweep** = trade della passata isolata.

| # | Strategia | Famiglia | Sel | Reg | MQL5 | Py | TF prof. | Prof | FE | Sweep |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `ADX_RSI` | MOMENTUM | 1 | 1 | `InpStrat_ADX_RSI`=T | `sig_adx_rsi` | D1 | sì | sì | 915 |
| 2 | `AMD_CONT` | AMD | 28 | **∅** | `InpUseStrat_AMD_Cont`=T | `sig_amd_cont` | — | **no** | sì | **∅** |
| 3 | `AMD_REVERSAL` | AMD | 24 | **∅** | `InpStrat_AMD_Reversal`=T | `sig_amd_reversal` | — | **no** | sì | **∅** |
| 4 | `BB_SQUEEZE` | VOLATILITY | 12 | 12 | `InpStrat_BB_SQUEEZE`=T | `sig_bb_squeeze` | D1 | sì | sì | **∅** |
| 5 | `BJORGUM` | LIQUIDITY | 6 | 6 | `InpStrat_BJORGUM`=T | `sig_bjorgum` | H4 | sì | sì | 397 |
| 6 | `BOLLINGER` | VOLATILITY | 2 | 2 | `InpStrat_BOLLINGER`=T | `sig_bollinger` ⚠️ | D1 | sì | sì | 144 |
| 7 | `BREAKOUT_ACC` | TREND | 9 | 9 | `InpStrat_BREAKOUT_ACC`=T | `sig_breakout_acc` | D1 | sì | sì | 216 |
| 8 | `DISP_REBAL` | SMC | 35 | **∅** | `InpUseStrat_DispRebal`=T | `sig_disp_rebal` | H4 | sì | sì | **∅** |
| 9 | `ELLIOTT` | PATTERN | 36 | 36 | `InpUseStrat_Elliott`=F | `—` | — | **no** | sì | **∅** |
| 10 | `EMA_PULLBACK` | TREND | 11 | 11 | `InpStrat_EMA_PULLBACK`=T | `sig_ema_pullback` | H4 | sì | sì | **∅** |
| 11 | `FVG_CONT` | SMC | 8 | 8 | `InpStrat_FVG_CONT`=T | `sig_fvg_cont_ext` | H4 | sì | sì | 251 |
| 12 | `FVG_MIT` | SMC | 19 | 19 | `InpStrat_FVG_Mit`=T | `sig_fvg_mit` | D1 | sì | sì | **∅** |
| 13 | `ICHIMOKU` | TREND | 13 | 13 | `InpStrat_ICHIMOKU`=T | `sig_ichimoku` | H4 | sì | sì | **∅** |
| 14 | `IFVG` | SMC | 18 | 18 | `InpStrat_IFVG`=T | `sig_ifvg` | H4 | sì | sì | **∅** |
| 15 | `JUDAS_SWING` | SESSION | 29 | **∅** | `InpUseStrat_Judas`=T | `sig_judas_swing` | — | **no** | sì | **∅** |
| 16 | `LDN_REVERSAL` | SESSION | 30 | **∅** | `InpUseStrat_LdnReversal`=T | `sig_ldn_reversal` | — | **no** | sì | **∅** |
| 17 | `LIQ_SWEEP` | LIQUIDITY | 7 | 7 | `InpStrat_LIQ_SWEEP`=T | `sig_liq_sweep_ext` | D1 | sì | sì | 292 |
| 18 | `LIQ_VOID` | SMC | 34 | **∅** | `InpUseStrat_LiqVoid`=T | `sig_fvg_cont` | H4 | sì | sì | **∅** |
| 19 | `LONDON_BO` | TREND | 10 | 10 | `InpStrat_LONDON_BO`=T | `sig_breakout` ⚠️ | D1 | sì | sì | **∅** |
| 20 | `MACD` | MOMENTUM | 3 | 3 | `InpStrat_MACD`=T | `sig_macd` | H4 | sì | sì | 1244 |
| 21 | `MALAYSIAN_SNR` | LIQUIDITY | 26 | **∅** | `InpStrat_MalaysianSNR`=T | `sig_malaysian_snr` | D1 | sì | sì | **∅** |
| 22 | `NY_REVERSAL` | SESSION | 31 | **∅** | `InpUseStrat_NYReversal`=T | `sig_ny_reversal` | — | **no** | sì | **∅** |
| 23 | `OB_MIT` | SMC | 20 | 20 | `InpStrat_OB_Mit`=T | `sig_ob_mit_ext` | D1 | sì | sì | **∅** |
| 24 | `ORDER_BLOCK` | SMC | 15 | 15 | `InpStrat_ORDER_BLOCK`=T | `sig_order_block_ext` | D1 | sì | sì | **∅** |
| 25 | `OTE_CONT` | SMC | 25 | **∅** | `InpStrat_OTE_Cont`=T | `sig_ote_cont` | D1 | sì | sì | **∅** |
| 26 | `PO3` | AMD | 33 | **∅** | `InpUseStrat_PO3`=T | `sig_po3` | — | **no** | sì | **∅** |
| 27 | `RANGE_FADE` | VOLATILITY | 37 | 37 | `InpUseStrat_RangeFade`=T | `sig_bollinger` ⚠️ | D1 | sì | sì | **∅** |
| 28 | `RSI_DIV` | MOMENTUM | 14 | 14 | `InpStrat_RSI_DIV`=T | `sig_rsi_div` | H1 | sì | sì | **∅** |
| 29 | `SAR` | MOMENTUM | 4 | 4 | `InpStrat_SAR`=T | `sig_sar` | H4 | sì | sì | 261 |
| 30 | `SH_BMS_RTO` | LIQUIDITY | 21 | 21 | `InpStrat_SH_BMS_RTO`=T | `sig_ob_mit` ⚠️ | D1 | sì | sì | **∅** |
| 31 | `SILVER_BULLET` | SESSION | 23 | **∅** | `InpStrat_SilverBullet`=T | `sig_silver_bullet` | — | **no** | sì | **∅** |
| 32 | `SMS_BMS_RTO` | LIQUIDITY | 22 | **∅** | `InpStrat_SMS_BMS_RTO`=T | `sig_ob_mit` ⚠️ | D1 | sì | sì | **∅** |
| 33 | `STRUCT_REACT` | LIQUIDITY | 16 | 16 | `InpUseStructReact`=T | `sig_struct_react` | H1 | sì | sì | **∅** |
| 34 | `THREE_BAR_DELIVERY_BREAK` | LIQUIDITY | 27 | **∅** | `InpUseStrat_CISD`=T | `sig_cisd` (alias `CISD`) | H4 | sì | sì | **∅** |
| 35 | `TSI` | MOMENTUM | 5 | 5 | `InpStrat_TSI`=T | `sig_tsi` | D1 | sì | sì | 839 |
| 36 | `TURTLE_SOUP` | LIQUIDITY | 17 | 17 | `InpStrat_TurtleSoup`=T | `sig_turtle_soup` | H1 | sì | sì | **∅** |
| 37 | `WEEKLY_EXP` | SESSION | 32 | **∅** | `InpUseStrat_WeeklyExp`=T | `sig_breakout` ⚠️ | D1 | sì | sì | **∅** |

### Research-only (non live)

`SCALP_BB_FADE`, `SCALP_EMA`, `SCALP_RANGE_BRK`, `SCALP_RSI_SNAP` — presenti nel motore Python e nel
frontend, assenti dall'EA. Corretto per costruzione: sono strumenti di ricerca.

---

## Risultati della passata isolata (le 9 con dati)

Lotto fisso 0.01, DataCollectionMode, strategia isolata. Misurano il
**comportamento del trigger**, non il P&L di portafoglio.

| Strategia | Trade | Win rate | PF | Expectancy R |
|---|---|---|---|---|
| `ADX_RSI` | 915 | 48.55% | 0.82 | -0.028 |
| `BJORGUM` | 397 | 49.02% | 0.68 | -0.071 |
| `BOLLINGER` | 144 | 55.14% | 0.79 | -0.033 |
| `BREAKOUT_ACC` | 216 | 47.59% | 0.85 | -0.024 |
| `FVG_CONT` | 251 | 45.85% | 0.96 | -0.013 |
| `LIQ_SWEEP` | 292 | 50.0% | 1.04 | 0.004 |
| `MACD` | 1244 | 55.95% | 0.79 | -0.038 |
| `SAR` | 261 | 39.74% | 0.6 | -0.09 |
| `TSI` | 839 | 54.86% | 0.76 | -0.028 |

Nessuna delle nove ha expectancy positiva significativa. Il campione più ampio
(ADX_RSI, 915 trade) dà PF 0.82 ed expectancy −0.028R.

---

## Informazioni mancanti (§27.6)

1. `SOURCE_GAP` — `NEXUS_CORPUS_SEMANTIC_AUDIT_PRELIMINARY_v1.md` assente.
2. `SOURCE_GAP` — PDF e materiali di corso assenti dal repository: per le
   strategie SMC/ICT manca la definizione d'origine contro cui verificare la
   fedeltà concettuale.
3. `SOURCE_GAP` — 28 strategie su 37 non hanno dati di sweep isolato.
4. `SOURCE_GAP` — nessun risultato out-of-sample congelato: non risulta una data
   di congelamento (§16) per alcuna strategia.
5. `SOURCE_GAP` — non risulta un conteggio dei tentativi effettuati (§16): quante
   varianti, TF, simboli e combinazioni parametriche sono state provate prima di
   arrivare alla configurazione attuale.
