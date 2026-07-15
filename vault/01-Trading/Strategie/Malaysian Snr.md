---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: MALAYSIAN_SNR
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: MALAYSIAN_SNR

## Tipo
SMC / pattern strutturale

## Trigger meccanico
Support/resistance con storyline (fresh/flipped). Attiva ma non ancora validata a fondo su MT5.

## Configurazione attuale (v2.5.0)
- **Timeframe**: vedi NXS_StrategyProfiles.mqh
- **SL**: vedi NXS_StrategyProfiles.mqh× ATR · **TP**: vedi NXS_StrategyProfiles.mqh× ATR
- **Filtro HTF**: vedi NXS_StrategyProfiles.mqh
- **Trailing**: vedi NXS_StrategyProfiles.mqh
- **Rischio per trade**: 0.4%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 6 setup, 1W/0L/1BE, WR 100.0%, expR +0.164, **PF 99.00**
- **3 anni**: 0 trade eseguiti in questo build.

## Risultati (backtest 10y segmentato v2.5.0, 5 anni affidabili 2019-2023)
Ora esegue davvero (era a 0 trade in v2.4.8): 10 trade totali in 5 anni. R per
anno: 2019 +0.3 · 2020 +0.4 · 2021 -0.4 · 2022 +0.1 · 2023 0.0. **Somma +0.4R —
1 anno su 5 negativo**. Ancora troppo pochi trade per giudicare, ma il segnale
è leggermente positivo.

## Stato
🔬 Campione troppo piccolo (dato insufficiente) — ma non più "nessun trade":
ora esegue, va solo lasciata accumulare più campione.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]
