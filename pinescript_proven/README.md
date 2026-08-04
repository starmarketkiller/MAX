# Pine Script — strategie esterne consolidate (non-NEXUS)

Cartella nuova, separata da `pinescript/`, su richiesta esplicita dell'utente
(31/07): **"tutte le strategie che abbiamo mettiamole da parte, dobbiamo
avere una nuova cartella con strategie esistenti che già vanno e provarle e
migliorarle"**.

## Cosa cambia rispetto a `pinescript/`

`pinescript/` resta dov'è (non cancellata, solo messa da parte) — conteneva
27 port fedeli delle strategie interne del portafoglio NEXUS (MQL5), molte
delle quali **mai validate indipendentemente** o **già confermate perdenti/
disattivate in produzione** (vedi `pinescript/README.md` e
`docs/audits/corpus/NEXUS_STRATEGY_FIDELITY_REPORT_01.md`). Fedeltà al
codice MQL5 lì significa fedeltà a una logica la cui efficacia reale non era
mai stata dimostrata prima di questa sessione.

Qui il criterio è diverso e più stringente: ogni strategia deve essere
**esterna a NEXUS, pubblicamente documentata, con una fonte primaria
citabile e (dove disponibile) un riscontro storico reale** — non una
rielaborazione, non un'interpretazione "corretta da audit" di un concetto
SMC/ICT, ma la formulazione originale di chi ha inventato/pubblicato la
strategia. L'obiettivo non è più "questo codice fa quello che dice
l'EA", è "questa è una strategia che ha già dimostrato di funzionare da
qualche parte, prima ancora di testarla qui".

## Regola di fonte (obbligatoria per ogni file)

Ogni script deve avere in testa: autore/origine, anno, fonte primaria
citabile (libro, paper, pubblicazione dell'autore stesso), e i parametri
ESATTI come pubblicati — non una variante "migliorata" a intuito. Se una
scelta implementativa si allontana dalla fonte (es. per adattarla a
XAUUSD/Pine), va dichiarata esplicitamente come tale, mai silenziata.

## Roadmap iniziale

| # | Strategia | Fonte primaria | Perché "già va" |
|---|---|---|---|
| 1 | Turtle Trading — Donchian Channel Breakout (System 1) | Richard Donchian (concetto); Richard Dennis & William Eckhardt, 1983 (sistema); regole pubblicate da Curtis Faith, *Way of the Turtle* (2007) | Track record storico reale e documentato: il gruppo delle "Turtles" originali generò circa 175 milioni $ di profitti aggregati in ~4 anni con queste regole esatte (Michael Covel, *The Complete TurtleTrader*) |
| 2 | Golden/Death Cross (SMA 50/200) | Uso istituzionale documentato da decenni, nessun singolo autore | Il filtro di trend più studiato e replicato nella letteratura tecnica |
| 3 | RSI-2 Mean Reversion | Larry Connors & Cesar Alvarez, *Short Term Trading Strategies That Work* (2008) | Regole pubblicate CON statistiche di backtest quantificate dagli stessi autori |
| 4 | MACD classico (12/26/9) | Gerald Appel, anni '70-'79 | Parametri originali dell'inventore, non una variante |
| 5 | Bollinger %B / Squeeze | John Bollinger, regole ufficiali pubblicate dall'autore | Fonte primaria diretta, non una terza interpretazione |
| 6 | ADX/DMI Directional System | J. Welles Wilder, *New Concepts in Technical Trading Systems* (1978) | Sistema originale del creatore dell'ADX stesso |

Si parte da #1 (Turtle/Donchian) — è quella con il riscontro storico più
forte e diretto. Le altre seguono una alla volta, stesso standard di
sourcing, stesso protocollo di test di `docs/testing/TRADINGVIEW_AGENT_PROMPT.md`
(segnale grezzo prima, poi un parametro alla volta solo se giustificato)
una volta pronte.

## Stato

_(aggiornato man mano che le strategie vengono aggiunte e testate)_

| File | Strategia | Timeframe | Stato |
|---|---|---|---|
| `TURTLE_DONCHIAN.pine` | Turtle System 1 (Donchian 20/10) | D1 | Pronta per il test — piramidazione e filtro "skip" della fonte originale omessi in questa v1, dichiarato in testa al file |
