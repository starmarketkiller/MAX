---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, principi, lezioni]
created: 2026-07-12
updated: 2026-07-15
---

# Principi — le lezioni dure

Regole nate da errori reali fatti in questo progetto. Vanno rilette **prima** di
fidarsi di un nuovo risultato, non dopo.

## 1. Un backtest corto è un'ipotesi, non una conferma
v2.4.8: Sharpe **3.19** e net **+1050** sui 3 mesi. Stesso identico build sui 3 anni:
net **−863**, drawdown **87%** (conto quasi azzerato). Vedi
[[NEXUS EA - Lezione Overfitting 3Y]].

> **Regola**: nessun tuning è valido finché non è confermato su almeno due finestre
> temporali indipendenti. Un record sui 3 mesi non prova niente da solo.

## 2. Ogni strategia è indipendente — non esiste una ricetta unica
Scoperta verificata sul campo (non solo intuita): trend-following e mean-reversion
hanno bisogni opposti. Un trailing largo che fa volare TURTLE_SOUP (PF 2.04→2.72)
**distrugge** ICHIMOKU o BJORGUM nello stesso momento. La soluzione non è "trovare
il parametro giusto per tutte", è **dare a ciascuna il suo gate, il suo SL/TP, il
suo trailing, la sua corsia hedge**. Vedi [[NEXUS EA - Log Versioni]] (v2.4.4 vs
v2.4.5) e le singole schede in `01-Trading/Strategie/`.

> **Regola**: non giudicare mai una strategia con i parametri di un'altra. "Non
> funziona" spesso vuol dire solo "non l'ho ancora fatta operare secondo la sua
> natura".

## 3. Attenzione: questa stessa scoperta è anche una porta per l'overfitting
Il principio 2 è potente ma pericoloso se applicato senza il principio 1. Il
confine:
- **Aggiustamento sano**: capisco che una strategia è trend-following e le do un
  trailing largo perché la sua natura lo richiede → generalizza.
- **Overfitting travestito**: continuo a ritoccare i valori di ogni strategia finché
  il backtest sui 3 mesi è bello → è esattamente ciò che ha prodotto v2.4.8.

> **Regola**: ogni strategia "resa profittevole" va rivalidata sui 3 anni prima di
> essere dichiarata buona. Altrimenti si stanno costruendo 36 piccoli overfitting
> invece di uno grande. Lo stato di validazione di ognuna è tracciato nella sua
> scheda in `01-Trading/Strategie/`.

## 4. Un PF alto su pochi trade non è una prova
BJORGUM mostra PF 2.14 sui 3 anni — sembra tra le più solide. Ma sono solo **5
trade eseguiti** in 3 anni. Statisticamente insufficiente per dichiararla validata,
anche se il numero è bello.

> **Regola**: sotto ~15 trade, tratta il profit factor come rumore, non come segnale.
> Il numero di trade conta quanto il PF stesso.

## 5. Sito e MT5 sono due motori diversi — un edge lì non è un edge qui
Il motore Python del sito (dati Yahoo daily) e l'EA su MT5 (dati broker, timeframe
multipli) possono dare risultati **opposti** sulla stessa strategia (es. TURTLE_SOUP:
0.77 sul sito, 2.12 su MT5). Un risultato trovato sul sito è sempre un'**ipotesi da
validare**, mai una certezza diretta. Vedi [[Sito Backtest Lab - Note Tecniche]].

> **Regola**: quando riporti un numero, specifica sempre la fonte (sito o MT5) e
> l'orizzonte (3M o 3Y). "PF 1.5" da solo non vuol dire niente.

## 6. Un edge del sito non sostituisce una config MT5 già validata
Scoperta dal backtest 10y segmentato ([[NEXUS EA - Backtest 10Y Segmentato - Analisi]]):
MACD era **già validata** su MT5 (PF 1.11, v2.4.8, 3 anni). Il "raffinamento"
v2.5.0, basato sullo screening del motore sito, l'ha resa la seconda peggiore
strategia del portafoglio (-18.5R su 5 anni). Il principio #5 diceva "un edge
del sito è un'ipotesi da validare" — qui il caso è più grave: si è **sostituita**
una config MT5 già confermata con un'ipotesi non ancora testata su MT5.

> **Regola**: se una strategia è già validata su MT5, un miglioramento proposto
> dal sito va testato in **isolamento** (A/B, non sostituzione diretta) prima
> di rimpiazzare la config esistente. Non rischiare un edge confermato per
> inseguire un edge ancora ipotetico.

## 7. Un gate "giornaliero" non protegge dal drawdown cumulato
`InpMaxDailyDDPct=5.0` limita solo la perdita di **un singolo giorno** (si
resetta ogni giorno) — non esiste nel codice nessun limite sul drawdown
cumulato dal picco equity. Risultato: nel segmento 2020 del backtest 10y il
conto ha comunque perso l'87.22% di equity, identico al DD di v2.4.8 sui 3
anni ([[NEXUS EA - Lezione Overfitting 3Y]]) — lo stesso identico numero, due
build diverse, stessa causa strutturale mai chiusa.

> **Regola**: "protetto dal drawdown giornaliero" non vuol dire "protetto dal
> drawdown". Prima di fidarsi di un sistema di risk management, verifica se il
> gate è per-giorno, per-settimana o cumulato-dal-picco: sono tre cose diverse
> e solo l'ultima previene un conto azzerato in mesi di erosione lenta.

## 8. Il motore del sito non ha hedge, e un proxy col nome giusto può testare la cosa sbagliata
Due scoperte dall'audit del 15/07 ([[NEXUS EA - Motore Sito: Audit e Confronto 10Y]]):
il motore Python tiene una **sola posizione alla volta** (`pos = None`,
variabile singola) — non può mai simulare l'hedge tra strategie, per design,
indipendentemente dai dati. E il proxy `sig_sar()` non implementa Parabolic
SAR: è identico, trade per trade, a `sig_ema_pullback()`. Un numero con
l'etichetta giusta ("SAR → PF1.52") può derivare da un test che non ha mai
toccato la logica reale.

> **Regola**: prima di usare un numero dello screening sito per giustificare
> un cambio, verifica che (a) il motore possa strutturalmente rispondere alla
> domanda che gli stai facendo (l'hedge non è testabile lì, punto), e (b) la
> funzione segnale corrisponda davvero al nome che porta — non fidarti
> dell'etichetta, leggi il codice della funzione.

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Log Versioni]]
