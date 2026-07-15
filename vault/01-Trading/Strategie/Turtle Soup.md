---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: TURTLE_SOUP
created: 2026-07-12
updated: 2026-07-15
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

## Risultati (backtest 10y segmentato v2.5.0, 5 anni affidabili 2019-2023)
181 trade totali. R per anno: 2019 +2.1 · 2020 -1.8 · 2021 +4.2 · 2022 -0.5 ·
2023 +3.3. **Somma +7.3R — 3 anni su 5 positivi**, migliore performer del
portafoglio. Insieme a BREAKOUT_ACC e CISD forma un nucleo che non è mai
negativo nello stesso anno — vedi [[NEXUS EA - Hedge nel Tempo]].

## Stato
✅ VALIDATA — profittevole sui 3 anni (v2.4.8) e riconfermata sui 5 anni
2019-2023 (v2.5.0, config invariata). La strategia più solida del portafoglio.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Hedge nel Tempo]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]
