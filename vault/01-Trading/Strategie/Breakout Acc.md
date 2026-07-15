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

## Risultati (backtest 10y segmentato v2.5.0, 5 anni affidabili 2019-2023)
73 trade totali. R per anno: 2019 +1.2 · 2020 +0.7 · 2021 -0.5 · 2022 +2.0 ·
2023 +0.5. **Somma +3.9R — 4 anni su 5 positivi**. In controfase con
TURTLE_SOUP in 3 dei 5 anni (quando una perde l'altra guadagna) — le due non
sono mai negative nello stesso anno. Vedi [[NEXUS EA - Hedge nel Tempo]].

## Stato
🟢 PROMETTENTE — riabilitata con successo in v2.5.0 (era a 0 trade in v2.4.8).
Campione ancora sotto la soglia dei 15 trade/anno per essere pienamente
affidabile, ma il segnale su 5 anni è coerente. Candidata prioritaria per un
test isolato del nucleo hedge insieme a TURTLE_SOUP e CISD.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Hedge nel Tempo]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]
