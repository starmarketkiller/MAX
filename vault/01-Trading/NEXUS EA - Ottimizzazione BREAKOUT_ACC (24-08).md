---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, breakout-acc, ottimizzazione-individuale]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — Ottimizzazione individuale BREAKOUT_ACC (24-25/08)

## Perché

Diciottesima ottimizzazione — cluster trend-following, il
miglioramento più modesto del cluster (BUY-only PF1.33, n=274). Mai
verificata sulla laterale né spinta con trailing.

## Verifica laterale

BUY-only laterale: n=18, PF0.64, sumR=-5.7 — stessa direzione delle
altre, campione leggibile ma non conclusivo da solo.

## Trailing: nessun miglioramento reale — la robustezza peggiora sempre

| Config | retail PF (m1/m2) | finestre | n |
|---|---|---|---|
| **BUY-only, target fisso 1.5/4.0 (nota)** | **1.33 (1.19/1.48)** | **4/5** | 274 |
| BUY + trailing 2.0×ATR | 1.42 (1.08/1.80) | 3/5 | 274 |
| BUY + trailing 2.5×ATR | 1.20 (0.94/1.48) | 2/5 | 274 |
| BUY + trailing 3.0×ATR | 1.33 (0.82/1.86) | 4/5 | 274 |

Nessuna variante trailing eguaglia la robustezza del target fisso: pur
avendo qualche PF aggregato più alto (2.0×ATR: 1.42), le finestre
peggiorano sempre (3/5, 2/5) o restano uguali con una prima metà più
debole (3.0×ATR: m1 0.82). Il target fisso resta la scelta più solida.

## Verdetto

**Nessun cambiamento** — BREAKOUT_ACC resta con la configurazione già
nota (BUY-only, target fisso 1.5/4.0×ATR). Terzo "nessun miglioramento"
della giornata dopo TSI e MALAYSIAN_SNR_BREAKOUT/AMD_CONT — conferma
che il trailing non è un ingrediente universale, va sempre verificato.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
