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

## Risultati (backtest 10y segmentato v2.5.0, 6 anni affidabili 2019-2024)
18 trade totali (ancora pochi). R per anno: 2019 0.0 · 2020 0.0 · 2021 +0.7 ·
2022 +1.9 · 2023 +0.9 · 2024 -0.3. **Somma +3.2R — 1 anno su 6 negativo**
(2024, comunque marginale). Il primo anno in rosso della sua storia, ma resta
il terzo membro del nucleo hedge con TURTLE_SOUP e BREAKOUT_ACC — vedi
[[NEXUS EA - Hedge nel Tempo]].

## Stato
🟢 PROMETTENTE — campione ancora troppo piccolo (18 trade in 6 anni, sotto la
soglia dei ~15/anno) per dichiararla validata. Il segnale resta coerente ma
non più "mai negativo" come sembrava dopo i primi 5 anni.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Hedge nel Tempo]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]
