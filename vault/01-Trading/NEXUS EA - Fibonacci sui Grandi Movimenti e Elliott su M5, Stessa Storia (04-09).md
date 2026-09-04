---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, fibonacci, elliott, m5, analisi-csv]
created: 2026-09-04
updated: 2026-09-04
---

# NEXUS EA — Fibonacci sui grandi movimenti storici ed Elliott su M5: stessa storia (04/09)

## Perché

Due richieste dell'utente: (1) provare Fibonacci "all'indietro nel
tempo" — non solo il ritracciamento immediato di un leg, ma i livelli
dei movimenti più grandi della storia, verificati contro tutto il
resto della storia successiva; (2) ripetere il test Elliott su M5 (M1
non disponibile — dati Dukascopy in locale coprono solo fino a M5,
2021-2026, 224683 barre) e cercare quali "forme" di sequenza si
ripetono di più.

## Fibonacci sui 25 movimenti più grandi (2019-2026)

Presi i 25 leg più ampi di tutta la storia M30 (es. 5451→4498,
952 punti), calcolati i loro livelli Fibonacci (38.2/50/61.8/78.6%),
verificato l'esito di ognuno contro tutta la storia successiva:

| Esito | % |
|---|---|
| Sweppato | **63.0%** |
| Rispettato | 34.0% |
| Rotto | 0.0% |
| Mai più toccato | 3.0% |

⚠️ **Cautela metodologica**: sono i 25 movimenti più grandi di 7 anni —
i loro livelli finiscono spesso dentro un range già attraversato molte
volte, quindi è quasi garantito che vengano ritoccati prima o poi
(0% "rotto" lo conferma). Il 97% di reazione non è una prova forte di
precisione del livello, quanto del fatto che il prezzo ha avuto tempo
di tornarci. Il dato più informativo è la **prevalenza dello sweep
(63%) sul rispetto pulito (34%)** — anche sui livelli grandi, il
comportamento dominante è il liquidity grab, non il rimbalzo netto.

## Elliott su M5 — quinto timeframe, stessa conferma

| TF | Impulsi validi | Correzione profonda dopo |
|---|---|---|
| M30/H1/H4/D1 (visti prima) | 7.2-10.9% | 73.7-77.8% |
| **M5** | **6.6%** | **76.9%** |

Cinque timeframe su cinque, stesso risultato. Non un artefatto di
risoluzione.

## La "forma" che si ripete di più (M5, non Elliott)

Per ogni sequenza di 4 gambe consecutive, classificata la dimensione
di onda2/3/4 relativa a onda1 (piccola/media/grande):

| Forma | % |
|---|---|
| **Grande-Grande-Grande** (ogni onda più grande della precedente) | **26.4%** |
| Media-Grande-Grande | 9.0% |
| Media-Media-Media | 7.0% |

La forma dominante è un'**espansione continua**, non l'alternanza
impulso-correzione-impulso che la teoria di Elliott descrive. Coerente
con tutti i risultati di oggi: GOLD in questo campione si muove più
per accelerazione/momentum che per un ritmo ciclico ordinato.

## Non ancora fatto

- M1 non disponibile in locale — richiederebbe scaricare dati a
  granularità più fine, non fatto.
- I 25 movimenti più grandi si sovrappongono nel tempo/prezzo — non
  isolato un sottoinsieme indipendente per un test più pulito.
- Nessuna delle scoperte di questa nota è stata tradotta in una regola
  testabile su MT5.

## Collegamenti
[[NEXUS EA - Perché Pochi Trade, Analisi CSV Vera su ADX_RSI e BOLLINGER (04-09)]] ·
[[MOC - Trading]]

## Addendum — confluenza multi-timeframe, giorno della settimana, persistenza (04-05/09)

Su richiesta dell'utente ("trovi pattern di qualsiasi tipo"), tre
controlli aggiuntivi.

**Giorno della settimana** (punti di swing M30): distribuzione piatta,
nessun segnale forte (Mar/Mer 21.9%, Ven 16.8%, weekend quasi zero
come atteso).

**Persistenza higher-highs/lower-lows**: decadimento quasi geometrico
(46.8% si ferma dopo 1 streak, poi ~50-57% di continuazione a ogni
passo) — vicino a quanto ci si aspetterebbe dal caso, nessun "hot
hand" chiaro.

**Confluenza multi-timeframe — il risultato più forte**: vicino a un
vero pivot D1 (116 nella storia), la densità di livelli M30 (entro
0.5×ATR) è **75.1 in media, contro 24.5 vicino a un prezzo casuale
nello stesso range — 3.06× più alta**. I punti dove il mercato inverte
sul timeframe grande coincidono realmente con l'accumulo di struttura
sui timeframe piccoli, non per caso. Probabilmente l'ingrediente più
solido trovato in tutta questa indagine insieme alla sessione oraria
12-16 UTC.

### Non ancora fatto
- Non tradotto in una regola testabile (es. "entra solo dove
  confluenza M30 alta E sessione Overlap E livello esteso").
- Tolleranza di confluenza (0.5×ATR) non testata con altri valori.
