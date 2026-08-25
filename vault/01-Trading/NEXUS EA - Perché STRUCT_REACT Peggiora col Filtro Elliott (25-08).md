---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, struct-react, elliott-wave, diagnosi]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — Perché STRUCT_REACT è l'unica a peggiorare col filtro Elliott (25/08)

## Perché

Unica eccezione nella validazione del filtro Elliott multi-timeframe
(21/25 migliorano, vedi [[NEXUS EA - Filtro Elliott Wave Multi-Timeframe, il nuovo ingrediente universale (25-08)]]):
STRUCT_REACT peggiora (2.65→2.28). Coerente col pattern già visto ieri
(resiste a trailing e Fibonacci esaurimento-reverse), ma finora mai
capito nel dettaglio — indagine diretta sui trade rimossi dal filtro.

## Diagnosi: il filtro rimuove esattamente i suoi trade migliori

Scomposizione dei 50 trade BUY-only originali: 41 restano dopo il
filtro (PF2.28), **9 vengono rimossi — e quei 9 hanno PF5.32** (6
vincite da +3.0R, 3 perdite da -1.0R, sumR=+14.2). Il filtro non sta
scartando rumore, sta scartando la parte più redditizia del campione.

Guardando le date dei 9 trade rimossi: si concentrano in blocchi
ravvicinati (es. 3 trade consecutivi 30/04-02/05/2024, 2 il 27/10/2025)
— segno che STRUCT_REACT entra ripetutamente durante fasi di trend
sostenuto, dove il prezzo forma naturalmente sequenze di pivot che il
contatore Elliott classifica come "impulso a 5 onde appena concluso"
molto più spesso che in condizioni normali (i trend forti generano
gambe interne che soddisfano ripetutamente le regole di un impulso su
scale annidate — la natura frattale del mercato, la stessa che rende
il filtro utile altrove, qui gioca contro).

## Perché STRUCT_REACT è diversa dalle altre 24

STRUCT_REACT entra in reazione a un livello strutturale (supporto/
resistenza/liquidità) — il suo trigger è già una forma di filtro di
qualità basato sulla struttura del prezzo, concettualmente vicino a
quello che l'Elliott cerca di misurare (dove siamo nel movimento). Le
altre 24 strategie hanno trigger indipendenti dalla struttura d'onda
(incroci di medie, RSI, ADX, breakout di range) — per loro l'Elliott
aggiunge un'informazione NUOVA. Per STRUCT_REACT, l'Elliott misura
qualcosa di già in parte catturato dal segnale stesso, e quando i due
non sono perfettamente allineati (l'Elliott vede "esaurimento" dove
STRUCT_REACT vede "reazione valida da cavalcare"), il filtro toglie
segnale buono scambiandolo per rumore.

## Verdetto

**Confermato**: non è un caso isolato o rumore statistico, è un
meccanismo specifico e comprensibile — STRUCT_REACT non va combinata
col filtro Elliott, gli altri 24/25 casi restano il consiglio di
default. Nessuna azione correttiva necessaria: la tabella master già
non applica l'Elliott a STRUCT_REACT.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Filtro Elliott Wave Multi-Timeframe, il nuovo ingrediente universale (25-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
