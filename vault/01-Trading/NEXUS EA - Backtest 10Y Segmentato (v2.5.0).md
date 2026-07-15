---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, backtest, v2.5.0, data-quality]
created: 2026-07-15
updated: 2026-07-15
---

# Backtest 10 anni segmentato — v2.5.0

## Perché segmentato invece di un run unico
Un backtest unico 2016.07.11→2026.07.11 (tick-by-tick, GOLD M15) moriva ripetutamente
in background prima di completare (~5h per arrivare solo a marzo 2023). Diviso in 10
finestre da 1 anno, lanciate in sequenza sulla stessa istanza isolata di MT5 Tester
(`C:\MT5-Tester`) — nessun parallelismo possibile, un solo tester condiviso.

## Bug della pipeline: report duplicati
Lanciare un segmento troppo a ridosso della fine del precedente causa una race
condition nello script (`scripts/run_backtest.ps1`): se il nuovo report non viene
trovato subito, lo script ripiega su "ultimo file .htm modificato di recente" e
prende per errore il report del segmento **precedente**, silenziosamente (nessun
errore a schermo). Successo in 2 casi su 10 (segmento 2 e segmento 10). Verifica
usata da allora in poi su ogni segmento: diff byte-a-byte contro il report
precedente + controllo che l'ultima riga datata nell'agentlog corrisponda alla
`ToDate` richiesta.

## Trade totali per segmento (wins+losses da stats.csv)

| Finestra | Trade totali | Win | Loss | Strategie BLOCKED_BY_GATE |
|---|---|---|---|---|
| 2016-17 | **17** | 7 | 10 | 3 |
| 2017-18 | **3** | 3 | 0 | 1 |
| 2018-19 | **59** | 31 | 28 | 6 |
| 2019-20 | 534 | 231 | 303 | 13 |
| 2020-21 | 607 | 237 | 370 | 14 |
| 2021-22 | 568 | 282 | 286 | 15 |
| 2022-23 | 748 | 377 | 371 | 15 |
| 2023-24 | 539 | 271 | 268 | 9 |
| 2024-25 | 1089 | 458 | 631 | 21 |
| 2025-26 | 1559 | 665 | 894 | 22 |

## Il problema: 2016-2019 quasi senza trade
I primi 3 anni producono **17, 3 e 59 trade** contro le 500-1000+ dei segmenti
successivi — non rumore, un salto di ordine di grandezza. Il conteggio di
strategie BLOCKED_BY_GATE non spiega da solo il pattern (sale nel tempo, non
scende), quindi non è "il gate diventa più severo negli anni vecchi" in modo
lineare. Ipotesi principale non ancora confermata: i dati storici sono tick reali
solo per 2026.04-07 (vedi [[NEXUS EA - Lezione Overfitting 3Y]]), il resto è
ricostruito — 2016-2019 è la parte più lontana dai tick reali, quindi la più
esposta a un artefatto di ricostruzione (spread/gap sintetici troppo larghi che
fanno scattare i gate su margine/spread prima ancora del segnale).

**Non confermato.** Segmenti 1/2/3 rilanciati per verificare se il problema è
riproducibile o era anomalia del singolo run.

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Log Versioni]] · [[NEXUS EA - Lezione Overfitting 3Y]]
