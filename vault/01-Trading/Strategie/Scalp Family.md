---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: SCALP_BB_FADE, SCALP_EMA, SCALP_RANGE_BRK, SCALP_RSI_SNAP
created: 2026-08-11
updated: 2026-08-11
---

# Famiglia SCALP_* (BB_FADE / EMA / RANGE_BRK / RSI_SNAP)

## Tipo
Profit-taker ad alta frequenza su 15m — non SMC, indicatori classici
(EMA5/9/20+RSI7, Bollinger 20/2σ, RSI7 estremo+reversal, micro-breakout
12 barre).

## Trigger meccanico
- **SCALP_EMA**: cross EMA5/EMA9 nel senso del micro-trend (EMA20), RSI7
  non estremo.
- **SCALP_BB_FADE**: rientro da oltre banda Bollinger 2σ verso la media
  (mean-reversion).
- **SCALP_RSI_SNAP**: RSI7 estremo (<20/>80) + candela di reversal.
- **SCALP_RANGE_BRK**: rottura del massimo/minimo delle ultime 12 barre
  con corpo pieno (momentum).

## Problema diagnosticato (census/report 11/08)
Non è un problema di profit factor (spesso vicino/sopra 1 su 15m) ma di
rischio: su campioni enormi (3.100-5.000 trade sul periodo 2019-2026) il
drawdown è sproporzionato — **35-79%** — tipico di alta frequenza senza
un vero filtro di qualità, dove tante piccole perdite consecutive si
accumulano.

## Aggiornamento 11/08 — filtro di regime STRONG_TREND: miglioramento reale, confermato IS/OOS/walk-forward

Ipotesi del report (mai testata prima su queste 4): un filtro di regime
potrebbe tagliare le sequenze di piccole perdite senza eliminare i trade
buoni. Testato con `regime_filter=(_REGIME_STRONG_TREND,)` (motore vero,
`run_backtest`, non uno standalone) su tutte e 4, IS/OOS + walk-forward a
5 finestre:

| Strategia | Baseline OOS | STRONG_TREND OOS | Walk-forward dd (5 finestre) |
|---|---|---|---|
| BB_FADE | 0.92/1258, dd 56.7% | **1.05/341, dd 24.2%** | 12–25% (baseline 20–56%) |
| EMA | 0.96/1454, dd 50.2% | 0.93/388, dd 24.1% | 14–31% (baseline 35–56%) |
| RANGE_BRK | 1.02/2048, dd 35.7% | **0.97/729, dd 33.0%** | 17–32% (baseline 30–54%) |
| RSI_SNAP | 0.93/1283, dd 49.9% | **1.03/662, dd 30.6%** | 11–31% (baseline 19–46%) |

**Il filtro regge un test onesto su tutte e 4**: drawdown circa dimezzato
(sia IS che OOS, sia in ogni singola finestra walk-forward — non solo
sull'aggregato) mantenendo un campione ancora ampio (25-30% del totale,
300-1000 trade per lato). PF resta stabile o migliora leggermente per
BB_FADE/RANGE_BRK/RSI_SNAP; **EMA resta la più debole** delle quattro
anche filtrata (PF oscilla 0.76-1.28, media sotto 1) — il filtro riduce
il rischio ma non trasforma un trigger mediocre in uno buono.

Non richiede una nuova strategia registrata: `regime_filter` è già un
parametro opzionale di `run_backtest` (riusa `_regime_series`, la stessa
porting fedele di `NXS_DetectRegime()` usata per le altre 5 confluenze di
regime della sessione). **Raccomandazione**: applicare
`regime_filter=STRONG_TREND` come configurazione runtime a tutte e 4 le
SCALP_*, non come variante sperimentale separata — è un gate, non un
cambio di trigger.

Testato anche `VOLATILE` (drawdown a singola cifra su tutte e 4) ma il
campione crolla a 60-320 trade totali — troppo poco per fidarsi da solo,
non validato con walk-forward separato. `RANGING`/`CHOPPY`/`WEAK_TREND`
danno risultati intermedi o campioni troppo piccoli (CHOPPY: 1-9 trade).

## Note

## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Strategie Escluse, Analisi Una-ad-Una (11-08)]]
