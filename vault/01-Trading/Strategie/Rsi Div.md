---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: RSI_DIV
created: 2026-07-12
updated: 2026-07-12
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

## Stato
❌ NON VALIDATA — sotto PF 1.0 sui 3 anni (fallisce fuori-campione)

## Note


## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
