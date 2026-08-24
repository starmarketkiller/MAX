---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, sar-flip, ottimizzazione-individuale]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Ottimizzazione individuale SAR_FLIP (24/08)

## Perché

Nona ottimizzazione individuale — terzo posto per PF nel blocco "altre
solide" (BUY-only 1.78, n=76), non ancora verificata sulla finestra
laterale né spinta con trailing.

## Verifica laterale (fatta prima di tutto, non rimandata)

BUY-only laterale: n=8, PF0.31, sumR=-5.5 — stessa direzione già vista
su TSI/MALAYSIAN_SNR_BREAKOUT/ADX_RSI/SAR/ecc., campione troppo sottile
per confermare o smentire. Stesso caveat generale della
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]].

## Trailing: miglioramento modesto e più bilanciato tra le metà

| Config | retail PF (m1/m2) | finestre | n |
|---|---|---|---|
| BUY-only, target fisso 1.5/4.0 (nota) | 1.78 (1.40/2.27) | 4/5 | 76 |
| **BUY + trailing 2.0×ATR** | **1.82 (1.64/2.02)** | 4/5 | 76 |
| BUY + trailing 2.5×ATR | 1.73 (1.54/1.96) | 4/5 | 76 |
| BUY + trailing 3.0×ATR | 1.79 (1.31/2.35) | 4/5 | 76 |

Trailing 2.0×ATR migliora leggermente il PF aggregato (1.78→1.82) e —
più importante — **riequilibra le due metà della storia** (m1 1.40→1.64,
più vicino a m2) rispetto al target fisso, che dipendeva più
pesantemente dalla seconda metà. Stesso campione (n=76, nessuna
selezione aggiuntiva). 2.5×ATR e 3.0×ATR non migliorano ulteriormente.

## Verdetto

**Adottato trailing 2.0×ATR** al posto del target fisso 4.0×ATR —
miglioramento modesto ma reale, con distribuzione più stabile nel
tempo. Non ancora in MQL5 (SAR_FLIP non è tra le 2 strategie già
portate).

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
