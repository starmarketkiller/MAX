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
🔬 Campione troppo piccolo — confermato sui 10 segmenti: **8 trade totali su
10 anni** (1W/7L), 6 anni a zero. A differenza di IFVG non è mai a zero
strutturale (il pattern accade), ma quando accade **perde quasi sempre**
(1/8 vincenti) — dato ancora troppo scarso per dire se è rumore o un
problema reale, ma il segno negativo è degno di nota per quando arriverà
più campione. Nessun cambio di codice, priorità bassa rispetto al resto
del Blocco 2 (IFVG/FVG_CONT hanno dati più solidi da cui partire).

## Aggiornamento 11/08 — registro di zone attive, promettente su 4h

Il trigger MQL5 (`NXS_Strat_FVG_Mitigation`) confronta il gap tra le
candele i-6/i-4 SOLO con la barra CORRENTE - ogni coppia di candele
viene valutata per gap+mitigazione UNA SOLA VOLTA, esattamente 4-6
barre dopo la formazione. Se il prezzo impiega più tempo a tornare sul
gap, il segnale è perso per sempre - nessun registro persistente (a
differenza di SH_BMS_RTO_V2/OB style). Non un bug di fedeltà (MQL5 fa lo
stesso) - variante sperimentale nuova: zone tracciate fino a 15 barre.

Registrata `FVG_MIT_WINDOW`, testata su 4h (vero TF di profilo) e 1h:

| TF | IS baseline→window | OOS baseline→window | Walk-forward window |
|---|---|---|---|
| 4h | 1.13/107→**1.14/335** | 1.01/78→**1.05/217** | **3/5, range stretto 0.95-1.55** (baseline: 2/5, oscillava 0.39-1.85) |
| 1h | 1.29/278→0.85/834 | 1.02/196→0.98/582 | 1/5, drawdown 58% — **peggiora nettamente** |

**Su 4h (il TF vero di profilo)**: campione quasi triplicato, PF
leggermente migliore su entrambi i lati, e soprattutto molto più
stabile tra finestre (la baseline aveva un crollo a 0.39 in una
finestra, la window version resta sempre in un range ragionevole).
Stesso status di TURTLE_SOUP_CHOCH: promettente, non ancora confermato
al livello di CRT, ma un miglioramento di robustezza reale, non solo di
PF headline.

**Su 1h**: la finestra di 15 barre è troppo lunga in termini relativi
su un TF più basso (15 ore vs 60 ore su 4h) - include mitigazioni di
qualità più bassa, drawdown quasi triplicato. Conferma che il fix è
specifico al TF naturale della strategia, non universale - stesso
pattern già visto con TURTLE_SOUP_CHOCH (funziona su 4h, non su 1h).

**Con questo, entrambi i problemi aperti del nucleo hanno ricevuto un
tentativo serio**: FVG_MIT ha un miglioramento reale trovato (su 4h),
TSI no (variante cross-da-zona-estrema testata, negativa su entrambi i
TF - vedi [[Tsi]]).

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]
