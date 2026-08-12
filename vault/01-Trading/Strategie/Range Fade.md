---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: RANGE_FADE
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: RANGE_FADE

## Tipo
SMC / pattern strutturale

## Trigger meccanico
Fade del range (mean-reversion in laterale). Mai vista in setup su MT5 (0 trade in ogni test finora).

## Configurazione attuale (v2.5.0)
- **Timeframe**: vedi NXS_StrategyProfiles.mqh
- **SL**: vedi NXS_StrategyProfiles.mqh× ATR · **TP**: vedi NXS_StrategyProfiles.mqh× ATR
- **Filtro HTF**: vedi NXS_StrategyProfiles.mqh
- **Trailing**: vedi NXS_StrategyProfiles.mqh
- **Rischio per trade**: 0.6%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 0 trade eseguiti in questo build.
- **3 anni**: 0 trade eseguiti in questo build.

## Stato
PENDING — nessun trade eseguito sui 3 anni, dato insufficiente

## Aggiornamento 11/08 — proxy letterale, nessun test separato necessario

Confermato in `backtest.py`: `"RANGE_FADE": sig_bollinger, # mean-reversion
proxy` — riusa esattamente lo stesso trigger di BOLLINGER, non una logica
indipendente. Qualunque risultato su BOLLINGER si applica identico qui.
Vedi [[Bollinger]] per l'analisi (storico ampio: 1d quasi pareggio,
filtro regime WEAK_TREND aiuta solo fuori dal TF di profilo reale).

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
