# Execution Feasibility Layer v1 (Phase 5.5 sec.11)

Ogni futuro `EDGE_COMPONENT` deve avere due sezioni separate — nessun fenomeno diventa "deployable edge" finché `execution_status != EXECUTION_VALIDATED`.

## Schema

```json
{
  "component_id": "EC-...",
  "phenomenon": {
    "statistical_edge": "P(target|event) vs P(target|baseline)",
    "effect_size": {"delta_p": 0.0, "delta_e": 0.0},
    "confidence": "Wilson CI95 + Beta-Binomial posterior, vedi probability_schema",
    "baseline": "definizione del baseline matched usato"
  },
  "execution": {
    "signal_timestamp": "istante in cui l'evento/setup e' osservabile causalmente",
    "earliest_executable_timestamp": "il PRIMO istante in cui un ordine potrebbe realisticamente essere inviato (>= signal_timestamp, mai uguale se c'e' un gate/conferma a barra chiusa)",
    "reference_price": "prezzo usato per calcolare l'outcome teorico (spesso idealizzato)",
    "expected_fill_model": "market | limit-at-level | limit-at-trigger | stop, e assunzioni di slippage",
    "spread_sensitivity": "quanto l'edge si degrada al variare dello spread reale",
    "slippage_sensitivity": "quanto si degrada al variare dello slippage",
    "latency_sensitivity": "quanto si degrada per un ritardo di invio ordine di N secondi/barre",
    "order_type_feasibility": "quali tipi di ordine sono realisticamente disponibili per questo setup",
    "concurrent_position_sensitivity": "impatto di InpMaxConcurrent/InpMaxPerDirTF o vincoli di esposizione simili",
    "liquidity_session_sensitivity": "l'edge dipende da una sessione/liquidita' specifica?"
  },
  "execution_status": "NOT_TESTED | PLAUSIBLE | FRAGILE | EXECUTION_VALIDATED | NOT_EXECUTABLE"
}
```

## Status di esecuzione

| Status | Significato |
|---|---|
| `NOT_TESTED` | Nessun modello di fill reale applicato ancora |
| `PLAUSIBLE` | Analisi qualitativa/di massima suggerisce eseguibilità, nessun test quantitativo |
| `FRAGILE` | Testato con un modello di fill realistico, l'edge si riduce/inverte sotto stress di slippage/latenza |
| `EXECUTION_VALIDATED` | Testato con fill reale (tick reali o esecuzione live/demo), l'edge sopravvive |
| `NOT_EXECUTABLE` | Testato, l'edge non sopravvive a nessuna variante di esecuzione realistica provata |

## Applicazione retroattiva: EC-LIQUIDITY_SWEEP_RECLAIM

```json
{
  "component_id": "EC-LIQUIDITY_SWEEP_RECLAIM",
  "phenomenon": {
    "statistical_edge": "P(+1xATR before -1xATR) 75-81% (discovery/validation) vs baseline matched 51%",
    "effect_size": {"delta_p_validation": 0.299, "delta_e_validation_mfe_atr": 0.694},
    "confidence": "CI95 Wilson mai sovrapposte; Beta-Binomial posterior concorde; p raw ~4e-8 in validation (vedi multiple_testing_ledger_v1.json) - ma vedi guardrail: significativo non equivale a validato indipendentemente",
    "baseline": "barre non-RECLAIM/non-SWEEP matched per (terzile volatilita, terzile trend, anno), stessa direzione"
  },
  "execution": {
    "signal_timestamp": "chiusura della barra H4 di conferma reclaim (confirmed_at_row_index)",
    "earliest_executable_timestamp": "NON DETERMINATO - richiede un test dedicato (vedi Signal-to-Fill Gap Audit, sec.12)",
    "reference_price": "chiusura IDEALIZZATA della barra di conferma - stesso pattern gia' refutato per un fenomeno gemello in Phase 4 (WICK_SWEEP_RECLAIM, shadow PF 5.80 vs reale 0.78-0.80)",
    "expected_fill_model": "NON TESTATO in questa fase",
    "spread_sensitivity": "NON TESTATO",
    "slippage_sensitivity": "NON TESTATO - precedente diretto (Phase 4) mostra uno slippage favorevole medio di 42.6 pip che ha gonfiato artificialmente un fenomeno simile",
    "latency_sensitivity": "NON TESTATO",
    "order_type_feasibility": "NON TESTATO",
    "concurrent_position_sensitivity": "NON TESTATO",
    "liquidity_session_sensitivity": "NON TESTATO"
  },
  "execution_status": "NOT_TESTED"
}
```

**Nessuna nuova validazione di esecuzione è stata eseguita in questa fase** (vietato dal perimetro di Phase 5.5, sec. "NON deve rivalutare SWEEP+RECLAIM") — questo record esiste per rendere ESPLICITO che il fenomeno non ha ancora attraversato la sezione EXECUTION, non per colmare quel vuoto ora.
