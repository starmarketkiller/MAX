---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, malaysian-snr-breakout, ottimizzazione-individuale]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Ottimizzazione individuale MALAYSIAN_SNR_BREAKOUT (24/08)

## Perché

Settima ottimizzazione individuale — la più forte del blocco "altre
solide" (BUY-only PF1.93). `malaysian_snr_breakout_optimization_24-08.py`.

## Verifica laterale (fatta prima di tutto, non rimandata)

BUY-only laterale: n=6, PF0.45, sumR=-3.1 — stessa direzione di
ADX_RSI/SAR/ecc. (SELL relativamente più forte nel laterale) ma
campione troppo sottile per confermare o smentire. Stesso caveat
generale della [[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]] —
non contata come prova, solo coerente in direzione.

## Risultato: nessun miglioramento trovato — la config nota resta la migliore

| Config | retail PF (m1/m2) | finestre |
|---|---|---|
| **BUY-only, target fisso 1.5/4.0 (nota)** | **1.93 (1.83/2.04, 5/5)** | migliore |
| BUY + trailing 2.0×ATR | 1.88 (1.45/2.29) | 4/5 |
| BUY + trailing 2.5×ATR | 1.61 (1.58/1.63) | 4/5 |
| BUY + trailing 3.0×ATR | 1.88 (1.38/2.35) | 5/5 |
| D1-align (simmetrica) | 1.17 (0.67/1.87) | 2/5 |

Il trailing si avvicina ma non supera mai il target fisso, e introduce
più squilibrio tra le metà. L'allineamento D1 peggiora nettamente
(stessa firma già vista su strategie già forti con ER — vedi
[[NEXUS EA - Sweep Sistematico Allineamento D1 (24-08)]]: non aiuta chi
è già ben filtrato).

## Verdetto

**Nessun cambiamento** — MALAYSIAN_SNR_BREAKOUT resta con la
configurazione già nota (BUY-only, target fisso 1.5/4.0). Risultato
onesto: non ogni strategia ha margine di miglioramento con gli
ingredienti di oggi, e va detto chiaramente invece di forzare un
cambiamento marginale o peggiorativo.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
