---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, ensemble, tp-dinamico, walk-forward]
created: 2026-08-11
updated: 2026-08-11
---

# Ensemble riverificato + TP dinamico su liquidità (11/08, seguito)

Richiesta esplicita dell'utente: (1) verificare se il lavoro sull'ensemble
a voto (segnato "oro") avesse lo stesso difetto appena trovato sui filtri
di regime; (2) riprovare il TP dinamico ancorato alla liquidità reale
(il meccanismo dietro la forza di CRT) sulle altre strategie del nucleo.

## 1. Ensemble a voto — parzialmente valido, non uno "oro" falso

A differenza dei filtri di regime, `ensemble_engine_search.simulate()`
**non** aveva un bug di fedeltà nel senso stretto: il SL/TP piatto
(1.5×/3.0× ATR) è la stessa convenzione "flat baseline" usata come
riferimento in tutta la sessione, e le funzioni segnale (che decidono i
voti) non dipendono comunque dal SL/TP. Il problema reale era solo
`bars=60000` (storico vecchio) — corretto a 110000.

Risultato sullo storico ampio, ricerca greedy a voto uniforme, soglia
minima 2 voti concordi, combo finale a 15 strategie:

| | IS | OOS |
|---|---|---|
| Ensemble (15 strategie, min 2 voti) | PF 1.35/382 | PF 1.37/252 |

**Consistente** (IS≈OOS, non è overfitting) ma **non superiore a CRT da
sola** (OOS PF 1.25 su 4.711 trade — venti volte il campione
dell'ensemble, PF comparabile). Conclusione onesta: l'ensemble a voto
funziona come concetto (non è rumore), ma non offre un vantaggio pratico
sopra la singola strategia più forte già nel nucleo. Non prioritario da
portare in produzione rispetto ad altro.

## 2. TP dinamico su liquidità reale — non si trasferisce

L'infrastruttura (`STRATEGY_TARGETS_OPTIN`/`_liq_sweep_target`: target =
livello di liquidità più vicino tra PDH/PDL/Asian High-Low/ultimo swing
esterno confermato, con soglia di R:R minimo) esisteva già, testata una
volta sola su LIQ_SWEEP il 16/07 con esito "misto/non decisivo" sullo
storico vecchio. Riverificata su storico ampio + estesa a FVG_CONT
(unico altro candidato pulito nel nucleo — le altre strategie SMC hanno
già un SL/TP strutturale con priorità assoluta, es. TURTLE_SOUP/FVG_MIT,
un target dinamico lì sarebbe codice morto):

| Strategia | Walk-forward TP dinamico vs flat | Verdetto |
|---|---|---|
| LIQ_SWEEP (1d) | 2/5 | conferma il "misto" del 16/07 |
| FVG_CONT (4h) | 3/5, differenze nell'ordine del rumore (±0.05-0.08 PF) | nessun miglioramento reale |

**Il meccanismo che rende forte CRT non si trasferisce automaticamente.**
Ipotesi sul perché: in CRT il target (lato opposto del range) è
**strettamente accoppiato** alla stessa struttura locale a 3 candele che
genera il segnale d'ingresso — stesso "evento", stessa scala. In
LIQ_SWEEP/FVG_CONT il target dinamico usa livelli di sessione/giornalieri
più distanti e **debolmente accoppiati** all'evento d'ingresso (un
sweep/FVG locale non ha relazione diretta con dove sta il PDH/PDL). Non
è "TP su liquidità reale" in sé che funziona — è la coerenza di scala
tra struttura d'ingresso e struttura d'uscita, che CRT ha per costruzione
e queste due non hanno.

## Conclusione

Nessuna delle due piste dà un miglioramento pronto per la produzione.
Entrambe erano ipotesi motivate e valeva la pena verificarle con
disciplina (specialmente dato che l'ensemble era segnato "oro") - il
risultato onesto è che il nucleo attuale non ha un miglioramento
strutturale facile in attesa sul tavolo, oltre a TURTLE_SOUP_CHOCH
(vedi nota precedente).

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - CISD_TRUE (versione vera, negativa) e Censimento Completo (11-08)]] ·
[[Strategie/Turtle Soup]] ·
[[Strategie/Liq Sweep]]
