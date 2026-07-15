---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, fonte, msnr, smc, ict, malaysian-snr]
created: 2026-07-15
updated: 2026-07-15
---

# Fonte: "MSNR x SMC x ICT — The Alchemist" (Yanu Emmanuel)

PDF fornito dall'utente il 15/07 (51 pagine). Manuale di trading focalizzato
sulla **Malaysian Support & Resistance (MSNR)**, integrata con Smart Money
Concepts (SMC) e metodologia ICT. Questa è quasi certamente **la fonte
originale della strategia `MALAYSIAN_SNR`** nel nostro EA — l'implementazione
MQL5 attuale ("Support/resistance con storyline (fresh/flipped)", vedi
[[Malaysian Snr]]) cattura solo una frazione minima di quanto descritto qui.
Estratte sotto solo le regole direttamente azionabili, non l'intero libro.

## Come si identifica un livello SNR (diverso da high/low classico)
Si traccia la linea tra **CLOSE di una candela e OPEN della successiva**,
ignorando gli stoppini (wick):
- **Resistenza**: close di una candela rialzista → open della prossima
  ribassista (forma "A" su grafico a linea).
- **Supporto**: close di una candela ribassista → open della prossima
  rialzista (forma "V" su grafico a linea).

Questo è **diverso** da come identifichiamo SNR/pivot altrove nel codice
(che tipicamente usa high/low di N barre — vedi `_hh`/`_ll` in
`server/backtest.py` o gli `swing high/low` nel codice MQL5). Vale la pena
valutare se questa definizione close-to-open cattura meglio i veri livelli
istituzionali.

## Fresh vs Unfresh (già presente nel nostro codice, ma qui più preciso)
- **Fresh**: livello mai toccato da wick o body.
- **Unfresh**: già toccato (anche solo dal wick) — considerato più debole,
  ha "liquidità già raccolta".
- **Flip (SBR/RBS)**: se un livello unfresh viene rotto con una **chiusura
  di corpo intera** (non solo un wick), il ruolo si inverte — supporto rotto
  diventa resistenza (Support Becomes Resistance) e viceversa (Resistance
  Becomes Support). Una volta flippato, se il prezzo lo ritocca **solo con
  un wick** (senza richiudere oltre), il livello torna "fresh" nella nuova
  direzione — è il livello più forte da tradare.

## Storyline: la direzione è un gioco multi-timeframe gerarchico
"Storyline" = direzione attesa del prezzo, **solo per HTF** (Monthly/Weekly/
Daily), non per LTF:
- Monthly: non abbastanza consistente da usare per la direzione.
- Weekly: direzione principale.
- Daily: ritracciamento/roadblock per la direzione Weekly.
- H4: conferma/roadblock (gap level) per Daily e Weekly — **può anche
  disturbare la direzione Daily**.
- H1: speciale — decide se la direzione è valida o no, ma serve che dia una
  candela con wick/gap.

**Regola gerarchica**: se il Weekly è rialzista ma il Daily è ribassista, la
storyline Weekly rialzista **non può continuare** finché la storyline Daily
ribassista non si è conclusa. Le HTF sono vincolate dalle LTF intermedie, non
indipendenti.

## "2 TF's Confirmation Rule" — la regola operativa più concreta del libro
1. Il prezzo tocca un livello SNR fresh dell'HTF con un **rifiuto** (wick).
2. Si scende di **due timeframe** più in basso per cercare il **breakout**
   (qui il livello SNR non deve necessariamente essere fresh).
3. Weekly Setup → conferma su H4. Daily Setup → conferma su H1.
4. Al breakout sul LTF, **aspetta il pullback** per entrare (dalla "spalla
   destra" o dal livello QML — Quasimodo).

## Trendline: "angled SNR" + Marriage Concept
- Le trendline si tracciano collegando close/open (come le SNR), **non** i
  wick, e **non** si possono usare per collegare una GAP SNR.
- Servono **almeno 2 tocchi**, e nessuna candela deve chiudere oltre la
  linea nel frattempo.
- **Entra solo al 3° tocco** (wick che rifiuta la linea) — mai al 2°.
- **"Marriage Concept"** (attribuito al trader malese Ariff T.): quando una
  trendline e un livello SNR si intersecano nello stesso punto, quella è la
  confluenza più forte possibile — l'entrata va cercata lì.

## Sessioni / Kill zone
Si tradano principalmente le sessioni **Londra e New York** (massima
volatilità). BOS (Break of Structure) è valido **solo con chiusura di corpo
piena** oltre lo swing high/low — un wick non conta come BOS. Dopo un BOS,
**aspetta sempre il ritracciamento** prima di entrare, e tradare sempre nella
direzione del BOS.

## Esempi reali dal libro (RR molto ampi, coerente coi nostri dati)
Gli esempi concreti nel libro mostrano RR di **1:26, 1:22, 1:21** — TP molto
larghi rispetto allo SL, ottenuti raffinando l'entrata su timeframe via via
più bassi (Weekly/Daily bias → H4 struttura/QM level → H1 raffinamento OCL →
M15 conferma con trendline+liquidità). Questo è coerente con il pattern già
documentato nello screening sito ([[NEXUS EA - Screening Strategie (sito 10y)]]):
**TP largo (4.0-4.5× ATR) batte quasi sempre TP corto** — qui vediamo la
ragione strutturale: l'entrata raffinata su LTF con SL stretto, ma il target
resta quello della struttura HTF (molto più lontano).

## Concetti menzionati ma non spiegati in dettaglio (servono altre fonti)
- **QM / QML** (Quasimodo Level) — usato come riferimento d'entrata ma mai
  definito esplicitamente nel testo letto. Non implementato da nessuna parte
  nel nostro codice attuale.
- **CRT (Candle Range Theory)**, citata come concetto di ICT: si marca il
  range (high/low) del giorno precedente, e si osserva se la candela del
  giorno corrente chiude dentro quel range — potenziale setup. Da
  confrontare con `DISP_REBAL`/`RANGE_FADE`.

## Applicazione concreta: vedi [[NEXUS EA - Setup Buy-Sell — Framework]]
Il primo setup buy/sell ricostruito da questa fonte (MALAYSIAN_SNR) è lì.

## Collegamenti
[[MOC - Trading]] · [[Malaysian Snr]] · [[NEXUS EA - Setup Buy-Sell — Framework]] · [[NEXUS EA - Screening Strategie (sito 10y)]]
