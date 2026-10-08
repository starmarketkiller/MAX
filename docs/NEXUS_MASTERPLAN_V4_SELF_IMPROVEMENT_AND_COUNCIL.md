# NEXUS MASTERPLAN V4 — Self-Improvement Distribuito e Global Improvement Council

**Stato di questo documento: PROPOSTA, non implementata.** Nessun Global Improvement Council esiste oggi in nessuna forma — confermato indipendentemente da tutti e 7 i census di reparto (vedi [NEXUS_MASTERPLAN_V4.md §6](NEXUS_MASTERPLAN_V4.md#6-self-improvement-distribuito-e-coordinamento-proposta)). Questo documento descrive un design minimo, coerente col vincolo esplicito "non creare sette nuovi modelli o sette orchestratori", prima di qualunque implementazione.

## Perché un design, non ancora codice

Section 7 della task originale è esplicita: questa task è documentation-first. Prima di scrivere codice per un Global Improvement Council, le proposte vanno presentate. Questo documento È quella presentazione.

## Principio guida

**Ogni reparto migliora localmente in autonomia. Il Council coordina, non revisiona in sincrono ogni micro-operazione.** Un Council che deve approvare ogni singolo esperimento locale non scala e ricrea il collo di bottiglia umano che il sistema vuole eliminare — esattamente il rischio che la task originale chiede di evitare esplicitamente.

## Ciclo locale per reparto (lo stesso schema per tutti e 7, nessuna eccezione)

```
1. BASELINE MISURABILE
   Ogni reparto ha già (o avrà) una metrica propria leggibile da Executive State
   (es. Trading: win rate/profit factor via mt5_data_v1/analytics.py;
   Revenue: RevenueTelemetry; AI Fashion Agency: kpis.py).
   Nessuna nuova metrica va inventata qui — si riusa quello che il census
   ha già trovato come IMPLEMENTED per reparto.

2. ESPERIMENTO ISOLATO
   Un cambiamento locale (nuovo prompt, nuova soglia, nuova strategia di
   scoring) gira in un ramo/sandbox del reparto stesso, MAI sul percorso
   live di default. Riusa i pattern sandbox già esistenti per reparto
   (FreeCodingWorkerHandler.workspace_root, AI Fashion Agency's
   dry_run_v2.py/simulation.py) invece di inventarne uno nuovo per reparto.

3. REVISORE INDIPENDENTE
   Vedi NEXUS_MASTERPLAN_V4_INDEPENDENT_REVIEWER_MODEL.md — stesso
   revisore per tutti i reparti, non uno nuovo per reparto.

4. PROMOZIONE CONTROLLATA
   Solo dopo verdict POSITIVO del revisore indipendente E un confronto
   esplicito baseline-vs-variante. La promozione è un evento nel
   EventLedger esistente (nuovo event_type additivo, stesso pattern già
   usato per ogni estensione precedente dello schema — vedi
   contracts/nexus-event.schema.json).

5. ROLLBACK
   Ogni promozione deve essere reversibile: il baseline precedente resta
   leggibile/riattivabile. Per codice: git revert del commit di
   promozione. Per configurazione/soglie: versioning esplicito del
   valore precedente nell'evento di promozione stesso (non solo il nuovo
   valore).

6. CONDIVISIONE LEZIONI
   L'evento di promozione/rollback nell'EventLedger è l'unico canale di
   condivisione — ogni reparto (o il Council) può leggerlo senza che un
   reparto debba "spingere" attivamente una notifica ad altri 6.
```

## Global Improvement Council — ruolo preciso

**Cosa FA**:
- Legge gli eventi di esperimento/promozione/rollback di tutti i reparti dall'`EventLedger` condiviso (nessun nuovo bus di eventi).
- Risolve conflitti di **risorse** (due reparti vogliono testare contemporaneamente qualcosa che consuma lo stesso budget premium/tempo CPU locale).
- Risolve conflitti di **dipendenza** (un esperimento di Revenue dipende da un cambiamento non ancora promosso in Jarvis).
- Mantiene la vista aggregata già esistente: questo è letteralmente ciò che `executive_v1/state.py::ExecutiveStateBuilder` già fa per lo stato corrente — il Council è la sua estensione naturale per lo stato degli *esperimenti*, non un sistema parallelo.

**Cosa NON fa**:
- Non approva ogni singolo esperimento locale (quello è il Revisore Indipendente, per-reparto, asincrono).
- Non è un ottavo "agente" nuovo — è una funzione/vista, non un modello LLM aggiuntivo che gira in loop. Implementabile come estensione di `executive_v1/` (una sezione aggiuntiva, `improvement_section`), riusando esattamente il pattern a 9-domini già IMPLEMENTED.

## Schema evento proposto (additivo, stesso pattern di ogni estensione precedente)

```
IMPROVEMENT_EXPERIMENT_STARTED   {department, experiment_id, baseline_ref, hypothesis}
IMPROVEMENT_EXPERIMENT_REVIEWED  {experiment_id, reviewer_verdict, evidence_refs}
IMPROVEMENT_PROMOTED             {experiment_id, department, previous_value, new_value}
IMPROVEMENT_ROLLED_BACK          {experiment_id, department, reason}
```

Da aggiungere a `contracts/nexus-event.schema.json` in modo additivo quando si passa all'implementazione — non ora (questo è un documento di design, non un commit di schema).

## Perché questo non viola "non creare sette orchestratori"

Zero nuovi processi/servizi. Il "Council" è una vista di lettura su dati già esistenti (EventLedger) più 4 nuovi tipi di evento. Ogni reparto continua a usare il proprio Orchestrator/TaskQueue esistente per eseguire l'esperimento stesso — questo documento aggiunge solo il *protocollo di reporting*, non un nuovo motore di esecuzione.

## Cosa serve prima di implementare (checklist di approvazione)

- [ ] Conferma utente che questo design è accettabile prima di scrivere codice.
- [ ] Il Revisore Indipendente (documento separato) deve esistere prima che "promozione controllata" sia azionabile.
- [ ] Almeno un reparto (probabilmente AI Fashion Agency o Jarvis, i più maturi) come pilota prima di estendere a tutti e 7.
