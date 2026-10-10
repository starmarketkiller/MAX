# NEXUS MASTERPLAN V4.1 — Implementation Roadmap

Le 9 milestone richieste dalla task (sez.20), con dipendenze esplicite e collegamento alle priorità già stabilite in V4. **Nessuna milestone qui è stata eseguita in questa sessione** — questo documento è il piano, non un log di lavoro svolto.

## Vincolo di sequenza esplicito dalla task

Le priorità già concordate per chiudere executor/recovery (territorio Codex), Mobile Assistant e Fashion Agency **restano preservate** — questa roadmap non le scavalca. Il Mobile Assistant (Milestone implicita in [NEXUS_JARVIS_DELIVERY_ARCHITECTURE_V1.md](NEXUS_JARVIS_DELIVERY_ARCHITECTURE_V1.md)) resta esplicitamente FUTURE, non una milestone numerata qui sotto a meno che l'utente non la richieda.

## Le 9 milestone

### Milestone 1 — Canonical Documentation + Contract Design
**Stato: questa sessione (V4 + V4.1).** 13 documenti V4 + 13 documenti V4.1 + 5 contratti schema. Nessuna azione aggiuntiva richiesta per chiudere questa milestone — è l'output di questo lavoro.

### Milestone 2 — Read-only Workflow Engineering Viewer
**AGGIORNATA dopo la scoperta del Command Floor di Codex (vedi [Gap Analysis V4.1 §Riconciliazione](NEXUS_ARCHITECTURE_GAP_ANALYSIS_V4_1.md#riconciliazione-con-command-floor-di-codex-scoperta-a-fine-sessione))**: questa milestone **è in gran parte già realizzata** da `frontend/src/command/CommandFloorPage.jsx` + `stations.js`/`live.js`/`engine.js` + `server/jarvis_v1/floor_workflow.py`/`task_result_view.py`. Non "costruire da zero" — verificare con l'utente/Codex se:
(a) basta estendere Command Floor esistente con altri workflow reali oltre al fashion handoff, o
(b) formalizzare `stations.js` in uno schema versionato (`NEXUS_WORKFLOW_DEFINITION_V1`) ha un beneficio reale, o
(c) questa milestone è da considerare già chiusa.
Decisione dell'utente, non presa qui.

### Milestone 3 — Department Result Packet + Independent Review Foundation
**Dipende da**: Milestone 1.
Implementare `DEPARTMENT_RESULT_PACKET_V1` e i livelli L0-L2 di `NEXUS_INDEPENDENT_REVIEW_V1` come adattatori sopra `finalization_gate.py`/`core/result_packet.py` già esistenti — nessuna riscrittura di quei componenti.

### Milestone 4 — Local Self-Improvement V1 — observation/proposals
**Dipende da**: Milestone 3 (serve L2 per EVALUATE).
Solo le fasi OBSERVE→DIAGNOSE→HYPOTHESIZE→PLAN del ciclo (vedi [Self-Improvement V1](NEXUS_DISTRIBUTED_SELF_IMPROVEMENT_V1.md)) — produzione di proposte, nessun esperimento eseguito ancora. Reparto pilota: Jarvis Operations o AI Fashion Agency.

### Milestone 5 — Trading Intelligence Room simulation/research
**Dipende da**: Milestone 1.
Implementare i ruoli Scout/News/Sentiment/Charts come nodi di workflow in modalità ricerca/simulazione — **mai esecuzione live**, il Risk Gate deterministico (`NXS_RiskShield.mqh`) resta l'unico percorso verso un'esposizione reale, invariato. Chiude direttamente il gap #1 già identificato in V4 (gate go-live mancante).

### Milestone 6 — Templates per Revenue, Agency, Social, Finance, Engineering e Jarvis
**Dipende da**: Milestone 5 (pattern di riferimento) + Milestone 3.
Un `NEXUS_WORKFLOW_DEFINITION_V1` reale per ciascuno degli altri 6 reparti, usando i ruoli già mappati in [NEXUS_DEPARTMENT_TEAMS_V1.md](NEXUS_DEPARTMENT_TEAMS_V1.md). Finance dipende inoltre dall'aggregatore proposto in [Architecture Review V4 #4](NEXUS_MASTERPLAN_V4_ARCHITECTURE_REVIEW.md#4-high_impact-aggregatore-finance--cost-cross-reparto) — senza quello, il workflow Finance non ha dati reali da orchestrare.

### Milestone 7 — Global Improvement Council e experiment coordination
**Dipende da**: Milestone 4 completata su almeno un reparto pilota.
Implementazione minima del Council (vedi [NEXUS_MASTERPLAN_V4_SELF_IMPROVEMENT_AND_COUNCIL.md](NEXUS_MASTERPLAN_V4_SELF_IMPROVEMENT_AND_COUNCIL.md)) — estensione di `executive_v1/`, 4 eventi additivi, mai un revisore sincrono di ogni micro-operazione.

### Milestone 8 — Visual Rooms e pixel-art
**Parzialmente già presente**: Command Floor di Codex ha già una rappresentazione a "stazioni"/room (`FloorMap.jsx`, `floor.css`) per i 7 reparti — non è lo stile pixel-art delle immagini di riferimento dell'utente, ma la struttura di base (room→stazioni→stato visivo) esiste. Verificare con l'utente se desidera lo stile pixel-art SOPRA questa struttura esistente (restyling) prima di considerare questa milestone da zero.

### Milestone 9 — Controlled Promotion & Rollback
**Dipende da**: Milestone 7.
Implementazione completa di PROMOTE/REJECT/MONITOR del ciclo di self-improvement, con rollback reale (git revert per codice, versioning esplicito del valore precedente per configurazione/soglie).

## Dipendenze — vista grafica

```
M1 (fatto) ─┬─> M2 ──────────────────> M8
             ├─> M3 ──> M4 ──> M7 ──> M9
             └─> M5 ──> M6 (+ dipende da Finance aggregator, fuori roadmap)
```

## Priorità immediate raccomandate (le 3 prossime task implementative, non eseguite qui)

**Rivisto dopo la scoperta del Command Floor di Codex** — Milestone 2 non è più la priorità "a basso sforzo" (è in gran parte già fatta), il Global Improvement Council sale di priorità (gap confermato da due sistemi indipendenti, nessuno dei due lo copre):

1. **Global Improvement Council, implementazione minima** (Milestone 7, anticipata) — è l'UNICO gap confermato indipendentemente sia dal mio census sia dal sistema reale di Codex. Il valore di colmarlo ora è più alto di quanto stimato prima di questa scoperta.
2. **Backup automatico Render** (da [Render Infrastructure Plan](NEXUS_RENDER_INFRASTRUCTURE_PLAN.md)) — non è nella numerazione delle 9 milestone della task ma è il rischio infrastrutturale più concreto trovato, costo basso, indipendente da tutto il resto.
3. **Decisione con l'utente su Command Floor** — prima di qualunque altra milestone sul Visual Operations Center, chiarire con l'utente/Codex se Milestone 2/8 vanno chiuse com'è, estese, o riprogettate — non una task implementativa, ma un passo di coordinamento necessario prima di scrivere altro codice in quell'area.

Queste 3 non sostituiscono l'ordine delle 9 milestone — sono la sequenza con cui affrontarle per primo valore reale più rapido, aggiornata rispetto a quanto scritto prima della scoperta del Command Floor.
