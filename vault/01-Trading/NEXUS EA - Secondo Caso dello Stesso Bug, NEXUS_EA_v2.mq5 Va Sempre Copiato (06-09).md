---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, bug, p0, infrastruttura, metodo]
created: 2026-09-06
updated: 2026-09-06
---

# NEXUS EA — secondo caso dello stesso bug in un giorno, NEXUS_EA_v2.mq5 va sempre copiato dopo ogni edit (06/09)

## Perché

Costruita LEVEL_CONFLUENCE (merge PIVOT_WICK/STRUCT_REACT/MALAYSIAN_SNR):
zero trade su un test di 3 mesi ad alto rischio, nonostante input
echeggiati correttamente (selector 50, flag true). Investigazione
lunga (diagnostica passo-passo: entry della funzione, gate di barra,
scansione pivot) prima di trovare la causa.

## La causa — identica a quella di oggi pomeriggio, stesso errore ripetuto

Gli Include (`NXS_*.mqh`) sono giunzionati al repo git — ogni modifica
è immediatamente visibile a entrambi i terminali. **`NEXUS_EA_v2.mq5`
NO** — richiede copia manuale dopo ogni edit. La riga che collega
`NXS_Strat_LevelConfluence()` al ciclo di raccolta segnali era stata
aggiunta SOLO nel repo git, mai copiata nei terminali — il binario
compilato non conteneva quella chiamata, quindi la funzione non
veniva MAI invocata (confermato con un print incondizionato alla
primissima riga della funzione: zero output in tutto il test).

**Questo è lo stesso identico bug già trovato e "risolto" oggi
pomeriggio** (vedi
[[NEXUS EA - Il Filtro Sessione Era su un Percorso di Esecuzione Diverso (04-09)]],
addendum 05/09) per `InpProfileOverlapOnly`. È ricapitato perché la
correzione di stamattina non è diventata un'abitudine automatica —
mi sono ricordato di copiare l'ex5 compilato, ma non il sorgente
`.mq5` modificato prima di compilare, perché mentalmente ho trattato
"aggiungere una strategia nuova" come diverso da "editare un file
esistente", quando in realtà `NEXUS_EA_v2.mq5` è comunque il file che
ho editato per il wiring.

## Come è stata isolata (metodo, utile per il prossimo caso)

1. Verificato input echeggiati nel report → corretti, non è un
   problema di configurazione.
2. Print incondizionato alla prima riga di `NXS_Strat_LevelConfluence()`
   → zero output → la funzione non viene mai chiamata.
3. Print incondizionato alla prima riga di `NXS_CollectRaw()` (che
   contiene la chiamata) → **zero output anche qui**, nonostante
   questa funzione sia chiamata da ogni singolo test di oggi senza
   eccezioni → il sospetto si sposta dal mio codice nuovo
   all'infrastruttura di compilazione/copia.
4. `grep` diretto della stringa di diagnostica nel `.mq5` del
   terminale live → **assente**, mentre presente nel repo git →
   causa confermata in 10 secondi.

**Lezione di metodo**: quando un print incondizionato alla primissima
riga di una funzione non produce output, il sospetto va SUBITO
all'infrastruttura di build (file giusto compilato? copiato?), non
alla logica della funzione — avrebbe risparmiato ~40 minuti di
diagnostica a cascata (gate di barra, scansione pivot, tolleranze)
per un problema che non era mai lì.

## Regola operativa (da seguire sempre, non solo quando ci si ricorda)

Dopo QUALUNQUE modifica a `NEXUS_EA_v2.mq5` (non solo gli Include):
1. Copiare il file in ENTRAMBI i terminali PRIMA di compilare.
2. Compilare via MetaEditor sul terminale "live".
3. Copiare l'`.ex5` risultante nel terminale Tester.
4. Solo allora lanciare il test.

Saltare il passo 1 produce un fallimento silenzioso indistinguibile
da "la strategia non genera segnali" — identico nell'aspetto (zero
trade, nessun errore) ma con causa completamente diversa.

## Risultato pratico

Una volta corretto: pivot confermati regolarmente sui log diagnostici
(isHiPivot/isLoPivot true a intervalli regolari, come atteso). Test
reali rilanciati dopo la pulizia del codice diagnostico.

## Collegamenti
[[NEXUS EA - Il Filtro Sessione Era su un Percorso di Esecuzione Diverso (04-09)]] · [[NEXUS EA - Terzo Cancello Silenzioso Trovato su 7 Strategie, Audit Proattivo (05-09)]] · [[MOC - Trading]]
