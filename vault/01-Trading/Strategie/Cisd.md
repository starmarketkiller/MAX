---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: CISD
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: CISD

## Tipo
SMC/change in state

## Trigger meccanico
3 barre dello stesso segno + rottura dell'estremo (Change in State of Delivery).

## Configurazione attuale (v2.5.0)
- **Timeframe**: H4
- **SL**: 1.5× ATR · **TP**: 3.0× ATR
- **Filtro HTF**: True
- **Trailing**: stretto (incassa presto)
- **Rischio per trade**: 0.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 57 setup, 1W/2L/1BE, WR 33.3%, expR -0.209, **PF 0.18**
- **3 anni**: 9 setup, 1W/0L/0BE, WR 100.0%, expR +0.323, **PF 99.00**

## Risultati (backtest 10y segmentato v2.5.0, 5 anni affidabili 2019-2023)
15 trade totali (ancora pochi). R per anno: 2019 0.0 · 2020 0.0 · 2021 +0.7 ·
2022 +1.9 · 2023 +0.9. **Somma +3.5R — 0 anni su 5 negativi**, l'unica
strategia del portafoglio a non aver mai chiuso un anno in rosso. Terzo membro
del nucleo hedge con TURTLE_SOUP e BREAKOUT_ACC — vedi
[[NEXUS EA - Hedge nel Tempo]].

## Stato
🟢 PROMETTENTE — campione ancora troppo piccolo (15 trade in 5 anni, sotto la
soglia dei ~15/anno) per dichiararla validata, ma il segnale è coerente e mai
negativo. Prioritaria per un test isolato del nucleo hedge.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Hedge nel Tempo]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]
