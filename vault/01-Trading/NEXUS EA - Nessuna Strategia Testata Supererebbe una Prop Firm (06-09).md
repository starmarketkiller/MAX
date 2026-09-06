---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, prop-firm, drawdown, consistency, valutazione-strategica]
created: 2026-09-06
updated: 2026-09-06
---

# NEXUS EA — nessuna strategia testata oggi supererebbe una prop firm (06/09)

## La domanda

L'utente: "riuscirei mai a passare una prop firm con queste strategie? Io
non penso" — verificato retroattivamente su tutte le curve di balance
già generate oggi, senza rilanciare nulla (script `propfirm_metrics.py`).

## Metodo

Per ogni test: drawdown massimo picco-valle sul balance, P&L per
giornata di trading, serie massima di giorni consecutivi in perdita,
quante volte una singola giornata ha superato una perdita del 5%
(soglia giornaliera tipica stile FTMO), e se il drawdown massimo ha
superato il 10% (soglia totale tipica). Soglie illustrative — variano
per firm, ma sono rappresentative dell'ordine di grandezza standard.

## Risultato — tutte le 8 strategie controllate falliscono su ENTRAMBE le regole

| Strategia | Net (3 anni) | Max DD | Giorno peggiore | Serie perdite | Violazioni -5%/giorno |
|---|---|---|---|---|---|
| SAR | +439% | 34.4% | -5.9% | 5gg | 12 |
| EMA_PULLBACK | +68% | 20.5% | -8.8% | 5gg | 4 |
| **FVG_CONT** | +265% | **15.5%** | -5.0% | 4gg | **1** |
| ADX_RSI | +168% | 21.9% | -6.7% | 4gg | 9 |
| MACD | +198% | 33.9% | -6.7% | 7gg | 10 |
| BOLLINGER | +35% | 21.1% | -9.4% | 2gg | 2 |
| STRUCT_REACT | +156% | 31.5% | -8.6% | 5gg | 12 |
| LEVEL_CONFLUENCE (chiusa) | -91% | 91.4% | -15.0% | 10gg | 41 |

**Nessuna eccezione.** Anche la migliore in assoluto per questo scopo
(FVG_CONT — non a caso anche l'unica che batte il buy&hold in valore
assoluto) ha un DD massimo di 15.5%, il 50% oltre la soglia tipica del
10%, e ha comunque violato la soglia giornaliera una volta in 3 anni.

## Perché succede — non è un dettaglio, è strutturale

Questi risultati arrivano da un'ottimizzazione per **rendimento netto
totale su 3 anni**, non per drawdown vincolato. Le due cose non sono
la stessa cosa e in parte sono in tensione:
- Rendimenti enormi (SAR +439%) vengono da **rischio composto nel
  tempo** — il lotto cresce col balance, quindi i trade più tardivi
  (quando il conto è già cresciuto) muovono percentuali di conto molto
  più grandi in valore assoluto, gonfiando sia i guadagni che i
  drawdown in modo non lineare.
- Il win rate basso (28-38% per la maggior parte) con target ampi
  produce inevitabilmente serie di 4-7 giornate consecutive in
  perdita — statisticamente normali su un orizzonte di anni, ma
  letali dentro una finestra di valutazione di 30 giorni con un limite
  di drawdown fisso.
- L'ESL interno (5% di perdita FLOTTANTE per-trade) non impedisce che
  una singola GIORNATA (più trade, o un trade che chiude in perdita
  vicino al limite ESL) superi il 5% di perdita REALIZZATA — sono due
  soglie diverse che oggi non sono collegate tra loro.

## Cosa servirebbe (non ancora fatto)

Un obiettivo di ottimizzazione esplicitamente diverso, non solo "più
test sullo stesso PF":
1. **Rischio per trade drasticamente ridotto e fisso** (non
   percentuale composta) — taglia sia i guadagni sia (più che
   proporzionalmente) i drawdown.
2. **Limite di perdita giornaliera reale**, non solo per-trade — un
   gate che blocca nuovi ingressi per il resto della giornata se la
   perdita realizzata + flottante supera una soglia assoluta.
3. **Selezione delle strategie per Calmar/drawdown-adjusted return**,
   non per PF o Sharpe puro — FVG_CONT è già la più vicina per questo
   criterio, punto di partenza naturale per qualunque tentativo
   prop-firm-oriented.
4. Testare esplicitamente su una finestra di valutazione corta (30-60
   giorni, come una vera challenge), non solo sull'aggregato di 3 anni
   — il rischio di sequenza (quale sotto-finestra ti capita) è ignorato
   finora.

Nessuna di queste modifiche è stata ancora implementata — è un
obiettivo di design diverso da quello inseguito finora nella sessione
(rendimento totale), da affrontare come iniziativa separata se
l'utente vuole procedere in questa direzione.

## Collegamenti
[[NEXUS EA - Il Vero Benchmark e Buy&Hold, Quasi Tutto Oggi lo Perde (05-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
