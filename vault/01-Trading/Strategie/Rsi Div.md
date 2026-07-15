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

## Risultati (backtest 10y segmentato v2.5.0, 6 anni affidabili 2019-2024)
416 trade totali. R per anno: 2019 +1.6 · 2020 +1.3 · 2021 -2.0 · 2022 -9.4 ·
2023 +1.1 · **2024 -10.1**. **Somma -17.5R — 3 anni su 6 positivi**, ma ora
DUE anni catastrofici (2022 e 2024, entrambi peggiori di -9R) invece di uno
solo — il 2024 smentisce l'ipotesi "evento isolato nel 2022". Dettaglio:
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]].

## Stato
🔴 FALLITA — sale nel gruppo delle priorità con il segmento 9: con due anni
catastrofici su sei, non è più difendibile come "evento isolato del 2022".
Da rivedere con la stessa urgenza di SAR/MACD/ADX_RSI.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]
