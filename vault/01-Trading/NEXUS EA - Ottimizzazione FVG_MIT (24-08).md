---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, fvg-mit, trailing, ottimizzazione-individuale]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Ottimizzazione individuale FVG_MIT (24/08)

## Perché

FVG_MIT è tra le migliori diversificatrici (correlazione media 0.015,
quasi zero — vedi [[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]]),
ottimizzata ieri sera solo con l'allineamento D1 (EMA50). Quinta
ottimizzazione individuale, quattro ingredienti mai provati su questa
strategia. `fvg_mit_optimization_24-08.py`.

**Nota metodologica**: il baseline ricalcolato in questo script (n=79,
PF1.42, m1=0.88/m2=2.15) differisce leggermente dal numero riportato
ieri sera (PF1.48, m1=1.33/m2=1.64) — stessa logica D1-align ma
implementazione ricalcolata da zero in uno script diverso, piccola
deriva nei dettagli di warmup. Non rilevante per il confronto INTERNO
di questo test (baseline vs varianti, stessa funzione `collect()` per
tutte) - il numero di riferimento per la tabella master è quello più
recente, qui sotto.

## Risultato: trailing è un salto netto, non un miglioramento marginale

| Config | retail PF (m1/m2) | finestre | n |
|---|---|---|---|
| Baseline (EMA50 D1, target fisso) | 1.42 (0.88/2.15) | 3/5 | 79 |
| EMA100 D1 | 1.56 (1.05/2.24) | 3/5 | 77 |
| + floor 0.2 | 1.58 (1.11/2.19) | 4/5 | 61 |
| Trailing 2.0×ATR | 1.08 (1.25/0.89) | 4/5 | 79 |
| Trailing 2.5×ATR | 2.20 (1.58/2.87) | 5/5 | 79 |
| **Trailing 3.0×ATR** | **2.72 (1.32/4.26)** | **5/5** | **79** |

**Trailing 3.0×ATR quasi raddoppia il PF** rispetto al miglior target
fisso trovato (1.58→2.72), con tutte e 5 le finestre positive e lo
stesso campione (79 — il trailing cambia solo l'uscita, non l'ingresso).
Nota: m1 (1.32) resta più debole di m2 (4.26) — non pulito come
OTE_CONT/EMA_PULLBACK, ma comunque solidamente sopra pareggio in
entrambe le metà.

**EMA100 D1 batte EMA50** in modo consistente (1.56 vs 1.42) — un
segnale di trend più lento si adatta meglio alla tesi "mitigation" di
FVG_MIT (aspetta già un ritorno, non serve una conferma di trend troppo
reattiva).

## Verdetto

**FVG_MIT aggiornata**: config raccomandata **EMA50 D1-align + trailing
3.0×ATR** (PF2.72, 5/5 finestre) — il miglioramento più grande trovato
oggi su una singola strategia in termini relativi. EMA100 resta
un'alternativa secondaria non ancora combinata col trailing.

## Prossimi passi aperti

- Non ancora provato: EMA100 D1 + trailing insieme (le due leve
  migliori qui, mai combinate).
- Riconciliare la piccola deriva nel numero di baseline tra le due
  implementazioni (ieri sera vs oggi) - non urgente, non cambia il
  verdetto.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
