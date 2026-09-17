# Signal-to-Fill Gap Audit — metrica standard v1 (Phase 5.5 sec.12)

Metrica `SIGNAL_TO_FILL_GAP`, da calcolare per ogni futura implementazione reale di un `EDGE_COMPONENT` prima di dichiararlo `EXECUTION_VALIDATED`.

## Schema

```json
{
  "component_id": "EC-...",
  "measurement_window": {"start": "...", "end": "...", "n_signals": 0},
  "time_gap": {"unit": "seconds|bars", "median": null, "p90": null, "max": null},
  "price_gap": {"unit": "ATR|pip", "median": null, "p90": null, "direction_bias": "favorable|adverse|neutral"},
  "r_distortion": {"definition": "R calcolato su reference_price idealizzato vs R calcolato sul fill reale", "median_pct_change": null},
  "tp_sl_distortion": {"definition": "quanto SL/TP ancorati al reference_price si discostano da dove sarebbero ancorati al fill reale", "median_pct_change": null},
  "missed_entry_rate": {"definition": "frazione di segnali per cui il fill non e' mai avvenuto entro una finestra ragionevole (es. livello mai raggiunto, o mercato chiuso)", "value": null}
}
```

## Perché serve una metrica standard (non uno per caso)

Il progetto ha già incontrato questo esatto problema due volte, con esiti diagnostici diversi che una metrica comune avrebbe reso immediatamente confrontabili:

1. **WICK shadow/live mismatch** (Phase 4, `NEXUS EA - WICK_SWEEP Entry Timing Study`): shadow PF 5.80 vs reale PF 0.78-0.80, causato da uno **slippage favorevole medio di 42.6 pip** fra il trigger e il fill reale (`|slippage|>10pip` nell'86% dei casi) — un `price_gap` enorme e sistematicamente favorevole che gonfiava l'apparente edge.
2. **Volatility_Breakout entryRef mismatch** (Phase 3 correction): `entryRef` calcolato su ASK/BID live invece che sulla chiusura barra segnale (FROZEN_SIGNAL_SPEC_V1) — qui il `time_gap`/`price_gap` era piccolo sotto tick reali (Model=4: PF quasi invariato 1.165→1.156) ma MATERIALE sotto tick sintetici (Model=1: conteggio trade 16→28) — un caso in cui lo stesso tipo di gap ha impatto molto diverso a seconda del modello di esecuzione, non dell'entità del gap in assoluto.

Con `SIGNAL_TO_FILL_GAP` calcolata in modo uniforme, questi due casi sarebbero stati immediatamente confrontabili in termini di `price_gap.median` e `r_distortion.median_pct_change`, invece di essere scoperti con due indagini ad-hoc separate.

## Applicazione a EC-LIQUIDITY_SWEEP_RECLAIM (Phase 6, non eseguita qui)

Nessun numero calcolato in questa fase (richiederebbe testare l'esecuzione reale, vietato dal perimetro di Phase 5.5). Il record execution di EC-LIQUIDITY_SWEEP_RECLAIM (sec.11) dichiara esplicitamente `execution_status: NOT_TESTED` — `SIGNAL_TO_FILL_GAP` è la metrica che un futuro test di Phase 6 dovrà produrre prima di poter cambiare quello status.
