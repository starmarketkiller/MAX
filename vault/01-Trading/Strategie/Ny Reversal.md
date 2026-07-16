---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: NY_REVERSAL
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: NY_REVERSAL

## Tipo
Sessione/ICT (non portabile dal sito)

## Trigger meccanico
Reversal di sessione New York.

## Configurazione attuale (v2.5.0)
- **Timeframe**: N/D — non connessa al collector segnali
- **SL**: N/D — non connessa al collector segnali× ATR · **TP**: N/D — non connessa al collector segnali× ATR
- **Filtro HTF**: N/D — non connessa al collector segnali
- **Trailing**: N/D — non connessa al collector segnali
- **Rischio per trade**: N/D — non connessa al collector segnali%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 0 trade eseguiti in questo build.
- **3 anni**: 0 trade eseguiti in questo build.

## Stato
🔬 Prima serie di dati mai raccolta (16/07) — non più NOT_CONNECTED. Miglior
PF del gruppo su 1h (1.42) ma campione minuscolo (20 trade) — troppo poco
per fidarsi ([[NEXUS EA - Principi]] #4). Su 4h campione ancora più piccolo
(10 trade) e negativo. Nessun profilo MT5 esiste ancora.

## Prima connessione al sito (16/07)
Implementata la vera logica MQL5 (`NXS_Strat_NYReversal`): sessione
NY/Overlap + high/low della sessione Londra precedente (6-12 GMT, calcolato
dalle ultime 48 barre) come riferimento + sweep di quel range + CHoCH
(proxy). Vedi [[Amd Cont]] per il metodo.

Test SL1.5/TP3.0 generico, ~2 anni Yahoo intraday:

| TF | Trade | PF | DD% | Net |
|---|---|---|---|---|
| 1h | 20 | **1.42** | 2.97 | +470 |
| 4h | 10 | 0.50 | 6.79 | -400 |

Il campione più piccolo delle 7 strategie a sessione — il PF1.42 è
interessante ma su soli 20 trade non è ancora un segnale, è rumore
potenziale. Da riguardare quando ci sarà più storico. Non ancora validata
su MT5 (`InpStrategySelector=31`).

## Note

## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[Amd Cont]]
