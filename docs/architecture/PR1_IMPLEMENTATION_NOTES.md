# PR 1 — Implementation Notes (delta vs architecture pack)

Documento richiesto dal piano di esecuzione (16_MIGRATION_ROADMAP: "updated
architecture document where implementation differs"). Copre: call graph
`DEAL_ENTRY_OUT` prima/dopo, scostamenti dichiarati rispetto ai documenti
03/04, nota di migrazione e rollback.

Branch: `feature/trade-lifecycle-ledger` (il piano indicava
`fix/trade-lifecycle-ledger`; il PR #2 era già aperto col nome feature/ —
rinominarlo avrebbe orfanato PR e review. Solo naming, nessuna differenza
di contenuto.)

---

## 1. Call graph `DEAL_ENTRY_OUT`

### Prima (difetto confermato dal pack, doc 02/03)

```text
OnTradeTransaction(DEAL_ADD, entry==DEAL_ENTRY_OUT)     [per OGNI deal OUT]
 ├─ NXS_OnTradeClosed(pnl del singolo deal)             → contatore perdite
 │                                                        consecutive corrotto
 │                                                        dai parziali
 ├─ NXS_RegisterSLClose(dir)          [se reason==sl, anche su parziale]
 ├─ NXS_LogTradeCSV("CLOSE", …)       [N righe CLOSE per 1 trade]
 ├─ NXS_Prot_PushTradeReason(…)       [N push; backend sovrascrive pnl]
 ├─ NXS_Chain_OnTradeClose(…)         [chain transita N volte]
 └─ NXS_Notify_TradeClose(…)          [N notifiche]

NXS_Stats_ProcessClosedTrades()        [scanner OnTimer, indipendente]
 └─ NXS_Stats_RecordOutcome(per OGNI deal OUT)  → wins/losses gonfiati,
                                                   R dello spezzone sul
                                                   rischio intero
```

### Dopo (PR 1)

```text
OnTradeTransaction(DEAL_ADD)                       [qualsiasi deal nostro]
 └─ NXS_Ledger_OnDeal(deal)
     └─ NXS_Ledger_Touch(position_id)              [aggregate-diff]
         ├─ NXS_Ledger_AggregatePosition()         [ri-aggrega da history]
         ├─ diff con stato precedente → evento:
         │    OPEN / SCALE_IN / PARTIAL / FINAL / NONE(replay)
         └─ FINAL: exactly-once (emitted-set) → coda chiusure

 evento PARTIAL → NXS_LogTradeCSV("PARTIAL", pnl spezzone)   [solo audit]

 NXS_EA_DrainLedger()                    [OnTradeTransaction/OnTimer/OnDeinit]
  └─ NXS_EA_OnLogicalClose(tc aggregato)          [UNA volta per trade logico]
      ├─ NXS_OnTradeClosed(tc.pnl aggregato)      → perdite consecutive:
      │                                              1 trade = 1 aggiornamento
      ├─ NXS_RegisterSLClose(dir)                  [solo se il FINALE è sl]
      ├─ NXS_LogTradeCSV("CLOSE", aggregato)       [1 riga per trade]
      ├─ NXS_Stats_RecordOutcome(R aggregata)      [1 outcome per trade]
      ├─ NXS_Prot_PushTradeReason(event=close)     [1 push autoritativo]
      ├─ NXS_Chain_OnTradeClose(…)                 [1 transizione]
      └─ NXS_Notify_TradeClose(…)                  [1 notifica]

NXS_Stats_ProcessClosedTrades()   [scanner: ora alimenta SOLO il ledger,
                                   dedupe strutturale ⇒ mai doppi outcome]
NXS_Ledger_SweepPending()         [OnTimer: rete anti-race sui FINAL persi]
NXS_Ledger_Boot()                 [OnInit: resync offline, emitted-set persistito]
```

Requisito "exactly once" del piano: StrategyChain ✓, protezioni
loss-streak ✓, statistiche ✓, notifiche ✓ — tutte dentro
`NXS_EA_OnLogicalClose`, raggiunta una sola volta per trade logico.

## 2. Scostamenti dichiarati rispetto ai doc 03/04

| Spec (doc 03/04) | PR 1 | Motivo / destino |
|---|---|---|
| `LogicalTradeID` distinto da `PositionID` | `trade_uid = account:position_id` (logico ≡ position) | Valido su hedging (modalità del progetto); flip netting rilevato con warning e trattato come FINAL. Separazione piena quando serviranno gruppi grid/pyramid multi-position (PR 4/5). |
| Evento `POSITION_VOLUME_REDUCED` / `TRADE_CLOSED` | `event = partial` / `close` (+ `resync`, `close_request`) | Nomi canonici e busta evento completa (envelope doc 04) arrivano col ledger pieno in PR 9; la semantica è già quella richiesta. |
| Final-close: volume residuo zero **o** position inesistente | Volume-out ≥ volume-in (tolleranza volume-step) **e** position inesistente, più `SweepPending` periodico | L'AND evita un FINAL prematuro se la position è momentaneamente non visibile durante un parziale; lo sweep garantisce che il FINAL non si perda mai nel caso opposto. Stesso esito, più conservativo. |
| Ledger a 9 entità (`signals`…`deals`,`events`) | Tabella `trade_events` append-only + colonne additive su `trades` | Doc 03: "add the ledger without removing existing read models until migration is complete" — PR 1 introduce il livello minimo (eventi trade con unicità `(trade_uid,event)`); il modello completo è materia di PR 9. |
| `DealID` unico, replay senza duplicati | Nessuna tabella deal EA-side: il design aggregate-diff rende il replay strutturalmente inerte (stesso aggregato ⇒ nessun evento) | Equivalente funzionale con meno stato; i DealID entreranno nel ledger pieno (PR 9). |
| History sync con cursore | Ri-aggregazione finestra 7g, idempotente per `trade_uid` | Replay sicuro già garantito dall'unicità; il cursore arriva con la busta evento (PR 9). |
| `OrderID` distinto | Non modellato nel percorso di chiusura (nessun consumatore attuale) | Ordini richiesti/accettati/rifiutati = eventi di esecuzione del ledger pieno (PR 9). |

## 3. Semantica delle protezioni (cambio dichiarato)

`NXS_OnTradeClosed` (perdite consecutive, anti-revenge, anti-bleed, streak
sizing) passa da *per deal OUT* a *per trade logico con PnL aggregato* —
richiesto esplicitamente dal piano ("consecutive-loss protections … run
exactly once per logical trade"; difetto "corrupted consecutive-loss
counters", doc 03). Con zero parziali il comportamento è identico al
vecchio codice (1 OUT = 1 chiamata): la non-regressione zero-partial resta
valida. I gate daily-DD/profit-lock non passano da questa funzione (usano
balance/equity di conto) e sono invariati.

## 4. Migrazione

- **Backend**: additiva e idempotente (`_migrate_trade_ledger`): 5 colonne
  nuove su `trades` (NULL sulle righe storiche), tabella `trade_events`,
  indici. Nessun dato esistente modificato. Eseguita automaticamente a
  `init_db()`.
- **Compatibilità incrociata**: EA vecchio + backend nuovo → payload senza
  `event` trattato da `close` autoritativo (comportamento storico). EA nuovo
  + backend vecchio → i campi extra del JSON finiscono in `raw`, nessun
  errore; l'unica perdita è l'idempotenza dell'evento (comunque assente nel
  backend vecchio).
- **Storico affetto dal difetto parziali**: le righe `trades` precedenti al
  PR restano com'erano (potenzialmente PnL da ultimo spezzone). Marcatura
  `LEGACY_UNVERIFIED`/ricostruzione dai deal broker = PR 9, come da doc 04.

## 5. Rollback

- **EA**: ricompilare il parent `d0a94f3` (o `main`). Nessuno stato da
  ripulire: l'unico artefatto nuovo è il file emitted-set
  (`NEXUS_v1_ledger_emitted_<account>_<magic>.bin`), inerte per il codice
  vecchio; eliminabile a mano.
- **Backend**: revert dei commit. Le colonne additive e `trade_events`
  possono restare nel DB: il codice vecchio le ignora (SQLite non richiede
  down-migration per colonne aggiunte). Nessuna perdita di dati in entrambe
  le direzioni.
- Ordine sicuro: prima rollback EA, poi backend (o insieme); mai backend
  nuovo rimosso lasciando EA nuovo in produzione per lungo tempo (si
  perderebbe solo l'idempotenza evento, non dati).

## 6. Test

- Backend: `server/tests/test_trade_lifecycle.py` (9 test: 6 scenari del
  piano + payload legacy + migrazione idempotente su DB legacy).
- MQL5: `NXS_Ledger_SelfTest()` (deterministico, senza history) + checklist
  Strategy Tester in `docs/PR1_trade_lifecycle_acceptance.md` (compilazione
  e scenari a carico dell'agente desktop, unico ambiente con MetaEditor).
