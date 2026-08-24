---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, amd-cont, ottimizzazione-individuale]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Ottimizzazione individuale AMD_CONT (24/08)

## Perché

Undicesima ottimizzazione individuale — completa il blocco "altre
solide" (BUY-only PF1.62, n=137, m1=1.26/m2=2.06, 4/5 finestre), mai
verificata sulla finestra laterale né spinta con trailing o D1-align.

## Verifica laterale (fatta prima di tutto, non rimandata)

BUY-only laterale: n=14, PF0.37, sumR=-8.5 — stessa direzione già
vista su tutto il blocco (TSI, MALAYSIAN_SNR_BREAKOUT, SAR_FLIP): SELL
relativamente più forte nel laterale, campione leggibile ma non
sufficiente per una conferma definitiva. Stesso caveat generale della
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]].

## Risultato: nessun miglioramento trovato — il target fisso resta il migliore

| Config | retail PF (m1/m2) | finestre | n |
|---|---|---|---|
| **BUY-only, target fisso 1.5/4.0 (nota)** | **1.62 (1.26/2.06)** | 4/5 | 137 |
| BUY + trailing 2.0×ATR | 1.56 (1.05/2.14) | 4/5 | 137 |
| BUY + trailing 2.5×ATR | 1.51 (1.05/2.08) | 4/5 | 137 |
| BUY + trailing 3.0×ATR | 1.44 (0.87/2.11) | 4/5 | 137 |
| D1-align (simmetrica) | 1.46 (1.15/1.85) | 4/5 | 253 |

Il trailing peggiora sempre e in modo monotono con il multiplo (più
largo = peggio), e sbilancia ulteriormente m1 verso il basso.
L'allineamento D1 conferma la firma già vista più volte oggi (SAR,
MACD, FVG_CONT, MALAYSIAN_SNR_BREAKOUT): non aiuta chi è già ben
filtrato con ER — qui anzi peggiora nonostante il campione quasi
raddoppiato.

## Verdetto

**Nessun cambiamento** — AMD_CONT resta con la configurazione già nota
(BUY-only, target fisso 1.5/4.0×ATR). Chiude il blocco "altre solide":
su 4 strategie testate individualmente oggi (TSI, MALAYSIAN_SNR_BREAKOUT,
SAR_FLIP, FVG_CONT_V2, AMD_CONT — 5 in realtà), solo 2 hanno trovato un
miglioramento reale (SAR_FLIP, FVG_CONT_V2, entrambe via trailing) — il
trailing non è un ingrediente universale nemmeno dentro lo stesso
blocco, va verificato per-strategia come tutto il resto.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]
[[NEXUS EA - Sweep Sistematico Allineamento D1 (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
