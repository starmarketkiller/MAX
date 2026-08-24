---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, tsi, ottimizzazione-individuale]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Ottimizzazione individuale TSI (24/08)

## Perché

Ottava ottimizzazione individuale — la più forte del blocco "altre
solide" per PF (BUY-only 2.03, n=134). Non ancora spinta con trailing
né verificata sulla finestra laterale prima d'ora.

## Verifica laterale (fatta prima di tutto, non rimandata)

BUY-only laterale: n=13, PF0.39, sumR=-8.9 — stessa direzione già
vista su ADX_RSI/SAR/DONCHIAN_TURTLE/LIQ_SWEEP e coerente col risultato
di MALAYSIAN_SNR_BREAKOUT (n=6, PF0.45) nell'ottimizzazione precedente:
SELL relativamente più forte nel laterale, ma campione troppo sottile
per confermare o smentire in modo definitivo. Stesso caveat generale
della [[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]] —
non contata come prova contro la strategia, solo coerente in direzione
con l'ipotesi "beta di rally, non edge di segnale puro".

## Trailing: nessun miglioramento — il target fisso resta il migliore

| Config | retail PF (m1/m2) | finestre | n |
|---|---|---|---|
| **BUY-only, target fisso 1.0/6.0 (nota)** | **2.03 (1.97/2.10)** | migliore | 134 |
| BUY + trailing 2.0×ATR | 1.91 (1.97/1.85) | 4/5 | 136 |
| BUY + trailing 2.5×ATR | 1.87 (1.92/1.82) | 4/5 | 136 |
| BUY + trailing 3.0×ATR | 1.58 (1.59/1.57) | 3/5 | 136 |

Tutte le varianti trailing peggiorano rispetto al target fisso 6.0×ATR
già in uso — coerente col fatto che TSI ha già un RR ampio (1:6) dove
un target fisso lontano cattura meglio le code favorevoli di quanto
faccia un trailing che le taglia prima.

## Verdetto

**Nessun cambiamento** — TSI resta con la configurazione già nota
(BUY-only, 4h, SL 1.0×ATR / TP 6.0×ATR fisso, ER+floor 0.3). Stesso
risultato onesto della scorsa ottimizzazione (MALAYSIAN_SNR_BREAKOUT):
non ogni strategia ha margine con gli ingredienti di oggi.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
