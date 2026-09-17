# Feature Redundancy Audit v1 (Phase 5.5 sec.9)

Analisi reale (Pearson + Spearman, non stimata) delle 25 feature numeriche di `market_state_dataset_v1.csv`. Script: `server/research_scripts/phase5_5/feature_redundancy_audit.py`. Output completo: `feature_redundancy_audit_v1.json`. **Nessuna feature rimossa** (richiesto esplicitamente) — solo classificata.

## Classificazione (25 feature)

| Classe | n | Feature |
|---|---|---|
| UNIQUE | 13 | atr, directional_efficiency, trend_persistence_bars, atr_percentile, realized_vol, vol_acceleration, compression_percentile, dist_from_prev_day_low_atr, dist_from_prev_week_low_atr, roc, momentum_acceleration, momentum_persistence_bars, variance_ratio_proxy |
| REDUNDANT (derivazione di formula nota) | 5 | ema_slope_atr_norm (= ema_slope_raw/ATR), dist_from_rolling_high_atr (lato opposto di dist_from_rolling_low_atr), dist_from_prev_day_high_atr, dist_from_prev_week_high_atr, mean_reversion_score (= -lag1_autocorr_rolling) |
| HIGHLY_CORRELATED (associazione empirica, non formula) | 4 | ema_slope_raw, dist_from_rolling_low_atr, position_in_rolling_range, lag1_autocorr_rolling |
| KEEP_FOR_INTERPRETABILITY | 3 | return_direction, hour_utc, day_of_week |

## Coppie ad alta correlazione trovate (soglia \|r\|>0.90)

| Coppia | Pearson | Spearman | Tipo |
|---|---|---|---|
| lag1_autocorr_rolling ↔ mean_reversion_score | -1.000 | -1.000 | Derivazione di formula esatta (negazione) |
| ema_slope_raw ↔ ema_slope_atr_norm | 0.899 | 0.976 | Derivazione di formula (stessa quantità, scala diversa) |
| ema_slope_atr_norm ↔ position_in_rolling_range | 0.896 | 0.938 | **Empirica** — trend e location nel range sono meccanicamente collegati (un EMA in salita tende a coincidere con prezzo vicino ai massimi recenti) |
| dist_from_rolling_high_atr ↔ position_in_rolling_range | 0.884 | 0.950 | Empirica (stessa ragione) |
| dist_from_rolling_low_atr ↔ position_in_rolling_range | 0.873 | 0.933 | Empirica |
| ema_slope_raw ↔ position_in_rolling_range | 0.796 | 0.914 | Empirica |

## Interpretazione

Le due REDUNDANT "per formula" (ema_slope_atr_norm, mean_reversion_score) sono trasformazioni dirette di un'altra feature già presente — tenerle entrambe non è un errore (a volte la versione normalizzata è più comoda per confronti cross-regime), ma vanno **mai usate insieme come due predittori "indipendenti"** in un futuro modello (logistic regression, decision tree) senza saperlo.

Il gruppo HIGHLY_CORRELATED più interessante (ema_slope, dist_from_rolling_high/low, position_in_rolling_range, tutti correlati fra 0.79 e 0.95) rivela che **"trend" e "location nel range" non sono due assi indipendenti in questo dataset** — sono in gran parte la stessa informazione osservata da due formule diverse. Questo è rilevante retroattivamente per Phase 5: l'interazione predefinita `SWEEP_RECLAIM_x_LOCATION` (sec.F di Phase 5) usava `position_in_rolling_range` come condizione "indipendente" dal trend, ma la correlazione qui trovata suggerisce che quella condizione catturava in parte informazione di trend già implicitamente presente altrove — non invalida il risultato (che era comunque NO_EDGE), ma va tenuto a mente se in futuro si vorrà scomporre "location" e "trend" come due condizioni davvero distinte.

Nessuna feature è risultata LOW_INFORMATION (quasi costante) in questo dataset.
