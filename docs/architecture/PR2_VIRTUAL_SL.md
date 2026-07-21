# PR 2 — Virtual SL execution workflow

Corregge il ciclo Virtual SL, che era **doppiamente morto**: `NXS_EA_VirtSL_Register`
non veniva mai chiamato e `NXS_EA_VirtSL_Check()` su hit disattivava il record e
loggava, ma **non chiudeva la posizione**. Ora il ciclo è completo: register dopo
il fill reale → armed → trigger → richiesta chiusura → retry/backoff → conferma
reale → persistenza + riconciliazione al restart.

Branch: `feature/pr2-virtual-sl` (stacked su `feature/trade-lifecycle-ledger`,
da cui usa `NXS_Ledger_Emitted` per la conferma via ledger FINAL).

## Semantica virtSL vs brokerSL

| | Oggi (baseline) | PR2 in EXECUTE |
|---|---|---|
| SL logico `sig.slPrice` | sizing **e** inviato al broker | sizing **e** `virtSL` interno |
| SL inviato al broker | = SL logico | **hard SL largo** = entry ± `InpVirtSL_HardSL_ATRMult`×ATR, **congelato all'ingresso** (nessun ricalcolo su ATR successivo) |
| chiusura al livello logico | la fa il broker | la fa l'EA (virtual SL) con conferma reale; l'hard SL resta backstop catastrofico |

Il **sizing resta sempre sullo SL logico** (`slDist = |entryRef − sl|`, invariato).

## Modalità (default OFF)

`input ENUM_NXS_VSL_MODE InpVirtSL_Mode` — un solo controllo esplicito, non due booleani:

- **OFF** (default): baseline **byte-for-byte**. Nessun register, nessun file, SL
  logico al broker. I `.set` esistenti non contengono il nuovo enum → OFF garantito
  → **zero attivazione accidentale** (il vecchio `InpVirtSL_Enable` è stato rimosso).
- **OBSERVE**: il broker tiene lo SL logico (come OFF); il record viene registrato e
  la macchina a stati logga ARMED/TRIGGERED **senza chiudere né allargare** — shadow
  mode per validazione.
- **EXECUTE**: hard SL largo al broker, virtSL = SL logico, chiusura reale su hit.

## State machine

`ARMED → TRIGGERED → CLOSE_REQUESTED → CONFIRMED`, ramo `→ ESCALATED` da
CLOSE_REQUESTED dopo `InpVirtSL_MaxTries`. Logica in `NXS_VSL_Decide()` (funzione
**pura**, testabile senza broker).

- **CONFIRMED mai da DONE/PLACED** (= solo richiesta accettata). Deriva da:
  `NXS_Ledger_Emitted(positionId)` → `LEDGER_FINAL` (preferito), oppure
  `PositionSelectByTicket==false` → `POSITION_GONE`. La provenienza è registrata.
- **Retry**: su fallimento non disarma; conserva attempts + lastAttemptMs; backoff
  `InpVirtSL_BackoffMs`; dopo la soglia → **ESCALATED** con alert alta priorità e
  backoff lungo `InpVirtSL_EscBackoffMs`; **ESCALATED non è terminale** — continua a
  ritentare, limitato nel ritmo, finché la posizione non è confermata chiusa/assente.

## Hard SL

`NXS_VSL_ComputeHardSL()` normalizza a tick size e rispetta `SYMBOL_TRADE_STOPS_LEVEL`.
Se non valido → ritorna false e **mai** invia SL=0: fallback esplicito secondo
`InpVirtSL_BlockIfNoHardSL` (true = blocca l'entrata; false = SL logico al broker).

## Register dopo il fill reale

Correlazione request→fill senza "last order ticket": una **pending collection**
(`order_ticket`, symbol, magic, direction, strategy, request_time, virtSL, brokerSL)
riempita subito dopo `OrderSend` (order ticket reale via `NXS_TradeOrderTicket()`).
Al fill (`OnTradeTransaction`, DEAL_ENTRY_IN), il deal è associato tramite `DEAL_ORDER`
e registrato con `DEAL_POSITION_ID`. Pending scaduti (`InpVirtSL_PendingTTLsec`) purgati.

## Percorsi coperti (D1)

| Path | Apertura | PR2 |
|---|---|---|
| classic | `NXS_OpenTrade` → SafeBuy/SafeSell(sl) | ✅ |
| institutional | `NXR_OpenTrade` → SafeBuy/SafeSell(sl) | ✅ |
| grid | `NXS_GridRecovery`/`_nxs_inst_add` → DoBuy/DoSell(0,0) | ⛔ escluso (aprono con SL=0) |
| pyramid | `NXS_Pyramiding` → DoBuy/DoSell(0,0) | ⛔ escluso |
| split | `NXS_SplitTrade` → solo DoClosePartial | eredita il record del padre; un partial **non** conferma né cancella il Virtual SL |

## Persistenza + restart

File CSV versionato **separato** `NEXUS\virtsl_<login>_<magic>.csv`, header
`NXVSL;ver;login;magic`. Scrittura **atomica** (`.tmp` + `FileMove`), no-op in
tester/OFF. Al boot `NXS_VSL_Restore()`: valida account+magic+versione (mismatch →
ignora, **nessuna contaminazione** tra account/istanze); poi riconcilia — scarta
posizioni già chiuse, scarta FINAL già nel ledger (no doppioni), riarma
ARMED/TRIGGERED ancora validi, ricarica i pending pre-fill.

## File modificati

- `NXS_EdgeAdaptive.mqh` — sezione #7 riscritta (modi, stati, pending, ComputeHardSL,
  OnFill, Decide puro, Check, Persist/Restore, SelfTest).
- `NEXUS_EA_v2.mq5` — `OnFill` in OnTradeTransaction, `Restore` in OnInit, `Persist` in OnDeinit.
- `NXS_Globals.mqh` — `g_tradeOrderTicket` + getter (idioma di `g_tradeRetcode`; res.order non ha altro canale verso NXS_OpenTrade — dimostrato non-locale).
- `NXS_Execution.mqh` — wiring classic (PrepareEntry + OnRequested).
- `NXS_ReusePerformancePack.mqh` — wiring institutional/NXR (stesso schema; file fuori dall'allow-list stretto ma unico send site institutional — segnalato).

## Migrazione / rollback

- **Migrazione**: nessuna. OFF di default = baseline. Il file di stato nasce solo in
  OBSERVE/EXECUTE.
- **Rollback**: ricompilare il parent. L'unico artefatto è `virtsl_*.csv`, inerte per
  il codice vecchio; eliminabile a mano. Nessuna struttura dati persistente condivisa.

## Rischi di regressione

1. In EXECUTE, se la chiusura virtuale fallisce a ripetizione (EA offline, retry
   esauriti) la perdita reale arriva all'hard SL 4×ATR ≫ rischio dimensionato.
   Mitigato: default OFF, retry+escalation+persistenza, hard SL come tetto.
2. In EXECUTE, `POSITION_SL` sul broker diventa il valore largo → parser/dashboard
   che leggono lo SL della posizione vedono l'hard SL, non quello logico.
3. Interazione con PR1: la chiusura virtuale è un normale `close` del ledger →
   exactly-once preservato; la conferma preferisce il FINAL del ledger.
