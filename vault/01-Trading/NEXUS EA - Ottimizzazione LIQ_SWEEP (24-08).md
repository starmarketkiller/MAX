---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, liq-sweep, buy-sell, ottimizzazione-individuale]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Ottimizzazione individuale LIQ_SWEEP (24/08)

## Perché

LIQ_SWEEP era la strategia con la correlazione media più bassa di tutte
(0.084, vedi [[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]])
ma la peggiore nel portafoglio a 20 (crowding-out per bassa frequenza).
Seconda ottimizzazione individuale su richiesta dell'utente. Tre
ingredienti mai provati su LIQ_SWEEP: stop nativo dello sweep,
allineamento D1, split BUY/SELL con diagnosi per-data (non solo
per-conteggio, lezione di oggi). `liq_sweep_optimization_24-08.py`.

## Risultato: BUY-only è una scoperta pulita e ben verificata

| Config | retail aggPF (m1/m2) | finestre >=1 | Verdetto |
|---|---|---|---|
| Baseline simmetrica (nota) | 1.07 (1.03/1.11) | 3/5 | Già confermata due volte |
| Stop nativo dello sweep | 0.90 (0.79/1.02) | 2/5 | **Peggiora** — LIQ_SWEEP non beneficia del proprio stop nativo (a differenza di TURTLE_SOUP ieri) |
| Allineamento D1 (sostituisce ER) | 1.20 (1.01/1.42) | 2/5 | Migliora un po', m1 appena a pareggio |
| **BUY-only (SL1.5/TP6.0)** | **1.73 (1.73/1.73!)** | **5/5** | **La scoperta di questo giro** |

**LIQ_SWEEP BUY-only**: retail PF1.73, le due metà **identiche** (1.73/
1.73), **tutte e 5 le finestre positive** (1.42/1.81/3.75/1.04/1.42),
ECN 1.92 (m1=1.94/m2=1.90). Verificato con le date per evitare l'errore
di ieri sera (equal-count ≠ equal-calendario): la finestra più vecchia
(F0, 2020-11→2024-05, n=17) mostra PF1.42 — **genuinamente positiva
nella parte più vecchia e laterale della storia**, non solo nel rally
recente. Il lato SELL invece è debole e incoerente (F1-F3 crollano a
0.00/0.71/0.15) — non un vero flip di regime come STRUCT_REACT, solo un
lato più debole.

**Sostanzialmente diverso dai rescue BUY-only di ieri sera** (BJORGUM/
FVG_MIT/TSI_EXTREME, tutti rimossi dopo la diagnosi per-data): qui la
finestra vecchia È già forte da sola (1.42, non 0.3-0.9 come negli altri
casi), quindi non è beta mascherato dal rally — è un edge reale che il
lato SELL simmetrico stava diluendo.

## Verdetto

**LIQ_SWEEP promossa da baseline borderline a candidata solida**,
configurazione aggiornata: **BUY-only, SL1.5/TP6.0, 4h, ER+floor**. Da
sostituire alla versione simmetrica/trailing usate finora in ogni
simulazione di portafoglio futura.

## Prossimi passi aperti

- Non ancora provato: BUY-only + allineamento D1 insieme (le due leve
  migliori trovate oggi, mai combinate per questa strategia).
- Non ancora provato: BUY-only + trailing (invece di target fisso).
- Andrebbe riportata nel portafoglio a 20 con la nuova configurazione
  prima della prossima simulazione.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]]
[[NEXUS EA - Diagnosi Onesta del BUY-only (24-08)]]
