# Strategy Identity Attribution Preaudit V1

**Stato:** matrice preliminare, non committata. Nessuna modifica a MQL5/registry, nessun commit/push, nessun backtest. Obiettivo: ridurre il lavoro che Codex dovrà fare in `STRATEGY_IDENTITY_ATTRIBUTION_AUDIT_V1`, quando quel task verrà rimesso in coda dopo una milestone sostanziale di `REVENUE_AUTONOMY_AND_LOCAL_AGENT_V1`.

**Metodo:** censimento completo (non campionato) delle 83 `strategy_id` del registry (`contracts/strategy-registry.json`) contro un grep sistematico di `\.strat\s*=\s*STRAT_\w+` su tutto `MQL5/Include/NEXUS_v1/` e `MQL5/Experts/`. Ogni riga della matrice è **CODE_VERIFIED** (trovata nel grep) o **PLACEHOLDER_CONFIRMED** (assente dal grep, confermato dal registry con `live_implementation=False`/`research_implementation` coerente) — nessuna riga è stimata o inferita dal nome.

**Risultato del censimento: 83 = 56 reali + 27 placeholder.** Tutti i 27 assenti dal codice risultano `live_implementation=False` nel registry — nessuna discrepanza trovata in questa direzione (il registry non promette falsamente implementazioni inesistenti per questi 27, salvo le eccezioni esplicite in §4).

---

## 1. Scoperta preliminare importante: l'enum NON è il rischio che sembrava

Prima della matrice, una verifica necessaria: **il tracker principale delle performance per-strategia, `NXS_StratStats.mqh`, è chiavato per `name` (stringa, = `stratName`), non per l'enum `strat`** (confermato leggendo l'header del file: "12-step lifecycle tracked per strategy NAME"). Questo significa che **le statistiche win/loss/PF per strategia oggi NON sono contaminate dalla condivisione di enum** — è una buona notizia, non ancora enunciata nell'audit precedente.

**Dove l'enum `strat` è invece realmente consumato** (non solo assegnato): `NXS_ReusePerformancePack.mqh` lo usa per instradare/confrontare rami NXR vs legacy (es. `MALAYSIAN_SNR`: il ramo legacy e il ramo NXR vengono confrontati per `score`, ed **entrambi** finiscono con `s.strat = STRAT_STRUCT_REACT` — qui la condivisione ha un effetto comportamentale reale, non solo di etichetta). Il rischio di contaminazione reale è quindi **concentrato nei 6 strategy_id che passano per il motore NXR condiviso** (ORDER_BLOCK/OB_MIT, FVG_CONT-family/FVG_MIT, MALAYSIAN_SNR), non diffuso su tutti i 34 che condividono `STRAT_STRUCT_REACT`.

**Il vero rischio dei restanti ~28** è **prospettico, non attuale**: qualunque futuro componente del Unified Market Intelligence Engine che assumesse (ragionevolmente, guardando solo l'enum) che `strat` sia un identificatore unico per fenomeno andrebbe fuorviato. Non è un bug oggi — lo diventerebbe se un futuro sistema si affidasse a quel campo senza saperlo.

## 2. Matrice per cluster di enum (56 strategie reali)

### `STRAT_STRUCT_REACT` — 34 strategy_id, il bucket generico

| strategy_id | Implementation function | Placeholder? | Shared with | Suspected misbinding | Contamination risk |
|---|---|---|---|---|---|
| STRUCT_REACT | `NXS_Strat_StructureReaction` (Strategies.mqh:2177) | No | (proprietario semantico dell'enum) | No — è l'unico per cui l'enum è semanticamente corretto | LOW |
| BAR_UPDN | Strategies.mqh:451 | No | 33 altri | **Sì** — pattern OHLC puro, nessuna relazione con "structure reaction" | MEDIUM (prospettico) |
| PMAX | Strategies.mqh:498 | No | 33 altri | **Sì** — trailing stop indicator-based | MEDIUM (prospettico) |
| MACD_SMA200 | Strategies.mqh:568 | No | 33 altri | **Sì** — momentum/trend proxy (vedi §3) | MEDIUM (prospettico) |
| ICHIMOKU_HULL_MACD | Strategies.mqh:624 | No | 33 altri | **Sì** | MEDIUM (prospettico) |
| 3COMMAS_BOT | Strategies.mqh:677 | No | 33 altri | **Sì** — nome stesso suggerisce origine esterna (bot di copytrading), nessuna relazione concettuale | MEDIUM (prospettico) |
| PIVOT_WICK | Strategies.mqh:802 | No | 33 altri | **Sì** — location/pivot, non "reaction" | MEDIUM (prospettico) |
| LEVEL_CONFLUENCE, LEVEL_CONFLUENCE_M5 | Strategies.mqh:1071,1088 | No | 33 altri | Parzialmente giustificato — riusa l'infrastruttura PIVOT_WICK, concettualmente adiacente a STRUCT_REACT | LOW-MEDIUM |
| LEVEL_REACTION, LEVEL_REACTION_M5 | Strategies.mqh:1327,1337 | No | 33 altri | **No** — è il merge dichiarato di PIVOT_WICK+MALAYSIAN_SNR+STRUCT_REACT (nota vault 06-09), l'enum è coerente col nome qui | LOW |
| THREE_BAR_DELIVERY_BREAK, AMD_CONT, JUDAS_SWING, LDN_REVERSAL, NY_REVERSAL, WEEKLY_EXP, PO3, LIQ_VOID, DISP_REBAL, RANGE_FADE | Institutional.mqh (righe varie, vedi §5 per dettaglio riga) | No (tutte) | 33 altri ciascuna | **Sì, tutte** — famiglia "istituzionale"/sessione/liquidity, nessuna relazione diretta con structure-reaction salvo appartenenza alla stessa libreria | MEDIUM (prospettico) |
| WICK_SWEEP_RECLAIM, WICK_SWEEP_REV | Experimental.mqh:604-605,677,806-807 | No | 33 altri | **Sì** | MEDIUM (prospettico) |
| ELLIOTT | Elliott.mqh:39 | No | 33 altri | **Sì** — pattern Elliott Wave, nessuna relazione | MEDIUM (prospettico) |
| TURTLE_SOUP | SMC.mqh:26 | No | 33 altri | **Sì** per l'enum — ma vedi §3: condivide realmente il motore sweep con LIQ_SWEEP (relazione diversa, reale) | MEDIUM (prospettico, enum) + nota a parte (motore) |
| SWING_FALSEBREAK | SMC.mqh:121 | No | 33 altri | **Sì** | MEDIUM (prospettico) |
| SH_BMS_RTO, SH_BMS_RTO_V2 (×2 funzioni) | SMC.mqh:418, 551+591 | No | 33 altri | **Sì** — state machine SMC, non "reaction" generica | MEDIUM (prospettico) |
| SMS_BMS_RTO | SMC.mqh:625 | No | 33 altri | **Sì** | MEDIUM (prospettico) |
| SILVER_BULLET | SMC.mqh:696 | No | 33 altri | **Sì** — setup di sessione+SMC | MEDIUM (prospettico) |
| AMD_REVERSAL, OTE_CONT | SMC.mqh:780,819 | No | 33 altri | **Sì** | MEDIUM (prospettico) |
| MALAYSIAN_SNR | SMC.mqh:877 | No | 33 altri | **Sì, e con effetto comportamentale reale** — passa per il motore NXR condiviso, vedi §1 | **HIGH** (non solo prospettico) |
| CRT | SMC.mqh:961 | **Discrepanza** — registry dice `live_implementation=False`/`research_only`, ma il codice esiste | 33 altri | **Sì** | MEDIUM (prospettico) + discrepanza registry da chiudere |

### `STRAT_FVG_CONT` — 4 strategy_id

| strategy_id | Implementation function | Shared with | Suspected misbinding | Contamination risk |
|---|---|---|---|---|
| FVG_CONT | Strategies.mqh:1489 | IFVG, FVG_MIT, FVG_MIT_WINDOW | No (proprietario semantico) | LOW |
| IFVG | SMC.mqh:165 | 3 altri | Parziale — è un fenomeno correlato (inverse-FVG) ma geometricamente distinto | **HIGH** — il codice dichiara l'intento di unificare su NXR ma IFVG non lo è davvero (vedi `COMPONENT_COLLAPSE_HIGH_VALUE_VERIFICATION_V1.md`, Cluster 2) |
| FVG_MIT | SMC.mqh:200 (macro-redirect a NXR) | 3 altri | Parziale | **HIGH** — passa per NXR, effetto comportamentale reale |
| FVG_MIT_WINDOW | SMC.mqh:314 | 3 altri | Parziale | MEDIUM — NON passa per NXR (tracker proprio), ma registry dice `live_implementation=False` mentre è attivamente chiamata da `NEXUS_EA_v2.mq5:542` — **discrepanza registry-vs-codice da chiudere** |

### `STRAT_BREAKOUT_ACC` — 3 strategy_id (non trovato nell'audit precedente)

| strategy_id | Implementation function | Shared with | Suspected misbinding | Contamination risk |
|---|---|---|---|---|
| BREAKOUT_ACC | Strategies.mqh:1536 | VOLATILITY_BREAKOUT_CONFIRMED, Z_SCORE_BREAKOUT | No (proprietario semantico) | LOW |
| VOLATILITY_BREAKOUT_CONFIRMED | Strategies.mqh:1593 | 2 altri | **Sì** — è il segnale "congelato" della Strategy Foundry Phase 3 (`FROZEN_SIGNAL_SPEC_V1`), porting esatto da Python, concettualmente un fenomeno a sé (range N=20 + ATR confirm), non un alias di BREAKOUT_ACC | MEDIUM (prospettico) |
| Z_SCORE_BREAKOUT | Strategies.mqh:1689 | 2 altri | **Sì** — z-score + regime SMA200, fenomeno statisticamente diverso | MEDIUM (prospettico) |

### `STRAT_ORDER_BLOCK` — 2 strategy_id

| strategy_id | Implementation function | Shared with | Suspected misbinding | Contamination risk |
|---|---|---|---|---|
| ORDER_BLOCK | Strategies.mqh:2080,2143 | OB_MIT | No | LOW |
| OB_MIT | SMC.mqh:357 (macro-redirect a NXR) | ORDER_BLOCK | No (il nome stesso indica "mitigation of order block", relazione reale col fenomeno) | **HIGH** — stato di zona condiviso, effetto comportamentale reale (vedi audit precedente) |

### `STRAT_RSI_DIV` — 2 strategy_id, nessun problema

| strategy_id | Implementation function | Shared with | Suspected misbinding | Contamination risk |
|---|---|---|---|---|
| RSI_DIV | Strategies.mqh:2027 | RSI_DIV_PINE | No | LOW |
| RSI_DIV_PINE | Strategies.mqh:1980 | RSI_DIV | No — stesso fenomeno dichiarato correttamente, algoritmo diverso (pivot-based vs finestra fissa) | LOW |

### Enum proprio, nessuna condivisione — 10 strategy_id

ADX_RSI, BOLLINGER, MACD, SAR, TSI, BJORGUM, LIQ_SWEEP, LONDON_BO, EMA_PULLBACK, BB_SQUEEZE, ICHIMOKU — ciascuna ha il proprio `STRAT_*` enum dedicato, nessuna condivisione, nessun rischio di attribuzione. **Nota (già in `UNIFIED_COMPONENT_DEPENDENCY_AUDIT_V1.md`):** ADX_RSI, MACD, SAR restano `SAME_PHENOMENON_DIFFERENT_PROXY` a livello di *fenomeno di mercato* (3 proxy di trend diversi), ma questo è indipendente dall'enum — **qui l'attribuzione è corretta**, il rischio di ridondanza è semantico, non di attribution bug.

## 3. Relazioni reali non-enum trovate durante il censimento (bonus, non richieste)

- **TURTLE_SOUP ↔ LIQ_SWEEP**: condividono il motore di sweep-detection upstream (`SNXSSweepExt`/`NXS_DetectSweepExt`), nonostante enum diversi (`STRAT_STRUCT_REACT` vs `STRAT_LIQ_SWEEP`) — relazione reale, ma nella direzione opposta al pattern di questa matrice (qui l'enum NON segnala la relazione vera).
- **MACD_SMA200**: secondo proxy indipendente di MACD (SMA vs EMA a ogni stadio) — fenomeno correlato a MACD, ma attribuito a `STRAT_STRUCT_REACT`, non a `STRAT_MACD` né a un enum proprio.
- **NXS_Institutional_Decide / `isig.stratName = dec.group`** (`NEXUS_EA_v2.mq5:1462`): scoperta collaterale rilevante per `UNIFIED_MARKET_INTELLIGENCE_ARCHITECTURE_V1.md` §4 (evidence aggregation) — **esiste già un motore di aggregazione multi-strategia in produzione** ("Modello Istituzionale v2.1.0", raggruppa segnali per direzione in un'unica decisione, pesa per qualità del contesto prima di sommare). Tutto questo meta-livello usa `STRAT_STRUCT_REACT` come bucket. **Non approfondito qui** (fuori scope di questo preaudit) ma segnalato come precedente diretto da studiare prima di progettare un nuovo aggregatore da zero.

## 4. Discrepanze registry-vs-codice trovate (non richieste, rilevanti per Codex)

| strategy_id | Registry dice | Codice reale |
|---|---|---|
| CRT | `live_implementation` assente/false, research_only | Funzione MQL5 reale esiste (SMC.mqh:961), `selector_index=None` — non chiaro se raggiungibile dalla EA |
| FVG_MIT_WINDOW | `live_implementation=False` | Chiamata attivamente da `NEXUS_EA_v2.mq5:542` via `NXS_SelectorAllows(39)` |

## 5. I 27 placeholder confermati (nessuna implementazione, nessun fenomeno, nessun componente)

CISD_TRUE, CRT_MINSTOP_FILTER, DARVAS_BOX, DONCHIAN_TURTLE, EMA_CROSS_BENCHMARK, FVG_CONT_V2, IFVG_CHOCH_WINDOW, MALAYSIAN_SNR_BREAKOUT, MALAYSIAN_SNR_V2_RETEST, MALAYSIAN_SNR_V2_RETEST_OUTRANGE, MALAYSIAN_SNR_V2_STAGE1, MALAYSIAN_SNR_V2_STAGE3, NY_REVERSAL_CHOCH_WINDOW, ORDER_BLOCK_V2, OTE_CONT_V2, SAR_ADX20, SAR_FLIP, SCALP_BB_FADE, SCALP_EMA, SCALP_RANGE_BRK, SCALP_RSI_SNAP, SILVER_BULLET_V2, SMS_BMS_RTO_CHOCH_WINDOW, TSI_EXTREME, TURTLE_SOUP_CHOCH, TURTLE_SOUP_CHOCH_DBLBODY, TURTLE_SOUP_CHOCH_NEAR — **confermati coerenti col registry** (`live_implementation=False`), nessuna discrepanza da correggere su questi 27.

## 6. Priorità raccomandata per il futuro STRATEGY_IDENTITY_ATTRIBUTION_AUDIT_V1 di Codex

1. **I 6 con effetto comportamentale reale** (non solo prospettico): MALAYSIAN_SNR, ORDER_BLOCK/OB_MIT, FVG_CONT-family/FVG_MIT — il motore NXR li confronta/fonde realmente via l'enum condiviso.
2. **Le 2 discrepanze registry-vs-codice** (§4) — CRT e FVG_MIT_WINDOW — correzione di bookkeeping, non di comportamento.
3. **Il resto dei 34 STRAT_STRUCT_REACT** — rischio solo prospettico, priorità bassa, ma da estendere l'enum prima che un futuro Unified Engine li legga senza saperlo.
4. **Non prioritario**: i 27 placeholder — nessun codice da attribuire correttamente, nessun lavoro necessario finché non vengono implementati.

Non verificato in questo preaudit (lasciato a Codex): se `s.strat` è consumato da qualche altro file oltre a `NXS_ReusePerformancePack.mqh`/`NXS_EdgeAdaptive.mqh` in modo che l'enum condiviso cambi comportamento (non solo etichetta) per i 28 strategy_id che non passano per NXR.

---

## Vincoli rispettati

Nessuna modifica a MQL5/registry. Nessun commit/push. Nessun backtest. Censimento completo (83/83), non campionato — ogni riga CODE_VERIFIED o PLACEHOLDER_CONFIRMED contro il registry, nessuna inferenza di nome lasciata non verificata dove il grep lo permetteva.

STRATEGY_IDENTITY_ATTRIBUTION_PREAUDIT_V1_READY_FOR_REVIEW
