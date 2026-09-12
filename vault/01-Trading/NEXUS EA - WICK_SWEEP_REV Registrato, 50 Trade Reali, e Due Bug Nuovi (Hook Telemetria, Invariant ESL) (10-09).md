# WICK_SWEEP_REV registrato nel contract, primo Fast Smoke con trade reali - e due bug nuovi trovati eseguendo il test come richiesto

Contesto: dopo l'audit di Structure/Reaction/LEVEL_REACTION (vedi [[NEXUS EA - Audit Structure-Reaction-LEVEL_REACTION e WICK_SWEEP Bloccato dal Terzo Cancello (10-09)]]), l'utente ha autorizzato: (1) identita' canonica WICK_SWEEP_REV ovunque, (2) registrazione nel contract via source of truth (non a mano), (3) fix del consumo one-shot con funnel telemetria separato, (4) rilancio identico del Fast Smoke, (5) funnel completo, (6) metriche solo descrittive, (7) nessuna modifica ai parametri bloccati.

## Cosa e' stato fatto

- Identita': un solo residuo (commento in NEXUS_EA_v2.mq5) corretto a WICK_SWEEP_REV; il resto era gia' uniforme.
- Contract: backfill di LEVEL_CONFLUENCE/_M5/LEVEL_REACTION/_M5 in `knowledge/strategy_database.json` (gia' live via patch manuale mai passata dal generatore - senza backfill la rigenerazione le avrebbe rimosse) + WICK_SWEEP_REV, rigenerato con `contracts/generate_registry.py`, validato OK. Diff verificato: unico cambiamento di comportamento reale e' l'aggiunta di WICK_SWEEP_REV a `NXS_StrategyKnown()`.
- One-shot fix: `triggered` (sweep rilevato) e `consumed` (trade REALMENTE aperto) separati in `NXS_Strategies_Experimental.mqh`, throttle di un tentativo per barra H4, funnel telemetria (`NXS_WickSweep_PrintFunnel`, stampato a fine test da `OnDeinit`).
- Commit separati e pushati: `fcade35` (prototipo, mai committato prima), `4cdcd3d` (registrazione contract).
- Compilato 0 errori su Terminal1 e Terminal3. Rilanciato lo stesso identico Fast Smoke (nessun parametro cambiato) su Terminal3.

## Risultato: 50 trade reali (finalmente)

Report `nxs_fastsmoke_wicksweep.htm` (Terminal3, 2026.06.01-2026.08.26, selettore 54, lotto fisso 0.02):

- **50 trade**, PF **0.97**, net **-$5.77**, WR **20%** (10 vincenti/40 perdenti), 25 BUY/25 SELL (perfettamente simmetrico).
- Avg win **+$17.38**, avg loss **-$4.49** (RR realizzato ~3.87:1, vicino al nominale 100/25=4:1, differenza da spread/slippage).
- Max perdite consecutive: **9**.
- Avg hold: **10.7 min** (min 0, max 120.2) - molto breve per una strategia H4: la maggioranza degli stop scattano quasi subito dopo l'ingresso, coerente con entrate "di pancia" dentro un movimento ancora in corso piuttosto che un vero esaurimento.
- Exit authority: **40 BROKER_SL + 10 BROKER_TP = 50/50**, zero altro, **zero INVARIANT_FAIL** (il contratto RAW e' rispettato al 100% per questa strategia specifica, che non usa nessuna protezione opt-in).

Solo descrittivo, come richiesto: PF0.97/net negativo NON e' un verdetto di edge - e' il primo campione reale con un solo set di parametri bloccati, su 3 mesi.

## Funnel completo (dalla riga [WICKSWEEP][FUNNEL] a fine test)

```
h4Candles=321 levelsCreated=566 levelsRevisited=205 sweepsDetected=181
duplicateRetrigger=906 entryAttempts=0 entryRejected=0 entryOpened=0
buyOpened=0 sellOpened=0 levelsInvalidatedByPrice=80 levelsReplacedUnused=484
```

- **h4Candles=321**: barre H4 osservate in 3 mesi (~321/6 barre al giorno ≈ 53-54 giorni di trading pieno, coerente con weekend/festivi esclusi).
- **levelsCreated=566**: nuovi livelli (wick >=15 pip) registrati - alto: GOLD H4 produce spesso wick di quella dimensione.
- **levelsRevisited=205**: livelli ritoccati dal prezzo senza ancora raggiungere i 35 pip di sfondamento.
- **sweepsDetected=181**: livelli che hanno raggiunto lo sfondamento di 35 pip almeno una volta - **identico** al conteggio "OPEN BLOCCATO" del run precedente (post-fix multi-TF, pre-fix contract), come atteso: la logica di rilevazione del livello non e' cambiata, solo cosa succede DOPO.
- **duplicateRetrigger=906**: tentativi di sfondamento gia' innescato/tentato nella stessa barra, scartati dal throttle - conferma che senza il throttle per barra il segnale sarebbe scattato ~5x piu' spesso (906+181=1087 controlli totali sfondamento-vero contro 181 eventi unici).
- **levelsInvalidatedByPrice=80**: il prezzo e' rientrato sotto/sopra il livello originale prima di essere consumato (tesi di reversal smentita).
- **levelsReplacedUnused=484**: una nuova wick ha sostituito un livello non ancora consumato (il design "un solo livello per lato" scarta molte opportunita' - vedi nota nel file sperimentale).

### BUG NUOVO #1 - la telemetria attempts/rejected/opened e' rotta (hook sul percorso sbagliato)

`entryAttempts=entryRejected=entryOpened=buyOpened=sellOpened=0` nonostante 50 trade REALI aperti. Causa: ho agganciato `NXS_WickSweep_OnExecuteResult()` subito dopo `NXS_TryExecuteRC()` in `NEXUS_EA_v2.mq5`, ma quel loop (righe ~1358+) e' **morto quando `InpUseStrategyProfiles=true`** (sempre vero in Research Mode) - il blocco `=== PROFILI PER-STRATEGIA (v2.3.0) ===` (righe 1308-1356) chiama `NXS_OpenTrade()` DIRETTAMENTE e fa `return;` alla fine (riga 1355), quindi il loop che ho agganciato non viene mai raggiunto per nessun test Research Mode fatto finora (nemmeno ADX_RSI/EMA_PULLBACK/FVG_CONT, non solo WICK_SWEEP_REV).

Conseguenza pratica: `consumed` non si e' MAI impostato a `true` per nessun livello in questo run - il throttle "un tentativo per barra" ha continuato a permettere un nuovo tentativo ogni barra H4 finche' il livello non veniva invalidato dal prezzo o sostituito da una wick piu' nuova, indipendentemente dal fatto che un trade fosse gia' stato aperto per quel livello. L'unico argine reale ai duplicati e' stato il gate preesistente `NXS_StrategyHasOpenPos(s.stratName)` nel loop profili (riga 1330, "una posizione per strategia alla volta") - non il mio fix. I 50 trade sono realmente aperti e i loro SL/TP/PnL sono dati MT5 reali e attendibili, ma **non e' verificato che ognuno provenga da un livello genuinamente nuovo**: e' possibile che alcuni siano ri-tentativi tardivi sullo stesso livello stantio, aperti solo perche' nel frattempo la posizione precedente si era chiusa. Serve spostare l'hook nel loop corretto (righe 1316-1356) e rilanciare per avere numeri attempts/rejected/opened/consumed affidabili.

### BUG NUOVO #2 (trovato su ADX_RSI ESL ON, non WICK_SWEEP) - il contratto RAW non distingue una protezione opt-in dalla vera violazione

Eseguendo (come richiesto) il primo controllo del test ufficiale ADX_RSI RAW ESL ON (36 trade, PF1.61, net $1083.27, DD 25.52%/39.20%), isolato nel log per finestra oraria (12:24:34-17:10:40, lo stesso file di log e' condiviso da piu' run oggi):

- 15 BROKER_SL + 6 BROKER_TP + **14 OTHER/reason=expert**, e tutti e 14 gli OTHER generano **`[RESEARCH][INVARIANT_FAIL]`**.
- Causa: `tc.close_reason` (usato da `NXS_ResearchExitAuthority()`) viene popolato in `NXS_TradeLedger.mqh:478` da `_NXS_HistTrigger(HistoryDealGetInteger(d, DEAL_REASON))` (`NXS_HistorySync.mqh:28`) - una mappatura PURAMENTE sul campo numerico MT5 `DEAL_REASON` (client/mobile/web/**expert**/sl/tp/stop_out), che NON contiene mai le stringhe `NXS:DD`/`NXS:RISK`/`NXS:TIME`/`NXS:AUTOCLOSE`/`NXS:PROFIT` scritte nel commento del deal da `NXS_Prot_ClosePositionWithReason`. Un OrderSend esplicito dell'EA (qualunque protezione, incluso ESL) e' sempre taggato `DEAL_REASON_EXPERT`=3 -> `"expert"` -> `exit_authority=OTHER`. Il ramo `NXS:DD"->ESL/TOTAL_DD` dentro `NXS_ResearchExitAuthority()` (righe 160-164, scritto nel commit 4361194) e' quindi **codice morto**: non e' mai raggiungibile con l'attuale pipeline del ledger.
- Effetto: l'invariante RAW (pensato per intercettare "un terzo modulo nascosto chiude fuori dal contratto", il bug reale che ha portato al fix di AutoClose/MaxHold) non sa distinguere quel caso genuino da una protezione **esplicitamente opt-in per QUESTO test** (`InpResearchUseESL=true`) che sta facendo esattamente il suo lavoro dichiarato. I 14 pnl OTHER (-46 a -127, tutti negativi, nessun vincente) sono altamente coerenti con chiusure da equity/drawdown stop (mai un take, sempre una perdita tagliata) ma **non e' verificabile con certezza al 100%** da questo log, proprio perche' l'informazione che lo confermerebbe (il commento NXS:DD) si perde a monte nella pipeline del ledger.
- Non toccato: nessun fix applicato, come da perimetro "solo report" di questo giro. Va deciso se: (a) far leggere a `NXS_ResearchLogExit`/al chiamante anche il commento del deal (non solo `DEAL_REASON`) per recuperare il tag NXS:XXX, o (b) rilassare l'invariante quando l'authority e' "OTHER" ma la relativa protezione risulta esplicitamente opt-in per il run corrente.

## ADX_RSI RAW ESL ON - dato grezzo (in attesa del fix per una lettura pulita dei 14 OTHER)

36 trade (33 long/3 short, quasi tutta l'esposizione e' long), PF1.61, net $1083.27, DD 25.52% balance / 39.20% equity (piu' alto del 22.83% visto nel test precedente non ancora spiegato - nota MaxTotalDD separata, non toccata). 15 SL + 6 TP + 14 OTHER (verosimilmente ESL, non confermabile al 100% per il bug sopra) = 35, manca 1 al totale di 36 (probabile TESTER_END non ancora isolato nella finestra).
