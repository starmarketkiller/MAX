---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, ema-pullback, trailing, ottimizzazione-individuale]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Ottimizzazione individuale EMA_PULLBACK (24/08)

## Perché

Tensione irrisolta: versione D1 (PF2.53, m1=2.88/m2=2.23) ma solo 32
trade — troppo pochi per grande fiducia; versione 4h+D1-align (PF1.42,
n=241) più solida numericamente ma meno spettacolare. Quarta
ottimizzazione individuale. `ema_pullback_optimization_24-08.py`.

## Risultato: due miglioramenti distinti, non un compromesso — entrambi i lati migliorano

**D1 — allargare il campione togliendo il floor** (mai provato, il
floor ATR era stato applicato per abitudine, non verificato su questa
strategia specifica): campione cresce da 32 a 39 trade **E il PF
migliora invece di peggiorare** (2.41→2.57, finestre 4/5→5/5). Il floor
ATR, che aiuta altre strategie, qui era leggermente controproducente.

| Floor | n | retail PF (m1/m2) | finestre |
|---|---|---|---|
| 0.2 (config nota) | 33 | 2.41 (2.22/2.59) | 4/5 |
| 0.1 | 35 | 2.46 (2.01/2.96) | 3/5 |
| **0.0 / nessuno** | **39** | **2.57 (1.69/3.70)** | **5/5** |

**4h+D1-align — trailing invece di target fisso** (mai provato su
questa strategia): stesso campione ampio (241 trade, l'ingresso non
cambia), ma il PF sale sostanzialmente con il trailing:

| Config | retail PF (m1/m2) | finestre |
|---|---|---|---|
| Target fisso (nota) | 1.42 (1.15/1.74) | 4/5 |
| Trailing 2.0×ATR | 1.56 (1.19/1.90) | 5/5 |
| Trailing 2.5×ATR | 1.66 (1.04/2.26) | 4/5 |
| **Trailing 3.0×ATR** | **1.87 (1.26/2.49)** | 4/5 |

## Verdetto

**Due configurazioni complementari, non alternative**: 4h+D1-align+
trailing 3.0×ATR (PF1.87, campione ampio 241 — la config PRINCIPALE,
più affidabile statisticamente) e D1 nativo senza floor (PF2.57,
campione più piccolo 39 ma tutte le finestre positive — conferma/upside
di ordine superiore). Entrambe aggiornate nella tabella master.

## Prossimi passi aperti

- Non ancora provato: D1-senza-floor + trailing insieme (le due leve
  migliori trovate qui, mai combinate).
- Il floor ATR non aiuta sempre — terzo caso oggi (dopo l'allineamento
  D1) di un ingrediente che va verificato per strategia, non applicato
  come default.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
