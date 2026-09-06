---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, level-confluence, bug, negativo]
created: 2026-09-06
updated: 2026-09-06
---

# NEXUS EA — LEVEL_CONFLUENCE primo risultato vero: negativo su entrambi i lati (06/09)

## Perché

Dopo aver risolto **due bug distinti** che davano zero trade
(wiring mancante in `NEXUS_EA_v2.mq5`, poi un guardiano multi-TF
mancante che faceva valutare la strategia su ogni passaggio
H1/H4/D1/M30 invece che solo M15) e **un terzo** (`NXS_StrategyKnown()`
in `NXS_StrategyRegistry.mqh`, una whitelist hardcoded dentro
`NXS_OpenTrade()` che rifiutava ogni apertura con
"unknown_strategy") — vedi
[[NEXUS EA - Secondo Caso dello Stesso Bug, NEXUS_EA_v2.mq5 Va Sempre Copiato (06-09)]] —
finalmente un test vero: GOLD M15, 3 mesi (2026.06.05-2026.09.05),
selettore vero 50, simmetrica BUY+SELL, rischio 5%/trade.

## Risultato

| Metrica | Valore |
|---|---|
| Trade | 424 (260 BUY, 153 SELL) |
| Profit factor | **0.89** (negativo) |
| Net profit | **-$646.14** |
| Sharpe | -2.52 |
| Max DD equity | $1067.16 |
| Motivo chiusura | 238 SL (58%), 111 TP (27%), 9 drawdown-protection, resto altro |
| Durata media trade | 3.3h (min 0, max 55.8h) |

## Il test bidirezionale (il punto centrale della richiesta originale)

| | BUY | SELL |
|---|---|---|
| Trade | 260 | 153 |
| Net | -$595.78 | -$327.42 |
| Win rate | 35.8% | 32.7% |

**Entrambi i lati sono negativi, con win rate e magnitudine simili.**
Questo è un risultato diverso (e in un certo senso più onesto) di
quanto visto su MACD/ADX_RSI/BOLLINGER/STRUCT_REACT, dove il pattern
era "BUY va bene per il trend, SELL è rumore o rotto". Qui **nessuno
dei due lati ha edge**, non solo uno — il che esclude "sto solo
seguendo il trend per sbaglio" come spiegazione, ma non prova
nemmeno un edge reale: il trigger "touch" grezzo (qualunque tocco
entro tolleranza, senza richiedere conferma di chiusura o
confluenza) sembra semplicemente troppo permissivo e rumoroso.

## Limite dell'analisi — non ancora risolto

Non è stato possibile scomporre il risultato per tipo di trigger
(touch/sweep) o per confluenza D1, perché il commento salvato sul
deal MT5 è il formato generico
`NEXUS_v2.50|LEVEL_CONFLUENCE|score|PERIOD_M15`, non la stringa
`s.reason` interna (che conteneva "touch"/"sweep"/"D1conf"). Servirebbe
collegare `NXS_LogTradeCSV` o un log dedicato per recuperare questo
dettaglio — non fatto oggi per limiti di tempo.

**Osservazione indiretta rilevante**: usando `InpLevelConfRequireConfluence=false`
(nessun filtro), il test ha comunque prodotto 424 trade — ma non è
noto quanti fossero effettivamente in confluenza col pivot D1 vs no.
Prima di testare `InpLevelConfRequireConfluence=true` (l'idea
originale dell'utente: restringere solo ai punti di confluenza),
va verificato che la confluenza D1 non sia troppo rara nella finestra
di 3 mesi (i pivot D1 richiedono ~11 giorni di storico per il primo
pivot con `InpPivotWickLookback=5`) — rischio di andare a zero trade
di nuovo per motivi statistici, non per un bug.

## Non ancora fatto

- Trigger touch/sweep e confluenza non scomposti (vedi sopra).
- `InpLevelConfRequireConfluence=true` non ancora testato.
- Buy&hold non calcolato per questa finestra di 3 mesi specifica
  (il confronto costruito ieri usa una finestra diversa, 01/09/2023-
  14/08/2026) — non direttamente comparabile, andrebbe rifatto sulla
  stessa finestra se serve un confronto.
- Test sui 3 anni completi in coda, non ancora esaminato.

## Collegamenti
[[NEXUS EA - Secondo Caso dello Stesso Bug, NEXUS_EA_v2.mq5 Va Sempre Copiato (06-09)]] · [[NEXUS EA - Il Vero Benchmark e Buy&Hold, Quasi Tutto Oggi lo Perde (05-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
