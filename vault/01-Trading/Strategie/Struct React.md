---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: STRUCT_REACT
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: STRUCT_REACT

## Tipo
SMC/structure reaction

## Trigger meccanico
Reazione di prezzo (pin bar/rigetto) su un livello di struttura registrato (OB/FVG/swing) via NXS_Reaction engine.

## Configurazione attuale (v2.5.0)
- **Timeframe**: H1
- **SL**: 1.0× ATR · **TP**: 4.5× ATR
- **Filtro HTF**: True
- **Trailing**: stretto
- **Rischio per trade**: 0.5%
- **Abilitata nell'EA**: **No — disabilitata in NXS_Profile_Enabled**

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 0 trade eseguiti in questo build. (1804 setup rilevati ma nessuno eseguito — strategia disabilitata/bloccata)
- **3 anni**: 0 trade eseguiti in questo build. (432 setup rilevati ma nessuno eseguito — strategia disabilitata/bloccata)

## Stato
🔴 DISABILITATA — Test reale v2.3.1: 85 trade, -102$ (la peggiore).

## Note


## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
