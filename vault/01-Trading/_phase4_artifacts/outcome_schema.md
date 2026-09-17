# Outcome Surface — schema v1

Mappa della distribuzione naturale di esito per un Event/Setup PRIMA di scegliere TP/gestione (sezione 6 della richiesta). Non è ricerca del TP ottimale.

## Schema

```json
{
  "schema_version": 1,
  "setup_id": "SETUP-UPTREND_SWEEP_RECLAIM-v1",
  "sample_definition": {
    "symbol": "XAUUSD",
    "timeframe": "H4",
    "window_start": "2019-02-03",
    "window_end": "2022-02-03",
    "n_total_occurrences": 0,
    "n_censored": 0
  },
  "r_multiple_thresholds": {
    "p_plus_0_25R_before_minus_1R": {"n": 0, "value": null},
    "p_plus_0_5R_before_minus_1R":  {"n": 0, "value": null},
    "p_plus_1R_before_minus_1R":    {"n": 0, "value": null},
    "p_plus_1_5R_before_minus_1R":  {"n": 0, "value": null},
    "p_plus_2R_before_minus_1R":    {"n": 0, "value": null},
    "p_plus_3R_before_minus_1R":    {"n": 0, "value": null}
  },
  "mfe_distribution": {"unit": "R", "p10": null, "p50": null, "p90": null, "mean": null},
  "mae_distribution": {"unit": "R", "p10": null, "p50": null, "p90": null, "mean": null},
  "time_to_mfe_bars": {"p10": null, "p50": null, "p90": null},
  "time_to_mae_bars": {"p10": null, "p50": null, "p90": null},
  "time_to_target_bars": {"p10": null, "p50": null, "p90": null},
  "time_to_invalidation_bars": {"p10": null, "p50": null, "p90": null},
  "invalidation_definition_used": "opposite range boundary | fixed ATR multiple | structural break",
  "censoring_rule": "occorrenze non ancora concluse alla fine della finestra dati sono 'censored', non escluse silenziosamente"
}
```

Regole:
- `n_censored` deve essere tracciato esplicitamente — un'occorrenza ancora aperta a fine finestra non è né "vinta" né "persa", è censurata (rilevante anche per il modello Beta-Binomial, sezione probability).
- Ogni soglia R riporta il proprio `n` — soglie più alte hanno tipicamente `n` effettivo minore (non tutte le occorrenze raggiungono +3R prima di -1R nel periodo osservato), quindi ogni soglia porta la propria incertezza indipendente.
- Questo schema NON contiene alcun campo "recommended_tp" — deliberatamente, per evitare che diventi un veicolo per scegliere il target a posteriori.
