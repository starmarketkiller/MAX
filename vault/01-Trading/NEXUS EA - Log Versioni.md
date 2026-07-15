---
type: log
domain: trading
status: active
tags: [trading, nexus-ea, changelog]
created: 2026-07-12
updated: 2026-07-15
---

# NEXUS EA — log versioni

Cronologia sintetica delle build lavorate, con il numero che conta per ciascuna.
Fonte: messaggi di commit git + risultati backtest in `results/reports/`.

| Versione | Cosa cambia | Risultato chiave |
|---|---|---|
| v2.3.7 | Setup Matrix per-TF (fix starvation CISD) | net +237 (giù da v2.3.6, interazioni) |
| v2.3.8 | Riporta ADX_RSI + EMA_PULLBACK alla logica del sito | net +387, PF 1.11 — **primo salto reale** |
| v2.3.9 | Riporta TSI + FVG_CONT + ORDER_BLOCK | net +483, PF 1.12 (ma le 3 nuove restano <PF 1.0) |
| v2.4.0 | Sizing prevedibile (spegne anti-bleed/streak), rischio riallocato sui vincenti reali | net +356 (giù — troppe modifiche insieme, non isolate) |
| v2.4.1 | Hedge: corsie indipendenti + gate margine | (bundle con v2.4.0, non isolato) |
| v2.4.2 | Reaction/structure engine collegata a FVG_CONT/ORDER_BLOCK | net +356, DD 24.5% (SMC migliorano ma non profittevoli) |
| v2.4.3 | Torna alla meccanica campione v2.3.9 + tiene solo il reaction gate (isolamento pulito) | — |
| **v2.4.4** | Trailing "lascia correre" globale (1.5→2.5 ATR) | net +480 ma **DD 44.6%** — trail globale danneggia le mean-reversion |
| **v2.4.5** | Trailing **per-strategia** (trend larghi 2.5, mean-rev stretti 1.5) | **net +1005, Sharpe 3.17, DD 31.7%** — record |
| v2.4.6 | Attivazione trailing per-strategia (tentativo fix ICHIMOKU) | net +898 — regressione, scartata |
| v2.4.7 | Ripristina config campione v2.4.5 | torna a +1005 |
| v2.4.8 | Hedge ON (corsie 4 + gate margine) + ritira TSI/ICHIMOKU (0 trade confermati) | **net +1050, Sharpe 3.19, DD 29.6% — record assoluto sui 3 mesi** |
| ⚠️ | **Test di 3 ANNI su v2.4.8** | **net −863, DD 87% — overfitting confermato.** Vedi [[NEXUS EA - Lezione Overfitting 3Y]] |
| v2.5.0 | Screening 10y sul motore sito → filtro HTF universale applicato a ADX_RSI/EMA_PULLBACK/MACD/SAR/OB_MIT, riabilita TSI+BREAKOUT_ACC | Backtest 10Y segmentato (2016-2026): trade sani da 2019 in poi (500-1500/anno), ma **2016-2019 quasi senza trade** (17/3/59) — causa non confermata, in verifica. Vedi [[NEXUS EA - Backtest 10Y Segmentato (v2.5.0)]] |

## Pattern ricorrente osservato
1. Ogni volta che si isola UNA modifica alla volta, si legge il segnale pulito.
   Quando si impacchettano 2-3 modifiche insieme (v2.4.0/2.4.1/2.4.2), il segnale si
   confonde e si rischia di scartare una buona idea per colpa di un'altra cattiva.
2. Il trailing **globale** è sempre stato un compromesso peggiore del trailing
   **per-strategia** — trend e mean-reversion hanno bisogni opposti (correre vs
   incassare presto).
3. Il salto di v2.4.5 (+1005, da +483) è arrivato da UNA idea semplice (trailing
   su misura), non da un accumulo di piccoli tweak.

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Backtest 10Y Segmentato (v2.5.0)]]
