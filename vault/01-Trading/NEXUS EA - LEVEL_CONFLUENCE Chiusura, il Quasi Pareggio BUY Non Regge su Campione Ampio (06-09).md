---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, level-confluence, chiusura, negativo]
created: 2026-09-06
updated: 2026-09-06
---

# NEXUS EA — LEVEL_CONFLUENCE: il quasi pareggio BUY non regge su campione ampio, chiusura (06/09)

## Il test

Stessa configurazione della [[NEXUS EA - Confluenza Obbligatoria, Miglior Risultato Finora e BUY Quasi in Pareggio (06-09)]]
(conferma 2 barre, livelli H1/H4/D1, confluenza obbligatoria) ma su
**3 anni invece di 3 mesi**, per verificare se il quasi-pareggio BUY
visto su 73 trade regge su un campione più ampio.

⚠️ **Nota sul rischio**: questo test usa il rischio di default (0.5%
a trade), non il 5% usato nel test a 3 mesi — su 3 anni e ~1200 trade
un rischio così alto avrebbe fatto saltare il conto. I valori in
dollari NON sono confrontabili 1:1 tra i due test, solo le metriche
relative (PF, win rate, gap dalla soglia di pareggio) lo sono.

## Risultato

| Metrica | 3 mesi (73 BUY, rischio 5%) | 3 anni (547 BUY, rischio 0.5%) |
|---|---|---|
| Trade BUY | 73 | 547 |
| Net BUY | **-$0.51** (quasi pareggio) | -$277.24 |
| WR BUY | 35.6% | 36.7% |
| Soglia pareggio BUY | 35.6% (= WR, gap 0.0pp) | 39.9% (gap **-3.2pp**) |
| Trade SELL | 47 | 634 |
| Net SELL | -$273.13 | -$484.76 |
| WR SELL | 31.9% | 31.9% |
| Gap SELL | -7.2pp | -4.4pp |
| PF totale | 0.88 | 0.82 |

**Il quasi-pareggio BUY su 73 trade era un artefatto di campione
piccolo** — come già sospettato nella nota precedente. Su 547 trade
(quasi 7.5× il campione) il lato BUY torna chiaramente negativo
(-$277, gap -3.2 punti dalla soglia di pareggio).

## Ma non è un fallimento come le altre — è comunque il filtro migliore trovato

Guardando il **gap dalla soglia di pareggio** su tutte le iterazioni
testate (la metrica più onesta per confrontare campioni di taglia
diversa):

| Iterazione | Gap WR-soglia (BUY) | Gap WR-soglia (SELL) |
|---|---|---|
| Conferma2+HTF, M15 (295 trade) | -10.7pp | -10.7pp |
| Conferma2+HTF, M5 (346 trade) | -6.2pp | -4.2pp |
| **Confluenza obbligatoria, 3 anni (1181 trade)** | **-3.2pp** | **-4.4pp** |

La confluenza obbligatoria **dimezza il gap dalla redditività**
rispetto a tutte le versioni precedenti, su un campione molto più
grande e quindi più affidabile — è la selezione di ingresso migliore
trovata per questo concetto (tocco/sweep di livello), ma **non basta
ancora ad attraversare la soglia di pareggio**.

## Verdetto di chiusura

Dopo 5 iterazioni indipendenti (touch grezzo, conferma-barre, fonte
livelli HTF, TF di esecuzione M5, confluenza obbligatoria) nessuna ha
prodotto un risultato netto positivo, né su 3 mesi né su 3 anni, né
BUY né SELL. Il gap dalla soglia di pareggio si è ridotto
progressivamente (da -10.7pp a -3.2pp) ma non si è mai chiuso.
**LEVEL_CONFLUENCE va chiusa come strategia** e spostata nella
categoria "chiuse negative" del piano master, insieme a PIVOT_WICK e
BOLLINGER M5 scalp — stessa conclusione onesta, non un'ennesima
variante da testare all'infinito.

Il merito rimane: il lavoro ha comunque isolato QUALE filtro riduce
di più il gap (confluenza multi-TF > conferma-barre > niente), utile
come lezione di metodo per altre strategie basate su livelli
(MALAYSIAN_SNR, ORDER_BLOCK, ecc. — categoria 4 del piano master, mai
testate).

## Collegamenti
[[NEXUS EA - Confluenza Obbligatoria, Miglior Risultato Finora e BUY Quasi in Pareggio (06-09)]] · [[NEXUS EA - LEVEL_CONFLUENCE M5 vs M15, Stesso Esito Negativo su Entrambi i TF (06-09)]] · [[NEXUS EA - Conferma 2 Barre e Livelli HTF, Migliora il Rapporto ma Resta Negativo (06-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
