# Market State Vector v1 — schema e catalogo feature

Rappresentazione causale quantitativa dello stato di mercato. Ogni feature deve dichiarare `observation_point` (quando è calcolabile senza look-ahead) ed essere derivabile SOLO da dati fino a quell'istante incluso.

## Schema (per singola osservazione)

```json
{
  "schema_version": 1,
  "symbol": "GOLD",
  "timeframe": "H4",
  "bar_time": "2026-09-17T04:00:00Z",
  "observation_point": "bar_close",
  "trend": {
    "direction": -1,
    "slope_ema20": 0.0,
    "slope_ema50": 0.0,
    "strength_adx": 0.0,
    "persistence_bars": 0,
    "directional_efficiency": 0.0
  },
  "volatility": {
    "atr14": 0.0,
    "realized_vol_20": 0.0,
    "atr_percentile_252": 0.0,
    "vol_acceleration": 0.0,
    "compression_state": "NONE|COMPRESSING|COMPRESSED|EXPANDING",
    "vol_of_vol_20": 0.0
  },
  "structure": {
    "range_state": "INSIDE|AT_EXTREME|BREAKOUT",
    "swing_state": "HH|HL|LH|LL|UNDEFINED",
    "dist_from_recent_high_atr": 0.0,
    "dist_from_recent_low_atr": 0.0,
    "prev_day_high": 0.0, "prev_day_low": 0.0,
    "prev_week_high": 0.0, "prev_week_low": 0.0,
    "pos_in_rolling_range_pct": 0.0,
    "reentry_state": "NONE|BREAKOUT_PENDING|REENTERED"
  },
  "momentum": {
    "magnitude_roc_10": 0.0,
    "persistence_bars": 0,
    "acceleration": 0.0,
    "exhaustion_score": 0.0
  },
  "liquidity_activity": {
    "tick_activity_percentile": null,
    "spread_state": null,
    "sweep_state": "NONE|SWEEP_HIGH|SWEEP_LOW",
    "reclaim_state": "NONE|RECLAIMED_HIGH|RECLAIMED_LOW",
    "displacement_score": 0.0,
    "imbalance_density": null
  },
  "statistical_behavior": {
    "autocorr_lag1_20": 0.0,
    "variance_ratio_2_10": 0.0,
    "mean_reversion_score": 0.0,
    "realized_skew_20": 0.0,
    "tail_ratio_20": 0.0
  },
  "time": {
    "session": "ASIA|LONDON|NY|OVERLAP",
    "hour_utc": 4,
    "day_of_week": 3,
    "month": 9,
    "seasonality_bucket": null
  },
  "cross_market": {
    "dxy_available": false,
    "us_yields_available": false,
    "silver_gold_ratio_available": false,
    "vol_proxy_available": false,
    "futures_positioning_available": false
  }
}
```

## Catalogo feature — disponibilità/costo/sicurezza causale/priorità

| Feature | Disponibile oggi | Causalmente sicura | Costo dati | Frequenza | Plausibilità economica | Priorità |
|---|---|---|---|---|---|---|
| trend.direction/slope (EMA) | SI (EMA già in NXS_Globals) | SI (solo barre chiuse) | zero | per barra | alta (persistenza di trend è pattern noto) | P1 |
| trend.strength (ADX) | SI (ADX_RSI la usa già) | SI | zero | per barra | alta | P1 |
| trend.directional_efficiency | NO (non calcolata oggi) | SI (Kaufman efficiency ratio, causale) | zero (calcolo puro) | per barra | media-alta | P2 |
| volatility.atr | SI (g_atr) | SI | zero | per barra | alta | P1 |
| volatility.realized_vol | NO | SI | zero | per barra | alta | P1 |
| volatility.atr_percentile | NO | SI (percentile su finestra rolling passata, causale se la finestra non include il campione corrente in modo non causale — va implementato con attenzione) | zero | per barra | alta | P1 |
| volatility.compression/expansion | PARZIALE (BB_SQUEEZE la implica implicitamente) | SI | zero | per barra | alta | P1 |
| volatility.vol_of_vol | NO | SI | zero | per barra | media | P3 |
| structure.range_state/swing_state | PARZIALE (dentro a strategie tipo RANGE_FADE, LEVEL_REACTION, non esposta come feature indipendente) | SI se lo swing è confermato solo a barre chiuse (attenzione: uno swing "confermato" spesso richiede N barre successive — rischio look-ahead se non gestito, vedi Failure Memory) | zero | per barra | alta | P1 |
| structure.prev_day/week H/L | SI (dato OHLC standard) | SI | zero | per barra | alta | P1 |
| momentum.roc/acceleration/exhaustion | PARZIALE (RSI/MACD/TSI la implicano) | SI | zero | per barra | alta | P1 |
| liquidity.tick_activity_percentile | NO (serve dati tick, non solo OHLC) | SI se calcolata solo su tick passati | medio (serve storicizzare tick count per barra) | per barra (da tick) | media | P2 |
| liquidity.spread_state | PARZIALE (dipende da broker/simbolo, spesso non storicizzato) | SI | basso-medio (serve log spread storico, non sempre disponibile da MT5 storico) | per tick | media | P3 |
| liquidity.sweep_state/reclaim_state | PARZIALE (WICK_SWEEP_* la implementano dentro la strategia, non come feature di stato condivisa) | SI | zero | per barra | alta | P1 (va estratta come Event indipendente, sezione Event Registry) |
| liquidity.displacement_score | NO | SI | zero | per barra | media-alta | P2 |
| liquidity.imbalance_density | NO (richiede order flow/FVG count, non tick-by-tick order book — MT5 non fornisce book L2) | NO per order-flow vero (MT5 retail non ha depth-of-market storico affidabile); SI se ridefinita come "densità di FVG/gap price-based" (proxy, non vero order flow) | zero se proxy price-based | per barra | media (solo come proxy) | P3 |
| statistical.autocorrelation/variance_ratio | NO | SI (calcolo puro su ritorni passati) | zero | per barra | media (utile per distinguere regime trend/mean-reversion) | P2 |
| statistical.skew/tail | NO | SI | zero | per barra | media | P3 |
| time.session/hour/dow/month | SI (già usata da filtri sessione esistenti) | SI | zero | per barra | alta (effetti di sessione noti e già sfruttati in NEXUS) | P1 |
| time.seasonality_bucket | NO (nessuna feature stagionale esplicita oggi) | SI ma richiede molti anni di storico per essere robusta — rischio overfitting su pochi cicli annuali | zero | per barra | bassa-media (da trattare con cautela, alto rischio data-mining) | P3 |
| cross_market.DXY | NO | SI se i dati DXY sono allineati per timestamp e non ri-espressi con revisioni successive | dati esterni (feed aggiuntivo, es. Dukascopy USDX o proxy sintetico da majors) | per barra | alta (oro è storicamente anti-correlato a USD) | P2 — vale la pena investigare la fonte dati |
| cross_market.US yields | NO | SI in linea di principio, ma yields ufficiali spesso hanno revisioni/gap di pubblicazione — rischio leakage se la fonte non è tick-accurate storicamente | dati esterni (serve provider, es. FRED/ICE, non banale integrarlo tick-accurate) | giornaliera tipicamente (mismatch di frequenza con H4/M15 NEXUS) | alta (yields reali guidano il gold) | P3 (costo/complessità alta rispetto a beneficio nel breve termine) |
| cross_market.silver/gold ratio | NO | SI se entrambi i simboli hanno storico tick-accurate sincronizzato (Dukascopy ha anche XAGUSD) | basso (stesso downloader Dukascopy già in uso) | per barra | media (relazione nota ma meno diretta di DXY) | P2 |
| cross_market.vol proxy (es. VIX-like) | NO | dipende dalla fonte — VIX vero è su equity, non oro; servirebbe un proxy specifico (es. GVZ, Gold volatility index) o vol realizzata multi-asset | dati esterni, potenzialmente a pagamento per GVZ storico | giornaliera | media | P3 |
| cross_market.futures positioning (COT) | NO | SI ma a bassissima frequenza (settimanale, pubblicato con ritardo) — utile solo come feature di regime lento, mai per trigger di breve periodo | dati esterni gratuiti (CFTC COT report) | settimanale | media (utile per bias di posizionamento, non per timing) | P3 |

**Nota metodologica.** "Disponibile oggi" = calcolabile da dati OHLC/tick già presenti in NEXUS senza nuove fonti esterne. "Causalmente sicura" segnala esplicitamente dove il rischio di look-ahead è concreto (swing confirmation, percentile su finestra, feature stagionali con pochi cicli) — questi casi vanno implementati con lo stesso rigore già richiesto per FROZEN_SIGNAL_SPEC_V1: definire l'observation point ESATTO prima di calcolare qualunque statistica su di esso.
