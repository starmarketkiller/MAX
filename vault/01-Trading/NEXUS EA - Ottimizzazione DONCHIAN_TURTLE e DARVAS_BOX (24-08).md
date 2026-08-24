---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, donchian-turtle, darvas-box, ottimizzazione-individuale]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — Ottimizzazione individuale DONCHIAN_TURTLE e DARVAS_BOX (24-25/08)

## Perché

Diciannovesima/ventesima ottimizzazione — chiudono il cluster
trend-following. Le due strategie sono **correlate al 99.7%** (vedi
[[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]]) — praticamente
lo stesso segnale, quindi testate insieme invece di duplicare il
lavoro.

## Verifica laterale

DONCHIAN_TURTLE fa parte del batch originale di 6 corrette in
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]:
BUY laterale PF0.59 (n=24), SELL laterale PF1.90 (n=11) — stessa
direzione delle altre. Non riverificata separatamente per DARVAS_BOX
data la correlazione 99.7% già nota — assumere lo stesso pattern è
ragionevole qui, a differenza di strategie non correlate.

## Trailing: nessun miglioramento su entrambe — pattern identico

| Config | DONCHIAN_TURTLE PF (m1/m2, finestre) | DARVAS_BOX PF (m1/m2, finestre) |
|---|---|---|
| **Target fisso 1.5/4.0 (nota)** | **1.56 (1.47/1.67), 5/5** | **1.58 (1.44/1.73), 5/5** |
| Trailing 2.0×ATR | 1.56 (1.28/1.86), 2/5 | 1.58 (1.27/1.91), 3/5 |
| Trailing 2.5×ATR | 1.40 (1.18/1.64), 2/5 | 1.42 (1.16/1.70), 2/5 |
| Trailing 3.0×ATR | 1.52 (0.96/2.11), 3/5 | 1.53 (0.95/2.17), 4/5 |

Conferma diretta della correlazione 99.7%: i numeri sono quasi
identici su entrambe. In tutti i casi il trailing **collassa la
robustezza delle finestre** (5/5→2-4/5) pur mantenendo un PF aggregato
simile o leggermente inferiore — stesso pattern già visto su
BREAKOUT_ACC. Il target fisso resta nettamente la scelta più solida
per questo cluster specifico.

## Verdetto

**Nessun cambiamento per entrambe** — restano con la configurazione
già nota (BUY-only, target fisso 1.5/4.0×ATR). Chiude il cluster
trend-following: su 5 strategie (DONCHIAN_TURTLE, DARVAS_BOX, ADX_RSI,
SAR_ADX20, BREAKOUT_ACC), solo 2 (ADX_RSI, SAR_ADX20) hanno trovato un
miglioramento reale col trailing — le altre 3, tutte col pattern
"finestre che collassano", no.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]
[[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
