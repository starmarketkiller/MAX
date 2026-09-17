# Market State Dataset v1 — schema (Phase 5.B)

Dati reali (non un design teorico): `server/research_scripts/phase5/data/market_state_dataset_v1.csv` (4809 barre H4, colonne elencate sotto) + `market_state_dataset_v1.meta.json` (parametri, provenance, garanzie causali). Costruito da `server/research_scripts/phase5/build_market_state.py`.

**Fonte prezzo**: barre H4 XAUUSD aggregate da tick Dukascopy validati in Phase 4 (`DUKASCOPY_TICK_DATA_VALID`, 148.097.525 tick, 2019-02-03→2022-02-03) — `server/research_scripts/phase5/build_h4_bars.py`. OHLC costruito sul BID; spread medio per barra tracciato separatamente. Allineamento barra: UTC fisso (00/04/08/12/16/20) — convenzione di ricerca indipendente, non allineata al server-time del broker live (irrilevante per questo dataset Python, rilevante invece per la validazione SAR su MT5, sezione L, dove l'allineamento è verificato separatamente).

**Garanzia causale**: ogni `.rolling()` è trailing (mai `center=True`); le feature "giorno/settimana precedente" usano SOLO il giorno/settimana completo precedente (shift esplicito prima del merge); nessuna feature usa barre successive a quella di osservazione.

## Colonne (29 totali)

| Gruppo | Colonna | Definizione | Finestra/parametro |
|---|---|---|---|
| Trend | return_direction | segno del ritorno 1-barra | — |
| Trend | ema_slope_raw / ema_slope_atr_norm | ΔEMA, normalizzato in ATR | EMA(20) |
| Trend | directional_efficiency | Kaufman efficiency ratio | N=20 |
| Trend | trend_persistence_bars | barre consecutive con stesso segno di ritorno | lookback 20 |
| Volatility | atr | ATR di Wilder | N=14 |
| Volatility | atr_percentile | percentile causale dell'ATR corrente | finestra 252 |
| Volatility | realized_vol | std dei log-ritorni | N=20 |
| Volatility | vol_acceleration | ATR[i]-ATR[i-5] | lag 5 |
| Volatility | compression_percentile | percentile causale della media ATR a 10 barre | finestra 120 |
| Structure | dist_from_rolling_high/low_atr | distanza da massimo/minimo rolling, in ATR | N=20 |
| Structure | position_in_rolling_range | posizione [0,1] nel range rolling | N=20 |
| Structure | dist_from_prev_day/week_high/low_atr | distanza dal giorno/settimana COMPLETO precedente, in ATR | — |
| Momentum | roc | rate of change | N=10 |
| Momentum | momentum_acceleration | Δroc | — |
| Momentum | momentum_persistence_bars | barre consecutive con stesso segno di Δroc | lookback 20 |
| Statistical | lag1_autocorr_rolling | autocorrelazione lag-1 dei ritorni, rolling | finestra 60 |
| Statistical | variance_ratio_proxy | Var(ritorno k=4 barre)/(4×Var(ritorno 1 barra)) | finestra 60 |
| Statistical | mean_reversion_score | -lag1_autocorr_rolling | — |
| Time | hour_utc, session, day_of_week | ora/sessione/giorno della barra | mappa sessione fissa (vedi meta.json) |

**Warmup**: NaN concentrato nelle prime ~75 barre (atr_percentile, la finestra più lunga a 252) — non droppato, lasciato esplicito.

**Versione/provenance**: `schema_version:1`, parametri congelati in `P` dentro `build_market_state.py`, mai modificati dopo aver visto risultati di edge (nessun parametro qui è stato scelto guardando gli outcome di Phase 5.F-J).
