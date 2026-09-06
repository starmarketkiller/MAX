---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, esl, adx-rsi, correzione]
created: 2026-09-06
updated: 2026-09-06
---

# NEXUS EA — correzione sull'ESL: disattivarlo peggiora ADX_RSI, non lo migliora (06/09)

## Il test

Verifica empirica dell'ipotesi della nota precedente
([[NEXUS EA - Scoperta ESL, Costo Nascosto Trasversale a Tutti i Test (06-09)]]):
ADX_RSI D1 nudo, 3 anni, `InpUseESL=false` invece del 5% di default.

## Risultato — il contrario di quanto ipotizzato

| | ESL attivo (04/09) | ESL disattivato (06/09) |
|---|---|---|
| Trade | 51 | 51 |
| PF | **2.04** | **1.26** |
| Net (3 anni) | **+$1675.65** | **+$573.18** |
| Max DD equity | $596.09 | **$1470.84** (147% del deposito) |
| Sharpe | 1.20 | 0.52 |
| Recovery factor | — | 0.39 |

**Disattivare l'ESL peggiora nettamente il risultato**, non lo
migliora — PF quasi dimezzato, netto ridotto di due terzi, e il
drawdown massimo supera il deposito iniziale (147%), il che in un
conto reale avrebbe significato margin call/liquidazione ben prima
della fine dei 3 anni.

## Dettaglio SELL — la prova più chiara

Le stesse identiche 7 operazioni SELL (l'ESL non tocca gli ingressi,
solo le uscite forzate):

| | ESL attivo | ESL disattivato |
|---|---|---|
| Net SELL | +$28.06 | **-$370.87** |
| Win rate | 14.3% | **0.0%** |

Le stesse 7 operazioni, lasciate correre senza la rete di sicurezza
dell'ESL, sono peggiorate da quasi-pareggio a perdita totale (0/7
vincenti). Questo conferma direttamente che per queste operazioni
l'ESL stava **tagliando la perdita al momento giusto**, non
togliendo un trade che si sarebbe ripreso.

## Come si concilia con la nota precedente

La nota del 06/09 mattina aveva trovato che le uscite "dd" (ESL)
erano, IN MEDIA, la categoria più dannosa per $ per trade (-$85/-$87
contro -$30/-$23 degli SL veri) — **questo resta vero**, i trade
che l'ESL taglia sono individualmente costosi. Ma la conclusione
"quindi disattivarlo aiuterebbe" era prematura: quel costo medio più
alto riflette il fatto che l'ESL scatta solo sui trade che sono GIÀ
andati molto male (altrimenti non avrebbero raggiunto la soglia), non
che l'ESL stia rovinando trade altrimenti sani. **Il vero confronto
corretto non è "quanto costa il trade quando l'ESL scatta" ma "quanto
sarebbe costato SENZA l'ESL"** — ed è quest'ultimo numero, verificato
ora, a essere molto peggiore.

## Lezione di metodo

Un costo medio alto su una categoria di uscita non implica
automaticamente che rimuovere quella categoria migliori il risultato
— serve sempre il confronto diretto con e senza, non solo l'analisi
della categoria isolata. Stessa logica già applicata ai filtri
Elliott/Overlap (mai assumere, sempre testare il prima/dopo) ora vale
anche per le protezioni di rischio.

## ESL resta attivo, nessuna modifica alla configurazione

Non ci sono ulteriori azioni da questa scoperta per ADX_RSI —
la configurazione di riferimento resta quella con ESL al 5% di
default, già confermata positiva.

## Collegamenti
[[NEXUS EA - Scoperta ESL, Costo Nascosto Trasversale a Tutti i Test (06-09)]] · [[NEXUS EA - ADX_RSI D1 Confermata Positiva sul Vero MT5, BUY Domina (04-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
