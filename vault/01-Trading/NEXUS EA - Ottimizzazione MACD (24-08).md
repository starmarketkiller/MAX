---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, macd, ottimizzazione-individuale]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Ottimizzazione individuale MACD (24/08)

## Perché

Tredicesima ottimizzazione — nucleo storico. MACD è l'unica strategia
del nucleo rimasta **simmetrica** (BUY-only dava solo +0.12, non
valeva la pena passare — vedi [[NEXUS EA - Sweep Sistematico BUY-SELL (24-08)]]),
quindi non ha bisogno della verifica laterale anti-beta (nessuna
selezione direzionale in gioco). Mai spinta con trailing.

## Trailing: miglioramento netto, pulito, simmetrico

| Config | retail PF (m1/m2) | finestre | n |
|---|---|---|---|
| Simmetrica, target fisso 1.5/4.0 (nota) | 1.46 (1.39/1.54) | 5/5 | 1498 |
| **Simmetrica + trailing 2.0×ATR** | **1.72 (1.43/2.04)** | 5/5 | 1498 |
| Simmetrica + trailing 2.5×ATR | 1.61 (1.44/1.79) | 5/5 | 1498 |
| Simmetrica + trailing 3.0×ATR | 1.56 (1.25/1.88) | 5/5 | 1498 |

Miglioramento tra i più netti della giornata (1.46→1.72, +18%) su un
campione grande (n=1498) e completamente simmetrico — nessun rischio
di beta di rally nascosto, vale per entrambe le direzioni su tutto lo
storico. 5/5 finestre in entrambi i casi.

## Verdetto

**Adottato trailing 2.0×ATR** al posto del target fisso 4.0×ATR. Non
ancora in MQL5 (MACD non è tra le 2 strategie già portate).

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
