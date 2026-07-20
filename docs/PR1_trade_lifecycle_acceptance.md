# PR 1 — Trade Lifecycle Ledger: acceptance test (agente desktop)

Il branch `feature/trade-lifecycle-ledger` NON è compilato: questo ambiente non
ha MetaEditor. Prima di qualsiasi merge l'agente desktop deve:

## 0. Compilazione

1. `git fetch origin feature/trade-lifecycle-ledger && git checkout feature/trade-lifecycle-ledger`
2. Compilare `NEXUS_EA_v2.mq5` con MetaEditor (build 5833). **Zero errori attesi**;
   eventuali warning su funzioni non più usate (`_nxs_stats_dealR`,
   `_nxs_stats_dealHoldSec`, `NXS_FindPositionOpenTime`) sono accettabili.
3. NON toccare il terminale dello sweep (7F8E…): usare il terminale live o una
   terza installazione. Lo sweep continua con l'.ex5 della baseline `e6ce816`.

## Cosa verifica ogni test (Strategy Tester, visual o no, GOLD M15, pochi giorni)

Il riferimento è `NEXUS_trades.csv` (Common Files): righe `PARTIAL` e una sola
riga `CLOSE` per position, più il log `[NEXUS LEDGER]`.

### 1. One entry + one full exit
Run normale con 1 trade. Atteso: 1 `CLOSE` con pnl = pnl del deal OUT,
`lots` = volume di ingresso. Stats: 1 outcome (wins+losses aumenta di 1).

### 2. Two partial exits + final exit
Abilitare split/partial (InpSplitTrade o chiusura parziale manuale in visual
mode: chiudere 2 volte metà posizione, poi il resto).
Atteso: 2 righe `PARTIAL` (pnl dello spezzone) + **1 sola** riga `CLOSE` con
pnl = somma dei tre spezzoni, `lots` = volume totale entrato,
r_multiple = pnl_totale / rischio iniziale. Stats: **1 solo** outcome.
(Prima: 3 CLOSE, 3 outcome, chain/notify triplicati.)

### 3. Duplicate deal replay
Non riproducibile direttamente nel tester; equivalente verificato:
il selftest backend (`server/tests/test_trade_lifecycle.py`, replay×3) +
design del ledger (l'evento nasce dal *diff* dell'aggregato history: lo stesso
deal ri-consegnato non cambia l'aggregato ⇒ nessun evento). In visual mode si
può verificare che `NXS_Stats_ProcessClosedTrades` (che ri-scansiona la stessa
history di OnTradeTransaction) non produca doppi outcome: wins+losses deve
restare = numero di trade logici.

### 4. Restart and history resync
Solo live/demo (il tester non ha restart): aprire un trade, chiuderlo, staccare
l'EA, chiudere un secondo trade con EA staccato (manuale), riattaccare l'EA.
Atteso nel log: `[NEXUS LEDGER] boot: 1 trade logici chiusi offline riconciliati`
(solo il secondo); nessun doppio push del primo (backend: 1 riga per trade,
evento `close` singolo + `resync`). Il file
`NEXUS_v1_ledger_emitted_<account>_<magic>.bin` deve esistere nei Files.

### 5. Two positions on the same symbol
Due strategie che aprono quasi insieme (o pyramiding). Atteso: 2 `CLOSE`
distinte con position_id diversi, pnl ciascuno del proprio trade; mai
attribuzione incrociata.

### 6. Exactly one TRADE_CLOSED per logical trade
Su un run completo: `grep -c CLOSE NEXUS_trades.csv` = numero di position
chiuse in history MT5 (History → Positions). Backend:
`SELECT trade_uid, COUNT(*) FROM trade_events WHERE event='close' GROUP BY
trade_uid HAVING COUNT(*)>1` deve restituire zero righe.

## Effetti attesi sui numeri (non-regressione)

- Con **zero** chiusure parziali (configurazione sweep attuale: lotto fisso,
  niente split), wins/losses/PF signal-level devono coincidere col vecchio
  codice: il ledger cambia i numeri SOLO dove prima erano sbagliati (parziali).
- `NXS_OnTradeClosed` (daily-DD/anti-revenge) riceve gli stessi totali di
  prima (delta realizzato per deal), quindi le protezioni non cambiano.

## Limiti dichiarati

- Conti NETTING: `position == trade logico` non regge (warning nel log al primo
  deal INOUT); il progetto usa hedging.
- `close_by` (chiusura per compensazione): volume/PnL contati sul deal della
  position corrente.
- La PK backend `trades.ticket` resta position_id (collisione teorica tra
  account diversi: documentata, fix = rebuild tabella, fuori scope PR1).
