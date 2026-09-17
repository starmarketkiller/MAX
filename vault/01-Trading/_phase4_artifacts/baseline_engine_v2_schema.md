# Baseline Engine v2 — schema e confronto v1/v2 (Phase 5.5 sec.5)

Implementazione: `server/research_scripts/phase5_5/baseline_engine_v2.py`. Dimostrazione reale eseguita su RECLAIM (298/300 eventi matchati), output completo in `baseline_engine_v2_reclaim_demo.json`.

## Metodo (in ordine crescente di rigore)

1. **COARSENED_EXACT** (= v1 di Phase 5): cella `(terzile volatilità, terzile trend, anno)`, intero pool della cella usato come baseline, nessuna nozione di "quanto simile" fosse la singola riga.
2. **NEAREST_NEIGHBOUR standardizzato** (nuovo): dentro il pool v1, i K=5 vicini più prossimi per distanza euclidea su feature continue standardizzate (`atr_percentile, ema_slope_atr_norm, directional_efficiency, position_in_rolling_range, roc`). Standardizzazione (media/std) calcolata **solo sulla finestra di discovery** (mai sulla validation, per evitare leakage).
3. **PROPENSITY_SCORE** (diagnostico): logistic regression (evento~feature standardizzate, via `scipy.optimize`, nessuna libreria ML esterna) usata SOLO come controllo di bilanciamento, non come metodo di matching primario in questa versione.

## Schema per-osservazione (novità v2)

```json
{
  "event_row": 123,
  "coarsened_cell": ["MED", "UP", 2020],
  "v1_pool_size": 812,
  "v2_nn_matched_rows": [118, 340, 55, 902, 77],
  "v2_nn_distances": [0.21, 0.34, 0.41, 0.48, 0.52],
  "v2_avg_distance": 0.392,
  "v2_match_quality": "GOOD",
  "features_matched": ["atr_percentile","ema_slope_atr_norm","directional_efficiency","position_in_rolling_range","roc"]
}
```

Ogni osservazione ora sa ESATTAMENTE quale/i riga/righe di baseline sono state usate, la distanza, le feature matchate, e la qualità del match — nessun baseline "random indiscriminato" (mai stato così, ma ora è anche misurabile quanto sia buono).

**Soglie di qualità** (dichiarate ex-ante): GOOD < 0.5, FAIR < 1.0, POOR ≥ 1.0 (distanza euclidea media sulle feature standardizzate).

## Risultato reale (RECLAIM, 298 eventi matchati su 300)

| Qualità | n | % |
|---|---|---|
| GOOD | 92 | 30.9% |
| FAIR | 197 | 66.1% |
| POOR | 9 | 3.0% |

Nessun match POOR domina il campione — la maggioranza dei controlli scelti sono ragionevolmente vicini all'evento nello spazio delle feature standardizzate, non semplicemente "nella stessa cella grezza".

## Diagnostica propensity score

AUC-proxy (Mann-Whitney) = **0.745** — la separazione fra barra-di-conferma-RECLAIM e controllo sulle feature di stato correnti non è casuale (atteso: la conferma stessa implica un movimento di prezzo/momentum riconoscibile già catturato dalle feature usate). Il propensity score qui è in gran parte una ricodifica a scalare delle stesse feature già usate da NN — non offre un guadagno indipendente misurabile in questo caso specifico a bassa dimensionalità, ma la sua utilità va rivalutata quando il matching userà più feature (rischio di "curse of dimensionality" per NN puro, dove PS diventa più prezioso).

## Miglioramento rispetto a v1 (risponde alla domanda finale 5)

v1: un evento sapeva solo "la sua cella aveva N barre di controllo", nessuna misura di quanto quelle barre fossero davvero simili nello spazio delle feature continue. v2: ogni evento ha una distanza di match esplicita e una classificazione di qualità — permette di **escludere o pesare** in futuro i match POOR, e di verificare (come qui) che il segnale RECLAIM non dipenda da un baseline mal costruito: il miglioramento è di **osservabilità/auditabilità del matching**, non un cambio del risultato numerico di Phase 5 (che resta quello riportato, non ri-validato qui — vedi vincolo esplicito di questa fase).
