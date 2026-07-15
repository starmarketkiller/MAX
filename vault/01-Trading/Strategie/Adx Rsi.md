---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: ADX_RSI
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: ADX_RSI

## Tipo
Trend-following

## Trigger meccanico
EMA50 come filtro trend + RSI in banda 45-65 (long) / 35-55 (short) — logica del sito, riportata in v2.3.8.

## Configurazione attuale (v2.5.0)
- **Timeframe**: D1
- **SL**: 1.0× ATR · **TP**: 4.0× ATR
- **Filtro HTF**: True
- **Trailing**: largo (corre)
- **Rischio per trade**: 1.3%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, CONFIG PRECEDENTE (diversa da quella sopra))
- **3 mesi**: 4361 setup, 20W/26L/11BE, WR 43.5%, expR +0.014, **PF 1.17**
- **3 anni**: 780 setup, 21W/42L/19BE, WR 33.3%, expR -0.094, **PF 0.45**

## Risultati (backtest 10y segmentato v2.5.0, 6 anni affidabili 2019-2024)
596 trade totali. R per anno: 2019 +0.4 · 2020 -3.0 · 2021 -3.7 · 2022 -4.2 ·
2023 -3.7 · 2024 -1.1. **Somma -15.3R — solo 1 anno su 6 positivo (2019,
marginale +0.4)**. Il 2024 è meno negativo dei tre anni precedenti — primo
segno debole di miglioramento, da confermare col segmento 10. Dettaglio
completo: [[NEXUS EA - Backtest 10Y Segmentato - Analisi]].

## Stato
🔴 FALLITA — confermato su campione ampio (452 trade). Come SAR, l'HTF filter
è correttamente attivo nel codice (`NXS_StrategyProfiles.mqh:23`) ma il fix
non ha invertito la tendenza già vista su v2.4.8 (PF 0.45 sui 3 anni). Peggiora
anno dopo anno dal 2019 al 2022. Terza priorità di intervento dopo SAR e MACD.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]
