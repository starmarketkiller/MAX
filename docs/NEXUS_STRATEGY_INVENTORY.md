# NEXUS — INVENTARIO CANONICO DELLE STRATEGIE

> Consegna 1 del `NEXUS_CLOUD_STRATEGY_WORK_PACKAGE_v1` (§27.1, §27.2, §27.6),
> aggiornato dalla Fase A.
> **Documento generato** da `contracts/gen_strategy_docs.py` a partire da
> `contracts/strategy-registry.json`. Non modificarlo a mano: rigeneralo.

| | |
|---|---|
| Strategie nel registro | 41 (37 live, 4 research-only) |
| Round di sweep corrente | `sweep37-baseline-e6ce816` |
| Misurate sul round corrente | 8 |
| Con dato surrogato | 1 |
| Mai misurate | 28 |
| Collisioni di implementazione | 2 |
| Conflitti fra stato dichiarato e codice | 2 |

## Fonti

- `knowledge/strategy_database.json`
- `MQL5/Include/NEXUS_v1/NXS_StrategyProfiles.mqh (NXS_Profile_TF)`
- `MQL5 via contracts/extract_selectors.py (selector_index, interruttori)`
- `server/backtest.py (STRATEGIES)`

`selector_index` e gli interruttori NON sono piu' trascritti: sono derivati dal
codice MQL5 da `contracts/extract_selectors.py`, e `contracts/validate_registry.py`
fallisce se registro e codice divergono.

### Cosa NON e' verificabile da qui

`SOURCE_GAP` — `NEXUS_CORPUS_SEMANTIC_AUDIT_PRELIMINARY_v1.md`, i PDF e i
materiali di corso non sono presenti nel repository. Per le strategie SMC/ICT
manca quindi la definizione d'origine contro cui verificare la fedelta'
concettuale (§7): il confronto possibile e' solo MQL5 ↔ Python.

---

## Matrice di corrispondenza

Legenda: **Sel** indice di isolamento · **TF** timeframe dichiarato
(`—` = non dichiarato, non "qualunque") · **Py** funzione del motore research ·
**Ev** stato dell'evidenza · **Coll** condivide l'implementazione research.

| # | Strategia | Famiglia | Sel | Interruttore MQL5 | TF | Py | Ev | Coll |
|---|---|---|---|---|---|---|---|---|
| 1 | `ADX_RSI` | MOMENTUM | 1 | `InpStrat_ADX_RSI`=T | D1 | `sig_adx_rsi` | **MEASURED** | — |
| 2 | `AMD_CONT` | AMD | 28 | `InpUseStrat_AMD_Cont`=T | — | `sig_amd_cont` | UNKNOWN | — |
| 3 | `AMD_REVERSAL` | AMD | 24 | `InpStrat_AMD_Reversal`=T | — | `sig_amd_reversal` | UNKNOWN | — |
| 4 | `BB_SQUEEZE` | VOLATILITY | 12 | `InpStrat_BB_SQUEEZE`=T | D1 | `sig_bb_squeeze` | UNKNOWN | — |
| 5 | `BJORGUM` | LIQUIDITY | 6 | `InpStrat_BJORGUM`=T | H4 | `sig_bjorgum` | **MEASURED** | — |
| 6 | `BOLLINGER` | VOLATILITY | 2 | `InpStrat_BOLLINGER`=T | D1 | `sig_bollinger` | **MEASURED** | RANGE_FADE |
| 7 | `BREAKOUT_ACC` | TREND | 9 | `InpStrat_BREAKOUT_ACC`=T | D1 | `sig_breakout_acc` | **MEASURED** | — |
| 8 | `DISP_REBAL` | SMC | 35 | `InpUseStrat_DispRebal`=T | H4 | `sig_disp_rebal` | UNKNOWN | — |
| 9 | `ELLIOTT` | PATTERN | 36 | `InpUseStrat_Elliott`=F | — | `—` | UNKNOWN | — |
| 10 | `EMA_PULLBACK` | TREND | 11 | `InpStrat_EMA_PULLBACK`=T | H4 | `sig_ema_pullback` | UNKNOWN | — |
| 11 | `FVG_CONT` | SMC | 8 | `InpStrat_FVG_CONT`=T | H4 | `sig_fvg_cont_ext` | **MEASURED** | — |
| 12 | `FVG_MIT` | SMC | 19 | `InpStrat_FVG_Mit`=T | D1 | `sig_fvg_mit` | UNKNOWN | — |
| 13 | `ICHIMOKU` | TREND | 13 | `InpStrat_ICHIMOKU`=T | H4 | `sig_ichimoku` | UNKNOWN | — |
| 14 | `IFVG` | SMC | 18 | `InpStrat_IFVG`=T | H4 | `sig_ifvg` | UNKNOWN | — |
| 15 | `JUDAS_SWING` | SESSION | 29 | `InpUseStrat_Judas`=T | — | `sig_judas_swing` | UNKNOWN | — |
| 16 | `LDN_REVERSAL` | SESSION | 30 | `InpUseStrat_LdnReversal`=T | — | `sig_ldn_reversal` | UNKNOWN | — |
| 17 | `LIQ_SWEEP` | LIQUIDITY | 7 | `InpStrat_LIQ_SWEEP`=T | D1 | `sig_liq_sweep_ext` | **MEASURED** | — |
| 18 | `LIQ_VOID` | SMC | 34 | `InpUseStrat_LiqVoid`=T | H4 | `sig_fvg_cont` | UNKNOWN | — |
| 19 | `LONDON_BO` | TREND | 10 | `InpStrat_LONDON_BO`=T | D1 | `sig_london_bo` | UNKNOWN | — |
| 20 | `MACD` | MOMENTUM | 3 | `InpStrat_MACD`=T | H4 | `sig_macd` | **MEASURED** | — |
| 21 | `MALAYSIAN_SNR` | LIQUIDITY | 26 | `InpStrat_MalaysianSNR`=T | D1 | `sig_malaysian_snr` | UNKNOWN | — |
| 22 | `NY_REVERSAL` | SESSION | 31 | `InpUseStrat_NYReversal`=T | — | `sig_ny_reversal` | UNKNOWN | — |
| 23 | `OB_MIT` | SMC | 20 | `InpStrat_OB_Mit`=T | D1 | `sig_ob_mit_ext` | UNKNOWN | — |
| 24 | `ORDER_BLOCK` | SMC | 15 | `InpStrat_ORDER_BLOCK`=T | D1 | `sig_order_block_ext` | UNKNOWN | — |
| 25 | `OTE_CONT` | SMC | 25 | `InpStrat_OTE_Cont`=T | D1 | `sig_ote_cont` | UNKNOWN | — |
| 26 | `PO3` | AMD | 33 | `InpUseStrat_PO3`=T | — | `sig_po3` | UNKNOWN | — |
| 27 | `RANGE_FADE` | VOLATILITY | 37 | `InpUseStrat_RangeFade`=T | D1 | `sig_bollinger` | UNKNOWN | BOLLINGER |
| 28 | `RSI_DIV` | MOMENTUM | 14 | `InpStrat_RSI_DIV`=T | H1 | `sig_rsi_div` | UNKNOWN | — |
| 29 | `SAR` | MOMENTUM | 4 | `InpStrat_SAR`=T | H4 | `sig_sar` | ⚠️ SURROGATE | — |
| 30 | `SH_BMS_RTO` | LIQUIDITY | 21 | `InpStrat_SH_BMS_RTO`=T | D1 | `sig_sh_bms_rto` | UNKNOWN | — |
| 31 | `SILVER_BULLET` | SESSION | 23 | `InpStrat_SilverBullet`=T | — | `sig_silver_bullet` | UNKNOWN | — |
| 32 | `SMS_BMS_RTO` | LIQUIDITY | 22 | `InpStrat_SMS_BMS_RTO`=T | D1 | `sig_sms_bms_rto` | UNKNOWN | — |
| 33 | `STRUCT_REACT` | LIQUIDITY | 16 | `InpUseStructReact`=T | H1 | `sig_struct_react` | UNKNOWN | — |
| 34 | `THREE_BAR_DELIVERY_BREAK` | LIQUIDITY | 27 | `InpUseStrat_CISD`=T | H4 | `sig_cisd` | UNKNOWN | — |
| 35 | `TSI` | MOMENTUM | 5 | `InpStrat_TSI`=T | D1 | `sig_tsi` | **MEASURED** | — |
| 36 | `TURTLE_SOUP` | LIQUIDITY | 17 | `InpStrat_TurtleSoup`=T | H1 | `sig_turtle_soup` | UNKNOWN | — |
| 37 | `WEEKLY_EXP` | SESSION | 32 | `InpUseStrat_WeeklyExp`=T | D1 | `sig_weekly_exp` | UNKNOWN | — |

### Research-only (non live)

`SCALP_BB_FADE`, `SCALP_EMA`, `SCALP_RANGE_BRK`, `SCALP_RSI_SNAP` — presenti nel motore
Python e nel frontend, assenti dall'EA. Corretto per costruzione.

---

## Conflitti fra stato dichiarato e codice

Il registro descrive uno stato, il codice ne applica un altro. Registrati, non
risolti: la riconciliazione e' una decisione del proprietario.

| Strategia | Default nel codice | Stato nel registro | Disattivabile dalla dashboard |
|---|---|---|---|
| `DISP_REBAL` | ENABLED | DISABLED | BLOCKED |
| `ELLIOTT` | DISABLED | ACTIVE | ALLOWED |

## Collisioni di implementazione

Strategie che condividono la stessa funzione del motore research: in ricerca
producono lo stesso segnale per costruzione. Gli id restano distinti; finche' la
collisione e' `UNRESOLVED`, il gruppo vale **un solo generatore di segnali**.

| Gruppo | Funzione condivisa | Rappresentante | Classificazione |
|---|---|---|---|
| BOLLINGER ≡ RANGE_FADE | `sig_bollinger` | `BOLLINGER` | PENDING_OWNER_REVIEW |

## Proxy dichiarati

`proxy_for` e' un'asserzione scritta a mano nel generatore. Accanto, il fatto:
la funzione research usata coincide con quella del bersaglio dichiarato?

| Strategia | Proxy dichiarato di | Funzione usata | Coincide col bersaglio |
|---|---|---|---|
| `LIQ_VOID` | `FVG_CONT` | `sig_fvg_cont` | **no** |
| `LONDON_BO` | `BREAKOUT_ACC` | `sig_london_bo` | **no** |
| `RANGE_FADE` | `BOLLINGER` | `sig_bollinger` | sì |
| `SH_BMS_RTO` | `OB_MIT` | `sig_sh_bms_rto` | **no** |
| `SMS_BMS_RTO` | `OB_MIT` | `sig_sms_bms_rto` | **no** |
| `WEEKLY_EXP` | `BREAKOUT_ACC` | `sig_weekly_exp` | **no** |

## Collegamenti

`docs/NEXUS_STRATEGY_MISMATCH_REPORT.md` ·
`docs/NEXUS_STRATEGY_PRIORITY_MATRIX.md` ·
`docs/NEXUS_STRATEGY_EVIDENCE_PROVENANCE.md`
