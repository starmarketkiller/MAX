---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, principi, lezioni]
created: 2026-07-12
updated: 2026-07-12
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

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Log Versioni]]
