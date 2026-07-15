---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: FVG_MIT
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: FVG_MIT

## Tipo
SMC / pattern strutturale

## Trigger meccanico
FVG mitigation su retest maturo con rejection. Mai vista in setup su MT5 (0 trade).

## Configurazione attuale (v2.5.0)
- **Timeframe**: vedi NXS_StrategyProfiles.mqh
- **SL**: vedi NXS_StrategyProfiles.mqh× ATR · **TP**: vedi NXS_StrategyProfiles.mqh× ATR
- **Filtro HTF**: vedi NXS_StrategyProfiles.mqh
- **Trailing**: vedi NXS_StrategyProfiles.mqh
- **Rischio per trade**: 0.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 0 trade eseguiti in questo build.
- **3 anni**: 0 trade eseguiti in questo build.

## Risultati (backtest 10y segmentato v2.5.0, 5 anni affidabili 2019-2023)
Ora esegue (era a 0 trade in v2.4.8): solo 3 trade in 5 anni (1W/2L), R totale
-0.2. Dato ancora troppo scarso per dire alcunché.

## Stato
🔬 Campione troppo piccolo — non più "nessun trade" ma il volume resta
bassissimo (3 trade in 5 anni), da monitorare senza aspettative.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]
