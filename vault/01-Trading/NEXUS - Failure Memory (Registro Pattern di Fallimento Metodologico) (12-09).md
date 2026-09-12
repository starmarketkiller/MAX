# NEXUS — Failure Memory (Registro Pattern di Fallimento Metodologico)

Registro cumulativo di pattern di errore metodologico scoperti durante la ricerca su NEXUS — non specifico di una singola strategia. Obiettivo: prima di fidarsi di un nuovo risultato di ricerca (shadow, replay, backtest esterno), controllare se ricade in uno di questi pattern già noti.

Ogni voce: nome del pattern, cosa succede quando si presenta, come è stato scoperto la prima volta, come si previene/verifica.

---

## `SHADOW_EXECUTION_ASSUMPTION`

**Pattern**: una simulazione "shadow"/virtuale che assume un fill idealizzato (es. esattamente al prezzo di trigger, o esecuzione istantanea senza gate reali) produce numeri che descrivono correttamente *quella simulazione*, ma non sono una stima di performance eseguibile finché non validati contro un'esecuzione reale con lo stesso preflight/gate/slippage.

**Scoperto in**: validazione WICK_SWEEP_RECLAIM — lo shadow riportava PF 5.80 assumendo un fill esatto al `trigger_price`; il Fast Smoke reale (stesso campione, stessa cadenza) ha dato PF 0.78-0.80. Il counterfactual FILL_ANCHORED e il replay tick-level (RECLAIM_TICK/RECLAIM_LIMIT_RETEST) hanno poi escluso che l'anchor SL/TP fosse correggibile in modo semplice — l'edge shadow semplicemente non sopravvive a nessuna forma di esecuzione realistica testata. Vedi [[NEXUS EA - WICK_SWEEP Entry Timing Study - HYPOTHESIS STRONGLY SUPPORTED NOT YET EXECUTION-VALIDATED (11-09)]].

**Prevenzione**: qualunque risultato "shadow"/virtuale va etichettato esplicitamente come tale (non "risultato", ma "ipotesi") finché non esiste un run reale con lo stesso campione di eventi e lo stesso motore di esecuzione (preflight, protezioni, gate) a confermarlo.

---

## `TIMEZONE_MISMATCH`

**Pattern**: combinare timestamp da fonti diverse (es. MT5 broker time e una fonte tick esterna) senza verificare/dichiarare l'offset produce risultati sistematicamente sbagliati che possono sembrare plausibili se guardati solo in aggregato (es. metriche fuori scala ma non ovviamente "impossibili" a prima vista).

**Scoperto in**: replay tick-level WICK_SWEEP_RECLAIM — i timestamp MT5 in `run5_dataset.json` erano ora broker UTC+3, la fonte tick Dukascopy era UTC. Verificato concretamente: il `trigger_price` dello sweep_id=7 compariva nel flusso Dukascopy 3h00m02s prima del timestamp MT5. Senza correggere, il replay produceva slippage "impossibili" (100-400+ pip) ed esiti TP con pnl negativo — un segnale chiaro che qualcosa era rotto, ma solo perché l'errore era abbastanza grande da essere visibile.

**Prevenzione**: ogni replay che combina timestamp da fonti diverse deve dichiarare esplicitamente l'offset (`broker_time_offset`) usato e validarlo su almeno un esempio concreto prezzo↔timestamp prima di fidarsi di qualunque risultato aggregato.

---

## `DATA_COVERAGE_GAP`

**Pattern**: un fetch di dati esterni (storico tick, candele, ecc.) può avere buchi di copertura silenziosi e ampi. Se non misurati esplicitamente, un buco che cade proprio nel momento critico di un evento analizzato produce un risultato individualmente sbagliato che si nasconde dentro una media aggregata plausibile.

**Scoperto in**: fetch tick Dukascopy per il replay WICK_SWEEP_RECLAIM — primo tentativo (6 fetch paralleli × 12 connessioni) con **~53% delle ore feriali mancanti** (quasi certamente rate-limit lato server, non assenza reale di dati); gap-fill dedicato a bassa concorrenza ha recuperato gran parte ma **~21% è rimasto mancante** anche dopo il retry.

**Prevenzione**: dopo ogni fetch di dati esterni usati per un'analisi causale evento-per-evento, misurare esplicitamente la copertura oraria/giornaliera contro l'intervallo atteso (escludendo i periodi di mercato chiuso legittimi). Flaggare esplicitamente (non escludere silenziosamente né includere senza avviso) gli eventi il cui esito dipende da una finestra dati mancante.

---

## `CAUSAL_HOOK_MISMATCH`

**Pattern**: un hook diagnostico/shadow agganciato a un punto diverso della pipeline di esecuzione reale rispetto a quello che intende specchiare diverge dal comportamento reale, anche quando la logica interna dell'hook è identica bit-per-bit a quella della strategia reale.

**Scoperto in**: validazione shadow WICK_SWEEP_RECLAIM, tre iterazioni di fix parità:
1. Mancava un gate one-shot per livello nello shadow (diverso dalla strategia reale) → 1100 vs 182.
2. Lo shadow leggeva bid/ask ad ogni tick, mentre la strategia reale (e l'intero router) è gated dal "New Bar Gate" globale a una valutazione per barra `InpTFEntry` → 258 vs 182. Scoperta architetturale documentata a parte in [[NEXUS - Global New-Bar Gate - Signal Sampling Audit (12-09)]].
3. L'hook shadow era posizionato PRIMA dei gate `paused/entryAllowed/license/protections/spread/news` in `OnTick()` — se uno di questi bloccava il tick, la strategia reale non veniva mai valutata, ma lo shadow (eseguito prima) vedeva comunque l'evento → 213 vs 182.

Risolto solo alla quarta iterazione, posizionando l'hook esattamente subito prima di `NXS_CollectAllSignals()`, dopo tutti gli stessi gate del percorso reale.

**Prevenzione**: ogni futuro shadow/diagnostic path deve dichiarare esplicitamente a quale punto esatto della pipeline OnTick()/execution si aggancia (prima/dopo quali gate), e la parità con il comportamento reale va verificata numericamente (conteggio esatto), non assunta dalla sola somiglianza del codice. Requisito esplicito dell'utente, valido per ogni futuro lavoro di questo tipo — non solo WICK_SWEEP.

---

## Come estendere questo registro

Aggiungere una nuova voce quando un futuro filone di ricerca scopre un pattern di errore metodologico che non è specifico della singola strategia/analisi in corso, ma potrebbe ripresentarsi altrove. Non registrare qui bug di singola strategia (quelli restano nel `knowledge/strategy_database.json` della strategia, campo `bug_storici`) — solo pattern **di metodo**.
