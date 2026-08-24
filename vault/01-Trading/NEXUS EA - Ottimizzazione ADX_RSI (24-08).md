---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, adx-rsi, ottimizzazione-individuale]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — Ottimizzazione individuale ADX_RSI (24-25/08)

## Perché

Sedicesima ottimizzazione — prima del cluster trend-following, la
strategia più solida del gruppo (BUY-only PF1.77, n=728, verificata
per-data in precedenza). Mai spinta con trailing.

## Verifica laterale — già fatta, il flip più netto di tutto il batch

Fa parte del batch originale di 6 corrette in
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]:
BUY laterale PF**0.23** (n=63), SELL laterale PF**2.53** (n=70) — il
flip più drammatico di tutta la giornata. Nessun nuovo test necessario
qui.

## Trailing: il miglioramento più pulito del cluster finora

| Config | retail PF (m1/m2) | finestre | n |
|---|---|---|---|
| BUY-only, target fisso 1.5/4.0 (nota) | 1.77 (1.92/1.63) | 5/5 | 728 |
| BUY + trailing 2.0×ATR | 2.08 (1.93/2.21) | 5/5 | 728 |
| **BUY + trailing 2.5×ATR** | **2.20 (2.20/2.21)** | **5/5** | 728 |
| BUY + trailing 3.0×ATR | 2.18 (1.96/2.38) | 5/5 | 728 |

2.5×ATR è la scelta più netta vista oggi: PF più alto (1.77→2.20,
+24%), 5/5 finestre come il baseline, e le due metà della storia
praticamente identiche (2.20 vs 2.21) — nessun compromesso da
segnalare, a differenza di FVG_CONT/LONDON_BO.

## Verdetto

**Adottato trailing 2.5×ATR** — miglioramento netto e senza
controindicazioni, sul secondo campione più grande testato oggi
(n=728). Non ancora in MQL5.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
