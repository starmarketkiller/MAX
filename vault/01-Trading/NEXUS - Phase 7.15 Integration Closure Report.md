# NEXUS - Phase 7.15 — Integration Closure Report (chiusura Phase 7.14)

**Baseline:** `4e29fd5` (Phase 7.14 + fix verificatore). Nessun lavoro concorrente rilevato (fetch eseguito prima e dopo). Nessuna ricerca economica, nessuna nuova campagna di backtest completa, nessun run Tester lanciato in questa fase.

**Obiettivo**: chiudere il perimetro di validazione di Phase 7.14 — verificare la regressione su un checkout pulito, delimitare il perimetro OB_MIT, correggere le conclusioni sul confronto EA/Python dove non sostenute da una ricostruzione causale, documentare sorgenti/binari senza compilare né eseguire nulla.

---

## 1. Regressione sul commit finale (checkout pulito)

Riesecuzione dei 18 test originariamente falliti su `git worktree` di `4e29fd5`: **nessuno dei 18 nomi originali fallisce più** — erano un artefatto dello stato della working tree (diff non committato vs HEAD), risolto dal commit stesso. Su un checkout pulito emergono invece **19 fallimenti distinti in 7 gruppi**, tutti classificati:

| Gruppo | N test | Categoria | Causa |
|---|---|---|---|
| Phase 7.12 staleness self-check | 1 | Atteso | Verificatore rileva correttamente che il proprio finding è superato dal fix — comportamento voluto |
| Phase 7.13 staleness self-check | 1 | Atteso | Stesso comportamento, verificatore di Phase 7.13 |
| Phase 7.13 `multi_tf_dataset_v1.json` mancante | 7 | Dichiarato | Limite di riproducibilità già documentato nel vault di Phase 7.13 (31MB non committato) |
| Phase 7.9c hash SHA256 | 2 | Ambientale | `git core.autocrlf=true` altera i byte (LF→CRLF) su fresh checkout — **confermato preesistente**, riprodotto anche a `7b823b9` prima di qualunque lavoro ORDER_BLOCK |
| Phase 7.9d percorso certificato | 1 | Ambientale | Traversata relativa hardcoded nel verificatore storico, non portabile a un worktree in path diverso — **confermato preesistente** |
| Phase 7.9g hash SHA256 | 1 | Ambientale | Stessa causa di 7.9c |
| Phase 7.9k `KeyError` | 6 | **Difetto reale, RISOLTO in questa fase** | Collisione di nome modulo Python (`build_decision_card_v2.py` duplicato fra phase7_9k e phase7_14) |

**Nessuna regressione reale causata dal fix ORDER_BLOCK.** Nessun test congelato modificato, nessuna assertion disabilitata. Il gruppo Phase 7.9k era l'unico difetto genuino trovato — introdotto in questa sessione (nome file generico riusato), **corretto rinominando il file di Phase 7.14** (non un file storico di un'altra fase) in `build_order_block_decision_card_v2.py`. Verificato: suite completa ri-eseguita dopo la rinomina, **489 passed, 2 failed** (solo le due staleness self-check attese, invariabili per costruzione).

**Proposte non applicate** (verificatori storici congelati, fuori scope modificarli qui): normalizzare gli hash su contenuto testuale invece che sui byte grezzi per 7.9c/7.9g; risolvere la cartella `Common/Files` di MetaQuotes via `%APPDATA%` invece di una traversata relativa hardcoded per 7.9d.

## 2. Perimetro OB_MIT (entrambe abilitate)

Analisi statica + un test deterministico breve (secondi, non un nuovo run Tester — non necessario, il meccanismo è puramente logico):

- **Ordine di chiamata**: `NXS_Strat_OrderBlock()` (riga 535) precede sempre `NXS_Strat_OB_Mitigation_Structural()` (riga 543), stesso pass, stesso tick.
- **Consumo della zona**: poiché `NXS_Strat_OrderBlock()` è chiamata DUE VOLTE nello stesso tick quando entrambe sono abilitate (diretta + tramite wrapper), e `g_obBuy`/`g_obSell` sono le stesse variabili, un retest consumato dalla prima chiamata rende la seconda chiamata (OB_MIT) strutturalmente incapace di produrre un segnale duplicato nello stesso tick — **confermato con un test deterministico Python** (stesso modulo replica validato contro il trace EA reale in Phase 7.13/7.14): nessun doppio segnale, la seconda chiamata vede la zona già consumata.
- **Dipendenza dal toggle**: `InpStrat_ORDER_BLOCK=false` disabilita silenziosamente anche OB_MIT, indipendentemente da `InpStrat_OB_Mit`.
- **Selettore 20 isolato**: confermato (già stabilito in Phase 7.14) — isolare OB_MIT da solo lo rende strutturalmente muto.
- **`InpScalpTFOverride`**: **nuovo finding correlato** — "ORDER_BLOCK" è nell'elenco di override, "OB_MIT" no. Se l'override fosse attivo (default OFF, non attivo in produzione), il meccanismo di trigger reale sotto OB_MIT girerebbe sul TF di override di ORDER_BLOCK, non sul `PERIOD_D1` che il registro dichiara per OB_MIT altrove (rischio/hold-time/trailing) — una divergenza reale ma **non attiva oggi**. Non corretto in questa fase (nessuna modifica al registro autorizzata).

**Distinzione esplicita**: "guardia ereditata" (fatto strutturale, verificato) ≠ "comportamento integrato validato" (l'interazione dinamica ORDER_BLOCK+OB_MIT con entrambe abilitate non è mai stata osservata in un run MT5 reale — dedotta da codice + test deterministico, non da un trace live).

## 3. Confronto EA/Python — correzione tracciata

I tre livelli tenuti distinti (pre/post-fix stessi dati; strutturale fra fonti diverse; parity evento-per-evento) mostrano che **solo il livello 1 (A vs B, Phase 7.14) resta pienamente valido**. Il livello 2 (B vs C) conteneva un'affermazione (`residual_explained: true`) **non sostenuta da una ricostruzione causale** — verificato: solo 1/8 eventi B e 1/7 eventi C condividono data+direzione; le barre D1 sulle date contestate sono risultate **numericamente identiche** fra due fonti indipendenti, escludendo "prezzo diverso quel giorno" come causa. **Corretto** a `CANDIDATE_CAUSE_NOT_ISOLATED` (probabile path-dependence della state machine su un punto a monte mai isolato in questa fase). Conteggi non forzati a coincidere. Correzione applicata con revisione tracciata su `phase7_14/build_parity_comparison.py` e `build_decision_card_v2.py` (ora `build_order_block_decision_card_v2.py`) — **la decisione principale `FIX_CAUSALLY_VALIDATED` non cambia**, perché dipende solo dal livello 1.

## 4. Sorgenti e binari

Nessuna compilazione né esecuzione in questa fase — solo lettura/hash di file esistenti. **Sorgente finale**: `MQL5/Include/NEXUS_v1/NXS_Strategies.mqh` contiene solo la guardia (verificato via `verify_phase_7_14.py`). **Build diagnostiche pre/post-fix**: documentate (log di compilazione, timestamp) ma i loro `.ex5` transitori non sono stati preservati (sovrascritti dalla build successiva) — il sorgente esatto resta ricostruibile dallo snapshot dell'istrumentazione già committato. **Build finale pulita**: verificata con un controllo incrociato esplicito — il `.ex5` attualmente presente nel terminale `D0E8209F...` ha timestamp coincidente (entro 2 minuti) con `compile_final_clean.log` e **successivo** all'ultima compilazione diagnostica, quindi non riflette istrumentazione residua. Il secondo terminale (`7F8EC41F...`) non è mai stato toccato in nessuna fase di questo lavoro — il suo `.ex5` precede l'intera sessione. Nessuna compilazione diagnostica è stata bloccata dall'approvazione automatica in questa fase (non è stata tentata alcuna compilazione).

## 5. Stato finale

- **ORDER_BLOCK**: `FIX_CAUSALLY_VALIDATED` (Phase 7.14, non toccato da questa chiusura).
- **OB_MIT**: fix si propaga automaticamente (nessuno stato/percorso proprio) — comportamento dinamico con entrambe abilitate simultaneamente **non osservato dal vivo**, solo dedotto staticamente + test deterministico. Un finding correlato (override selettivo TF) documentato, non corretto.
- **Regressione**: 0 regressioni reali; 1 difetto di isolamento test trovato e risolto (rinomina file di questa sessione); resto classificato come vincoli storici/ambientali preesistenti, non toccati.
- **Confronto EA/Python**: livello 1 (A/B) valido; livello 2 (B/C) corretto da "spiegato" a "causa candidata, non isolata".

## Prossima azione raccomandata

Nessuna promozione live, nessuna valutazione di redditività. Se si vuole procedere oltre: (a) costruire un run reale con ORDER_BLOCK e OB_MIT **entrambe abilitate simultaneamente** (richiede `InpStrategySelector=0` con le altre strategie disattivate via i loro toggle individuali) per validare dinamicamente — non solo staticamente — l'interazione a punto 2; (b) isolare la causa esatta della path-dependence B/C del punto 3, tramite una ricostruzione parallela identica-per-barra su un'unica fonte dati; (c) eventualmente correggere il `InpScalpTFOverride` gap per OB_MIT se si deciderà mai di attivare quell'input in produzione.

## Deliverables

`build_regression_reclassification.py` + `regression_reclassification_v1.json`, `build_ob_mit_perimeter.py` + `ob_mit_perimeter_v1.json`, `build_ea_python_comparison_classification.py` + `ea_python_comparison_classification_v1.json`, `build_sources_and_binaries_audit.py` + `sources_and_binaries_audit_v1.json`, verificatore indipendente (VERIFY OK), 26/26 test propri, correzione tracciata su 2 artifact di Phase 7.14 + nota nel suo vault report, rinomina di `phase7_14/build_decision_card_v2.py` → `build_order_block_decision_card_v2.py` (risolve la collisione con phase7_9k), questo vault report.

## Vincoli preservati

Nessun artifact storico o raw cancellato. Nessun test congelato modificato per ottenere verde. Nessuna compilazione o esecuzione EA lanciata. Nessuna sostituzione né avvio dell'EA su alcun terminale. Nessuna optimization, ricerca economica o campagna di backtest.

---

```
7.14: FIX_CAUSALLY_VALIDATED (A/B su stessi tick reali - MAI in dubbio)
7.15: CHIUSURA PERIMETRO COMPLETATA
  regressione checkout pulito: 0 regressioni reali, 1 difetto di
    isolamento test trovato E RISOLTO (collisione nome modulo)
  OB_MIT: guardia ereditata confermata, comportamento dinamico con
    entrambe abilitate NON osservato dal vivo (solo statico+deterministico)
  EA/Python: livello A/B intatto, livello B/C corretto
    da "spiegato" a "causa candidata non isolata" (revisione tracciata)
  sorgenti/binari: binario deployato verificato pulito per timestamp
    incrociato col log di compilazione, non solo per sorgente pulito
SUITE COMPLETA: 489 passed, 2 failed (entrambi staleness self-check attesi)
PROSSIMO: nessuna azione decisa qui - tre piste proposte (interazione
  dinamica OB/OB_MIT dal vivo, isolamento path-dependence B/C, gap
  InpScalpTFOverride su OB_MIT)
```
