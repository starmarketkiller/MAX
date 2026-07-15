---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: RSI_DIV
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: RSI_DIV

## Tipo
Reversal/divergenza

## Trigger meccanico
Divergenza RSI-prezzo: minimo di prezzo più basso ma RSI più alto (o viceversa per short).

## Configurazione attuale (v2.5.0)
- **Timeframe**: H1
- **SL**: 1.0× ATR · **TP**: 4.5× ATR
- **Filtro HTF**: False
- **Trailing**: stretto (incassa presto)
- **Rischio per trade**: 1.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 502 setup, 45W/46L/6BE, WR 49.5%, expR +0.024, **PF 1.07**
- **3 anni**: 135 setup, 24W/22L/3BE, WR 52.2%, expR -0.044, **PF 0.86**

## Risultati (backtest 10y segmentato v2.5.0, 5 anni affidabili 2019-2023)
285 trade totali. R per anno: 2019 +1.6 · 2020 +1.3 · 2021 -2.0 · 2022 **-9.4**
· 2023 +1.1. **Somma -7.4R — 3 anni su 5 positivi**, ma un singolo anno
(2022) da solo cancella tutti gli altri. Dettaglio:
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]].

## Stato
❌ NON VALIDATA — sotto PF 1.0 sui 3 anni e sui 5 anni. Diversa dagli altri
falliti: qui il problema sembra concentrato in un singolo anno anomalo (2022)
più che una tendenza strutturale — varrebbe la pena capire cosa è successo
nel 2022 specificamente prima di scartarla.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]
