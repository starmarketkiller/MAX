---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, fvg-cont-v2, ottimizzazione-individuale]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Ottimizzazione individuale FVG_CONT_V2 (24/08)

## Perché

Decima ottimizzazione individuale — quarto posto nel blocco "altre
solide" (BUY-only PF1.68, n=65), l'unica con stop nativo precalcolato
(`ind['fvg_v2_sl']`/`ind['fvg_v2_tp']`, non un multiplo ATR fisso)
invece del solito 1.5/4.0×ATR.

## Verifica laterale — campione troppo sottile per dire qualsiasi cosa

BUY-only laterale: **n=2**, PF0.0, sumR=-2.3. A differenza delle altre
strategie corrette oggi (n=6-17, comunque sottili ma leggibili), qui il
campione è talmente piccolo da non essere nemmeno indicativo in
direzione — non contarlo né a favore né contro, semplicemente non c'è
segnale sufficiente nella finestra laterale per questa strategia.

## Trailing sullo stop nativo: miglioramento netto e pulito

Lo stop nativo (strutturale, legato alla FVG) resta come **rischio
iniziale**, poi trail con un multiplo ATR che stringe solo se più
favorevole (mai allarga) — stesso meccanismo chandelier usato su
FVG_MIT/Z_SCORE_BREAKOUT/SAR_FLIP.

| Config | retail PF (m1/m2) | finestre | n |
|---|---|---|---|
| BUY-only, target nativo fisso (nota) | 1.68 (1.34/2.15) | 5/5 | 65 |
| **BUY + trailing 2.0×ATR (su stop nativo)** | **2.03 (1.72/2.60)** | **5/5** | 65 |
| BUY + trailing 2.5×ATR | 1.72 (1.91/1.43) | 5/5 | 65 |
| BUY + trailing 3.0×ATR | 2.73 (1.46/4.64) | 3/5 | 65 |

3.0×ATR ha il PF aggregato più alto ma è trainato da poche operazioni
enormi verso fine storico (m2=4.64 contro m1=1.46, e solo 3/5 finestre
positive) — segno di un risultato meno robusto, non promosso.
**2.0×ATR è la scelta migliore**: PF più alto del target fisso, 5/5
finestre come il baseline, e le due metà restano equilibrate (1.72 vs
2.60, non uno sbilanciamento estremo).

## Verdetto

**Adottato trailing 2.0×ATR sullo stop nativo** — miglioramento pulito
(1.68→2.03, stesso campione, stessa robustezza per finestre). Non
ancora in MQL5 (FVG_CONT_V2 non è tra le 2 strategie già portate).

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
