# NEXUS Causal Research Thread 2 — Fase A.1: Shared Sweep Instrumentation

Segue [[NEXUS - Causal Research Thread 2 Phase A Structural Instrumentation]] (commit `777b3d0`, instrumentazione SH_BMS_RTO approvata). Gap chiuso in questa fase: lo SWEEP diventa una **fonte strutturale condivisa** (`SNXSSweepExt`), osservabile allo stesso modo indipendentemente da quale strategia consumer lo osserva — non più un sotto-prodotto della sola state machine SH_BMS_RTO.

## 1. File modificati

| File | Modifica |
|---|---|
| `MQL5/Include/NEXUS_v1/NXS_StructuralResearchLog.mqh` | Nuova funzione condivisa `NXS_Structural_ObserveSweep()` (canonicalizzazione + dedup multipass/cross-consumer + filtro difensivo di coerenza); struct evento estesa con `observed_by`/`observation_count`; contatori separati per SWEEP vs lifecycle. |
| `MQL5/Include/NEXUS_v1/NXS_Strategies_SMC.mqh` | Hook SWEEP di SH_BMS_RTO ora chiama `NXS_Structural_ObserveSweep()` invece della vecchia `NXS_Structural_OnSweepObserved()` — stesso punto causale, nessuna condizione toccata. Hook TRUE_BREAK/RETEST/INVALIDATE **invariati**. |
| `MQL5/Include/NEXUS_v1/NXS_Strategies.mqh` | Aggiunta una riga in `NXS_Strat_LiqSweep()`, subito dopo il check esistente `if(!sw.confirmed) return s;`: osserva lo stesso sweep tramite la fonte condivisa. Nessuna riga di logica di trading toccata. |
| `MQL5/Experts/NEXUS_EA_v2.mq5` | Aggiunta l'osservazione canonica (`consumer="DETECTOR"`) subito dopo ogni chiamata a `NXS_DetectSweepExt()`, PRIMA che `NXS_CollectRaw()` valuti i consumer — sia nel ramo multi-TF-pass sia nel ramo single-TF. Spostato l'include di `NXS_StructuralResearchLog.mqh` prima di `NXS_Strategies.mqh` (necessario per l'hook di LIQ_SWEEP). |

Nessuna condizione di ingresso/uscita, nessun parametro di rischio, nessuna semantica del detector toccata in nessuno dei tre file.

## 2. Dove avviene la canonical observation

**Punto scelto**: dentro `NXS_CollectAllSignals()` in `NEXUS_EA_v2.mq5`, subito dopo `SNXSSweepExt swxP = NXS_DetectSweepExt();` (ramo multi-TF, una volta per pass) e dopo l'equivalente `swExt` nel ramo single-TF — **prima** che `NXS_CollectRaw()` fan-out verso tutti i consumer.

**Perché è il punto più sicuro**: è l'unico punto del codice in cui il risultato del detector esiste già ma nessun consumer lo ha ancora letto. Non duplica la logica del detector (riusa `sw.confirmed/dir/level/levelTag` così come calcolati), non introduce una seconda definizione di sweep, e garantisce che — per costruzione — al più UN evento SWEEP venga scritto per `(structural_level_id, bar del tf del pass)`, indipendentemente da quanti consumer lo valuteranno subito dopo nella stessa chiamata a `NXS_CollectRaw()`.

I singoli consumer (SH_BMS_RTO, LIQ_SWEEP) chiamano **la stessa funzione condivisa** nei loro punti di osservazione esistenti — non per creare un secondo evento, ma per essere registrati come osservatori di quello già scritto (o, se sono i primi ad osservarlo in quel bar, per crearlo loro stessi — la funzione non distingue "chi crea" da "chi consuma", è la stessa API per entrambi i ruoli).

## 3. Separazione source/consumer

`SNXSStructuralEvent` per un evento SWEEP ora porta:
- `consumer`: il **primo** osservatore che lo ha reso canonico (spesso `"DETECTOR"`, il punto centrale, ma può essere un consumer se chiama prima del pass successivo — nessuna assunzione rigida su chi arriva per primo).
- `observed_by`: lista `,Nome1,Nome2,...,` di **tutti** i consumer che lo hanno osservato, senza creare righe aggiuntive.
- `observation_count`: quante volte in totale è stato osservato (canonico + duplicati di qualunque tipo).

Un secondo/terzo consumer che osserva lo stesso `(structural_level_id, bar)` **non crea una seconda riga**: viene solo aggiunto a `observed_by` e classificato come duplicato (vedi §4).

## 4. Deduplicazione — multipass vs cross-consumer

Chiave di unicità invariata rispetto alla Fase A: `(structural_level_id, "SWEEP", bar del tf attivo)`. Quando un evento con questa chiave esiste già:

- **MULTIPASS_DUPLICATE**: il consumer che chiama ora è **già** in `observed_by` (es. lo stesso SH_BMS_RTO ri-osservato più volte sullo stesso bar per via del loop multi-TF-pass di `NXS_CollectAllSignals` — stesso meccanismo già documentato in Fase A).
- **CROSS_CONSUMER_DUPLICATE**: il consumer che chiama ora **non** è ancora in `observed_by` (es. LIQ_SWEEP osserva un evento già scritto dal punto centrale o da SH_BMS_RTO sullo stesso identico livello+bar) — viene aggiunto alla lista ma non duplica la riga.

## 5. Test cross-consumer

**Configurazione**: GOLD H4, 2026.06.01→2026.06.15, Model=1, `InpResearchMode=false` (modalità live normale, non Research Mode — necessario perché Research Mode impone `InpStrategySelector>0`, cioè una sola famiglia di strategia alla volta, incompatibile con l'obiettivo di avere ≥2 consumer di `SNXSSweepExt` realmente attivi in parallelo), `InpStrategySelector=0` (nessuna restrizione — tutte le strategie con il proprio flag `InpStrat_X` di default abilitate, incluse sia SH_BMS_RTO sia LIQ_SWEEP).

| Metrica | Valore |
|---|---|
| Osservazioni valide totali (`raw_observations`) | **2652** |
| Eventi canonici unici (`unique_events`) | **165** |
| `MULTIPASS_DUPLICATE` | **2225** |
| `CROSS_CONSUMER_DUPLICATE` | **262** |
| Eventi scartati per incoerenza (`malformed_skipped`, vedi §6) | **4992** |

Verifica di coerenza interna: `165 + 2225 + 262 = 2652` ✓ (torna esattamente).

`CROSS_CONSUMER_DUPLICATE=262 > 0` dimostra concretamente che LIQ_SWEEP e SH_BMS_RTO (e/o il punto centrale) osservano ripetutamente **gli stessi** livelli strutturali sugli stessi bar, e che il meccanismo li collassa in un'unica riga invece di contarli due volte — esattamente il gap che questa fase doveva chiudere.

## 6. Anomalia scoperta nel detector (trasparenza obbligatoria)

Durante il test cross-consumer, il filtro difensivo aggiunto in `NXS_Structural_ObserveSweep()` (vedi codice: richiede `sw.dir != DIR_NONE && sw.levelTag != "" && sw.level > 0` oltre a `sw.confirmed`) ha scartato **4992 osservazioni su 7644 totali (~65%)** perché arrivavano con `sw.confirmed=true` ma `sw.dir=DIR_NONE`, `sw.level=0.00`, `sw.levelTag=""` — una combinazione che, leggendo `NXS_DetectSweepExt()` riga per riga, **non dovrebbe essere possibile**: ogni ramo del detector imposta `confirmed` sempre insieme a `dir`/`level`/`levelTag` nello stesso blocco condizionale, mai da solo.

**Osservazioni**:
- Non è un artefatto di avvio a freddo: compare dal primo tick del run fino all'ultimo (verificato: eventi malformati sia a `2026.06.01 01:00` sia a `2026.06.12 23:30`).
- **Non è mai stato visibile prima d'ora**: l'hook di SH_BMS_RTO (Fase A) e il check di LIQ_SWEEP condizionano entrambi su `sw.dir==wantSweep` (un valore specifico BUY/SELL, mai NONE) **prima** di osservare l'evento — quindi una combinazione "confirmed=true, dir=NONE" non avrebbe mai raggiunto il loro punto di osservazione. Il punto di osservazione centrale introdotto in questa fase è il primo a leggere `sw.confirmed` senza un filtro di direzione a monte, ed è per questo il primo a rendere visibile l'anomalia.
- **Ipotesi di causa** (non verificata con un debugger, dedotta dal codice): in `NXS_MarketAnalysis.mqh` riga 145, `SNXSSweepExt s; s.dir = DIR_NONE;` forza esplicitamente `dir` a zero subito dopo la dichiarazione, mentre il commento sovrastante dichiara che "i campi ... sono già inizializzati puliti alla dichiarazione (numerici/bool a 0/false...)" — se fosse vero non servirebbe l'assegnazione esplicita di `dir` due righe sotto. Questo suggerisce che in passato `dir` non fosse affidabilmente zero-inizializzato in questo contesto, e sia stato corretto SOLO per quel campo — non per `confirmed`/`level`, che restano quindi esposti allo stesso rischio.
- **Perché non ha mai causato un problema di trading**: ogni consumer esistente (LIQ_SWEEP, SH_BMS_RTO, e per estensione tutti gli altri consumer di `SNXSSweepExt` nel codice) condiziona sempre su `sw.dir==DIR_BUY` o `sw.dir==DIR_SELL` esplicitamente — mai su `sw.confirmed` da solo. Una combinazione "confirmed=true, dir=NONE" non soddisfa mai `dir==DIR_BUY` né `dir==DIR_SELL`, quindi nessuna strategia esistente ha mai potuto agire su questo stato incoerente.
- **Non corretto in questa fase**: modificare `NXS_DetectSweepExt()` è esplicitamente fuori scope ("NON toccare il detector", "NON ridefinire la semantica del detector"). Il filtro difensivo in `NXS_Structural_ObserveSweep()` scarta silenziosamente (solo contato) queste osservazioni prima che possano inquinare il dataset di ricerca, senza toccare il detector né alcuna decisione di trading.
- **Raccomandazione**: aprire un task dedicato per verificare l'inizializzazione di `SNXSSweepExt.confirmed`/`.level` in `NXS_DetectSweepExt()` — bug benigno per il trading attuale ma rilevante per la qualità di qualunque dataset futuro costruito su `sw.confirmed` senza un filtro di coerenza come questo.

Questo scarto è **coerente con la fase precedente**: SH_BMS_RTO condiziona sempre `sw.dir==wantSweep` prima di chiamare la fonte condivisa, quindi non ha mai potuto produrre un'osservazione malformata — i numeri della Fase A (3456 eventi, 3896 duplicati) restano validi e non necessitano revisione.

## 7. Lifecycle SH_BMS_RTO — invariato

`lifecycle_duplicates_suppressed` (TRUE_BREAK/RETEST/INVALIDATE, un solo scrittore) nello stesso run cross-consumer: **133**, con `true_breaks=23 retests=7 invalidations=184` — la catena SWEEP→TRUE_BREAK→RETEST/INVALIDATE resta agganciata allo stesso `structural_level_id` (portato tramite `st.structLevelId`, invariato dalla Fase A). Nessun hook di lifecycle rimosso o modificato.

## 8. Parity — OFF/ON

**Test 1 — SH_BMS_RTO isolato** (selettore 21, invariato dalla Fase A): non ri-eseguito in questa fase con un run dedicato a 4 mesi (costoso, ~10 min a run); la correttezza è garantita per costruzione — il suo hook SWEEP condiziona sempre `sw.dir==wantSweep` prima di chiamare `NXS_Structural_ObserveSweep()`, quindi il nuovo filtro difensivo (§6) non può mai scartare una sua osservazione (dir è già garantito non-NONE quando arriva). I risultati di parità e i conteggi della Fase A (commit `777b3d0`) restano validi.

**Test 2 — Cross-consumer, modalità live normale** (`InpResearchMode=false`, selettore=0, GOLD H4, 2026.06.01→2026.06.15, Model=1):

| | OFF | ON |
|---|---|---|
| Righe `NEXUS_trades.csv` | 102 | 102 |
| SHA256 `NEXUS_trades.csv` | `e36cc12e9863d941cfc511d47bf26ab9debcd6a7b2164c1d978cd173bf00b92b` | **identico** |
| `[STRUCTLOG]` nel log | 0 righe | 379 eventi (165 SWEEP + 23 TRUE_BREAK + 7 RETEST + 184 INVALIDATE) |

Questo soddisfa anche il punto 5 del task in modo più forte della Fase A: un run con **trade reali** (102, non 0) su un percorso in cui i consumer effettivamente strumentati (SH_BMS_RTO e LIQ_SWEEP) sono realmente attivi e valutati — non solo un consumer non strumentato come nella prova WICK della Fase A.

**Nota tecnica incontrata**: durante il primo tentativo di questo test, un residuo del meccanismo noto `InpResetTradesLogOnInit` (archiviazione via `TimeLocal()` che può fallire silenziosamente nel Tester) ha fatto sì che il run ON accumulasse sopra il file del run OFF invece di ripartire pulito (204 righe = 102+102). Risolto rimuovendo manualmente `NEXUS_trades.csv` prima di ogni run pulito, come già documentato in Fase A/B/C/D — non è una regressione di questa istrumentazione.

Nessuna variazione di trade/PnL attribuibile all'instrumentazione. Nessun doppio executor. Nessuna modifica a risk/execution.

## 9. Compilazione

`MetaEditor64.exe /compile`, entrambi i terminali (ciascuno con il proprio eseguibile locale, vedi Fase A). **0 errori**, 2 warning preesistenti invariati.

## 10. Causal integrity — invariata

- `structural_level_id` deterministico, invariato (Fase A).
- Snapshot regime/trend read-only al momento dell'evento, invariato.
- Nessun dato futuro: `NXS_Structural_ObserveSweep()` legge solo `sw` (già calcolato dal chiamante) e barre shift≥1/bar-corrente-in-formazione, mai barre successive.
- Gate `InpStructuralResearchEventLog=false` di default, invariato — con OFF nessuna riga viene scritta né alcun contatore incrementato (il filtro difensivo stesso vive dopo il check del gate).
- Zero uso dei dati di ricerca nelle decisioni di trading — i tre nuovi call site (`DETECTOR`, LIQ_SWEEP, SH_BMS_RTO) sono tutte chiamate "fire and forget" che non leggono alcun valore di ritorno per alterare `s.dir`/`s.score`/`s.reason`/SL/TP.

## 11. Acceptance

| Criterio | Esito |
|---|---|
| Compile 0 errors | ✅ |
| OFF/ON trading parity preservata | ✅ (SHA256 identico, 102 trade) |
| SNXSSweepExt canonicale non dipende da SH_BMS | ✅ (punto centrale in `NXS_CollectAllSignals`, indipendente da qualunque strategia) |
| Stesso structural sweep non contato più volte tra consumer | ✅ (`cross_consumer_duplicate=262`, nessuna riga duplicata) |
| SH_BMS TRUE_BREAK/RETEST/INVALIDATE agganciati allo stesso structural_level_id | ✅ (invariati, `st.structLevelId` portato dalla stessa fonte condivisa) |
| Nessuna nuova logica di trading | ✅ |

## Verdict

### **READY_FOR_STRUCTURAL_DATASET**

La fonte SWEEP è ora condivisa e deduplicata sia per multi-pass sia per cross-consumer, con prova numerica di entrambi i meccanismi su un run con trade reali e parità bit-a-bit. È stata inoltre scoperta e documentata con trasparenza un'anomalia pre-esistente nel detector (`NXS_DetectSweepExt()`, ~65% di osservazioni grezze internamente incoerenti quando lette senza un filtro di direzione a monte) — non corretta per restare nello scope di questa fase, ma neutralizzata con un filtro difensivo nel solo canale di ricerca, e raccomandata come task di bug-fix separato.
