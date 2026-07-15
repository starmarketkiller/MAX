---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: MACD
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: MACD

## Tipo
Trend-following

## Trigger meccanico
MACD > signal e sopra 0, prezzo sopra EMA200 (long, speculare per short).

## Configurazione attuale (v2.5.0)
- **Timeframe**: H4
- **SL**: 2.0× ATR · **TP**: 3.0× ATR
- **Filtro HTF**: True
- **Trailing**: stretto (incassa presto)
- **Rischio per trade**: 1.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, CONFIG PRECEDENTE (diversa da quella sopra))
- **3 mesi**: 2134 setup, 72W/48L/24BE, WR 60.0%, expR +0.062, **PF 1.35**
- **3 anni**: 742 setup, 52W/42L/13BE, WR 55.3%, expR +0.023, **PF 1.11**

## Risultati (backtest 10y segmentato v2.5.0, 6 anni affidabili 2019-2024)
994 trade totali. R per anno: 2019 -6.2 · 2020 -11.9 · 2021 +2.5 · 2022 -4.4 ·
2023 +1.5 · 2024 -2.6. **Somma -21.1R — 2 anni su 6 positivi**, dominata da
due anni catastrofici (2019 e 2020). Il 2024 resta negativo ma meno grave dei
peggiori. Dettaglio completo: [[NEXUS EA - Backtest 10Y Segmentato - Analisi]].

## Stato
🔴 REGREDITA — questa è la scoperta più importante su MACD: sotto v2.4.8 era
**già validata** (PF 1.11 sui 3 anni, 94 trade). Il "raffinamento" v2.5.0
basato sullo screening sito (motore Python/Yahoo, non MT5) l'ha resa la
**seconda peggiore strategia del portafoglio**. Conferma [[NEXUS EA -
Principi]] #5 su scala molto più ampia: un edge del sito non va sostituito a
una config MT5 già validata senza prima confermarlo su MT5. Da valutare se
tornare alla config v2.4.8 (SL/TP diversi, vedi log commit) e ri-testare.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]
