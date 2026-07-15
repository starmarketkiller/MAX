---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: BJORGUM
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: BJORGUM

## Tipo
Trend/livelli chiave

## Trigger meccanico
Rottura di livelli chiave Bjorgum con conferma HTF.

## Configurazione attuale (v2.5.0)
- **Timeframe**: H4
- **SL**: 1.0× ATR · **TP**: 4.5× ATR
- **Filtro HTF**: True
- **Trailing**: stretto (incassa presto)
- **Rischio per trade**: 2.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 133 setup, 6W/4L/0BE, WR 60.0%, expR +0.046, **PF 1.31**
- **3 anni**: 23 setup, 4W/1L/1BE, WR 80.0%, expR +0.210, **PF 2.14**

## Risultati (backtest 10y segmentato v2.5.0, 5 anni affidabili 2019-2023)
46 trade totali. R per anno: 2019 -3.1 · 2020 -0.8 · 2021 -2.3 · 2022 -2.0 ·
2023 +1.6. **Somma -6.6R — 4 anni su 5 negativi.** Il campione più ampio
ribalta completamente il segnale ottimista dei 3 anni (PF 2.14, ma solo 5
trade eseguiti) — esattamente il rischio descritto in
[[NEXUS EA - Principi]] #4. Dettaglio: [[NEXUS EA - Backtest 10Y Segmentato - Analisi]].

## Stato
⏳ PENDING, ma il segnale si è ribaltato in negativo — non trattarla più come
"attraente ma con pochi dati". Con 46 trade il PF non è più rumore: è un
trend negativo reale in 4 anni su 5.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]
