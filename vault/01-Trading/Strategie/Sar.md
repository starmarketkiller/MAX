---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: SAR
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: SAR

## Tipo
Trend-following

## Trigger meccanico
Parabolic SAR sotto il prezzo + EMA9>EMA21 (long, speculare per short).

## Configurazione attuale (v2.5.0)
- **Timeframe**: H4
- **SL**: 1.5× ATR · **TP**: 4.0× ATR
- **Filtro HTF**: True
- **Trailing**: largo (corre)
- **Rischio per trade**: 1.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, CONFIG PRECEDENTE (diversa da quella sopra))
- **3 mesi**: 3163 setup, 81W/109L/22BE, WR 42.6%, expR +0.041, **PF 1.21**
- **3 anni**: 1169 setup, 72W/80L/17BE, WR 47.4%, expR -0.035, **PF 0.88**

## Risultati (backtest 10y segmentato v2.5.0, 6 anni affidabili 2019-2024)
1.129 trade totali. R per anno: 2019 -10.9 · 2020 -14.3 · 2021 -1.9 · 2022
-1.4 · 2023 -0.7 · 2024 -5.1. **Somma -34.3R — 0 anni su 6 positivi.** La
peggiore di tutte le 38 strategie, di gran lunga, e il segmento 9 conferma
ulteriormente il pattern (nessun segno di ripresa). Dettaglio completo:
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]].

## ⚠️ Scoperta 15/07: il proxy sito non testa SAR
`sig_sar()` in `server/backtest.py` è, di fatto, un incrocio EMA20/EMA50 —
verificato eseguendolo che produce la sequenza di trade **identica,
operazione per operazione**, a `sig_ema_pullback()` sugli stessi dati.
Il sito non ha mai testato Parabolic SAR. Il numero "PF1.52" citato per
giustificare il fix HTF v2.5.0 non dice nulla sulla vera strategia. Dettaglio:
[[NEXUS EA - Motore Sito: Audit e Confronto 10Y]].

## Stato
🔴 FALLITA — confermato su campione ampio (1.129 trade, 6 anni consecutivi
tutti negativi). Il filtro HTF di v2.5.0 è correttamente attivo nel codice
(`NXS_StrategyProfiles.mqh:45`) ma la sua giustificazione (screening sito) è
**invalida** — vedi sopra. **Priorità #1, doppia**: (1) spegnere o riscrivere
la logica di trigger MQL5 da zero (Parabolic SAR reale, non un incrocio EMA);
(2) fixare il proxy del sito così da poter testare la strategia vera prima di
rimetterla in produzione.

## Analisi trade-level (15/07)
Score interno senza potere predittivo (WR piatto ~40-44% da score 60 a 99).
Bias direzionale forte: LONG 45.7% WR vs SHORT 38.0% WR. Tagliando gli short
la perdita si dimezza ma **resta negativa** (-380.7$ vs -1.054.7$ totali) —
a differenza di MACD/RSI_DIV, qui il problema non è solo direzionale.
Dettaglio: [[NEXUS EA - Analisi Trade-Level SAR MACD RSI_DIV]].

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Motore Sito: Audit e Confronto 10Y]] · [[NEXUS EA - Analisi Trade-Level SAR MACD RSI_DIV]]
