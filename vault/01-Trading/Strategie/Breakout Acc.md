---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: BREAKOUT_ACC
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: BREAKOUT_ACC

## Tipo
Breakout/accettazione

## Trigger meccanico
Chiusura sopra/sotto un range di 20 barre per 2 candele consecutive (accettazione, non solo tocco).

## Configurazione attuale (v2.5.0)
- **Timeframe**: D1
- **SL**: 1.0× ATR · **TP**: 4.5× ATR
- **Filtro HTF**: True
- **Trailing**: largo (corre)
- **Rischio per trade**: 0.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, CONFIG PRECEDENTE (diversa da quella sopra))
- **3 mesi**: 0 trade eseguiti in questo build. (250 setup rilevati ma nessuno eseguito — strategia disabilitata/bloccata)
- **3 anni**: 0 trade eseguiti in questo build. (268 setup rilevati ma nessuno eseguito — strategia disabilitata/bloccata)

## Risultati (backtest 10y segmentato v2.5.0, 6 anni affidabili 2019-2024)
101 trade totali. R per anno: 2019 +1.2 · 2020 +0.7 · 2021 -0.5 · 2022 +2.0 ·
2023 +0.5 · 2024 +0.4. **Somma +4.3R — 5 anni su 6 positivi**, l'unica delle
tre del nucleo hedge a restare solidamente positiva anche nel 2024 (quando
TURTLE_SOUP e CISD sono girate negative). La componente più stabile del
nucleo. Vedi [[NEXUS EA - Hedge nel Tempo]].

## Stato
🟢 PROMETTENTE — la migliore del portafoglio dopo l'aggiornamento del
segmento 9 (TURTLE_SOUP si è ridimensionata). Campione ancora sotto la soglia
dei 15 trade/anno per essere pienamente affidabile, ma il segnale su 6 anni è
il più coerente di tutti. Candidata prioritaria per un test isolato del
nucleo hedge, ora come componente centrale più che paritaria.

## Fix Blocco 5 (16/07): 5° bug di proxy trovato, ma qui il segnale regge (e migliora)
Controllo sistematico di tutte le strategie "reali" sul sito (non tra i 6
proxy già dichiarati) su richiesta dell'utente dopo i 4 bug trovati su
SAR/BJORGUM/MACD/RSI_DIV. Trovato: `sig_breakout` (riusato per
BREAKOUT_ACC) chiedeva **una sola chiusura** oltre il range — la vera
`NXS_Strat_BreakoutAcc()` richiede **due chiusure consecutive** (vera
"Acceptance", il concetto stesso nel nome). Creata `sig_breakout_acc()`
dedicata con la logica corretta.

A differenza degli altri 4 bug, qui **la correzione non smentisce il
segnale**: sulla config reale (D1) il PF **migliora** (1.88→2.15) e il DD
**scende** (15.91%→12.25%) — BREAKOUT_ACC, già la componente più stabile
del nucleo hedge su MT5 reale, si conferma solida anche col test corretto.
Nessun cambio al profilo MQL5 (D1 resta la scelta giusta), solo il proxy
sito sistemato per accuratezza futura.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Hedge nel Tempo]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]]
