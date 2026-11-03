# STRATEGY_CONTRACT_H1_A — frozen before any economic result is observed

**Strategy ID**: `H1_A`. **Strategy Version**: `H1_A_V1`. Not present
in `contracts/strategy-registry.json` (canonical file, never
modified) — this harness supplies a **local-only**
`registry_status = {"H1_A": "RESEARCH_ONLY"}` to
`phase5d_shadow_engine_v1.registry_lookup.classify()`, which maps
`RESEARCH_ONLY` to `OBSERVATION_ONLY` (never
`AUTHORIZED_EXECUTABLE`) — same bucketing function and vocabulary as
every other NEXUS shadow-engine candidate, no parallel authorization
logic.

**Naming note**: "H1-A" is the strategy identifier (Hypothesis 1,
variant A — the Liquidity Sweep + Failed-Close Reclaim idea selected
across `nexus_telegram_trading_intelligence_02` /
`nexus_telegram_visual_intelligence_03` /
`nexus_telegram_before_after_reconstruction_04`), **not** a
timeframe. The operating timeframe of this implementation is **H4**
(see Data Layer below).

Every rule below not already supported by prior NEXUS research is
tagged **DESIGN_ASSUMPTION_V1** — a frozen, declared choice, never
presented as validated.

## 1. Timeframe e livelli supportati

- **Timeframe**: H4 only, UTC bar boundaries `[0,4,8,12,16,20]`.
  Reused directly from `server/research_datasets/market_state_v1/`
  (manifest-verified, see `DATA_PROVENANCE.md`) — not rebuilt.
- **Symbol**: XAUUSD, BID price side (per that dataset's manifest —
  no separate ASK series in this dataset; see §3 for how this
  limits the spread model). **DESIGN_ASSUMPTION_V1**: this slice
  does not attempt a MID/BID synthesis — it declares BID as the
  reference price throughout and never claims a MID-based level.
- **Livelli supportati**: esattamente uno per bar, per lato
  (PREEXISTING_LEVEL_HIGH, PREEXISTING_LEVEL_LOW) — vedi §2. Nessun
  livello di sessione, nessun livello settimanale/mensile in questa
  versione (fuori scope, non un'omissione accidentale).

## 2. PREEXISTING_LEVEL — definizione numerica (DESIGN_ASSUMPTION_V1)

Nessuna fonte esaminata nelle 4 missioni Telegram (02-04) ha mai
fornito una definizione oggettiva di "livello di liquidità" o
"swing" riutilizzabile 1:1 — confermato ripetutamente, più di recente
in `nexus_telegram_visual_intelligence_03/TRADING_V1_SHORTLIST_REASSESSMENT.md`
e `nexus_telegram_before_after_reconstruction_04/TRADING_V1_IMPLICATIONS.md`.
Questa versione congela quindi una regola propria, **riusata da una
finestra già esistente nel codebase, non inventata da zero**: lo
stesso lookback N=20 già fissato per `market_state_dataset_v1.csv`
(vedi `server/research_scripts/phase5e_causal_replay_v1/baseline_signal.py`,
che a sua volta cita `vault/01-Trading/_phase4_artifacts/phase5_market_state_dataset_schema.md`).

```
PREEXISTING_LEVEL_HIGH(t) = max(high[t-20 .. t-1])   # strict prior window
PREEXISTING_LEVEL_LOW(t)  = min(low[t-20 .. t-1])    # strict prior window
```

Il livello di bar `t` non usa mai `high[t]`/`low[t]`/`close[t]` — per
costruzione, "pre-esistente" significa letteralmente calcolato solo
da barre strettamente precedenti.

**Timestamp di disponibilità**: `PREEXISTING_LEVEL_HIGH(t)`/
`PREEXISTING_LEVEL_LOW(t)` sono conoscibili non appena la barra
`t-1` è chiusa — cioè **all'apertura della barra `t`**
(`bar[t].open_time`). Questo è un timestamp di disponibilità, non il
momento in cui il segnale H1-A diventa disponibile (vedi §5, diverso
e successivo).

## 3. SWEEP — definizione numerica (DESIGN_ASSUMPTION_V1)

```
SWEEP_HIGH(t) = bar[t].high > PREEXISTING_LEVEL_HIGH(t)   # any penetration, zero buffer
SWEEP_LOW(t)  = bar[t].low  < PREEXISTING_LEVEL_LOW(t)
```

Nessun buffer minimo (in punti/ATR) è richiesto per contare come
sweep — la soglia più semplice e oggettiva possibile, dichiarata
come scelta di design, non come conclusione di ricerca. Le missioni
02-04 hanno confermato che nessuna fonte quantifica mai questa
soglia (`nexus_telegram_visual_intelligence_03/VISUAL_TRADING_RULES.csv`,
riga `ictcrt_trading_hub`: "Soglia esatta di sweep... non
quantificata"). Un buffer diverso da zero è un parametro esplicito
del motore (vedi `decision_engine/h1a_detector.py`), non hardcoded,
così una futura missione può testarlo senza riscrivere la regola.

## 4. RECLAIM — regola (STRONGLY_INFERRED dalla ricerca, soglia DESIGN_ASSUMPTION_V1)

Valutato sulla **stessa barra** del sweep (fallimento di chiusura
sullo stesso bar), coerente con l'evidenza visiva diretta trovata
in `elliott_wave_secret #4521` ("price swept the weekly liquidity,
but the candlestick failed to close below it") e con la sequenza
completa Sweep→Struttura→Entry trovata in `ictcrt_trading_hub`:

```
RECLAIM_AFTER_SWEEP_HIGH(t) = SWEEP_HIGH(t) and bar[t].close <= PREEXISTING_LEVEL_HIGH(t)
RECLAIM_AFTER_SWEEP_LOW(t)  = SWEEP_LOW(t)  and bar[t].close >= PREEXISTING_LEVEL_LOW(t)
```

Un `SWEEP` senza `RECLAIM` (chiusura oltre il livello, vero
breakout) **non è un CANDIDATE H1-A** — è un fenomeno diverso
(breakout confermato), fuori scope per questa strategia, non un
difetto.

## 5. Momento esatto in cui il segnale diventa disponibile

Il `CANDIDATE` (e la conseguente decisione BUY/SELL/WAIT) è
disponibile **esattamente al close della barra `t`**
(`bar[t].open_time + 4h`) — mai prima, perché sia `SWEEP` che
`RECLAIM` richiedono `high[t]`/`low[t]`/`close[t]`, conoscibili solo
a chiusura. Stesso principio già applicato in
`phase5e_causal_replay_v1/replay.py::_bar_close_timestamp` (riusato
identico, non reinventato).

## 6. Condizioni BUY/SELL/WAIT

| Condizione | Decisione | Motivo (reason_code) |
|---|---|---|
| `RECLAIM_AFTER_SWEEP_LOW(t)` e non anche `RECLAIM_AFTER_SWEEP_HIGH(t)` | **BUY** | `CANDIDATE_LONG_SWEEP_RECLAIM` |
| `RECLAIM_AFTER_SWEEP_HIGH(t)` e non anche `RECLAIM_AFTER_SWEEP_LOW(t)` | **SELL** | `CANDIDATE_SHORT_SWEEP_RECLAIM` |
| Entrambe vere sulla stessa barra | **WAIT** | `AMBIGUOUS_BOTH_SIDES_SWEPT_AND_RECLAIMED` |
| `SWEEP` vero ma `RECLAIM` falso (breakout confermato) | **WAIT** | `SWEEP_WITHOUT_RECLAIM_NOT_H1A_SETUP` |
| Nessun sweep | **WAIT** | `NO_SWEEP_DETECTED` |
| Storia insufficiente (< 20 barre pregresse) | **WAIT** | `INSUFFICIENT_WARMUP_HISTORY` |
| Candidate valido ma un tentativo nella stessa direzione è già aperto (non chiuso) per questo simbolo | **WAIT** | `DUPLICATE_SUPPRESSED_OPEN_ATTEMPT_EXISTS` |

**WAIT è sempre un record emesso**, con `reason_code` esplicito —
mai l'assenza di un evento (requisito esplicito del mandato, sezione
4).

## 7. Stop e invalidazione (DESIGN_ASSUMPTION_V1)

```
stop_LONG  = bar[t].low  - bar[t].avg_spread
stop_SHORT = bar[t].high + bar[t].avg_spread
```

Il buffer riusa il campo `avg_spread` **già presente nella barra
stessa** (dataset `xauusd_h4_bars.csv`, colonna `avg_spread`) invece
di un numero arbitrario — dato reale, deterministico, non inventato,
ma la scelta di usarlo come buffer di stop è una decisione di design
di questa missione, non una conclusione di ricerca.

**Invalidazione** = prezzo tocca/supera lo stop (nessuna
invalidazione strutturale separata in questa versione — fuori scope,
dichiarato).

## 8. Regola iniziale di uscita (DESIGN_ASSUMPTION_V1)

```
risk_distance = abs(entry_price - stop)
target_LONG   = entry_price + 2 * risk_distance   # fixed 2R
target_SHORT  = entry_price - 2 * risk_distance
```

**Non rivendica di rappresentare il concetto di "Draw On Liquidity"**
visto nelle immagini (missioni 02-04): nessuna fonte quantifica mai
quel target, quindi questa versione usa un R-multiple fisso e
dichiarato, non una ricostruzione del target "reale" dei canali.

**Entry price**: close della barra `t` o apertura della barra
`t+1`? Scelta: **`NEXT_OPEN_V1`** (apertura della barra successiva),
riusando `FillModel` già definito in
`server/research_execution_model_v1.py` (import diretto, non
copiato) — più conservativo di `SIGNAL_CLOSE_LEGACY` perché non
assume un'esecuzione istantanea nell'istante in cui il segnale
diventa noto.

## 9. Deduplicazione

- **Idempotenza evento**: `event_id` = hash deterministico di
  `(strategy_id, strategy_version, symbol, timeframe, bar_epoch,
  decision, reason_code)` — stessa barra valutata due volte produce
  lo stesso `event_id`, mai un duplicato (stesso principio di
  `phase5d_shadow_engine_v1.contract.canonical_hash`, riusato).
- **Deduplicazione di esposizione**: un nuovo CANDIDATE nella stessa
  direzione viene suppresso (`WAIT`/`DUPLICATE_SUPPRESSED_OPEN_ATTEMPT_EXISTS`)
  se esiste già un tentativo di carta APERTO (non ancora uscito) per
  lo stesso simbolo — un solo tentativo attivo alla volta, nessun
  Grid/Pyramid/recovery/martingala (vincolo esplicito del mandato,
  sezione 5).

## 10. Event ID e Strategy Version

- `strategy_id = "H1_A"`, `strategy_version = "H1_A_V1"` — presenti
  in OGNI record emesso (Decision, Paper Execution, Journal).
- `event_id` come in §9 — deterministico, riproducibile, mai casuale.
- Un cambiamento futuro a una qualunque regola numerica di questo
  contratto (buffer, R-multiple, N del lookback) **richiede una
  nuova `strategy_version`** (`H1_A_V2`, ecc.) — mai una modifica
  silenziosa della stessa versione, per lo stesso motivo per cui
  `research_execution_model_v1.experiment_identity` lega l'identità
  dell'esperimento al suo contratto di esecuzione.

## 11. Cosa NON è in questa versione (fuori scope dichiarato)

- Nessun contesto HTF (filtro su timeframe superiore) — DECISIONE
  PROGETTUALE non ancora presa, come già segnalato in
  `nexus_telegram_trading_intelligence_02/TRADING_V1_HYPOTHESIS_SHORTLIST.md`.
  Nessuna chiamata HTF in questa versione.
- Nessuna gestione a griglia (H1-B, ipotesi separata, non
  implementata qui per vincolo esplicito "Nessun Grid, Pyramid,
  recovery o martingala").
- Nessuna correzione del timestamp per contenuto forward (H1-C) —
  non applicabile qui, questa è una strategia di prezzo su dati di
  mercato, non su testo Telegram.
- Nessuna sessione/orario di trading escluso — ogni barra H4 valida
  è valutata, 24/7 nel periodo del dataset.
