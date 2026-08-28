---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, ote-cont, multi-timeframe, trailing, ottimizzazione-individuale]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Ottimizzazione individuale OTE_CONT (24/08)

## Perché

Terza ottimizzazione individuale. OTE_CONT (diversificatrice genuina,
correlazione media 0.028 - vedi [[NEXUS EA - Correlazione tra le 20
Strategie (24-08)]]), già solida (SL1.0/TP6.0, retail PF1.61,
m1=1.69/m2=1.52) ma con due finestre deboli (F1/F2 = 0.89) e respinta
su D1 (morta pre-2024). `ote_cont_optimization_24-08.py`.

## Risultato: tre miglioramenti reali, il più pulito è l'allineamento D1

| Config | retail aggPF (m1/m2) | finestre | n | Note |
|---|---|---|---|---|
| Baseline (SL1.0/TP6.0) | 1.61 (1.69/1.52) | 3/5 | 129 | F1/F2 deboli (0.89) |
| **Allineamento D1 (sostituisce ER)** | **1.83 (1.89/1.77)** | **5/5** | **242** | **Tutte le finestre positive, campione quasi raddoppiato** |
| Trailing 2.0xATR | 2.00 (2.38/1.66) | 4/5 | 129 | Buono ma F2 debole (0.85) |
| Trailing 3.0xATR | 2.04 (2.79/1.36) | 4/5 | 129 | Aggregato più alto ma più squilibrato (m1»m2) |
| BUY-only | 2.13 (1.87/2.40) | 4/5 | 85 | F3 debole (0.32) - instabile |
| SELL-only | 0.79 (1.05/0.52) | 2/5 | 44 | Debole, F1-F3 quasi a zero - scartata |

**L'allineamento D1 è il miglioramento più pulito**: aggPF sale da 1.61 a
1.83, **tutte e 5 le finestre positive** (contro le 3/5 della baseline),
il campione quasi raddoppia (129→242, il filtro D1 è meno restrittivo
dell'ER su questa strategia) e le due metà sono più bilanciate
(1.89/1.77 contro 1.69/1.52) — stessa firma pulita già vista ieri sera
su FVG_MIT con lo stesso ingrediente. **Secondo caso in due giorni** in
cui l'allineamento D1 batte il filtro ER standard.

Il trailing migliora l'aggregato ma introduce più instabilità tra
finestre; BUY-only migliora ma con una finestra debole (0.32); SELL-only
è chiaramente da scartare.

## Verdetto

**OTE_CONT aggiornata**: config raccomandata **allineamento D1 (non
ER) + SL1.0/TP6.0, 4h** — il miglioramento più robusto e ben
distribuito nel tempo trovato oggi per questa strategia.

## Prossimi passi aperti

- Non ancora provato: allineamento D1 + trailing insieme (le due leve
  migliori trovate qui, mai combinate).
- L'allineamento D1 ha ora funzionato bene 2 volte su 2 tentativi
  (FVG_MIT ieri sera, OTE_CONT oggi) — vale la pena provarlo
  sistematicamente su altre baseline prima di continuare con altri
  ingredienti sparsi.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]]
[[NEXUS EA - Ottimizzazione LIQ_SWEEP (24-08)]]
