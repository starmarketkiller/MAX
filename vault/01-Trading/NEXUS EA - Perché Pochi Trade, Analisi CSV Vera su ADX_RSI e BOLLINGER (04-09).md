---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, adx-rsi, bollinger, frequenza, analisi-csv]
created: 2026-09-04
updated: 2026-09-04
---

# NEXUS EA — Perché così pochi trade: analisi vera dei CSV su ADX_RSI e BOLLINGER (04/09)

## Perché questa nota

L'utente ha giustamente contestato che mi ero fermato ai numeri
aggregati (PF/WR/net) senza guardare i trade uno per uno né capire
meccanicamente cosa limita la frequenza (ADX_RSI: 51 trade/3 anni,
BOLLINGER BUY-only: 68 trade/3 anni — meno di 1/settimana per
entrambe). Questa nota corregge il tiro: date dei trade estratte dai
deal CSV reali, più una ricostruzione indipendente (Python, dati
Dukascopy M15 risampionati a D1) delle 3 condizioni del trigger
ADX_RSI per capire quanto sono davvero restrittive **prima** di
incolpare l'ultimo gate a valle.

⚠️ La ricostruzione Python è un'**approssimazione diagnostica**, non
il motore MQL5 reale (stessa cautela di sempre su proxy vs motore
vero) — serve a capire l'ordine di grandezza del problema, non è un
numero definitivo.

## ADX_RSI (D1): il trigger NON è il collo di bottiglia

Ricostruite ADX(14 Wilder)/RSI(14)/EMA(50) su GOLD D1 (Dukascopy M15
risampionato), periodo 2023-09→2026-08, 910 giorni con indicatori
pronti:

| Condizione | Giorni | % |
|---|---|---|
| ADX ≥ 20 | 566 | 62.2% |
| Setup completo (ADX+trend+RSI+prezzo, tutte insieme) | **318** | **34.9%** |

**Il trigger grezzo si forma su quasi 1 giorno su 3** — non è affatto
raro. Eppure il Tester reale ha prodotto solo 51 trade. La causa vera,
trovata leggendo le date apertura/chiusura dal deal CSV:

**Le posizioni restano aperte in media 15 giorni** (target 10×ATR +
breakeven a 1.5R, nessun limite di tempo), con diverse durate di
36-41 giorni. Sommando le durate: **762 giorni su 1089 (70% dell'intero
periodo) c'è già una posizione ADX_RSI aperta** — il gate "una
posizione per strategia" (già documentato più volte nel vault come
meccanismo esistente) blocca qualunque nuovo ingresso per il 70% del
tempo, indipendentemente da quante volte il setup si riformi.

**Conclusione onesta**: la bassa frequenza di ADX_RSI non è un
problema del trigger (che si forma spesso), è una conseguenza diretta
della gestione dell'uscita (target molto largo, tenuto per settimane).
Se si vuole più frequenza, la leva è l'uscita (target più vicino,
time-stop), non il trigger — ma questo cambierebbe anche il PF/payoff
attuale (6.25:1), da testare con cautela, un ingrediente alla volta.

## BOLLINGER H4 (BUY-only): qui è davvero il trigger a essere raro

Stessa verifica sui deal reali: posizioni aperte in media **29 ore**
(~1.2 giorni), coprono solo **7.7% del periodo totale** (2003 ore su
26160). Qui il gate "posizione aperta" NON è il collo di bottiglia —
il rientro in banda dopo un tocco è semplicemente un evento raro su
H4 (68 volte in ~2600 barre H4, un tocco+rientro ogni ~38 barre, circa
1 ogni 6 giorni). Meccanicamente diverso da ADX_RSI: qui la bassa
frequenza è davvero nel trigger, non nella gestione.

## Tabella di sintesi

| | ADX_RSI (D1) | BOLLINGER (H4, BUY-only) |
|---|---|---|
| Trade in 3 anni | 51 | 68 |
| Durata media posizione | 15 giorni | 29 ore |
| % tempo con posizione aperta | 70% | 7.7% |
| Collo di bottiglia reale | **Gestione (target largo, holding lungo)** | **Trigger (rientro in banda è raro su H4)** |

## Non ancora fatto

- Non verificato se un limite di durata (i molti "40-41 giorni"
  ricorrenti in ADX_RSI potrebbero indicare un cap nascosto non
  disattivato dai miei flag — `InpUseMaxHold=false` era impostato, ma
  la ricorrenza esatta di 40-41 giorni è sospetta, da controllare nel
  codice se esiste un altro limite non intercettato).
- Nessun test ancora fatto con uscita più stretta su ADX_RSI per
  vedere se la frequenza sale mantenendo un PF accettabile.
- La ricostruzione Python delle 3 condizioni ADX_RSI non è stata
  validata contro il vero calcolo MQL5 (stessa cautela proxy-vs-motore
  di sempre) — utile per capire l'ordine di grandezza, non un numero
  definitivo.

## Collegamenti
[[NEXUS EA - ADX_RSI D1 Confermata Positiva sul Vero MT5, BUY Domina (04-09)]] ·
[[NEXUS EA - BOLLINGER H4 Nuda, BUY Positivo SELL Negativo, Conferma Python (04-09)]] ·
[[MOC - Trading]]
