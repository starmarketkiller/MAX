---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, mql5, protezioni, bug, max-total-dd]
created: 2026-09-10
updated: 2026-09-10
---

# Verifica protezione Max Total DD — zero trigger nonostante DD 22.83% (10/09)

## Test

`nxs_regtest_maxtotaldd_check` — FVG_CONT, stesso periodo/config dello
step2 baseline (2023.09.01-2026.08.26, D1/H4 multi-TF), con
`InpUseMaxTotalDD=true`, `InpMaxTotalDDPct=10.0` aggiunti ieri (09/09).

## Risultato

168 trade, PF1.92, net $2628.45, DD bilancio 12.45%, **DD equity 22.83%**
— praticamente identico allo step2 baseline (168 trade, PF1.92, $2635.26,
DD 12.42%/22.79%). Differenze minime (arrotondamento).

## Problema trovato

`InpMaxTotalDDPct=10.0` significa che la protezione dovrebbe flattenare il
conto e mettere in pausa non appena l'equity scende del 10% dal picco.
L'equity DD massima riportata da MT5 è 22.83% — più del doppio della
soglia. **Zero occorrenze** di `"MAX_TOTAL_DD HIT"` o di qualunque log
`[NEXUS PROT]` relativo nell'intero log di 3 anni: la protezione non è mai
scattata, nonostante il conto abbia sicuramente attraversato un calo del
10%+ dal suo picco corrente in qualche momento della serie (è
matematicamente necessario per arrivare a un max DD del 22.83%).

Non corretto ancora (l'utente ha chiesto esplicitamente di aprire solo una
nota tecnica separata, commit distinto dal fix Research Mode). Approfondito
un po' di più il 10/09 mentre cercavo tutte le exit authority per il fix
RAW — non risolto, ma il quadro è più preciso:

**Funzione coinvolta**: `NXS_Prot_CheckMaxTotalDD()` in `NXS_Protections.mqh`.

**Stato/peak usato**: `g_maxDDPeakEquity` (double, globale, dichiarato in
`NXS_Globals.mqh`, default 0.0) — aggiornato ad ogni tick con
`if(eq > g_maxDDPeakEquity) g_maxDDPeakEquity = eq;` PRIMA del controllo
soglia, quindi il picco è sempre il massimo storico osservato dentro
questo stesso processo. **Non è persistito** (verificato: non compare in
`NXS_State.mqh`, quindi non c'è rischio di uno stato "vecchio" caricato da
un file lasciato da un test precedente — parte sempre da 0.0 ad ogni avvio
del terminale/Tester).

**Equity o balance**: usa `AccountInfoDouble(ACCOUNT_EQUITY)` (include il
P&L flottante), non balance — corretto per l'intento dichiarato ("mai
dimenticare un drawdown accumulato").

**Possibile problema di ordine chiamate trovato ora (non confermato come
causa, ma reale)**: `NXS_Prot_OnTick()` ha, PRIMA di arrivare a
`CheckMaxTotalDD()`, `if(g_pausedUntilNextOpen) return;`. Questo flag viene
messo a `true` da ESL/DPT/**AutoClose** (vedi nota collegata sulla
scoperta AutoClose) e **si azzera SOLO una volta al giorno**, dentro
`NXS_Prot_OnNewDay()` — nonostante il nome suggerisca "fino alla prossima
apertura", in realtà è "fino alla mezzanotte successiva". Con
`InpUseAutoClose=true` (default) che scatta ogni sera vicino alla chiusura
di sessione, `g_pausedUntilNextOpen` resta vero per la finestra fra
l'AutoClose serale e il rollover di mezzanotte (circa 15-20 minuti nel
nostro caso, `InpAutoCloseMin=15`) — durante quella finestra
`CheckMaxTotalDD()` non viene proprio chiamata. È una finestra breve, non
sembra sufficiente da sola a spiegare uno zero trigger totale su 3 anni,
ma è un candidato concreto da escludere prima di guardare altrove, ed è
comunque una scoperta a parte (il nome della variabile è fuorviante
rispetto al comportamento reale).

**Altre ipotesi ancora da verificare**:
- differenza tra equity calcolata tick-per-tick e la curva equity
  aggregata che MT5 riporta a fine test (possibile disallineamento di
  campionamento);
- va anche verificato se il test `nxs_regtest_maxtotaldd_check` aveva
  `InpUseAutoClose`/altre protezioni attive che avrebbero potuto interagire
  nello stesso modo.

Prossimo passo per chiudere davvero: instrumentare temporaneamente
`NXS_Prot_CheckMaxTotalDD()` con un log ad ogni tick (o ogni N tick) di
`eq`, `g_maxDDPeakEquity`, `ddPct` per individuare il momento esatto in cui
il DD reale supera il 10% e verificare se la funzione viene raggiunta in
quel momento o saltata.

## Verdetto

**Protezione non verificata come funzionante** — implementata (commit
`7491e42`, 09/09) ma il primo vero test di regressione mostra che non
scatta quando dovrebbe. Da NON considerare operativa finché non si trova e
corregge la causa. Segnalato, non corretto in questa sessione.

## Collegamenti
[[MOC - Trading]]
