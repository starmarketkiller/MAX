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

## Risultati (backtest 10y segmentato v2.5.0, 5 anni affidabili 2019-2023)
838 trade totali. R per anno: 2019 -10.9 · 2020 -14.3 · 2021 -1.9 · 2022 -1.4 ·
2023 -0.7. **Somma -29.2R — 0 anni su 5 positivi.** La peggiore di tutte le 38
strategie, di gran lunga. Dettaglio completo:
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]].

## Stato
🔴 FALLITA — confermato su campione ampio (838 trade). Il filtro HTF di
v2.5.0 è correttamente attivo nel codice (`NXS_StrategyProfiles.mqh:45`) ma
SAR non compare nemmeno tra le config vincenti dello screening sito — il fix
le è stato applicato per generalizzazione, non perché il suo screening
individuale lo confermasse. **Priorità #1**: spegnere o riscrivere la logica
di trigger da zero, non ha mai avuto un anno positivo in 5 anni di dati reali.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]
