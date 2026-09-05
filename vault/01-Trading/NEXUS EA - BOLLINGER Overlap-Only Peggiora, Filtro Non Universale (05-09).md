---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, bollinger, sessioni, filtro, negativo]
created: 2026-09-05
updated: 2026-09-05
---

# NEXUS EA — BOLLINGER H4 BUY-only + Overlap-only peggiora: il filtro sessione non è universale (05/09)

## Perché

Dopo la conferma che `InpProfileOverlapOnly` funziona davvero su
MACD H4 (PF1.53→1.74, net +5.7%, vedi
[[NEXUS EA - Il Filtro Sessione Era su un Percorso di Esecuzione Diverso (04-09)]]),
provato lo stesso filtro sulla miglior ricetta BOLLINGER trovata finora
(H4, BUY-only, PF1.35, Sharpe2.45 — vedi
[[NEXUS EA - BOLLINGER H4 Nuda, BUY Positivo SELL Negativo, Conferma Python (04-09)]])
per capire se il pattern si ripete.

## Risultato — non si ripete, peggiora nettamente

| | BUY-only nudo (baseline) | BUY-only + Overlap-only |
|---|---|---|
| Trade | 68 | **11** |
| Profit factor | 1.35 | 1.42 |
| Net profit | $352.92 | **$68.01** (-81%) |
| Sharpe | **2.45** | 0.74 |
| Recovery factor | 1.03 | 0.44 |

Il gate ha funzionato meccanicamente come previsto (verificato sul CSV
grezzo: i 11 trade sono concentrati solo nelle ore server 14-16, la
finestra Overlap) — non è un altro bug infrastrutturale, è proprio
questo l'effetto: comprime il campione da 68 a 11 trade su 3 anni.
Il PF sale leggermente ma su un campione troppo piccolo per essere
significativo, e la metrica che più contava per questa strategia (lo
Sharpe, il migliore di tutta l'indagine) crolla da 2.45 a 0.74.

## Interpretazione

Il filtro Overlap non è un miglioramento universale — dipende da
*dove* si concentra davvero l'edge della strategia. Per MACD la
maggioranza dei trade profittevoli cadeva già in quella finestra
oraria (il filtro toglieva soprattutto rumore). Per BOLLINGER
BUY-only l'edge è distribuito su più ore del giorno: restringere a
sole 3 ore toglie sia rumore sia segnale buono, e il campione residuo
è troppo piccolo per fidarsene.

## Analisi CSV per-trade

Sugli 11 trade (tutti BUY): 6 chiusi a stop loss, 5 a take profit
(quasi 50/50 per conteggio, ma il campione è troppo piccolo per
significato statistico). Pattern di durata **opposto** a quello sano
visto su MACD Overlap-only: le perdite si chiudono in **6.1h medie**,
i vincenti impiegano **38.6h** — rapporto 6.3:1 a favore dei vincenti,
ma su un campione di 11 trade questo dice più sulla fortuna del
campionamento che sulla strategia. Slippage sugli stop minimo (0.115
medio). Nessuna chiusura da protezione drawdown o altro meccanismo
non taggato — a differenza di MACD, qui ogni chiusura ha un motivo
chiaro nel commento.

## Decisione

BOLLINGER resta con la ricetta H4 BUY-only **nuda** (senza
Overlap-only) come miglior configurazione trovata. Non applicare
`InpProfileOverlapOnly` come default per tutte le strategie —
va testato caso per caso, esattamente come richiesto ("puoi tenere
tutti i filtri che vuoi basta che aiutino davvero la strategia").

## Collegamenti
[[NEXUS EA - BOLLINGER H4 Nuda, BUY Positivo SELL Negativo, Conferma Python (04-09)]] · [[NEXUS EA - Il Filtro Sessione Era su un Percorso di Esecuzione Diverso (04-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
