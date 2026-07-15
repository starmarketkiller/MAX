---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: EMA_PULLBACK
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: EMA_PULLBACK

## Tipo
Trend/pullback

## Trigger meccanico
EMA20>EMA50 (trend) + pullback che chiude di nuovo sopra EMA20 — logica del sito, riportata in v2.3.8.

## Configurazione attuale (v2.5.0)
- **Timeframe**: H4
- **SL**: 1.5× ATR · **TP**: 4.0× ATR
- **Filtro HTF**: True
- **Trailing**: stretto (incassa presto)
- **Rischio per trade**: 1.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, CONFIG PRECEDENTE (diversa da quella sopra))
- **3 mesi**: 379 setup, 12W/10L/6BE, WR 54.5%, expR +0.079, **PF 1.49**
- **3 anni**: 69 setup, 1W/7L/1BE, WR 12.5%, expR -0.377, **PF 0.14**

## Risultati (backtest 10y segmentato v2.5.0, 5 anni affidabili 2019-2023)
73 trade totali. R per anno: 2019 +0.6 · 2020 -2.1 · 2021 -3.1 · 2022 +2.4 ·
2023 +0.8. **Somma -1.4R — 3 anni su 5 positivi**, volatile (due anni
intermedi molto negativi tra due coppie di anni positivi). Dettaglio:
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]].

## Stato
⏳ PENDING — vicina al pareggio sui 5 anni ma poco stabile anno su anno. Non
prioritaria come SAR/MACD/ADX_RSI, ma nemmeno pronta per la validazione.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]
