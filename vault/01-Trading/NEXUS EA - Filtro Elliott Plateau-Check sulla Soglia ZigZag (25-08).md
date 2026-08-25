---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, elliott-wave, plateau-check, robustezza]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — Plateau-check sulla soglia ZigZag del filtro Elliott (25/08)

## Perché

Il filtro Elliott multi-timeframe (4h+D1) è stato validato finora con
un solo valore di soglia ZigZag (dev_mult=2.0 su entrambi i
timeframe) — mai sottoposto al plateau-check che ha già salvato Hull
Suite/ML Adaptive SuperTrend da un possibile overfitting nascosto.
Prima di considerare 2.0/2.0 la scelta definitiva, verificare che non
sia una cella isolata fortunata.

## Griglia 4×4 (dev_4h × dev_D1) su ADX_RSI e SAR

| | D1=1.5 | D1=2.0 | D1=2.5 | D1=3.0 |
|---|---|---|---|---|
| **ADX_RSI** 4h=1.5 | 1.91 | 1.93 | 2.01 | 1.98 |
| 4h=2.0 | 1.99 | **2.04** | 2.06 | 2.07 |
| 4h=2.5 | 1.84 | 1.86 | 1.94 | 1.90 |
| 4h=3.0 | 1.86 | 1.88 | 1.96 | 1.92 |

| | D1=1.5 | D1=2.0 | D1=2.5 | D1=3.0 |
|---|---|---|---|---|
| **SAR** 4h=1.5 | 1.63 | 1.65 | 1.64 | 1.63 |
| 4h=2.0 | 1.62 | **1.65** | 1.64 | 1.62 |
| 4h=3.0 | 1.58 | 1.58 | 1.58 | 1.57 |

(riga 4h=2.5 di SAR omessa per brevità, valori 1.55-1.57, stesso
pattern)

## Risultato: plateau genuino, non un picco isolato

Su **entrambe** le strategie, ogni singola cella della griglia (16
combinazioni) batte nettamente il baseline senza filtro (ADX_RSI 1.77,
SAR 1.51) — il range è 1.84-2.07 per ADX_RSI e 1.55-1.65 per SAR, **mai
sotto il baseline in nessuna cella**, sempre 5/5 finestre. La scelta
2.0/2.0 usata in tutti i test di oggi è ben dentro la zona stabile (per
ADX_RSI addirittura non è il massimo assoluto — 4h=2.0/D1=3.0 dà 2.07 —
ma la differenza è marginale e 2.0/2.0 resta nella parte alta del
plateau; per SAR 2.0/2.0 è letteralmente la cella migliore).

**Pattern di forma della griglia**: per ADX_RSI, dev_4h=2.0 è
sistematicamente meglio di 2.5/3.0 (troppo largo, pivot troppo radi,
meno segnali di esaurimento rilevati) e leggermente meglio di 1.5
(troppo stretto, più rumore). Per SAR, dev_4h=1.5-2.0 è la zona
migliore, 2.5-3.0 leggermente più debole ma mai sotto baseline. In
entrambi i casi la sensibilità a dev_D1 è più bassa della sensibilità
a dev_4h — il timeframe di ingresso conta di più per la calibrazione
fine, il D1 fa il suo lavoro di conferma di grado superiore in modo
più robusto a prescindere dal valore esatto.

## Verdetto

**dev_mult=2.0/2.0 confermato come scelta valida**, non fortunata —
resta il parametro di riferimento per tutti i test già fatti oggi
(20+ strategie, combinazione con trailing). Nessuna necessità di
rifare i test con un altro valore: il plateau garantisce che il
risultato non dipenda da una scelta di soglia particolare.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Filtro Elliott Wave Multi-Timeframe, il nuovo ingrediente universale (25-08)]]
[[NEXUS EA - Combinazione Trailing + Filtro Elliott, gli effetti si sommano (25-08)]]
