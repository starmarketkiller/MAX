---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: TURTLE_SOUP
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: TURTLE_SOUP

## Tipo
Reversal/liquidity sweep

## Trigger meccanico
Sweep di un estremo recente + rientro nel range (Turtle Soup classico), body[1]>=0.4 ATR per filtrare rumore.

## Configurazione attuale (v2.5.0)
- **Timeframe**: H1
- **SL**: 1.0× ATR · **TP**: 4.5× ATR
- **Filtro HTF**: True
- **Trailing**: largo (corre)
- **Rischio per trade**: 3.0%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 120 setup, 17W/12L/4BE, WR 58.6%, expR +0.298, **PF 3.15**
- **3 anni**: 54 setup, 11W/6L/2BE, WR 64.7%, expR +0.120, **PF 2.12**

## Stato
✅ VALIDATA — profittevole anche sui 3 anni

## Note


## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
