---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: OB_MIT
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: OB_MIT

## Tipo
SMC/order block

## Trigger meccanico
Stessa logica di ORDER_BLOCK (mitigazione strutturale), floor di score 68.

## Configurazione attuale (v2.5.0)
- **Timeframe**: D1
- **SL**: 1.5× ATR · **TP**: 4.0× ATR
- **Filtro HTF**: False
- **Trailing**: largo (corre)
- **Rischio per trade**: 0.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, CONFIG PRECEDENTE (diversa da quella sopra))
- **3 mesi**: 633 setup, 3W/4L/1BE, WR 42.9%, expR +0.032, **PF 1.37**
- **3 anni**: 220 setup, 5W/10L/1BE, WR 33.3%, expR -0.179, **PF 0.20**

## Risultati (backtest 10y segmentato v2.5.0, 5 anni affidabili 2019-2023)
108 trade totali. R per anno: 2019 -0.5 · 2020 -1.7 · 2021 +1.1 · 2022 -0.1 ·
2023 **-3.3**. **Somma -4.5R — 1 anno su 5 positivo**. Dettaglio:
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]].

## Stato
⏳ PENDING — continua a fallire come già sotto v2.4.8. Confermato sui 10
segmenti: **166 trade totali**, il campione più grande dopo FVG_CONT nel
Blocco 2. Solo 2 anni buoni (2021 FORTE, 2024 OK), 4 anni CRITICA.

## Fix reale 16/07: eredita il fix struttura esterna di ORDER_BLOCK
Wrapper di `NXS_Strat_OrderBlock` (floor score 68) — eredita automaticamente
il fix struttura esterna applicato lì (`g_structH1`, vedi [[Order Block]]
e [[NEXUS EA - Struttura Interna vs Esterna — Framework]]). Testata anche
la propria variante sito (`sig_ob_mit_ext`, con lo stesso BOS interno a 5
barre + trend esterno): config reale D1, **PF 1.71→1.80, DD 7.15%→3.94%**;
su 4h il salto è più netto (PF 1.22→1.98, DD quasi dimezzato). **Non
ancora validata su MT5 reale.**

Resta candidato Tier 1 per il framework Setup Buy-Sell insieme a
ORDER_BLOCK/FVG_CONT/FVG_MIT/IFVG (le "5 tipologie di Engulfing" di
Secret of 4.11) per un refactor più profondo in futuro.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[Order Block]] · [[NEXUS EA - Fonte Secret of 4111 (Ali Yusoff)]]
