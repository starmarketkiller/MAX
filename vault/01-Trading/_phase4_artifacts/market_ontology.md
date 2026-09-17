# NEXUS Market Ontology v1

Definizioni formali e separate per ogni concetto usato dalla nuova pipeline di ricerca:

```
MARKET STATE -> EVENT -> SETUP -> TRIGGER -> ENTRY -> INVALIDATION -> OUTCOME -> PROBABILITY -> EDGE -> STRATEGY
```

Regola generale: questi termini NON sono sinonimi intercambiabili. Ogni report/schema futuro deve usare il termine esatto per il concetto esatto. Dove il codice NEXUS attuale confonde due concetti (es. "strategy" che in realtà è solo un "setup" con un trigger fissato), va segnalato esplicitamente nell'audit semantico, non silenziosamente accettato.

---

## Market State

**Definizione.** Descrizione quantitativa, causale, dello stato del mercato in un dato istante — trend, volatilità, struttura, momentum, liquidità, comportamento statistico, tempo — calcolata SOLO da informazione disponibile fino a quell'istante incluso.

**Observation point.** Chiusura barra (per feature multi-barra) o tick (per feature intra-barra come spread/attività). Deve essere sempre dichiarato esplicitamente per ogni feature (vedi Market State Vector v1).

**Informazioni consentite.** Prezzo, volume/tick-volume, tempo, e derivati causali di questi fino all'istante di osservazione incluso.

**Informazioni future vietate.** Qualunque valore calcolato usando barre non ancora chiuse al momento dell'osservazione, valori "ripuliti"/ricalcolati con look-ahead (es. swing high/low confermato solo retrospettivamente), o percentili calcolati su una finestra che include il campione stesso in modo non causale.

**Rapporto con altri elementi.** Il Market State è il CONTESTO in cui un Event viene osservato; un Event non ha significato isolato dal Market State in cui accade (lo stesso evento — es. sweep — può essere edge in un contesto e rumore in un altro).

**Esempio NEXUS.** `g_atr` (ATR corrente), pendenza EMA, posizione nel range N-barre — tutte quantità già calcolate nell'EA ma finora usate implicitamente dentro le singole strategie, mai esposte come vettore di stato indipendente e riusabile.

---

## Context

**Definizione.** Il sottoinsieme del Market State rilevante per un particolare Event/Setup — non tutto lo stato di mercato è rilevante per ogni domanda; il Context è la proiezione pertinente (es. "regime di trend" per un setup di pullback, "regime di volatilità" per un breakout).

**Observation point.** Stesso istante dell'Event a cui si applica.

**Informazioni consentite.** Sottoinsieme dichiarato del Market State Vector.

**Informazioni future vietate.** Le stesse del Market State; inoltre è vietato scegliere a posteriori quale sottoinsieme di feature costituisce il "Context" in base al risultato osservato (data-mining del contesto).

**Rapporto con altri elementi.** Context ⊂ Market State. Setup = Context + Event + Preconditions.

**Esempio NEXUS.** "UPTREND" come contesto per un setup di sweep-and-reclaim: definito da feature di trend del Market State Vector, dichiarato PRIMA di osservare l'outcome del sweep.

---

## Event

**Definizione.** Un accadimento di mercato discreto, con timestamp preciso, rilevato da un detector causale — indipendente da qualunque strategia che potrebbe poi agire su di esso. Esempi: breakout, failed breakout, sweep, reclaim, displacement, compression release, retest, rejection.

**Observation point.** Il momento esatto (barra o tick) in cui il detector conferma l'evento.

**Informazioni consentite.** Prezzo/struttura fino all'observation point incluso.

**Informazioni future vietate.** Confermare un evento usando prezzo successivo all'observation point (es. classificare un breakout come "vero" solo perché poi ha continuato — quella è già Outcome, non Event).

**Rapporto con altri elementi.** Un Event esiste indipendentemente da qualunque Setup/Strategy. Più Setup diversi possono usare lo stesso Event Registry come input. Event + Context + Preconditions = Setup.

**Esempio NEXUS.** Il "breakout confermato" di VOLATILITY_BREAKOUT_CONFIRMED (true range barra segnale > 1.0×ATR oltre il range N=20) è un Event, oggi incorporato dentro una singola strategia invece di vivere nell'Event Registry condiviso.

---

## Setup

**Definizione.** Context + Event + Preconditions aggiuntive, SENZA ancora specificare il metodo di esecuzione (trigger/entry). Un Setup risponde alla domanda "in quale situazione di mercato mi interessa agire", non "come esattamente entro".

**Observation point.** Stesso dell'Event che lo compone, con il Context valutato allo stesso istante.

**Informazioni consentite.** Solo Context + Event + Preconditions dichiarate ex-ante.

**Informazioni future vietate.** Nessuna informazione oltre l'observation point del suo Event costitutivo.

**Rapporto con altri elementi.** Un singolo Setup può avere PIÙ Trigger/Entry possibili (close confirmation, market immediato, retest, limit) senza diventare per questo idee di mercato diverse — sono variazioni esecutive dello stesso Setup, da validare separatamente ma senza moltiplicare artificialmente il conteggio di "idee distinte".

**Esempio NEXUS.** `UPTREND + SWEEP_LOW + RECLAIM` è un Setup. Oggi nel codice NEXUS questo genere di combinazione è spesso incorporata rigidamente dentro un'unica funzione `NXS_Strat_*` con un solo trigger, invece di essere un Setup riusabile con trigger intercambiabili.

---

## Trigger

**Definizione.** La condizione precisa che, dato un Setup già attivo, determina il momento esatto in cui l'azione (Entry) viene generata.

**Observation point.** Barra o tick in cui la condizione trigger si verifica, successivo o coincidente con l'Event/Setup.

**Informazioni consentite.** Prezzo/struttura fino all'observation point del trigger.

**Informazioni future vietate.** Le stesse regole generali; inoltre non è ammesso scegliere il trigger a posteriori scegliendo quello che avrebbe dato il miglior risultato storico per lo stesso Setup (quello è ottimizzazione, non definizione).

**Rapporto con altri elementi.** Trigger presuppone un Setup già attivo. Trigger + Setup -> Signal.

**Esempio NEXUS.** "Chiusura barra oltre il range" (VOLATILITY_BREAKOUT_CONFIRMED) è un trigger; "prezzo raggiunge il livello in tempo reale" sarebbe un trigger diverso sullo stesso Setup.

---

## Signal

**Definizione.** L'output discreto generato quando un Trigger si attiva su un Setup: una proposta di trade con direzione, ma non ancora eseguita.

**Observation point.** Istante del Trigger.

**Rapporto con altri elementi.** Signal = Setup + Trigger, valutato. Un Signal genera un Entry solo se passa i filtri di esecuzione (slot di esposizione, selettori, ecc — già presenti in NEXUS come `InpMaxConcurrent`/`InpMaxPerDirTF`/`NXS_SelectorAllows`).

**Esempio NEXUS.** `SNXSSignal` (struct MQL5) è quasi esattamente questo concetto, ma nel codice attuale porta già dentro di sé entry/SL/TP invece di essere un oggetto "puro" pre-esecuzione — motivo per cui SIGNAL PRICE, REFERENCE PRICE e ORDER/FILL PRICE vanno tenuti concettualmente separati anche quando abitano lo stesso struct.

---

## Entry

**Definizione.** Il prezzo/istante teorico a cui la ricerca (Python o spec congelata) assume che la posizione venga aperta, usato come riferimento per calcolare rischio (R), SL, TP.

**Observation point.** Definito dalla spec del Setup/Trigger (es. "signal-bar close" per FROZEN_SIGNAL_SPEC_V1).

**Rapporto con altri elementi.** Entry ≠ Fill. Un Entry può coincidere con il Fill reale solo se l'esecuzione avviene esattamente a quel prezzo; altrimenti la differenza è slippage di esecuzione, non un errore di specifica — MA se il codice usa un prezzo DIVERSO da quello dichiarato come Entry nella spec per calcolare SL/TP, quello È un errore di specifica (esattamente il bug corretto in VOLATILITY_BREAKOUT_CONFIRMED nella correzione Phase 3).

**Esempio NEXUS.** `c1` (chiusura barra segnale) per VOLATILITY_BREAKOUT_CONFIRMED dopo la correzione.

---

## Fill

**Definizione.** Il prezzo REALE a cui l'ordine viene eseguito dal broker/tester.

**Observation point.** Istante di invio ordine.

**Rapporto con altri elementi.** In NEXUS, Fill = sempre `SymbolInfoDouble(sym, SYMBOL_ASK/BID)` al momento dell'invio (`NXS_DoBuy`/`NXS_DoSell`), per costruzione del motore, indipendentemente da qualunque Entry teorico calcolato a monte. Fill − Entry = slippage di esecuzione ordinario (non un bug, salvo che sia anomalmente grande).

**Esempio NEXUS.** Vedi correzione Phase 3, punto 1: distinzione tracciata esplicitamente nel codice `NXS_Globals.mqh`.

---

## Invalidation

**Definizione.** La condizione che dichiara falsificata l'ipotesi del Setup — non necessariamente coincidente con lo Stop-Loss operativo, anche se spesso i due si sovrappongono.

**Observation point.** Qualunque istante successivo all'Entry in cui la condizione si verifica.

**Rapporto con altri elementi.** Invalidation è concettualmente PRIMA di Stop: uno Stop è l'implementazione operativa (prezzo fisso) di un'idea di Invalidation (es. "il livello ha ceduto"). I due possono divergere (es. invalidation strutturale raggiunta prima del prezzo di stop).

**Esempio NEXUS.** Oggi quasi tutte le strategie NEXUS collassano Invalidation e Stop nello stesso prezzo fisso — accettabile come implementazione ma da NON confondere concettualmente quando si definisce un nuovo Setup nell'ontologia.

---

## Stop

**Definizione.** Il prezzo operativo che, se toccato, chiude la posizione in perdita.

**Observation point.** Calcolato all'Entry, monitorato tick-by-tick fino a modifica/chiusura.

**Rapporto con altri elementi.** Stop è l'implementazione prezzo-based di Invalidation (vedi sopra) e la base per il calcolo di R = |Entry − Stop|.

**Esempio NEXUS.** `s.slPrice` nello struct `SNXSSignal`.

---

## Target

**Definizione.** Il prezzo operativo che, se toccato, chiude la posizione in profitto per uscita pianificata (diverso da un'uscita discrezionale/trailing).

**Rapporto con altri elementi.** NON deve essere scelto prima di aver osservato la Outcome Surface (sezione 6) — scegliere il target guardando quale TP avrebbe massimizzato il risultato storico è overfitting, non ricerca.

**Esempio NEXUS.** `s.tpPrice`, oggi quasi sempre fissato a 1R per convenzione — la nuova pipeline richiede di mappare la distribuzione naturale (P(+0.25R)...P(+3R), MFE/MAE) PRIMA di fissare un target per un nuovo Setup.

---

## Outcome

**Definizione.** Il risultato osservato di un trade/Setup rispetto a soglie multiple, non solo win/loss binario: P(raggiungere X·R prima di −1R) per vari X, MFE, MAE, tempo-a-target, tempo-a-invalidazione.

**Observation point.** Durante tutta la vita del trade/finestra di osservazione, non solo alla chiusura.

**Rapporto con altri elementi.** Outcome alimenta Probability, che a sua volta alimenta Edge.

---

## Probability

**Definizione.** Una stima statistica di un Outcome, MAI un singolo rapporto vinte/totali senza contesto. Deve sempre includere: n, wins, losses, censored, observed probability, confidence interval, posterior Bayesiano (Beta-Binomial), effective sample size se applicabile.

**Rapporto con altri elementi.** 7/10 ≠ 700/1000 anche se entrambi "70%" — l'incertezza è parte della Probability, non un dettaglio a parte.

---

## Edge

**Definizione.** Miglioramento condizionale rispetto a un baseline appropriato e comparabile, MAI un risultato assoluto positivo isolato.

ΔP = P(Target | Setup, State) − P(Target | Baseline, State comparabile)
ΔE = E[R | Setup, State] − E[R | Baseline, State comparabile]

**Rapporto con altri elementi.** Un Setup con risultato assoluto positivo ma ΔP≤0 e ΔE≤0 rispetto al baseline NON ha edge dimostrato — ha solo un risultato positivo, che può essere spiegato dal comportamento generico del mercato in quello State.

---

## Strategy

**Definizione.** Un pacchetto operativo completo e implementato: Setup + Trigger + Entry + Invalidation/Stop + Target + Exit + Risk Model + Execution Model, pronto per essere eseguito (live o in backtest). È il livello PIÙ ALTO della gerarchia, non il punto di partenza della ricerca.

**Rapporto con altri elementi.** Una Strategy è la composizione finale di tutti i concetti sopra. Molte cose oggi chiamate "strategy" in NEXUS sono in realtà solo Setup o Event con un trigger fissato arbitrariamente — da segnalare nell'audit semantico (sezione 1) invece di accettare la nomenclatura esistente come vera.

---

## Trade Management

**Definizione.** Le regole che modificano una posizione APERTA nel tempo (trailing stop, breakeven, partial close, time-based exit) — logicamente separate da Entry/Stop/Target iniziali.

**Rapporto con altri elementi.** Trade Management agisce dopo l'Entry, può modificare Stop/Target originali; deve essere validato separatamente dal Setup stesso (un buon Setup con cattivo trade management può sembrare privo di edge, e viceversa).

---

## Risk Model

**Definizione.** Le regole di dimensionamento posizione e di esposizione aggregata (lot sizing, max posizioni concorrenti, max per direzione/TF, drawdown limits) — indipendenti dal merito del Setup.

**Rapporto con altri elementi.** Un Risk Model restrittivo (es. `InpMaxConcurrent=4`) può impedire a Signal validi di diventare Entry — questo è già stato osservato empiricamente nella correzione Phase 3 (la cascata su slot di esposizione che ha amplificato il cambio di conteggio trade in parity dopo il fix di entry semantics).

---

## Execution Model

**Definizione.** Come un Entry teorico diventa un Fill reale: tipo di ordine, prezzo di invio, slippage, latenza, modello di tick (sintetico vs reale) usato in test.

**Rapporto con altri elementi.** Execution Model spiega la differenza Entry-vs-Fill; nella correzione Phase 3 è stato dimostrato che il modello di tick (MT5 Model=1 sintetico vs Model=4 reale) cambia MATERIALMENTE quanto un errore di Entry-reference si propaga nei risultati di parity — l'Execution Model non è un dettaglio tecnico neutro, è parte integrante di cosa un test sta davvero misurando.
