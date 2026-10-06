# CONTEXTUAL_EDGE_DISCOVERY_V1 — Design Scientifico

**Stato:** proposta di design, non ancora committata — in attesa di revisione utente. Nessun codice scritto, nessun nuovo backtest eseguito, nessun parametro ottimizzato, nessun decision engine costruito, nessuna modifica a runtime/MQL5. Questo documento specifica il protocollo che Codex implementerà in una Phase 1 piccola e falsificabile, non lo implementa.

**Domanda che il protocollo deve rispondere, per ciascuno dei 6 componenti iniziali** (ADX_RSI, LIQ_SWEEP, ORDER_BLOCK, FVG_CONT, BREAKOUT_ACC, MACD): dato lo stato del mercato prima dell'ingresso, questo componente aggiunge valore condizionale misurabile, in quali stati, con quale frequenza e con quale robustezza — non "qual è il suo PF standalone".

---

## 0. Perché questo documento riusa, non inventa

Prima di proporre qualunque protocollo nuovo ho verificato se esiste già un precedente. Esiste, ed è sostanziale: l'arco **Phase 4→5→5.5→6→6.5→6.6→7.0-7.5A** (vault/01-Trading, commit `ad14e97`→`8593f9c`) ha già costruito un'ontologia causale di mercato, uno schema evento/componente/outcome/probabilità, un leakage guard, un Discovery Engine v2 mai bloccato, e si è fermato su un blocco statistico **specifico delle sequenze multi-step**, non dei componenti singoli che servono qui. Il protocollo sotto riusa esplicitamente quell'infrastruttura dove si applica e si allontana da essa esattamente dove quel blocco l'ha dimostrata inadatta. Ogni sezione dichiara cosa riusa e da dove.

**Lezione da non ripetere** (Phase 5): il componente promosso come caso di punta era in realtà `CONTAMINATED_VALIDATION` — scelto come headline **dopo** aver visto i risultati di validazione di tutti i 14 candidati del batch. Questo è esattamente il meccanismo contro cui questo design si costruisce (vedi §9, §11).

**Lezione da non ripetere** (Phase 7.4A): un gate di validità statistica che condiziona il rigetto sulla stessa diagnostica calcolata sul campione del test produce selezione avversa (premia i falsi positivi più eclatanti, fino a 2.5-7× il tasso nominale) — e non migliora aumentando n, perché il difetto è strutturale, non di campione. Questo design non costruisce un simile gate circolare (vedi §12).

**Precisazione esplicita, perché importante: Phase 7.4A non è "fallita tutta".** È fallito specificamente quel gate/meccanismo di selezione statistica sotto dipendenza temporale (il `SequenceBaselineAdapter`, il gate di validità condizionato, e la conclusione `SEQ-0015 formally non-viable`) — un problema nato dal caso *sequenze multi-step con overlap temporale pesante*, non un difetto dell'infrastruttura sottostante. Tutto il resto costruito nello stesso arco resta valido e riusato esplicitamente in questo documento, perché appartiene a un livello diverso (Phase 4, non Phase 7.4A) o perché non è mai stato coinvolto nel blocco: l'ontologia di mercato (§1-§4), il leakage guard (§12), l'evidence grading E0-E6 (§13), l'event/component schema (§3), `BaselineEngineV4` (§7) e il Discovery Engine v2 di Phase 7.0-7.1 (§8) — quest'ultimo **mai bloccato**, ha prodotto un `NO_SUPPORTED_CANDIDATE` onesto su un caso reale (RECLAIM) prima che il progetto escalasse al caso sequenze dove poi si è bloccato. Solo lo strato di selezione specifico delle sequenze va lasciato indietro.

---

## 1. Context vector pre-entry

**Riuso diretto:** `market_state_schema.md` (Phase 4) — vettore di stato già definito con `observation_point` esplicito per ogni campo (niente che richieda informazione post-entry). Il dataset causale reale esiste già: `market_state_dataset_v1.csv`, 4809 barre H4, Dukascopy, già costruito e non ricostruito ex novo qui.

**Estensione richiesta per Phase 1:** il vettore Phase 4 non include ancora le feature di costo reale (spread/slippage percentile) usate dal cost-calibrated re-evaluation del 15-09 (`ff9f0e5`, 24.1M tick). Aggiungere come campo opzionale del context vector il profilo di costo osservato nella finestra (uno dei 4 profili già calibrati), **non** un nuovo motore di costo.

## 2. Market/regime state

**Problema da risolvere prima di qualunque test (prerequisito Phase 1, non un test di edge):** esistono oggi **due** classificatori di regime costruiti indipendentemente e mai confrontati tra loro:
- `market_regime_layer_v1.py` (Phase 4, 18/09) — 5 stati: HIGH_VOL / LOW_VOL / TRANSITION / TRENDING / RANGING, su H4.
- Il classificatore causale di Phase 7.27 (28-09) — matching per trend/volatilità/anno, usato per il regime-controlled benchmark che ha riqualificato la dominanza BUY.

**Requisito Phase 1:** prima di usare un regime come variabile di contesto, verificare che i due classificatori producano etichette coerenti sulle finestre in comune (anche solo un confronto a matrice di confusione). Se divergono in modo sostanziale, dichiararlo come gap aperto — non significa che uno dei due sia sbagliato, significa che "regime" non è ancora un concetto unificato nel progetto e questo design non deve pretendere che lo sia. Nessun nuovo classificatore va costruito in Phase 1: si riusa quello dei due (o la loro intersezione) che risulta più coerente con la granularità richiesta dal componente in test.

**Vincolo esplicito su questo passo:** è un **controllo di compatibilità**, non una campagna di ottimizzazione dei regimi. Non va tunato nessun parametro di nessuno dei due classificatori per farli convergere, non va costruita una terza versione "migliorata", non va scelto il classificatore che "fa vedere meglio" il risultato MACD della Phase 1 — la scelta tra i due (o la loro intersezione) va fatta **prima** e indipendentemente da qualunque risultato di conditional expectancy su MACD, esattamente come la preregistrazione di §8 richiede.

## 3. Component/event representation

**Riuso diretto:** `event_registry_schema.md` (14 famiglie evento già definite, Phase 4) come base. Per ciascuno dei 6 componenti, un record causale con `observation_point` esplicito, **non** un semplice flag binario fired/not-fired:

- **ADX_RSI, LIQ_SWEEP, ORDER_BLOCK, FVG_CONT, BREAKOUT_ACC**: rappresentati come evento discreto (fired/not-fired) + le variabili continue sottostanti già disponibili dal loro stesso calcolo (es. ampiezza del liquidity sweep, distanza dalla order block zone) come feature di contesto aggiuntive, non solo come trigger binario.
- **MACD**: rappresentato **esplicitamente come feature continua** (valore histogram, slope, stato di crossover), non come segnale direzionale standalone — coerente col fatto che il suo status è `FAILED` standalone (Phase F, `edge_validation_status`) ma la domanda qui è se porta informazione di momentum/conferma quando combinato con contesto, non se è tradabile da solo.

**Vincolo di provenance obbligatorio (diretto da `EDGE_VALIDATION_REGISTRY_V1`, commit `3a0906a`):**
- **BREAKOUT_ACC** e **ORDER_BLOCK**: usare **solo** la logica di generazione segnale post-fix (`651d3a2`, `17da794`). Qualunque dataset o replay che usi la logica pre-fix è `CONTAMINATED_EVIDENCE` per definizione e non entra in questo lavoro.
- **LIQ_SWEEP**: usare solo la logica post-fix del detector (14-09). Il risultato OOS n=6 esistente resta `evidenza negativa con campione insufficiente`, non un prior che pre-giudica il nuovo test.
- Nessuno dei 6 componenti va preso dalla loro versione pre-fix o da `knowledge/strategy_database.json` (stale, 19/07) — solo dalla logica di generazione segnale corrente.

## 4. Outcome/path labels

**Riuso diretto:** `outcome_schema.md` (Phase 4) — superficie multi-soglia in R già definita e già usata su dati reali in Phase 5-6. Nessuna nuova definizione di outcome necessaria per Phase 1.

## 5. Recurrence metrics

Per ogni cella (componente × stato di regime): frequenza del componente **condizionata al regime** = (numero di eventi del componente osservati in quel regime) / (numero totale di barre eleggibili in quel regime nel periodo). Riportare sempre insieme a: (a) quota del periodo totale occupata da quel regime (per sapere se un "alto recurrence" è su un regime raro), (b) numero assoluto di eventi (per applicare §12 prima di qualunque interpretazione).

## 6. Conditional expectancy

Expectancy (R medio, per-soglia della superficie outcome di §4) del componente **condizionato al regime**, calcolata separatamente per cella — mai aggregata attraverso regimi diversi prima di aver fatto il confronto di §7.

## 7. Separare habitat effect da signal effect (il nucleo del task)

**Riuso diretto e diretto ampliamento del metodo già validato in Phase 7.27**, che ha già dimostrato di funzionare su questo esatto problema (dominanza BUY → largamente spiegata dal regime). Generalizzazione per componente singolo:

Per ogni cella (componente × regime), confrontare la conditional expectancy del componente (§6) contro un **benchmark regime-matchato** — non contro zero, non contro buy&hold generico, ma contro la distribuzione di outcome di barre nello stesso regime **senza** quel componente presente, usando lo stesso matching causale (`BaselineEngineV4`, già costruito e mai bloccato, con `match_dimensions` su trend/volatilità/periodo). Se il componente non supera il proprio benchmark regime-matchato con margine statisticamente significativo (dopo §11), l'edge osservato è attribuibile all'habitat, non al segnale — esattamente la correzione che l'utente ha richiesto di applicare con cautela, non come falsificazione automatica ma come declassamento di confidenza (vedi §14).

## 8. Robustness / metodologia OOS

**Riuso diretto della tassonomia già matura** di `independent_validation_integrity_v1.md` (Phase 4, 6 categorie): ogni risultato va etichettato esplicitamente come **TRUE_HOLDOUT**, **CONTAMINATED_VALIDATION** o **DISCOVERY_REUSE** — mai lasciato implicito. Solo `TRUE_HOLDOUT` conta per una promozione a `SUPPORTED` in §14. Lo split holdout va **preregistrato prima di guardare l'outcome**, usando `preregistration_provenance_guard.py` (Discovery Engine v2, Phase 7.0-7.1, mai bloccato, riusato tale e quale).

## 9. Cost stress

**Riuso diretto**, nessun nuovo motore di costo: applicare gli stessi 4 profili di costo reale calibrati su 24.1M tick (`NEXUS - 37 Strategy Cost-Calibrated Re-Evaluation.md`, `ff9f0e5`, 15-09) a qualunque cella promossa oltre `CANDIDATE` in §14. Un componente che perde il proprio edge condizionale sotto costi realistici non supera §14 indipendentemente dal risultato nudo.

## 10. Protezione da multiple testing

**Riuso diretto:** BH-FDR (confermato generico e riusabile — già applicato senza problemi in Phase 7.1 su un singolo candidato). **Piano di alpha-spending dichiarato PRIMA di guardare qualunque outcome**: il numero di celle testate (6 componenti × N stati di regime × soglie di outcome di §4) va fissato e congelato nella preregistrazione di §8, non deciso a posteriori in base a cosa "sembra promettente". Questo è il correttivo diretto all'errore di Phase 5 (§0).

## 11. Requisiti minimi di campione

**Riuso diretto** del metodo già validato in Phase 6.5 — **non** del gate bloccato in Phase 7.4A: dichiarare l'Effective Sample Size con 3 metodi indipendenti (block bootstrap compreso) **senza fonderli in un unico numero**, e senza condizionare il rigetto del test sulla stessa diagnostica calcolata sul campione del test (la causa esatta del blocco di Phase 7.4A — vedi §0). Soglia operativa, coerente con quanto già usato in questo corpus (LIQ_SWEEP n=6 giudicato esplicitamente insufficiente nella reconciliation del 05-10): sotto ~30 osservazioni effettive indipendenti, l'esito va etichettato **evidenza insufficiente**, non WEAK né FAILED — è una categoria distinta, non un punto basso della stessa scala.

## 12. Protezioni da leakage

**Riuso diretto:** `leakage_guard_v1.md` + `missing_data_policy_v1.md` (Phase 4, già con un difetto reale trovato e corretto in passato — il meccanismo funziona). Ogni campo del context vector (§1) e ogni feature del component representation (§3) deve passare un audit esplicito di `observation_point`: se un campo richiede informazione non disponibile al momento dell'entry, è escluso, non approssimato.

## 12-bis. Separazione obbligatoria diagnostica / selezione / test (anti-circolarità)

Vincolo esplicito per Phase 1, non derivato implicitamente da §11: la pipeline MACD deve mantenere **tre stadi computazionalmente separati, nessuno dei quali riusa l'output di un altro per decidere il proprio esito**:

1. **Diagnostica** (§2 riconciliazione regime, §11 calcolo ESS a 3 metodi) — produce solo descrizioni della struttura di dipendenza e della coerenza dei regime label. Non decide nulla da sola.
2. **Selezione** (§10 piano di alpha-spending, §11 soglia minima di campione) — decide quali celle (componente × regime × soglia outcome) **entrano** nel test, usando solo la numerosità grezza e la preregistrazione di §8 — **mai** una statistica di effetto o di significatività calcolata sullo stesso outcome che il test dovrà poi giudicare.
3. **Test** (§6 conditional expectancy, §7 confronto regime-matchato, §9 cost stress) — produce l'esito scientifico, usando solo le celle già fissate dallo stadio 2.

Nessuno stadio può essere ricalcolato o aggiustato dopo aver visto l'esito di uno stadio successivo (es.: non si torna a cambiare la soglia ESS di §11 dopo aver visto che una cella "quasi" supera il benchmark di §7). Questo è il correttivo diretto e specifico al meccanismo che ha prodotto selezione avversa in Phase 7.4A (§0) — qui applicato esplicitamente al test MACD, non solo enunciato in astratto.

## 13. Criteri di classificazione PROMISING / SUPPORTED / WEAK / REDUNDANT

Non 4 etichette arbitrarie — **ancoraggio diretto** alla Evidence Grading Scale E0-E6 già matura e testata su un caso reale completo (RECLAIM: E1→E2→BORDERLINE, mai promosso a E3 — Phase 4-6) e al vocabolario `edge_component_schema.md` (CANDIDATE/SUPPORTED/REFUTED/UNKNOWN):

| Etichetta nuova | Condizione | Corrispondenza E0-E6 |
|---|---|---|
| **WEAK** | Non supera il benchmark regime-matchato (§7) con margine significativo in nessuna cella, OPPURE evidenza insufficiente (§11) in tutte le celle testate | E0-E1 |
| **PROMISING** | Supera il benchmark regime-matchato in almeno una cella dopo correzione BH-FDR (§10), ma non ancora confermato su TRUE_HOLDOUT (§8) o non ancora sotto cost stress (§9) | E2/BORDERLINE |
| **SUPPORTED** | Supera §7+§9+§10+§11 **e** è confermato su split TRUE_HOLDOUT preregistrato | E3+ |
| **REDUNDANT** | L'edge condizionale è statisticamente indistinguibile da un altro componente già `SUPPORTED` nelle stesse celle di contesto — riusa la metodologia già esistente di `feature_redundancy_audit_v1.md` (25 feature già classificate con questo stesso criterio), estesa dal livello feature al livello componente | n/a (criterio di parsimonia, non di evidenza) |

Nessuna cella va forzata in una di queste 4 categorie se l'evidenza è genuinamente ambigua — in quel caso resta `UNKNOWN` (vocabolario Phase 4 già esistente), esplicitamente, come già fatto nella reconciliation del registry.

---

## 14. Phase 1 proposta — piccola e falsificabile

**Un solo componente, non sei.** Proposta: **MACD**, per un motivo scientifico preciso, non di comodo: è l'unico dei 6 con uno status standalone già `FAILED` (Phase F, segmentazione per-anno diretta, non inferenza di regime) e un dataset multi-anno già segmentato e pronto. Questo rende la domanda massimamente falsificabile con il minimo lavoro nuovo: *"MACD, già dimostrato fallito come segnale standalone, ha valore condizionale misurabile in almeno uno stato di regime, dopo correzione per multiple testing e sotto costi reali?"*

Se la risposta è no in modo netto (nessuna cella supera §7+§10 con evidenza sufficiente), è un risultato pulito e utile: non ogni strategia FAILED nasconde un edge condizionato, e lo sappiamo con rigore invece che per assunzione. Se la risposta è sì anche in una sola cella, è la prima prova concreta che l'approccio "Context → Setup → Outcome" cambia conclusioni già prese, con il minimo investimento possibile.

**Cosa comporta concretamente** (per Codex, non eseguito qui):
1. Riconciliare i due classificatori di regime (§2) — un confronto, non un nuovo classificatore.
2. Estrarre la rappresentazione continua di MACD (§3) sul periodo multi-anno già usato in Phase F.
3. Preregistrare (§8, `preregistration_provenance_guard.py` riusato) le celle da testare, la soglia di sample minimo (§11) e il piano BH-FDR (§10) — **prima** di calcolare qualunque expectancy.
4. Calcolare recurrence (§5) e conditional expectancy (§6) per cella.
5. Confronto regime-matchato (§7, `BaselineEngineV4` riusato).
6. Cost stress (§9, profili già calibrati) solo sulle celle che superano il passo 5.
7. Classificare (§13) ogni cella — incluso `UNKNOWN`/evidenza insufficiente dove onesto.

**Esplicitamente fuori scope per questa Phase 1** (per tutti e 6, non solo MACD): nessuna ricerca combinatoria sui 6 componenti insieme, nessuna costruzione di un motore di decisione/routing, nessuna modifica a `contracts/strategy-registry.json` o al runtime MQL5, nessun secondo componente finché Phase 1 non ha prodotto un verdetto (anche negativo) su MACD.

---

## 15. Cosa NON fa questo documento

- Non ottimizza parametri di nessuna strategia.
- Non esegue ricerca combinatoria indiscriminata sui 6 componenti.
- Non costruisce il decision engine / Strategy Portfolio / Regime Router descritto dall'utente come visione a lungo termine — quella resta una Phase successiva, non autorizzata qui.
- Non modifica `contracts/strategy-registry.json`, il suo generatore, o qualunque file MQL5/runtime.
- Non esegue backtest nuovi — Phase 1 è un design da implementare, non un'esecuzione.

## 16. Deliverable per Codex

Questo documento stesso, una volta approvato. Nessun altro file prodotto in questa fase.
