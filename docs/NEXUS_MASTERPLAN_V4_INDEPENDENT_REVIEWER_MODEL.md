# NEXUS MASTERPLAN V4 — Modello del Revisore Indipendente

**Stato di questo documento: PROPOSTA, non implementata.** Estende infrastruttura già reale (`review_pipeline_v1/`, `finalization_gate.py`) invece di sostituirla o duplicarla.

## Cosa esiste già (riusato, non reinventato)

Dal census System & Development:
- `server/review_pipeline_v1/` — pipeline di review multi-agente già esistente (NEXUS TASK #0008), con `review_matrix.py` (classificazione work_type/priorità) e `learning_telemetry.py` (metriche della pipeline di review stessa).
- `server/review_pipeline_v1/finalization_gate.py` — gate deterministico pre-FINALIZED, scansiona pattern di segreti reali prima che un work product possa essere marcato finalizzato. Non bypassabile.
- `core/result_packet.py::build_result_packet()` — già produce `verifier: {ran, passed, errors}` su ogni transizione di task (confermato nel census Jarvis & Automation — `MultiStageExecutor` costruisce `RESULT_PACKET_V1` solo quando ogni step è `VERIFIED` indipendentemente).

**Un concetto di "verifica indipendente" esiste quindi già a livello di singolo task.** Quello che manca è la sua applicazione esplicita al ciclo di self-improvement (confrontare una baseline con una variante), non il meccanismo di verifica in sé.

## Design proposto

Il Revisore Indipendente per il self-improvement **non è un nuovo agente LLM** — è una funzione deterministica + un punto di ancoraggio umano per i casi ambigui, esattamente come `finalization_gate.py` è deterministico per i segreti.

```
INPUT:  baseline_ref, variant_ref, metrica dichiarata dal reparto (es. win_rate,
        conversion_rate, KPI reach — sempre quella già IMPLEMENTED per quel
        reparto specifico, mai una nuova metrica inventata dal revisore)

PROCESSO:
  1. Verifica che baseline_ref e variant_ref siano stati misurati sulla
     STESSA finestra/condizioni (stesso principio già applicato in Trading:
     VOLBRK Serious 3Y resta PARTIALLY_BLOCKED finché le soglie non sono
     decise da un umano — il revisore eredita questa stessa disciplina
     fail-closed).
  2. Calcola la differenza (variant - baseline) sulla metrica dichiarata.
     Nessuna soglia di "successo" è universale (coerente con la critica
     esplicita della task originale a soglie come "PF > 1.5" come verità
     universali, già rifiutata nello skill MQL5_ENGINEERING_SKILL_V1).
  3. Se la differenza supera la soglia DICHIARATA DAL REPARTO in anticipo
     (pre-registrata nell'evento IMPROVEMENT_EXPERIMENT_STARTED, mai
     scelta post-hoc) → verdict POSITIVE.
  4. Se insufficiente campione, dati mancanti, o soglia non dichiarata in
     anticipo → verdict INCONCLUSIVE, mai POSITIVE per default.
  5. Se la differenza è negativa oltre un margine di rumore dichiarato →
     verdict NEGATIVE.
  6. Casi ambigui (campione piccolo, metriche miste, impatto cross-reparto)
     → ESCALATE a revisione umana, stesso meccanismo già esistente per
     l'escalation di task (ESCALATION_REQUIRED nell'EventLedger).

OUTPUT: IMPROVEMENT_EXPERIMENT_REVIEWED {experiment_id, verdict, evidence_refs}
        (stesso schema evento proposto nel documento Self-Improvement)
```

## Perché deterministico-prima-dell'LLM

Coerente col principio già verificato come IMPLEMENTED nel resto del sistema (`classify()` prima di `ministral_router.py`). Il revisore calcola, non "giudica" con un modello linguistico — un LLM può essere usato SOLO per spiegare il verdetto in linguaggio naturale a un umano (stesso pattern già reale in `executive_v1/conversation.py`: "i numeri non vengono mai da un modello, solo la spiegazione del 'perché' ci va").

## Perché non è un ottavo agente

Nessun nuovo processo persistente. È una funzione chiamata dal ciclo di self-improvement di ogni reparto (vedi documento Self-Improvement), con gli stessi dati che l'Orchestrator/EventLedger già possiedono.

## Pre-registrazione — perché è un requisito, non un dettaglio

Senza soglia di successo dichiarata PRIMA dell'esperimento, qualunque "miglioramento" diventa selezione post-hoc — esattamente l'errore metodologico che il resto di questa sessione (vedi UNIFIED_MARKET_INTELLIGENCE_SHADOW_PHASE1_PREREG, già nel vault) ha trattato come non negoziabile in ambito Trading. Questo documento applica la stessa disciplina a ogni reparto, non solo a Trading.

## Checklist prima di implementare
- [ ] Conferma utente sul design.
- [ ] Scegliere il reparto pilota (coerente con la checklist del documento Self-Improvement).
- [ ] Nessuna soglia universale va codificata — ogni reparto dichiara la propria in base alla propria metrica reale già esistente.
