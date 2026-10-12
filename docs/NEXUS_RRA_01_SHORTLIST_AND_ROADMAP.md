# NEXUS RRA-01 — Shortlist scientifica, Top 20 domande, Roadmap RECOVER/REPAIR/EXPLORE

Non è una classifica per Profit Factor. Priorità secondo: plausibilità del meccanismo, informazione nuova attesa, evidenza indiretta preesistente, indipendenza dei dati, costo computazionale, capacità dei detector esistenti, rischio overfitting/multiple-testing, rilevanza per l'EA/mercato, ridondanza. Riusa la coda-priorità esistente (`research_priority_queue_v1.json`, 8 criteri non pesati, PF escluso per policy) — non ne crea una seconda. Nessun esperimento qui è stato lanciato.

## 1. Shortlist scientifica (componenti meritevoli di approfondimento, non classifica PF)

1. **Protocollo same-feed A/B/C (BREAKOUT_ACC/ORDER_BLOCK)** — il pattern diagnostico più validato del corpus. Applicarlo alle 9 strategie DEFECT_CONFIRMED non quantificate è il lavoro a più alto rapporto informazione/costo disponibile oggi: il meccanismo è già dimostrato, manca solo la misura per ciascuna.
2. **g_adx/g_rsi/g_macd non ricalcolati per-pass** (Fase F, nuovo) — stesso meccanismo già dimostrato 3 volte (struttura, ORDER_BLOCK, TSI). Alta plausibilità, costo basso (stesso harness riusabile), rilevanza diretta per ADX_RSI (già FAILED nel backtest 6y — potrebbe essere la causa, non il mercato).
3. **FVG_CONT** — unica strategia che batte Buy&Hold con SELL genuino, ma `defect_status: UNKNOWN_REMEDIATION`. Prima di qualunque nuovo test, chiarire se il defect della famiglia FVG è stato risolto o no (gap di provenance, non di ricerca).
4. **Motore di confluenza generico** — gap strutturale confermato in Fase E. Costruirlo sopra `candidate_signature.py` permetterebbe di testare RECLAIM+struttura, o ORDER_BLOCK+liquidity sweep, senza nuove pipeline.
5. **LIQ_SWEEP, capire la causa dell'OOS negativo** — unico caso con OOS sufficiente e negativo. È il dato più informativo del corpus sul "cosa succede quando testiamo davvero fuori campione" — merita un'indagine dedicata (failure mode, non solo archiviazione).
6. **RSI_DIV, disaccordo di segno tra motori** — prima di decidere se la strategia è viva o morta, va risolto PERCHÉ TradingView e Python-sito disaccordano sul segno stesso (campione diverso? bug? regime?). Alta informazione, basso costo (solo diagnosi, no nuovo backtest).

## 2. Top 20 domande di ricerca più informative

Ordinate per valore informativo atteso vs costo, non per probabilità di successo.

1. Quanto delle 9 strategie DEFECT_CONFIRMED-non-quantificate (BAR_UPDN, PIVOT_WICK, PMAX, BB_SQUEEZE, SH_BMS_RTO, SH_BMS_RTO_V2, SILVER_BULLET, RANGE_FADE) ha un impatto materiale come ORDER_BLOCK (0% overlap) vs trascurabile?
2. g_adx/g_rsi/g_macd/g_macdSig non ricalcolati per-pass: quanto segnale di ADX_RSI (già FAILED) è dovuto a questo bug vs al mercato?
3. Perché TradingView e Python-sito disaccordano sul segno del risultato di RSI_DIV sullo stesso periodo-ish?
4. LIQ_SWEEP: la causa del fallimento OOS è overfitting sul periodo storico, un regime diverso, o un problema di esecuzione (il mismatch MQL5-ATR-fisso vs Python-dinamico già noto)?
5. Il defect FVG_CONT/FVG_MIT è stato davvero risolto (`UNKNOWN_REMEDIATION`)? Senza questa risposta, FVG_CONT (la strategia più promettente del corpus) resta inutilizzabile con fiducia.
6. L'asimmetria BUY/SELL in RECLAIM (tutto l'effetto concentrato su un lato) è un artefatto del periodo 2022-2023 (GOLD in forte uptrend) o un pattern strutturale del meccanismo?
7. La protezione Max Total DD (mai persistita su riavvio) ha effettivamente mancato un trigger reale in passato? Serve il log storico di riavvio EA per confermarlo.
8. BREAKOUT_ACC: il pattern BUY-dominante (69.4% continuation) è distinguibile dal semplice trend-alignment (100% confuso nel campione attuale, n=72)? Serve un campione con eventi contro-trend.
9. Un motore di confluenza generico (RECLAIM + struttura, o ORDER_BLOCK + liquidity sweep) produce selettività migliore di ciascun detector isolato?
10. Il collasso strutturale di SEQ-0009/SEQ-0015 (embargo≫gap mediano) è specifico di questi due meccanismi o un problema di design che colpirebbe qualunque futura sequenza con parametri simili?
11. Volume (tick o reale) aggiunge informazione a qualche detector esistente (sweep, breakout) se implementato e testato?
12. iFVG, mai implementato: vale la pena implementarlo dato che FVG "normale" è CANDIDATE/UNKNOWN_REMEDIATION, non un edge confermato?
13. Divergenza MACD (mai implementata, solo RSI divergence esiste ed è duplicata): la duplicazione RSI stessa nasconde un bug di cui unificare prima la logica?
14. SAR ha 3 verdetti diversi su 3 test diversi (vault=confermata, Serious3Y=borderline, external-validation=FAIL, live6y=-34.3R): qual è la causa della discrepanza — periodo, broker, o motore?
15. "Nessuna strategia supererebbe una prop firm" (verdetto su 8/8): quali regole specifiche di prop firm (DD giornaliero? consistency?) sono le più vincolanti, e sono risolvibili con risk sizing o sono strutturali?
16. Il modulo Market Regime Layer v1 (mai usato come trigger per design) aggiungerebbe valore se usato per STRATIFICARE la selezione di LIQ_SWEEP/ORDER_BLOCK invece che solo per diagnosi?
17. Timeframe M1/M5/W1 nel motore causale (`behavior_lab_v1`, oggi solo M15/H4): la stessa famiglia IMPULSE/PULLBACK mostra pattern diversi a grana più fine o più grossa?
18. `research_intelligence_v1` non importa ancora `contextual_edge_phase1`: una volta collegato, la memoria cross-family cambia priorità rispetto a oggi?
19. Le 5 strategie SUSPECT (non DEFECT_CONFIRMED) per cross-timeframe contamination (MACD_SMA200, ICHIMOKU_HULL_MACD, 3COMMAS_BOT, RSI_DIV_PINE, BOLLINGER) — il rischio pratico è davvero basso come classificato, o va riverificato ora che si sa che ADX/RSI/MACD globali hanno lo stesso problema?
20. SH_BMS_RTO v1 (il più promettente tra le ICT/SMC testate, campione piccolo): un campione più ampio sullo stesso detector conferma o il PF era rumore su n piccolo?

## 3. Roadmap: RECOVER / REPAIR / EXPLORE

### RECOVER (risultati esistenti non ancora classificati correttamente)
| Item | Costo | Dipendenze |
|---|---|---|
| Riconciliare `edge-validation-registry.json` (TSI defect_status) con l'artifact Phase 7.18 (FIX_CAUSALLY_VALIDATED) | Basso | Nessuna — solo lettura+decisione editoriale |
| Riconciliare conteggio strategie live (53 vs 55, registry vs Phase 7.11 census) | Basso | Nessuna |
| Chiarire `defect_status: UNKNOWN_REMEDIATION` di FVG_CONT/FVG_MIT | Basso-medio | Richiede rileggere il commit storico del fix, se esiste |
| Collegare VOLBRK Serious 3Y: aggiornare qualunque memoria/doc che lo segna ancora "PARTIALLY_BLOCKED" allo stato reale FAIL/ARCHIVE | Basso | Nessuna |
| Costruire `research_intelligence_v1.ingest.import_contextual_edge()` (adapter mancante, pattern identico a `import_behavior_lab_summary`) | Medio | Nessuna, solo codice nuovo additivo |

### REPAIR (esperimenti importanti invalidati da difetti di codice/dati/metodologia)
| Item | Costo | Dipendenze |
|---|---|---|
| Quantificare impatto reale sulle 9 strategie DEFECT_CONFIRMED non misurate (stesso protocollo A/B/C) | Medio (×9) | Harness già pronto (Phase 7.9/7.13) |
| Verificare/quantificare g_adx/g_rsi/g_macd non ricalcolati per-pass (nuovo) | Medio | Stesso harness, nuovo target |
| Persistere `g_maxDDPeakEquity` su file (richiede autorizzazione esplicita, è codice MQL5 live) | Basso (codice), ALTO (rischio se non autorizzato) | **Autorizzazione utente esplicita prima di toccare MQL5** |
| Fix `.gitattributes` per `macd_preregistration_v1.json` (binary marking) — chiude i 2 test rossi di `contextual_edge_phase1` | Basso | Nessuna |
| Correggere la collisione pytest dei file bakeoff `qwen2.5-*` (punto nel nome file) | Basso | Nessuna |

### EXPLORE (domande nuove, falsificabili, non duplicate)
| Item | Costo | Dipendenze |
|---|---|---|
| Diagnosi causa OOS negativo LIQ_SWEEP (domanda #4) | Medio | Dataset 7.24/7.25 già pronto |
| Motore di confluenza generico (domanda #9) | Alto | Richiede design + nuova preregistrazione, nuovo hypothesis_id |
| Diagnosi disaccordo di segno RSI_DIV tra motori (domanda #3) | Basso-medio | Nessuna, solo confronto dati esistenti |
| Estensione timeframe `behavior_lab_v1` a M1/M5/W1 (domanda #17) | Medio | Nessuna, estensione additiva di `bars.py` |
| Implementazione volume come feature (domanda #11) | Alto | Richiede nuovo detector, nuova preregistrazione |

## 4. Nota di integrazione con Research Intelligence

Nessuna di queste domande è stata preregistrata o eseguita in questa sessione (vincolo esplicito del task). L'ingresso naturale in RI-01 per ciascuna EXPLORE è `generator.py`/`hypotheses.py` (stessi template di `register_candidates`, origin `AI_PROPOSAL` se proposta da un modello, `HUMAN` se decisa dall'utente) — non un sistema parallelo. Le voci RECOVER/REPAIR, essendo correzioni di processo o difetti, seguono il percorso `IMPROVEMENT_PROPOSAL` già esistente in `review.py`/`proposals.py` (classi `DEFECT_FIX`/`PROCESS_IMPROVEMENT`), con l'eccezione della persistenza di `g_maxDDPeakEquity` che tocca EA/live e richiede quindi `touches_frozen_or_live=true` + approvazione umana esplicita, come da gate già esistente.
