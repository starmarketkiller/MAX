# Trading Edge Status Reconciliation V1

**Stato:** proposta canonica, non ancora committata — in attesa di revisione utente, come richiesto in `EDGE_VALIDATION_PROVENANCE_RECONCILIATION_V1`. Nessuna strategia, runtime, parametro MQL5 o backtest è stato toccato per produrre questo documento. È bookkeeping su evidenza già esistente, non nuova scienza.

**Da dove nasce:** distilla in artifact canonico il contenuto di `TRADING_EDGE_STATUS_RECONCILIATION_V1` (prodotto come output di sessione il 2026-10-05, mai persistito prima d'ora) e chiude i gap di provenance sui 7 defect storici richiesti prima che `EDGE_VALIDATION_REGISTRY_V1` (Codex) venga committato.

**Correzioni applicate rispetto alla prima stesura** (richieste dall'utente):
1. Campioni OOS piccoli (es. LIQ_SWEEP n=6) → evidenza negativa con avvertenza di numerosità insufficiente, non "FAILED" netto.
2. Il regime-controlled benchmark (Phase 7.27) riduce la confidenza nell'edge standalone di strategie BUY-dominanti — non le falsifica automaticamente.

---

## Parte 1 — Mapping edge_validation_status (21 strategie ACTIVE+default_enabled con evidenza reale)

| strategy_id | edge_status | fonte/data | SHA | evidence grade | defect noto |
|---|---|---|---|---|---|
| ADX_RSI | CANDIDATE | Phase 7.27 (28-09) + 04-09 + cost-recalc 15-09 | non rintracciato | nudo 3Y + cost-recalc PASS; **regime-confounded (7.27), confidenza standalone ridotta non falsificata** | nessuno |
| BB_SQUEEZE | DEFECT_BLOCKED | Phase 7.10 (23-09) | `651d3a2` (baseline audit) | — | CROSS_TIMEFRAME_STATE_CONTAMINATION, non corretto |
| BOLLINGER | BORDERLINE | 05-09 + Phase 7.10 (23-09) | non rintracciato | "confermata" invalidata da buy&hold (cattura 3-14%); SUSPECT non confermato di contaminazione | SUSPECT, non confermato |
| BREAKOUT_ACC | FORWARD_REQUIRED | Phase 7.21 (27-09) | fix: `651d3a2` (Phase 7.9G, 23-09) | fix applicato e causalmente validato; CI95 edge include zero, concentrazione 133.7%, OOS 1 trade — campione insufficiente | **REMEDIATED** (vedi Parte 2) |
| EMA_PULLBACK | CANDIDATE | Cost-recalc 15-09 | `ff9f0e5` | SERIOUS_BACKTEST_CANDIDATE | nessuno |
| FVG_CONT | CANDIDATE | 15-09 + 07-09 | `ff9f0e5` | segnale nudo promosso; variante SLReclaim bypassa le protezioni conto, fix non confermato | SLReclaim bypass, non confermato risolto |
| ICHIMOKU | CANDIDATE | Cost-recalc 15-09 | `ff9f0e5` | PF1.08, n=79 | nessuno confermato |
| JUDAS_SWING | CANDIDATE | Cost-recalc 15-09 | `ff9f0e5` | SERIOUS_BACKTEST_CANDIDATE | nessuno |
| LIQ_SWEEP | CANDIDATE | Phase 7.25 (28-09) + 15-09 | non rintracciato | PF1.48 post-fix; **OOS n=6 = evidenza negativa, campione insufficiente — non un "no" definitivo** | detector bug fixato 14-09 |
| LONDON_BO | BORDERLINE | Cost-recalc 15-09 | `ff9f0e5` | PF1.02 — margine minimo | nessuno |
| MACD | FAILED | Phase F (16-09) | non rintracciato | SERIOUS_VALIDATION_FAIL, 2/3 anni negativi, SELL PF=0.13 (test diretto per-anno, non inferenza di regime — sovrascrive la promozione del 15-09) | nessuno strutturale |
| MALAYSIAN_SNR | CANDIDATE | Cost-recalc 15-09 | `ff9f0e5` | PF1.18, n=53 — campione modesto | nessuno |
| NY_REVERSAL | BORDERLINE | Cost-recalc 15-09 | `ff9f0e5` | PF1.06, n=55 — marginale | nessuno |
| ORDER_BLOCK | FORWARD_REQUIRED | Phase 7.22 (27-09) | fix: `17da794` (Phase 7.14, 27-09) | fix applicato e causalmente validato; CI95 include zero, concentrazione 197% | **REMEDIATED** (vedi Parte 2) |
| RSI_DIV | FAILED | 15/07 | non rintracciato | -17.5R/6 anni, campione ampio; assente dai 36 positivi del 15-09 (inferenza per assenza, non confermata nel dettaglio) | nessuno |
| SAR | BORDERLINE | Phase F (16-09) | non rintracciato | SERIOUS_VALIDATION_BORDERLINE, SELL PF=0.84/92 | ex-bug InpRiskProfile, isolato 08-09 |
| SH_BMS_RTO | DEFECT_BLOCKED | Phase 7.10 (23-09) | `651d3a2` (baseline audit) | — | CROSS_TIMEFRAME_STATE_CONTAMINATION, non corretto |
| SILVER_BULLET | DEFECT_BLOCKED | Phase 7.10 (23-09) | `651d3a2` (baseline audit) | — | CROSS_TIMEFRAME_STATE_CONTAMINATION, non corretto |
| STRUCT_REACT | CANDIDATE (debole) | 05-09 | non rintracciato | solo prima conferma, mai ripreso con rigore maggiore | nessuno confermato |
| TSI | DEFECT_BLOCKED | Phase 7.10 (23-09) | `651d3a2` (baseline audit) | "caso più severo" (stato ricorsivo doppio EMA) | CROSS_TIMEFRAME_STATE_CONTAMINATION, non corretto |
| Z_SCORE_BREAKOUT | CANDIDATE | Cost-recalc 15-09 | `ff9f0e5` | PF1.23, n=460 — campione ampio | nessuno |

**Riferimento (non default_enabled):** CRT — FAILED robusto (25-08, griglia 36 combinazioni, costi dominanti), nessuna evidenza in conflitto.

### Casi ambigui (non forzati in PASS/FAIL)

AMD_REVERSAL, OTE_CONT (discrepanza: registry=ACTIVE vs nota vault stale="Disabilitata" — vedi Parte 3), PO3, SMS_BMS_RTO, WEEKLY_EXP — evidenza insufficiente o contraddittoria per classificare con fiducia piena.

### Strategie senza evidenza scientifica (UNVALIDATED per assenza di ricerca)

ELLIOTT e SWING_FALSEBREAK (mai entrate in pipeline di ricerca, solo live). Le restanti ~55-60 delle 83 totali del registry — nessuna `default_enabled=true`, nessuna decisione scientifica trovata; raggruppate, non approfondite singolarmente (rischio live nullo).

---

## Parte 2 — Reconciliation defect storici (7 strategie richieste)

Metodo usato per ciascuna: (a) verificata la classificazione originale in Phase 7.10 (`stateful_strategy_static_audit_v1.json` / `cross_timeframe_state_contamination_failure_memory_v1.json`, baseline `651d3a2`); (b) cercata qualunque nota vault/docs/commit successiva che citi la strategia dopo il 23-09; (c) per i due casi con un fix noto, verificato lo **scope esatto del diff** (non solo la nota che lo descrive) per escludere remediation incidentale sulle altre 5; (d) verificato lo stato corrente `default_enabled`/`status` nel registry — **senza usarlo come prova di remediation**, come richiesto esplicitamente.

| strategy_id | defect confermato | data/fase | remediation successiva? | SHA/fonte | stato finale |
|---|---|---|---|---|---|
| **BREAKOUT_ACC** | COOLDOWN_STATE_CONTAMINATION | Phase 7.9F (22-09), confermato IMPLEMENTATION_DEFECT_CONFIRMED | **Sì** — guardia TF-scoped early-return in `NXS_Strat_BreakoutAcc()`, 4→47 trade, causalmente validata | `651d3a2` (Phase 7.9G, 23-09) — diff: solo `MQL5/Include/NEXUS_v1/NXS_Strategies.mqh`, +11 righe | **REMEDIATED** |
| **ORDER_BLOCK** | STATE_MACHINE_CONTAMINATION | Phase 7.10 (23-09), poi trace reale Phase 7.13 | **Sì** — guardia TF-scoped, 18.485 mutazioni non canoniche → 123→8 segnali D1 sugli stessi tick, causalmente validata su trace EA reale | `17da794` (Phase 7.14, 27-09) — diff: solo `MQL5/Include/NEXUS_v1/NXS_Strategies.mqh`, +11 righe | **REMEDIATED** |
| **BAR_UPDN** | COOLDOWN_STATE_CONTAMINATION (stessa classe di BREAKOUT_ACC) | Phase 7.10 (23-09) | **No** — nessuna nota/commit trovata dopo il 23-09 che citi BAR_UPDN in relazione al defect. Confermato per esclusione diretta: il diff `651d3a2` tocca solo la funzione `NXS_Strat_BreakoutAcc()`, non una utility condivisa — il fix non si propaga a BAR_UPDN | nessuna (defect non remediato) | **DEFECT_BLOCKED** |
| **PIVOT_WICK** | COOLDOWN_STATE_CONTAMINATION | Phase 7.10 (23-09) | **No** — stesso motivo di BAR_UPDN; nessuna evidenza di remediation trovata | nessuna | **DEFECT_BLOCKED** |
| **PMAX** | RECURSIVE_VALUE_STATE_CONTAMINATION (longStop/shortStop/dir) | Phase 7.10 (23-09) | **No** — nessuna nota/commit trovata; classe di defect più severa (corrompe il valore, non solo il timing), nessun fix applicabile per analogia da BREAKOUT_ACC/ORDER_BLOCK (classe diversa) | nessuna | **DEFECT_BLOCKED** |
| **RANGE_FADE** | STATE_MACHINE_CONTAMINATION (stessa classe di ORDER_BLOCK/SH_BMS_RTO/SILVER_BULLET) | Phase 7.10 (23-09) | **No** — il diff `17da794` tocca solo la funzione di ORDER_BLOCK, non una state machine condivisa; nessuna nota successiva | nessuna | **DEFECT_BLOCKED** |
| **SH_BMS_RTO_V2** | STATE_MACHINE_CONTAMINATION | Phase 7.10 (23-09) | **No** — stesso motivo di RANGE_FADE. Nota: il codice MQL5 esiste ancora oggi in `NXS_Strategies_SMC.mqh` (non toccato da nessuno dei due fix), nonostante il registry lo marchi `RESEARCH_ONLY`/`live_implementation=false` — **discrepanza registry-vs-codice separata, non verificata ulteriormente qui** | nessuna | **DEFECT_BLOCKED** |

**Nota su "non inferire remediation da ACTIVE" (vincolo esplicito dell'utente):** BAR_UPDN, PIVOT_WICK, PMAX e RANGE_FADE sono oggi `status=DISABLED`/`default_enabled=false` nel registry — questo riduce il rischio *runtime* immediato ma **non è stato usato come prova di remediation** del defect, che resta una proprietà del codice indipendente dallo stato di attivazione. Nessuno dei 5 casi sopra è stato classificato `UNKNOWN_REMEDIATION`: per tutti e 5 la ricerca è stata esaustiva (grep su vault/docs/research_scripts + verifica diretta dello scope dei due diff di fix) e non ha trovato nulla di ambiguo — l'assenza di evidenza è essa stessa l'evidenza di "non corretto", non un caso dubbio.

---

## Parte 3 — Discrepanze fonte stale vs vault recente

- `knowledge/strategy_database.json` (generato 19/07, baseline `e6ce816`) è completamente superato — es. ADX_RSI vi appare PF0.82 (lotto fisso, pre-fix), contraddetto da decisioni di settembre molto più recenti e rigorose. Non va usato come fonte per lo stato attuale.
- `vault/01-Trading/Strategie/*.md` + `MOC - Strategie.md` sono ferme alla stessa generazione di luglio — es. **OTE_CONT vi è "Disabilitata"** mentre il registry odierno lo marca `ACTIVE`/`default_enabled=true`. Discrepanza non risolta in questo documento (riportata come caso ambiguo in Parte 1).
- `docs/architecture/17_STRATEGY_REGISTRY_RECONCILIATION.md` (21/07) è anch'esso pre-espansione del registry (41 record totali allora vs 83 oggi) — utile solo per la mappa dei research proxy (es. `RANGE_FADE` proxato da `BOLLINGER` in ricerca), non per lo stato corrente.
- Il cost-recalc del 15-09 stesso (`ff9f0e5`) è parzialmente superato per BREAKOUT_ACC, LIQ_SWEEP, MACD, SAR, ADX_RSI — tutte riqualificate da fasi più recenti (Phase F 16-09, Phase 7.1x-7.27, 20-28/09). Resta comunque la fonte più recente e affidabile per le ~15 strategie che nessuna fase successiva ha più toccato.

---

## Parte 4 — Tabella finale per Codex

`strategy_id → edge_status → defect_status → source → SHA`

| strategy_id | edge_status | defect_status | source | SHA |
|---|---|---|---|---|
| ADX_RSI | CANDIDATE | — | Phase 7.27 + cost-recalc 15-09 | `ff9f0e5` (cost-recalc) |
| BAR_UPDN | UNVALIDATED | DEFECT_BLOCKED | Phase 7.10 | `651d3a2` |
| BB_SQUEEZE | UNVALIDATED | DEFECT_BLOCKED | Phase 7.10 | `651d3a2` |
| BOLLINGER | BORDERLINE | SUSPECT (non confermato) | 05-09 + Phase 7.10 | n.d. |
| BREAKOUT_ACC | FORWARD_REQUIRED | REMEDIATED | Phase 7.21 / Phase 7.9G | `651d3a2` |
| CRT | FAILED | — | 25-08 | n.d. |
| EMA_PULLBACK | CANDIDATE | — | Cost-recalc 15-09 | `ff9f0e5` |
| FVG_CONT | CANDIDATE | UNKNOWN_REMEDIATION (SLReclaim bypass, non confermato risolto) | 15-09 / 07-09 | `ff9f0e5` |
| ICHIMOKU | CANDIDATE | — | Cost-recalc 15-09 | `ff9f0e5` |
| JUDAS_SWING | CANDIDATE | — | Cost-recalc 15-09 | `ff9f0e5` |
| LIQ_SWEEP | CANDIDATE | — | Phase 7.25 | n.d. |
| LONDON_BO | BORDERLINE | — | Cost-recalc 15-09 | `ff9f0e5` |
| MACD | FAILED | — | Phase F 16-09 | n.d. |
| MALAYSIAN_SNR | CANDIDATE | — | Cost-recalc 15-09 | `ff9f0e5` |
| NY_REVERSAL | BORDERLINE | — | Cost-recalc 15-09 | `ff9f0e5` |
| ORDER_BLOCK | FORWARD_REQUIRED | REMEDIATED | Phase 7.22 / Phase 7.14 | `17da794` |
| PIVOT_WICK | UNVALIDATED | DEFECT_BLOCKED | Phase 7.10 | `651d3a2` |
| PMAX | UNVALIDATED | DEFECT_BLOCKED | Phase 7.10 | `651d3a2` |
| RANGE_FADE | UNVALIDATED | DEFECT_BLOCKED | Phase 7.10 | `651d3a2` |
| RSI_DIV | FAILED | — | 15/07 | n.d. |
| SAR | BORDERLINE | — | Phase F 16-09 | n.d. |
| SH_BMS_RTO | UNVALIDATED | DEFECT_BLOCKED | Phase 7.10 | `651d3a2` |
| SH_BMS_RTO_V2 | UNVALIDATED | DEFECT_BLOCKED | Phase 7.10 | `651d3a2` |
| SILVER_BULLET | UNVALIDATED | DEFECT_BLOCKED | Phase 7.10 | `651d3a2` |
| STRUCT_REACT | CANDIDATE | — | 05-09 | n.d. |
| TSI | UNVALIDATED | DEFECT_BLOCKED | Phase 7.10 | `651d3a2` |
| Z_SCORE_BREAKOUT | CANDIDATE | — | Cost-recalc 15-09 | `ff9f0e5` |
| ELLIOTT | UNVALIDATED | — | mai in ricerca | n.d. |
| SWING_FALSEBREAK | UNVALIDATED | — | mai in ricerca | n.d. |
| AMD_REVERSAL, OTE_CONT, PO3, SMS_BMS_RTO, WEEKLY_EXP | AMBIGUOUS | — | vedi Parte 1/3 | n.d. |
| *(restanti ~55-60 strategie del registry)* | UNVALIDATED | — | nessuna decisione trovata | n.d. |

**Provenance gap residuo:** solo FVG_CONT ha un `UNKNOWN_REMEDIATION` genuino (il bug SLReclaim è confermato ma non c'è nota successiva che ne confermi o neghi il fix — non classificabile con fiducia come DEFECT_BLOCKED né come REMEDIATED). Tutti gli altri 6 defect richiesti sono chiusi con evidenza diretta: 2 REMEDIATED (BREAKOUT_ACC, ORDER_BLOCK), 4 DEFECT_BLOCKED con assenza di evidenza verificata esaustivamente (BAR_UPDN, PIVOT_WICK, PMAX, RANGE_FADE) + SH_BMS_RTO_V2 allo stesso modo.

---

## Prossimo passo

Report da mostrare all'utente prima di qualunque commit/push, come richiesto. Se approvato, questo file alimenta `EDGE_VALIDATION_REGISTRY_V1` (Codex) — nessuna modifica fatta qui a `contracts/strategy-registry.json` o al suo generatore.
