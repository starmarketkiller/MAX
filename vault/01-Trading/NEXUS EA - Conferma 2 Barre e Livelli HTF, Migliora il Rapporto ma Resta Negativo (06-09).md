---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, level-confluence, negativo, htf]
created: 2026-09-06
updated: 2026-09-06
---

# NEXUS EA — conferma a 2 barre + livelli H1/H4/D1: migliora il rapporto vincita/perdita ma resta negativo (06/09)

## Cosa è cambiato rispetto al primo test

Due modifiche insieme (stessa finestra 3 mesi, rischio 5%, per
confronto diretto col primo risultato):
1. Livelli **solo da H1/H4/D1** (prima M15/M30) — idea dell'utente
   "segnamo i livelli D1 H4 H1 e entriamo su M15 e M5".
2. **Conferma a 2 barre** prima di entrare (prima sparava al primo
   tocco) — fix per l'osservazione "il prezzo continua per 50+ pip
   prima di tornare, se torna".

## Risultato

| Metrica | Primo test (touch, M15/M30) | Ora (conferma 2, H1/H4/D1) |
|---|---|---|
| Trade | 424 | 295 |
| Profit factor | 0.89 | 0.83 |
| Net profit | -$646.14 | -$837.33 |
| Win rate | 34.0% | 35.3% (BUY) / 35.0% (SELL) |
| Max DD equity | $1067 | $1163 |

**Il netto è peggiorato**, non migliorato — nonostante meno trade e un
win rate leggermente più alto. La causa: aspettare la conferma
significa entrare più tardi, quindi quando va male perde di più
rispetto a prima in proporzione.

## Ma il dettaglio è più interessante del numero finale

| | Valore |
|---|---|
| Vincita media | +$32.33 |
| Perdita media | -$27.28 |
| Durata media vincite | 3.9h |
| Durata media perdite | 2.5h |

Il **rapporto rischio/rendimento è ora sano** (vincita media > perdita
media, vincite tenute più a lungo delle perdite — esattamente il
comportamento "taglia le perdite, lascia correre i vincenti" che
manca a molte altre strategie testate oggi). Il problema non è più la
gestione del trade, è che il **win rate (35%) resta sotto la soglia
di pareggio** (~45.7%, dato il rapporto vincita/perdita attuale).

BUY e SELL restano entrambi negativi e vicini (35.3%/35.0% WR,
net -$1081/-$582) — conferma ulteriore che non è un problema di
esposizione al trend, è il trigger stesso che non seleziona abbastanza
bene i punti di ingresso.

## Interpretazione

La conferma a 2 barre ha risolto il sintomo che l'utente aveva
notato (entrare troppo presto su rotture che continuano) ma non la
causa di fondo: il tocco di un livello H1/H4/D1, anche confermato per
2 barre, non è di per sé un segnale con abbastanza vantaggio
statistico. Il prossimo passo naturale è la **confluenza obbligatoria**
(`InpLevelConfRequireConfluence=true`, non ancora testata) — se un
livello dove 2+ delle tre TF alte coincidono seleziona meglio dei
livelli isolati, potrebbe alzare il win rate sopra soglia invece di
limitarsi a cambiare il rapporto vincita/perdita.

## Non ancora fatto

- `InpLevelConfRequireConfluence=true` non testato.
- Variante M5 (stessi livelli H1/H4/D1, esecuzione M5) in coda,
  risultato non ancora arrivato al momento di scrivere questa nota.
- Non provato ad aumentare la soglia di conferma oltre 2 barre.

## Collegamenti
[[NEXUS EA - LEVEL_CONFLUENCE Primo Risultato Vero, Negativo su Entrambi i Lati (06-09)]] · [[NEXUS EA - LEVEL_CONFLUENCE 3 Anni Conferma il Negativo (06-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
