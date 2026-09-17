# Setup Registry — schema v1

Setup = Context + Event + Preconditions, disaccoppiato dal metodo di esecuzione specifico (vedi [[market_ontology]] — Setup).

## Schema

```json
{
  "schema_version": 1,
  "setup_id": "SETUP-UPTREND_SWEEP_RECLAIM-v1",
  "display_name": "Uptrend + Sweep Low + Reclaim",
  "context": {
    "required_state": {
      "trend.direction": 1,
      "trend.strength_adx": {"min": 20}
    }
  },
  "event_refs": ["SWEEP", "RECLAIM"],
  "event_sequence_constraint": "RECLAIM must occur within N bars after SWEEP, same direction leg",
  "preconditions": [
    "sweep.magnitude >= 0.3 ATR",
    "no prior SETUP of same family triggered in last cooldown_bars"
  ],
  "cooldown_bars": 6,
  "known_trigger_variants": ["close_confirmation", "immediate_market", "retest", "limit_at_level"],
  "status": "PROPOSED|UNDER_VALIDATION|VALIDATED|REFUTED|RETIRED",
  "ex_ante_definition_date": "2026-09-17",
  "ex_ante_definition_frozen": true,
  "source_events_schema_version": 1
}
```

Punti chiave:
- `event_refs` punta a famiglie dell'Event Registry, MAI a codice di una strategia specifica.
- `known_trigger_variants`: enumerazione esplicita — l'esistenza di più varianti di trigger sullo stesso Setup NON deve automaticamente contare come N "idee di mercato" diverse (vedi sezione 5 della richiesta originale); ogni variante va comunque validata separatamente come possibile fonte di edge incrementale nell'ESECUZIONE, non nell'idea.
- `ex_ante_definition_frozen`: un Setup, una volta marcato `UNDER_VALIDATION`, non può più essere modificato nella sua definizione di Context/Event/Preconditions senza creare una nuova versione (`vN`) — stessa disciplina già imposta a FROZEN_SIGNAL_SPEC_V1.
- `status`: uno stato REFUTED è informazione permanente, non va cancellato dal registro (vedi Failure Memory / re-interpretazione ricerca passata).
