# Market Regime Layer v1 (Phase 5.5 sec.6)

Implementazione: `server/research_scripts/phase5_5/build_regime_layer.py`. Output: `regime_layer_v1.csv` (etichetta per barra) + `regime_schema_v1.json` (definizione/soglie/distribuzione).

**Descrittivo, non un segnale**: nessuna strategia legge questa colonna per decidere un trade — serve a stratificare/interpretare i risultati (es. popolare finalmente il campo `regime_breakdown` del Probability Engine, sec.G di Phase 5, mai concretamente popolato finora).

## 5 stati, priorità dichiarata ex-ante

1. **HIGH_VOL** — `atr_percentile` > 66.67° percentile (soglia calcolata SOLO sulla finestra di discovery)
2. **LOW_VOL** — `atr_percentile` < 33.33° percentile
3. **TRANSITION** — `trend_persistence_bars` ≤ 2 (un cambio di direzione avvenuto nelle ultime 1-2 barre — trend non ancora stabilito)
4. **TRENDING** — `directional_efficiency` > 66.67° percentile (e non già classificato sopra)
5. **RANGING** — tutto il resto, per esclusione

La priorità (vol estrema prima, poi freschezza del trend, poi efficienza direzionale) è dichiarata qui una volta per tutte — non è stata scelta guardando quale ordine avrebbe dato una distribuzione "più bella".

## Feature di input, observation point, versione

`atr_percentile, directional_efficiency, trend_persistence_bars` (tutte già in `market_state_dataset_v1.csv`, garanzie causali invariate). Observation point: chiusura barra corrente. Nessuna feature futura.

## Distribuzione reale (4809 barre)

| Regime | Tutto il periodo | Discovery | Validation |
|---|---|---|---|
| LOW_VOL | 1612 (33.5%) | 1097 | 515 |
| HIGH_VOL | 1498 (31.2%) | 1090 | 408 |
| TRANSITION | 1260 (26.2%) | 862 | 398 |
| RANGING | 242 (5.0%) | 157 | 85 |
| TRENDING | 122 (2.5%) | 85 | 37 |
| NaN (warmup) | 75 | 75 | 0 |

TRENDING è raro (2.5%) — atteso: richiede contemporaneamente vol non estrema, alta efficienza direzionale E trend non recentemente rovesciato, una congiunzione stretta. Le proporzioni discovery/validation sono simili (nessun regime scomparso o esploso fra le due finestre), un primo controllo di sanità sulla stabilità della definizione nel tempo.
