---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, crt, m5, conferma, costi]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — CRT: range H4 con conferma M5 (24/08)

## Perché

Ipotesi dell'utente: per la maggior parte delle strategie una conferma
extra (aspettare una barra in più prima di entrare) si è già rivelata
controproducente (vedi [[NEXUS EA - Stop Strutturale M5 su Segnali H1 (16-08)]],
Test 2 — nessun miglioramento su 6 strategie riprovate con stop nativo).
Ma per CRT il problema noto è diverso e specifico: lo stop è sempre
ancorato al wick della candela di sweep, e quando quel wick è minimo il
rischio in R esplode per via dei costi fissi (la "saga costi-dominanti",
vedi `_crt_series` in `backtest.py`). L'idea: usare il range di una
candela H4 **chiusa** come livello, e aspettare la chiusura di una
candela **M5** (non la stessa TF del range) per la conferma del falso
breakout — stop più preciso, potenzialmente più occasioni al giorno.

## Meccanismo testato

Variante NUOVA, distinta dal CRT esistente (che usa 3 candele consecutive
sulla stessa TF):

1. CRH/CRL = high/low dell'ultima candela H4 **chiusa**.
2. Durante il periodo H4 successivo, ogni candela M5 è un potenziale
   sweep: high supera CRH ma chiude sotto CRH (rientro) → SELL, stop =
   high di quella candela M5. Speculare per CRL → BUY.
3. Entrata a mercato all'apertura della M5 successiva (convenzione
   standard del motore, mai dentro la barra del segnale).
4. Uscita a rapporto fisso 1:2 (richiesta esplicita, non ATR).

**Assunzione dichiarata** (unico punto ambiguo della richiesta): "chiude
sotto il range" interpretato come "chiude sotto CRH" (rientra dentro o
sotto il range), non "chiude sotto CRL" (rientro totale) — stessa
semantica del CRT esistente (`swept_high ... close<=crh`). Da confermare
se il meccanismo sembra promettente.

Nessun filtro di regime applicato — un fade di un breakout non è un
sistema trend-following, il filtro ER usato altrove non si applica per
costruzione (una sola ipotesi per esperimento: qui il meccanismo di
entrata, non il regime).

## Risultato: bocciata, costi dominanti confermati

Script: `crt_h4range_m5confirm_24-08.py` (H4 dal motore reale, M5 dalla
cache Dukascopy).

**15.197 trade grezzi** (~1.5 per periodo H4, coerente con "più occasioni
al giorno"). PF grezzo (senza costi): **1.08**, win rate 35% (soglia di
pareggio per 1:2 è 33.3% — edge grezzo reale ma sottilissimo).

Con costi reali applicati, il PF collassa:

| Preset | aggPF | sumR | finestre PF≥1 |
|---|---|---|---|
| retail | 0.04 | -40.042R | 0/5 |
| ECN | 0.23 | -17.215R | 0/5 |

Causa diagnosticata direttamente (non ipotizzata): `risk_dist` mediano
**$1.22** (p10 $0.36, p90 $4.60) — stop sistematicamente minuscoli, lo
stesso meccanismo di fallimento già visto nell'addendum 17/08 dello stop
M5 (quando lo stop si stringe, il costo fisso in $ diventa dominante in
termini di R). Qui è ancora più estremo perché il segnale non richiede
alcuna "freschezza" del setup — la stessa condizione di sweep può restare
vera per più candele M5 consecutive mentre il prezzo oscilla intorno al
livello, producendo molti trade quasi identici a rischio minimo.

**Tentativo di salvataggio**: applicato lo stesso floor che ha
funzionato altrove (0.3×ATR(H4), scarta i trade sotto — modalità "skip",
non "widen", coerente con la lezione già acquisita che allargare
peggiora). Risultato: scarta 14.193 trade su 15.197 (93%), i 1.004
superstiti restano **negativi** su entrambi i preset (retail PF 0.40,
ECN PF 0.69, 0/5 finestre in entrambi). Il floor non rescue: a differenza
del CRT classico, qui la popolazione con stop più largo non ha un edge
residuo sufficiente — il segnale stesso sembra concentrare il poco edge
grezzo proprio nei trade a rischio minimo, che sono anche quelli che i
costi uccidono per primi.

## Verdetto

Bocciata. L'ipotesi era ragionevole (edge grezzo reale, seppur sottile) e
la diagnosi conferma che il problema è esattamente quello previsto
dall'utente (stop/costi), ma la conferma M5 su range H4 non lo risolve —
lo aggrava, perché rimuove il vincolo "una entrata per periodo" che il
CRT classico ha implicitamente (3 candele fisse) e permette al motore di
generare trade ripetuti a rischio quasi nullo sullo stesso livello.

## Prossimi passi aperti

- Non provato: richiedere che il sweep M5 sia il **primo** della serie
  per quel periodo H4 (invalidare il livello dopo il primo tentativo,
  vinto o perso) — ridurrebbe drasticamente il conteggio trade e
  eliminerebbe la ripetizione a rischio minimo, ma è un meccanismo
  diverso da testare come ipotesi separata, non dedotto qui.
- Non provato: R:R diverso da 1:2 (es. 1:3-1:4, coerente con lo stop
  stretto) — cambierebbe la soglia di pareggio ma non il problema di
  fondo (i costi dominano quando risk_dist è nell'ordine di $1).
- La lettura alternativa di "chiude sotto il range" (chiusura sotto CRL,
  rientro totale) non è stata testata — cambierebbe drasticamente il
  numero di trade (molto più raro), da verificare con l'utente prima di
  investire altro tempo.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Stop Strutturale M5 su Segnali H1 (16-08)]]
