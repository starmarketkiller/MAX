---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, london-bo, ottimizzazione-individuale]
created: 2026-08-24
updated: 2026-08-25
---

# NEXUS EA — Ottimizzazione individuale LONDON_BO (24/08)

## Perché

Quindicesima ottimizzazione — chiude il nucleo storico. LONDON_BO è
l'unica del nucleo con filtro ER senza floor ATR (SL/TP 1.0/4.5). Mai
verificata sulla finestra laterale né spinta con trailing.

## Verifica laterale

BUY-only laterale: n=8, PF0.0, sumR=-9.7 (nessun trade vincente in
quella finestra) — stessa direzione delle altre strategie del batch
corretto, campione sottile. Stesso caveat generale della
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]].

Nota: il ricalcolo di baseline oggi dà PF1.69 (1.58/1.80, n=70, 4/5)
contro il PF1.60 (1.71/1.49) registrato nella tabella master — stessa
piccola deriva tra script indipendenti già documentata per FVG_MIT,
non riconciliata, i numeri di questa nota sono interni e coerenti tra
loro.

## Trailing: miglioramento reale, sia PF che robustezza delle finestre

| Config | retail PF (m1/m2) | finestre | n |
|---|---|---|---|
| BUY-only, target fisso 1.0/4.5 (ricalcolo oggi) | 1.69 (1.58/1.80) | 4/5 | 70 |
| **BUY + trailing 2.0×ATR** | **1.83 (1.38/2.32)** | **5/5** | 70 |
| BUY + trailing 2.5×ATR | 2.18 (1.37/3.09) | 3/5 | 70 |
| BUY + trailing 3.0×ATR | 1.71 (1.03/2.46) | 3/5 | 70 |

2.5×ATR ha il PF aggregato più alto ma solo 3/5 finestre positive
(peggio del baseline) — scartato per lo stesso motivo di FVG_CONT_V2 e
MALAYSIAN_SNR_BREAKOUT oggi: PF alto ma meno robusto. **2.0×ATR è la
scelta migliore**: PF più alto del target fisso E finestre più solide
(5/5 contro 4/5).

## Verdetto

**Adottato trailing 2.0×ATR** — miglioramento su entrambi gli assi
(PF e robustezza). Non ancora in MQL5.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
