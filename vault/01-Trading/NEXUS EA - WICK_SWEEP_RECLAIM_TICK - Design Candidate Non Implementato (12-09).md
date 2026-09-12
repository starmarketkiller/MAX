# WICK_SWEEP_RECLAIM_TICK — Design Candidate (NON implementato)

## Stato: SOLO DESIGN, nessuna riga di logica scritta, nessun test

Creata per tracciare il secondo filone possibile emerso dalla correzione metodologica in [[NEXUS EA - WICK_SWEEP Entry Timing Study - HYPOTHESIS STRONGLY SUPPORTED NOT YET EXECUTION-VALIDATED (11-09)]]: lo shadow validato (e quindi anche `WICK_SWEEP_RECLAIM`, implementata fedele a quella cadenza) era/è **M15-gated**, non tick-level. Questa nota descrive SOLO l'idea per una variante genuinamente tick-level — non è stata scritta logica, non è stata compilata, non è stata testata.

## Idea

- **Detection (ARM)**: resta sulla stessa coorte canonica M15 (`isNewCohortBar`), esattamente come `WICK_SWEEP_RECLAIM` — nessun cambiamento qui.
- **Follow-up (monitoraggio reclaim)**: girerebbe su OGNI tick reale, indipendentemente dal New Bar Gate globale — cioè l'hook di monitoraggio dovrebbe essere agganciato PRIMA del New Bar Gate (`NEXUS_EA_v2.mq5:1175-1178`) invece che dopo, o in un punto che lo bypassa deliberatamente per questa sola funzione.

## Perché non è banale, e perché non è stato implementato ora

1. **Il New Bar Gate è condiviso da tutta la pipeline** (`NXS_CollectAllSignals` e tutto ciò che segue). Un hook posizionato prima di esso gira ad ogni tick, ma deve replicare da solo i controlli che il gate normalmente garantisce indirettamente (evitare rivalutazioni ridondanti, gestire cambi di stato che presuppongono "siamo su una barra nuova").
2. **I numeri non sarebbero comparabili 1:1 con lo shadow già validato**: un reclaim genuinamente tick-level troverebbe il ritorno al trigger_price potenzialmente PRIMA del prossimo boundary M15 — reclaim più veloci, probabilmente più frequenti (più eventi "disponibili"), e possibilmente un WR/PF diverso (il prezzo potrebbe non aver ancora confermato la stessa forza di reversal che si vede aspettando fino al prossimo M15). Servirebbe un NUOVO studio Python/shadow dedicato a questa cadenza prima di implementare l'esecuzione reale, non un porting diretto dei numeri già raccolti.
3. **Rischio di duplicare l'errore già corretto una volta**: prima di scrivere questa variante andrebbe validata con una NUOVA passata shadow (osservazionale, come già fatto per RECLAIM_TRIGGER M15) per evitare di scoprire un'altra sorpresa architetturale (es. altri gate silenziosi) solo dopo aver già implementato l'esecuzione reale.

## Prerequisiti prima di anche solo iniziare un prototipo shadow

- Decisione esplicita dell'utente di procedere su questo filone (non presa automaticamente).
- Un nuovo blocco SHADOW (puramente osservazionale, zero ordini reali) con l'hook posizionato PRIMA del New Bar Gate, per misurare la vera distribuzione dei reclaim delay a livello tick e confrontarla con quella M15-gated già nota (mediana 900s).
- Solo se quel nuovo shadow mostra un miglioramento/comportamento interessante rispetto a `WICK_SWEEP_RECLAIM` (M15-gated): considerare un'implementazione reale `WICK_SWEEP_RECLAIM_TICK` con identità e selettore ANCORA separati (non 55, non 54).

## Non toccato / non fatto

- Nessuna modifica al New Bar Gate globale.
- Nessuna riga di codice per questa variante.
- Nessun test lanciato.
