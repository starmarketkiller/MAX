---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, sar, ema-pullback, python, mql5, risk-size, metodo]
created: 2026-08-28
updated: 2026-08-28
---

# NEXUS EA — Diff Python vs MQL5 su SAR/EMA_PULLBACK: limite strutturale del motore di ricerca (28/08)

## Il metodo (utile per ogni confronto futuro)

L'utente ha condiviso un prompt-metodo per confrontare rigorosamente
un'implementazione Python/Pine ("fonte di verità" presunta) contro la
funzione MQL5 corrispondente, cercando 5 categorie di "gap di
traduzione": (1) shift/repaint, (2) timezone/definizione barra, (3)
matematica degli indicatori, (4) esecuzione/spread/slippage, (5)
gestione posizioni. Applicato su SAR ed EMA_PULLBACK, le due strategie
risultate negative nel backtest reale di stanotte (PF0.92 e PF0.55).

## Punti 1-3: fedeltà confermata

Entrambe le funzioni Python (`sig_sar`, `sig_ema_pullback` in
`server/backtest.py`) portano un commento datato **04/08**: "fedeltà
verificata riga-per-riga con NXS_Strat_SAR/EMAPullback (MQL5 reale)" —
un audit già fatto in una sessione precedente. Riverificato stanotte:

- **SAR**: `sar < prezzo AND ema9 > ema21` (stato, non evento di flip) —
  identico in entrambi i linguaggi. `psar_series()` implementa il vero
  algoritmo di Wilder (AF/extreme-point/flip standard), stessi parametri
  (step 0.02, max 0.2) di `InpSAR_Step`/`InpSAR_Max`.
- **EMA_PULLBACK**: trend persistente 5 barre, impulso precedente
  (11 barre, soglia 1.0×ATR), touch+reclaim con tolleranza 0.15×ATR —
  ogni condizione e ogni range di shift coincide esattamente tra Python
  e MQL5 (verificato indice per indice, non solo a occhio).

**Conclusione punti 1-3**: nessun bug di traduzione. La logica del
segnale è identica.

## Punto 4-5: il gap vero — il motore Python non conosce il lotto minimo

Cercato in tutto `backtest.py`: **zero occorrenze** di `min_lot`,
`volume_min`, `lot_step`, o qualunque floor a 0.01. Il motore Python
dimensiona la posizione in modo **continuo**, proporzionale al
rischio% configurato, come se si potesse sempre aprire esattamente il
lotto necessario, per quanto piccolo.

Il motore MQL5 reale no: se il lotto minimo tradabile (0.01) rischia più
dell'`InpMaxRiskAtMinLotPct` (8%) del saldo per quello stop, l'ordine
viene **rifiutato del tutto** — il gate RISK_SIZE, già identificato
stanotte come responsabile del blocco di ~94% dei tick decisionali su un
conto da $1000 (vedi note precedenti). Su un conto piccolo questo non è
un dettaglio: decide **quali segnali sopravvivono all'esecuzione reale**,
e il sottoinsieme superstite può avere un profilo di rischio/rendimento
diverso dall'insieme completo che Python valuta.

Conferma indiretta: il default di `run_backtest()` in `backtest.py` è
`start_equity=10000.0` — dieci volte il conto reale usato stanotte
($1000). A $10.000 il lotto minimo non rischia quasi mai troppo, quindi
RISK_SIZE non morderebbe praticamente mai in quella simulazione.

## Verdetto

**SAR (PF0.92) ed EMA_PULLBACK (PF0.55) non sono bug di codice.** La
logica è fedele, verificata due volte. Il PF reale più basso della stima
Python riflette (a) un limite strutturale del motore di ricerca (nessuna
modellazione del lotto minimo/RISK_SIZE — vale per QUALUNQUE strategia
confrontata così, non solo queste due) e (b) probabile variazione di
regime tra lo storico ampio usato per la stima Python (2019-2026) e la
finestra reale disponibile (Nov 2025-Ago 2026, l'unica con tick reali).

**Implicazione pratica**: qualunque PF stimato in Python su un conto
"grande" (default $10k) va trattato come un limite superiore ottimistico
per un conto piccolo reale, non come previsione diretta — a prescindere
da quanto la logica del segnale sia fedele.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Piramidare, Debug Completo e Verdetto sul Portafoglio (28-08)]]
[[NEXUS EA - Sei Strategie da TradingView Pine Script (28-08)]]
