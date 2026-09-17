# NEXUS - Market Intelligence Foundation

Cambio di paradigma della ricerca NEXUS: da `STRATEGY -> BACKTEST -> PF` a `MARKET STATE -> EVENT -> SETUP -> TRIGGER -> ENTRY -> INVALIDATION -> OUTCOME -> PROBABILITY -> EDGE -> STRATEGY`. Questo documento è l'indice e la sintesi; il dettaglio completo di ogni sezione vive negli artifact collegati in `vault/01-Trading/_phase4_artifacts/`. Nessun nuovo EA implementato, nessuna strategia ottimizzata, nessun trading live/demo autonomo avviato — coerente con il vincolo esplicito di questa fase (ricerca infrastrutturale).

Baseline di partenza: correzione Phase 3 approvata (commit `8c24cd4`/`85f8b41`), VOLATILITY_BREAKOUT_CONFIRMED resta `HOLD_NEEDS_MORE_EVIDENCE`, il Fast Structural pre-correzione è metodologicamente superseded.

---

## 0. Preflight Semantic Integrity — VOLATILITY_BREAKOUT_CONFIRMED

**Trovato**: la registry generata mostrava `default_enabled=true`, `auto_disable_eligible=true`, `status=ACTIVE` per VOLATILITY_BREAKOUT_CONFIRMED, mentre il vero input compilato `InpStrat_VolBreakoutConfirmed=false` ("mai verificata su MT5 - default OFF") e il verdetto resta HOLD_NEEDS_MORE_EVIDENCE.

**Causa**: durante la correzione Phase 3, `knowledge/strategy_database.json` era stato aggiornato con `stato: "attiva"` (inteso come "implementata/codificata"), ma il generatore (`contracts/generate_registry.py`) interpreta `stato: "attiva"` come "ACTIVE" → `default_enabled=true` — collisione di significato fra "codice presente" e "raccomandato per default live".

**Correzione**: `stato` corretto a `"sperimentale"` (stessa categoria già usata correttamente per WICK_SWEEP_REV/RECLAIM, i cui `default_enabled=false` combaciano con i loro `InpStrat_*=false` reali). Rigenerato e validato (`validate_registry.py`: OK). Nessuna ricompilazione necessaria (questi campi non sono codificati in `NXS_StrategyRegistry.mqh`). Commit `1ebae49`.

`supported_symbols=["*"]` e `risk_class="STANDARD"` restano invariati: sono valori strutturalmente costanti in TUTTA la registry (nessuna strategia ha mai un valore diverso — il motore non ha gating per simbolo, e `risk_class` non è ancora popolato con differenziazione reale). Non sono "sbagliati per definizione" ma sono placeholder non informativi — documentato, non corretto silenziosamente, perché non esiste oggi una fonte-di-verità alternativa per popolarli diversamente senza inventare un dato.

**Scoperta cruciale emersa dall'audit di sezione 1 (vedi sotto)**: questo stesso pattern di mismatch (`default_enabled=true` nella registry vs `Inp*=false` nel codice compilato) è **sistemico**, non isolato. Il sub-agent che ha condotto l'audit di sezione 1 aveva inizialmente segnalato 11 strategie; **verifica diretta di questo claim** (come richiesto esplicitamente dal proprietario del progetto — "non assumere che un'affermazione sia sufficiente senza verifica") ha confermato **10 delle 11** e **scartato PIVOT_WICK**: la sua `stato` nel knowledge base è `"disabilitata in produzione"`, che il generatore mappa correttamente a `status=DISABLED`/`default_enabled=false` — verificato leggendo direttamente `contracts/strategy-registry.json` (`PIVOT_WICK -> status: DISABLED, default_enabled: False`), quindi PIVOT_WICK NON ha il mismatch, contrariamente al claim iniziale.

Le **10 strategie con mismatch confermato** (registry `status=ACTIVE`/`default_enabled=true`, ma `Inp*=false` verificato riga per riga in `NXS_Inputs.mqh`): **AMD_CONT** (`InpUseStrat_AMD_Cont=false`), **BJORGUM** (`InpStrat_BJORGUM=false`), **FVG_MIT** (`InpStrat_FVG_Mit=false`, codice morto via redirect `InpNXR_Enable`), **IFVG** (`InpStrat_IFVG=false`, codice morto), **LDN_REVERSAL** (`InpUseStrat_LdnReversal=false`), **LIQ_VOID** (`InpUseStrat_LiqVoid=false`, e comunque strutturalmente irraggiungibile con `InpUseHTFBias=false` di default), **OB_MIT** (`InpStrat_OB_Mit=false`, codice morto via redirect), **RANGE_FADE** (`InpUseStrat_RangeFade=false`), **THREE_BAR_DELIVERY_BREAK/CISD** (`InpUseStrat_CISD=false`), **TURTLE_SOUP** (`InpStrat_TurtleSoup=false`). Tre di queste (IFVG/FVG_MIT/OB_MIT) sono codice morto indipendentemente dal toggle. **Non corretto in questa fase** (richiederebbe una verifica individuale del razionale storico di ciascuna, fuori scope per "ricerca infrastrutturale, non ottimizzazione") — segnalato come raccomandazione prioritaria di follow-up. Catalogato come pattern di fallimento sistemico `REGISTRY_METADATA_SEMANTIC_MISMATCH` in [[failure_memory]].

---

## 1. Semantic Strategy Audit

Dettaglio completo: [[semantic_strategy_audit]] (53/53 strategie live auditate dal codice MQL5 reale, non dai nomi).

- **≈46 idee di mercato genuinamente distinte** su 53 strategy_id registrate.
- **7 cluster di duplicati/varianti** (22 strategy_id coinvolti): OB_MIT≡ORDER_BLOCK (TRUE_DUPLICATE); cluster a 6 membri PIVOT_WICK/MALAYSIAN_SNR/LEVEL_CONFLUENCE(+M5)/LEVEL_REACTION(+M5) (SEMANTIC_DUPLICATE, stessa idea "reazione a livello chiave", fonti diverse); SH_BMS_RTO/SMS_BMS_RTO (stessa idea "sweep→break struttura→ritorno", detector diversi); RSI_DIV/RSI_DIV_PINE, MACD/MACD_SMA200, SAR/PMAX/3COMMAS_BOT, AMD_CONT/PO3, WICK_SWEEP_REV/WICK_SWEEP_RECLAIM, TURTLE_SOUP/SWING_FALSEBREAK (MINOR_VARIANT).
- **4 strategie MISNAMED**: THREE_BAR_DELIVERY_BREAK (toggle/funzione dicono ancora "CISD" ma non è un vero Change-In-State-of-Delivery); OB_MIT (codice = wrapper letterale di ORDER_BLOCK, non una mitigazione); IFVG/FVG_MIT (nomi implicano strategie SMC attive, in realtà codice morto redirect a `InpNXR_Enable=false` hardcoded); LIQ_VOID (registry dice ACTIVE, strutturalmente irraggiungibile perché richiede `htf.bias != NEUTRAL` con `InpUseHTFBias=false` di default).
- **Scoperta cross-cutting** (vedi sezione 0): il sub-agent aveva inizialmente segnalato 11 strategie "ACTIVE"/`default_enabled:true` in registry ma in realtà `false` di default nel codice compilato; verifica diretta riga-per-riga ha confermato **10 su 11** (PIVOT_WICK escluso: è già correttamente `DISABLED`/`default_enabled:false` in registry).

---

## 2. Formal Ontology

Dettaglio completo: [[market_ontology]] — definizioni separate e rigorose di Market State, Context, Event, Setup, Trigger, Signal, Entry, Fill, Invalidation, Stop, Target, Outcome, Probability, Edge, Strategy, Trade Management, Risk Model, Execution Model, ciascuna con observation point, informazioni consentite/vietate, rapporto con gli altri concetti, esempio NEXUS concreto (incluso il caso Entry-vs-Fill della correzione Phase 3 come esempio canonico).

---

## 3. Market State Vector v1

Dettaglio completo: [[market_state_schema]] — schema JSON per Trend/Volatility/Structure/Momentum/Liquidity-Activity/Statistical-Behavior/Time/Cross-Market, con per ogni feature: disponibilità oggi, sicurezza causale, costo dati, frequenza, plausibilità economica, priorità (P1/P2/P3).

Sintesi: la maggior parte delle feature P1 (trend/volatility/structure/momentum/time di base) sono già calcolabili da dati OHLC esistenti a costo zero — semplicemente non sono mai state esposte come vettore di stato condiviso, sono sepolte dentro le singole strategie. Le feature cross-market (DXY, yields, silver/gold ratio, proxy di volatilità, positioning) richiedono fonti dati esterne non ancora integrate, con costo/complessità crescente (silver/gold ratio è il candidato più economico, essendo già su Dukascopy).

---

## 4-5. Event Registry & Setup Registry

Dettaglio completo: [[event_registry_schema]], [[setup_registry_schema]]. 15 famiglie di eventi candidate definite con detector/observation-point/direzione/magnitudo/provenienza causale esplicita. Setup = Context + Event + Preconditions, esplicitamente disaccoppiato dal Trigger/metodo di esecuzione — più varianti di trigger sullo stesso Setup non contano come idee di mercato distinte.

---

## 6-7. Outcome Surface & Probability/Uncertainty Engine

Dettaglio completo: [[outcome_schema]], [[probability_schema]]. Outcome Surface mappa la distribuzione naturale (P(+0.25R..+3R prima di -1R), MFE/MAE, tempo-a-target/invalidazione) PRIMA di scegliere un target — nessun campo "TP raccomandato" nello schema, deliberatamente. Probability Engine: modello Beta-Binomial interpretabile (prior Beta(1,1) di default, dichiarato quando informato), ogni stima riporta wins/losses/censored/n/CI95/posteriore — mai un rapporto nudo tipo "7/10=70%".

---

## 8-11, 15. Edge Definition, Conditional Edge, Interaction Research, Survival, High-Probability Setup

Dettaglio completo: [[edge_and_interaction_methodology]].

- **Edge** = ΔP e ΔE rispetto a un baseline comparabile con lo stesso Market State — mai un risultato assoluto positivo isolato.
- **Conditional Edge**: piano con logistic regression → shallow tree → Bayesiano gerarchico → GAM eventuale, nessuna rete neurale in questa fase, split discovery/validation sempre disgiunto.
- **Interaction Research**: solo interazioni predefinite con motivazione economica esplicita, vietata la ricerca combinatoria esaustiva.
- **Survival/Decay**: hazard di invalidazione, decadimento dell'expectancy nel tempo — un TIME_STOP va introdotto solo se emerge dai dati, mai a priori.
- **High-Probability Setup**: 8 requisiti congiunti (ex-ante definition, osservazione causale, campione sufficiente, edge vs baseline, validazione indipendente, incertezza quantificata, stabilità per regime, nessuna dipendenza da outlier patologici) — il solo win rate non è mai sufficiente.

---

## 12. Edge Component Library

Dettaglio completo: [[edge_component_schema]] — schema + 7 componenti candidati iniziali, riconciliati con l'evidenza reale raccolta in sezione 13 (vedi sintesi finale sotto).

---

## 13. Re-Interpretazione della Ricerca Esistente

Dettaglio completo: [[reinterpreted_research]] — **34 report esistenti** riletti sotto la nuova ontologia, nessun test rifatto. Include: la triade causale WICK Sweep (Friday/level-age REFUTATI su 3 periodi indipendenti), l'intera infrastruttura Structural/Unified-Level-Engine (SWEEP→TRUE_BREAK→RETEST→INVALIDATE), il bug di memoria non inizializzata `SNXSSweepExt` (ha fabbricato un trade storico fittizio per AMD_REVERSAL), l'intera linea WICK_SWEEP_RECLAIM (shadow PF 5.80 vs reale PF 0.78-0.80, chiusa formalmente), Strategy Foundry Phase 1-3, la validazione SAR/MACD a 3 anni, l'audit del modello di costo broker (13/67 falsi negativi storici).

**Edge component SUPPORTATI**: volatility-expansion-breakout (MEDIUM), trend-persistence/reversal SAR (MEDIUM-HIGH ma asimmetrico BUY/SELL), broker-cost-realism come gate di validità (STRONG), liquidity-reclaim come fenomeno reale ma non ancora catturabile in esecuzione (WEAK-MEDIUM come fenomeno, REFUTATO come edge eseguibile).

**Edge component REFUTATI (13)**: effetto Friday, level-age su WICK-sweep, penetration/age/TF come precursori TRUE_BREAK (confound), feature di qualità TRUE_BREAK/RETEST, failed-breakout fade, precondizione di compressione di volatilità, precondizione di compressione di sessione, continuazione da displacement/imbalance-stack, regime come gate standalone, famiglia PIVOT_WICK, famiglia LEVEL_REACTION/LEVEL_CONFLUENCE, WICK_SWEEP_REV/RECLAIM (tutte le varianti di esecuzione), MACD H4 a 3 anni.

**Catalogo failure pattern**: 24 istanze consolidate + 2 nuove dalla correzione Phase 3 → [[failure_memory]] (26 pattern totali, con checklist di verifica proposta per ciascuno).

---

## 16. AI / Agent Architecture Research

Dettaglio completo: [[agentic_architecture_research]] — 9 sistemi analizzati (Gordon, OpenAlgo, Agentic Trading Lab/FinAgent, OpenAlice, NautilusTrader, Freqtrade, Hummingbot, QuantConnect Lean, TradingAgents).

**Pattern convergenti validati** (indipendentemente da ≥2 progetti non correlati):
1. Decisione e rischio/esecuzione come stadi separati non bypassabili, connessi da oggetti tipizzati (non stato mutabile condiviso) — il pattern più convergente (4/9 progetti).
2. Approvazione umana pre-esecuzione come modalità di prima classe per componenti agentic/LLM.
3. Stesso percorso di codice per backtest e live, con i punti di divergenza documentati esplicitamente (non assunti via — NautilusTrader è il caso più rigoroso).
4. Prevenzione lookahead/leakage trattata come strumentazione continua (Freqtrade `lookahead-analysis`/`recursive-analysis` come comandi di prima classe), non un'assunzione di design one-shot.
5. Audit trail immutabile e strutturato come primitiva di design, non un log aggiunto dopo.

**Anti-pattern da evitare**: dichiarare parità backtest-live senza nominare le eccezioni; feature extraction annegata dentro il prompt dell'agente invece che come livello indipendente ispezionabile; trattare il marketing di profittabilità come evidenza architetturale; un unico database condiviso per tutto lo stato.

---

## 14. Failure Memory

Dettaglio completo: [[failure_memory]] — 26 pattern di fallimento consolidati con checklist di verifica proposta per ciascuno, inclusi i 2 pattern nuovi scoperti nella correzione Phase 3 (`REGISTRY_METADATA_SEMANTIC_MISMATCH`, ora confermato sistemico su 11 strategie; `DEFAULT_CONVENTION_ASSUMED_FAITHFUL_TO_FROZEN_SPEC`).

---

## 17. Dukascopy — Recovery Pass e Integrity Audit

Il primo download (2019-02-03 → 2022-02-03, 1097 giorni) aveva terminato con 107/1097 giorni incompleti (399 ore fallite su 26328 totali, per 503/timeout dal server Dukascopy). Eseguiti recovery pass paralleli riusando il manifest esistente (solo ore failed/missing ri-scaricate, sessione HTTPS persistente, backoff esponenziale già presenti nello script v2): passata 1 → 107→1 giorno incompleto; passata 2 (retry mirato con timeout esteso sull'unica ora residua, un timeout transitorio) → 0 giorni incompleti, 0 ore fallite.

**Integrity audit completo** (script dedicato, sola lettura, output completo in `_phase4_artifacts/dukascopy_integrity_audit.json`):

- Ore attese: 26328 (1097 giorni × 24h). Ore contabilizzate: 26328 (17768 ok + 8560 vuote + 0 fallite). 0 giorni incompleti.
- Tick totali: **148.097.525**. Primo tick: 2019-02-03T23:00:05.597 UTC. Ultimo tick: 2022-02-03T23:59:59.693 UTC — copre esattamente la finestra dichiarata.
- 0 timestamp duplicati, 0 tick fuori ordine, 0 anomalie bid>ask, 0 file decodificati corrotti.
- Spread (unità prezzo raw XAUUSD): p10=0.267, p50=0.342, p90=0.497, p99=1.164, min=0.009, max=16.694 — coerente con un feed ECN istituzionale (Dukascopy), tipicamente più stretto del broker retail usato nei test MT5 live; non è un'anomalia, è una caratteristica nota della fonte dati diversa.
- **791 giorni inizialmente segnalati** dallo script di audit come "ore vuote fuori dalla finestra di chiusura weekend attesa" — **verificato direttamente** (non assunto, come richiesto): ispezionati 5 giorni campione (2019-02-05/06/07, 2020-01-06/07), in OGNUNO l'unica ora vuota è le **22:00 UTC**, la nota fascia di bassissima liquidità fra la chiusura di New York e l'apertura Asia/Sydney per l'oro — un pattern di mercato reale, quotidiano e ricorrente, non un buco nei dati. Il modello di "ore di chiusura attese" implementato nello script di audit copriva solo la chiusura settimanale FX (venerdì 22:00 → domenica 22:00 UTC), non questa quiete infragiornaliera specifica dell'oro — è un falso positivo del MIO strumento di audit (modello troppo semplice), non un difetto del dataset Dukascopy.

**Verdetto: `DUKASCOPY_TICK_DATA_VALID`.** Il dataset è utilizzabile per SAR e per qualunque altra ricerca causale di questa fase.

---

## Risposte alle domande finali

**1. Quante strategie NEXUS sono realmente diverse semanticamente?**
≈46 su 53 registrate (vedi [[semantic_strategy_audit]]).

**2. Quali sono duplicate/minor variants/misnamed?**
7 cluster di duplicati/varianti (22 strategy_id): OB_MIT≡ORDER_BLOCK; {PIVOT_WICK, MALAYSIAN_SNR, LEVEL_CONFLUENCE(+M5), LEVEL_REACTION(+M5)}; SH_BMS_RTO/SMS_BMS_RTO; RSI_DIV/RSI_DIV_PINE; MACD/MACD_SMA200; SAR/PMAX/3COMMAS_BOT; AMD_CONT/PO3; WICK_SWEEP_REV/RECLAIM; TURTLE_SOUP/SWING_FALSEBREAK. 4 misnamed: THREE_BAR_DELIVERY_BREAK (ancora "CISD" nel nome tecnico), OB_MIT (wrapper letterale di ORDER_BLOCK), IFVG/FVG_MIT (codice morto), LIQ_VOID (strutturalmente irraggiungibile).

**3. Quali concetti attualmente chiamati strategy sono in realtà setup/event/trigger?**
La maggior parte delle strategie a singolo indicatore (SAR, MACD, ADX_RSI, TSI, BOLLINGER) sono in realtà un Setup (contesto di trend/momentum) + un Event (incrocio/soglia indicatore) fusi con UN SOLO Trigger hardcoded (entrata immediata) — non decoupled come richiede la nuova ontologia. Il cluster LEVEL_REACTION è letteralmente un Event ("tocco/breach di livello chiave") con 4 varianti di trigger/fonte-livello impacchettate come 4 "strategie" separate invece che come varianti di trigger di un unico Setup. VOLATILITY_BREAKOUT_CONFIRMED è essenzialmente un Event (espansione di volatilità confermata) più un trigger di chiusura-barra — il Setup "contesto + evento" non è mai stato isolato dal codice della strategia. SH_BMS_RTO/SMS_BMS_RTO sono in realtà un Setup a 3 Event concatenati (sweep→break struttura→ritorno), non un singolo evento atomico.

**4. Quali variabili fondamentali mancano oggi?**
Cross-market (DXY, yields USA, rapporto silver/gold, proxy di volatilità, positioning COT — vedi [[market_state_schema]]); directional efficiency (Kaufman); volatilità realizzata e relativo percentile; autocorrelazione/variance ratio; punteggio di displacement; tick-activity percentile; feature di sessione oltre ai filtri già impliciti in alcune strategie.

**5. Quali variabili esistenti sono ridondanti?**
I 4 pool di "livelli chiave" mantenuti separatamente da PIVOT_WICK/MALAYSIAN_SNR/LEVEL_CONFLUENCE/LEVEL_REACTION per la stessa idea di mercato (reazione a livello); i pool di livello di WICK_SWEEP_REV/RECLAIM e la Unified Level Engine che li ha in parte già consolidati; il calcolo ATR/EMA/RSI ripetuto indipendentemente dentro decine di strategie invece che condiviso da un unico Market State Vector.

**6. Quali variabili rischiano leakage/lookahead?**
Conferma di swing/pivot che richiede barre future per essere "confermata" (rischio se non gestita causalmente); percentili calcolati su finestre rolling se la finestra include il campione corrente in modo non causale; età di un livello se il pool non ha un tetto di freschezza (pattern `STALE_LEVEL_AGE_BIAS` già osservato); feature stagionali con pochi cicli annuali disponibili (alto rischio di overfitting anche se causalmente "sicure" in senso stretto); qualunque feature "TRUE_BREAK/FAILED_BREAKOUT" che per definizione è nota solo dopo N barre dall'evento iniziale.

**7. Quali edge components sono già supportati dai dati?**
Volatility-expansion-breakout (MEDIUM); trend-persistence/reversal SAR (MEDIUM-HIGH, asimmetrico); broker-cost-realism come gate di validità (STRONG); liquidity-reclaim come fenomeno di mercato reale ma non ancora catturabile in esecuzione (WEAK-MEDIUM).

**8. Quali edge components sono stati refutati?**
I 13 elencati in sezione 13 sopra (effetto Friday, level-age WICK, confound penetration/age/TF, qualità TRUE_BREAK/RETEST, failed-breakout fade, precondizioni di compressione volatilità/sessione, continuazione displacement-stack, regime standalone, famiglia PIVOT_WICK, famiglia LEVEL_REACTION/CONFLUENCE, WICK_SWEEP_REV/RECLAIM tutte le varianti, MACD H4 3 anni).

**9. Quali sono ancora unknown?**
STRUCT_LEVEL_SWEEP come strategia live (solo design + Python esplorativo); WICK_TICK_NATIVE (mai implementato); soglie di breach-depth validate sulla popolazione reale (oggi importate da uno studio esterno non replicato); displacement-imbalance-stack come ipotesi di fade (mai testata pulitamente); dati COT/positioning; distinzione raw-level vs trigger-price reclaim per WICK_SWEEP_RECLAIM; replica OB/FVG nel dataset Python STRUCT_LEVEL_SWEEP; baseline storiche di TURTLE_SOUP/JUDAS_SWING/LDN_REVERSAL/PO3 (esposte al bug di memoria non inizializzata, mai ri-verificate su una finestra dove hanno realmente fatto trading).

**10. Quali massimo 5 setup meritano il prossimo esperimento causale?**
1. **Volatility-expansion breakout — campione esteso**: unico candidato nativo MEDIUM con verdetto HOLD_NEEDS_MORE_EVIDENCE per campione live troppo sottile (n=14) — priorità massima, dati Dukascopy ora completi al 100% per un test più lungo.
2. **Asimmetria SELL del segnale SAR**: strutturale su 2 motori/periodi indipendenti — capire SE è un artefatto di regime (rally secolare) o una proprietà strutturale del segnale merita un esperimento causale dedicato, ora possibile su dati Dukascopy pre-2023 completi.
3. **Liquidity-reclaim con modello di esecuzione alternativo**: il fenomeno grezzo (WR 59% vs 16.9% baseline) è reale ma ogni variante di esecuzione finora testata (market M15-gated, tick-detection, limit-retest, fill-anchored) è stata refutata — un modello di esecuzione ancora non provato (es. ordine limite piazzato al momento del reclaim invece che al trigger originale) potrebbe chiudere il divario fenomeno-vs-eseguibilità.
4. **Penetration/ATR al momento dello sweep → TRUE_BREAK strutturale**: 2 su 3 periodi indipendenti hanno mostrato un effetto reale ma sotto la soglia di materialità — ora che il dataset Dukascopy è completo, un retest su campione più ampio può risolvere se è un vero effetto piccolo o rumore.
5. **Confound trend-regime su ADX_RSI/MACD/BOLLINGER "BUY-dominante"**: mai testato con segmentazione di regime — un esperimento causale che isoli sotto-periodi non-bull-secolare (ora possibile sull'intero storico tick Dukascopy) determinerebbe se è edge di trend-persistence reale o solo artefatto del rally 2023-2026.

---

## Raccomandazione di follow-up (non eseguita in questa fase)

Il mismatch sistemico `default_enabled` confermato per 10 strategie (AMD_CONT, BJORGUM, FVG_MIT, IFVG, LDN_REVERSAL, LIQ_VOID, OB_MIT, RANGE_FADE, THREE_BAR_DELIVERY_BREAK, TURTLE_SOUP — sezione 0/1) merita una passata dedicata di correzione della source-of-truth, strategia per strategia — stessa classe di fix già applicata a VOLATILITY_BREAKOUT_CONFIRMED, ma richiede verifica individuale (alcune potrebbero avere ragioni storiche diverse per `stato: attiva` nonostante il default OFF) prima di modificare `knowledge/strategy_database.json` in blocco. Non eseguito qui per restare dentro il perimetro "ricerca infrastrutturale, non ottimizzazione".
