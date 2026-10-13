# NEXUS RRA-01 — Research Recovery & Cross-Engine Architecture: Master Findings

**Stato: completo per quanto verificabile in questa sessione.** Copre la sintesi dei 7 censimenti paralleli (Fasi A/C/D/E/F del task + addendum coverage/gap). I deliverable di dettaglio (mappa strategie/varianti, Untested Experiment Registry, coverage matrix sparsa, shortlist, Top 20 domande, roadmap RECOVER/REPAIR/EXPLORE) sono in due documenti correlati: [NEXUS_RRA_01_STRATEGY_LEDGER_AND_COVERAGE.md](NEXUS_RRA_01_STRATEGY_LEDGER_AND_COVERAGE.md) e [NEXUS_RRA_01_SHORTLIST_AND_ROADMAP.md](NEXUS_RRA_01_SHORTLIST_AND_ROADMAP.md). Resta aperto solo il punto 7 di "Lavoro rimanente" (verifica indipendente sul codice — ora risolta, vedi §0 aggiornato) e l'implementazione effettiva (fuori scope di un audit: proposte, non codice).

Fonti: 7 censimenti in sola lettura (nessuna modifica a codice/EA, nessuno sweep, nessun accesso a split protetti) su `server/research_scripts/phase2..phase7_28`, `vault/01-Trading` (309 note), MQL5 detector coverage, caccia trasversale MT5/TradingView/parità, inventario Fast Research Engine.

## 0. Flag di sicurezza — causa confermata sul codice

**Protezione Max Total Drawdown non verificata/non scattante — causa trovata.** Fonte: nota vault "Verifica Max Total DD" (DD reale 22.83% contro soglia 10%, zero trigger, "non risolta"). Verificato sul codice reale: `g_maxDDPeakEquity` (`NXS_Globals.mqh:169`) è inizializzata a `0.0` e **non viene mai persistita su file** — a ogni riavvio dell'EA (ricompilazione, riavvio terminale/VPS, nuova sessione Tester) si azzera, e il tick successivo la imposta all'equity corrente, dimenticando qualunque picco storico precedente al riavvio. Se un riavvio avviene durante un drawdown già in corso, la protezione sottostima il drawdown reale dal vero picco storico. Non è confermato che questo sia stato LA causa dell'incidente specifico del 22.83% (servirebbe il log di riavvio di quel periodo), ma è un difetto reale e verificabile indipendentemente da quell'incidente. Nessuna modifica al codice eseguita (richiede autorizzazione esplicita separata, trattandosi di MQL5 live) — vedi roadmap REPAIR nel documento shortlist.

## 1. Discrepanze fattuali trovate (da riconciliare, non risolte qui)

1. **VOLBRK Serious 3Y**: la memoria di sessione lo segnava PARTIALLY_BLOCKED/non eseguire. Gli artifact (`phase7_8g/h/i`) mostrano che è stato eseguito 3 volte (2 run falliti per bug infrastrutturali, 1 valido: n=183, PF=0.867, expectancy −0.067R, CI95 attraversa zero) con verdetto finale **FAIL → ARCHIVE_CURRENT_DESIGN** (22/09).
2. **TSI defect status**: `contracts/edge-validation-registry.json` segna `defect_status: DEFECT_BLOCKED`. Gli artifact di Phase 7.17/7.18 dichiarano `FIX_CAUSALLY_VALIDATED` (guardia TF-scoped verificata su trace EA live). Registry non sincronizzato con gli artifact di fase.
3. **Conteggio strategie live**: registry canonico = 53 live/83 totali. Phase 7.11 census (vault) dichiara 55 live (corretto da 53). Non riconciliato.
4. **Working tree locale vs origin/main**: il branch usato per questo audit era 25 commit indietro rispetto a `origin/main`; `behavior_lab_v1/` e `research_intelligence_v1/` esistono solo su `origin/main` (PR #39/#40). Censiti via `git show origin/main:<path>`, nessun merge/pull eseguito. Chi continua questo audit deve fare lo stesso o aggiornare il branch.
5. **Causa dei 2 test falliti in `contextual_edge_phase1`** (notati durante un task precedente in questa stessa sessione come "pre-esistenti, non riverificati"): **ora risolta come diagnosi** — `macd_preregistration_v1.json` non è marcato `binary` in `.gitattributes`; con `core.autocrlf=true` il checkout Windows riscrive LF→CRLF, l'hash sul disco non combacia col sidecar, e `load_frozen_preregistration()` solleva fail-closed per design. Non corretto (richiede modifica `.gitattributes`, fuori scope di un audit).

## 2. Fase F — Matrice detector MQL5 (sintesi; dettaglio completo nei censimenti)

Nessun detector è READY. Il meglio osservato è CANDIDATE/FORWARD_REQUIRED. Rischi di parità cross-timeframe **nuovi, non ancora in nessun registro**:
- `g_atr` globale (soglia Order Block/FVG) resta fisso sull'entry-TF anche nei pass multi-TF del router — diverso da `g_struct`, già corretto dalla v2.0.34.
- `g_adx`/`g_rsi`/`g_macd`/`g_macdSig` non ricalcolati per-pass — istanza non rimediata di CROSS_TIMEFRAME_STATE_CONTAMINATION.
- RSI divergence: due implementazioni diverse coesistono nello stesso codice (ammesso da un commento nel codice stesso).

Gap reali (concetti assenti in tutto MQL5): volume (tick/real) come feature; iFVG; etichetta MSS distinta da CHOCH; divergenza MACD; confluenza volume-prezzo.

## 3. Fase E — Fast Research Engine: verdetto (da censimento dedicato)

| Requisito | Verdetto | Componente |
|---|---|---|
| Tick/barre multi-TF M1..W1 | PARZIALE | `behavior_lab_v1` solo M15/H4 |
| Indicatori/detector causali | COPERTO | `behavior_lab_v1/events.py`, `contextual_edge_phase1/macd_features.py` |
| Feature multidimensionali | PARZIALE | solo 1 famiglia (`contextual_edge_phase1`, 60 celle) |
| Confluenze | **MANCANTE** | nessun motore generico trovato |
| Eventi/sequenze | COPERTO | `phase7/engine/sequence_structural_feasibility_gate.py`, `candidate_lifecycle.py` |
| Outcome/costi | COPERTO | `behavior_lab_v1/events.py`, `baseline_engine_v4.py` |
| Ricerca regime/sessione | COPERTO | `behavior_lab_v1/sessions.py`, `compare_regime_classifiers.py` |
| Test anti-overfitting | COPERTO | `dependence_validity_gate.py`, `multiple_testing_v2.py`, `matched_pair_permutation_test.py`, `control_reuse_ledger.py`, `post_hoc_quarantine.py` |

**Raccomandazione**: non costruire un motore parallelo. Estendere lo stack esistente su 3 gap: timeframe unificato M1..W1, motore di confluenza generico, adapter `research_intelligence_v1.ingest.import_contextual_edge()` (oggi assente — RI-01 importa solo da `phase7_26` e `behavior_lab_v1`).

Nessun benchmark hardware (tempo/RAM/throughput) esiste in nessun componente censito — gap dichiarato, non inventato.

## 4. Fase D — Cross-Engine Parity: stato reale

Confronto a 3 motori documentato (`vault/.../Confronto 3 Motori 17-07`): MACD concorda su MT5/TradingView/Python; ADX_RSI concorda su direzione, diverge su drawdown; SAR in disaccordo diretto sul segno del PF; **RSI_DIV è il caso più serio: i motori disaccordano persino su se la strategia sia profittevole**, attribuito a differenza di campione (1.5y TradingView vs 3.5y sito), non a bug. Principio applicato: nessun motore è tie-breaker, MT5/produzione resta verità per le decisioni live.

Famiglia di script `parity`/`fidelity` in Phase 7 (matura, molti JSON reali): `build_python_fidelity_classification.py` dichiara formalmente che Python non può validare PF/P&L di LIQ_SWEEP (logica di uscita diverge da MQL5) — disciplina "MT5 = ground truth" applicata, non solo dichiarata.

TradingView: implementazione reale (10 file `.pine` v6, non solo proposta), Batch 1 testato con risultati reali su TradingView Tester nativo, Batch 2 codice pronto ma non ancora eseguito. Nessuna integrazione automatica (flusso manuale).

## 5. Catena evidenziale più rigorosa trovata (RECLAIM/sweep, esempio di metodo)

Phase 5 (discovery) → RECLAIM SUPPORTED_EDGE (n=300) → Phase 5.5 (audit retroattivo) scopre contaminazione da selezione post-hoc, riclassifica a POST_HOC_CANDIDATE/E2 → Phase 6 (true holdout) verdetto BORDERLINE (ΔP=0.057 contro soglia 0.15, asimmetria BUY/SELL) → Phase 6.5 (dependence audit) HIGH overlap 99.1% → Phase 6.6 chiusura formale: **E2, RETAIN_E2, promotion_allowed=false**. Questo è il pattern di rigore che il resto del corpus (BREAKOUT_ACC, ORDER_BLOCK, TSI, LIQ_SWEEP) replica in Phase 7: tutte le 4 famiglie economicamente testate restano in stato `EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION` o peggio — **nessuna strategia nel corpus ha mai raggiunto una promozione economica oltre E2/discovery**, salvo le correzioni mecchaniche (fix di bug, diverso da edge).

## 6. Componenti riutilizzabili confermati (indipendenti dall'esito strategia)

Baseline Engine v4 (matching NN direction/state-aware), Market Regime Layer v1, Multiple Testing Ledger BH-FDR, Leakage Guard, Dependence/clustering audit + block bootstrap, Dukascopy downloader v2, Research Evidence Ledger + Decision Card schema, `sequence_structural_feasibility_gate.py`, `candidate_lifecycle.py` (macchina a stati GENERATED→...→SUPPORTED/REFUTED), `nxs_benchmark_generators.py` (modelli nulli: random/unconditional/periodic/regime-matched), protocollo diagnostico same-feed A/B/C (BREAKOUT_ACC/ORDER_BLOCK) — candidato a standard per le 9 strategie DEFECT_CONFIRMED non ancora corrette.

## 7. Stato dei deliverable

Completati in questa sessione (vedi i 2 documenti correlati):
1. Mappa strategie/varianti con stato di test per famiglia — [STRATEGY_LEDGER_AND_COVERAGE §1](NEXUS_RRA_01_STRATEGY_LEDGER_AND_COVERAGE.md#1-registro-storico-per-famiglia-stato-di-test-non-di-implementazione).
2. Untested Experiment Registry (TESTED_VALID/INCONCLUSIVE/INVALID/PARTIALLY_TESTED/NEVER_TESTED/UNKNOWN) — [§2](NEXUS_RRA_01_STRATEGY_LEDGER_AND_COVERAGE.md#2-untested-experiment-registry--gap-espliciti-perimetro-censito-dichiarato).
3. Coverage Matrix sparsa (solo combinazioni osservate, non materializzata esaustivamente come richiesto) — [§3](NEXUS_RRA_01_STRATEGY_LEDGER_AND_COVERAGE.md#3-coverage-matrix--rappresentazione-sparsa-solo-combinazioni-osservate).
4. Test da non ripetere — [§4](NEXUS_RRA_01_STRATEGY_LEDGER_AND_COVERAGE.md#4-test-da-non-ripetere-evidenza-negativa-sufficiente).
5. Shortlist scientifica + Top 20 domande + roadmap RECOVER/REPAIR/EXPLORE — [SHORTLIST_AND_ROADMAP.md](NEXUS_RRA_01_SHORTLIST_AND_ROADMAP.md).
6. Flag di sicurezza Max Total DD — causa confermata sul codice, §0 sopra.

Non fatto (proposte esplicitamente fuori scope di un audit, richiedono decisione/autorizzazione dell'utente):
- Implementazione dell'adapter `research_intelligence_v1.ingest.import_contextual_edge()` (proposto, non scritto).
- Qualunque modifica al codice MQL5 (persistenza `g_maxDDPeakEquity`, fix `.gitattributes`, ricalcolo per-pass di ADX/RSI/MACD) — tutte richiedono autorizzazione esplicita separata, elencate nella roadmap REPAIR.
- Esecuzione di una qualunque delle 20 domande di ricerca (vincolo del task: solo audit/progettazione).

Tutto il materiale grezzo dei 7 censimenti (ciascuno 2000-4000 parole, denso e citato per file) resta nella trascrizione della sessione — nessuna sintesi in questi 3 documenti ha inventato numeri non presenti in quei report.
