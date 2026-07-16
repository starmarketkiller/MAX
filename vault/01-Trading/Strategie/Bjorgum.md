---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: BJORGUM
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: BJORGUM

## Tipo
Trend/livelli chiave

## Trigger meccanico
Rottura di livelli chiave Bjorgum con conferma HTF.

## Configurazione attuale (v2.5.0)
- **Timeframe**: H4
- **SL**: 1.0× ATR · **TP**: 4.5× ATR
- **Filtro HTF**: True
- **Trailing**: stretto (incassa presto)
- **Rischio per trade**: 2.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 133 setup, 6W/4L/0BE, WR 60.0%, expR +0.046, **PF 1.31**
- **3 anni**: 23 setup, 4W/1L/1BE, WR 80.0%, expR +0.210, **PF 2.14**

## Risultati (backtest 10y segmentato v2.5.0, 5 anni affidabili 2019-2023)
46 trade totali. R per anno: 2019 -3.1 · 2020 -0.8 · 2021 -2.3 · 2022 -2.0 ·
2023 +1.6. **Somma -6.6R — 4 anni su 5 negativi.** Il campione più ampio
ribalta completamente il segnale ottimista dei 3 anni (PF 2.14, ma solo 5
trade eseguiti) — esattamente il rischio descritto in
[[NEXUS EA - Principi]] #4. Dettaglio: [[NEXUS EA - Backtest 10Y Segmentato - Analisi]].

## Stato
🔴 Confermato su 10 segmenti: **96 trade reali, -8.6R, 5/6 anni negativi**.
Non più rumore statistico — un trend negativo reale e ampio.

## Fix applicati Blocco 3 (16/07)

**Bug trovato — stesso tipo di quello già corretto su SAR**: `sig_bjorgum()`
sul motore sito era un proxy EMA ribbon (allineamento 12/26/50,
trend-following) — **completamente diverso** dalla vera
`NXS_Strat_Bjorgum()` in MQL5, che è un rimbalzo su pivot a 30 barre
(mean-reversion agli estremi). Concetti opposti: uno insegue il trend,
l'altro scommette contro gli estremi. Il "PF3.46" che giustificava la
config attuale nel profilo veniva da questo proxy sbagliato — non ha mai
testato la vera strategia. **Corretto** `server/backtest.py::sig_bjorgum`
per implementare davvero il rimbalzo su pivot.

**Ricerca esterna sul vero metodo Bjorgum** (fonti in fondo): il metodo
reale ha 3 pattern distinti — Breakout, False Breakout/Trap, e **Back
Check** (pullback su un livello "flippato": rotto con corpo, poi ritestato
dal lato opposto). Il nostro trigger non implementa nessuno dei 3 con
precisione — è un ibrido senza conferma di rottura/flip.

**Test A/B con la logica corretta**:
| Versione | TF | HTF | Trade | PF | DD% | Net |
|---|---|---|---|---|---|---|
| Sito vecchio (EMA ribbon, bacato) | 4h | ON | 18 | 3.46 | 2.97 | +2.601 |
| MQL5 reale (pivot bounce) | 4h | ON | 6 | 0.88 | 2.97 | -62 |
| MQL5 reale | 4h | **OFF** | 114 | 1.16 | 19.05 | +1.576 |
| + conferma flip/Back Check | 4h | OFF | 32 | **0.95** | 12.24 | -138 |

**La conferma flip/Back Check peggiora** (PF scende su ogni TF testato,
0.66-0.95 contro 0.75-1.16 senza) — ipotesi dalla fonte esterna testata e
**respinta**, non applicata.

**Config candidata applicata al profilo MQL5** (`NXS_StrategyProfiles.mqh`):
SL1.5/TP3.0, **HTF OFF** (invece di SL1.0/TP4.5/HTF ON) — la config con
miglior DD trovata dopo il fix del proxy (PF1.20, DD13.4%, 110 trade/10y
sul sito). **Non ancora validata su MT5** — richiede conferma via test
isolato (`InpStrategySelector=6`), stesso avvertimento già dato per
ADX_RSI/SAR: un miglioramento sul sito è un'ipotesi, non una certezza
([[NEXUS EA - Principi]] #5/#6).

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]] · [[Sar]]
