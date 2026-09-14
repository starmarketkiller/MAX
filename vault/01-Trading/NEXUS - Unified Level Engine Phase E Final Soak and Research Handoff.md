# Unified Level Engine — Phase E: Final Soak + Research Handoff

Segue [[NEXUS - Unified Level Engine Phase D WICK Authority Parity Gate]] (commit `4de431f`, MIGRATION_READY). Ultima fase infrastrutturale prima della ricerca causale. **Nessuna modifica di codice in questa fase**: solo test aggiuntivi e documentazione (verificabile da `git diff` — nessun file `.mqh`/`.mq5` toccato). Legacy non rimosso, selector 55 non toccato, nessuna nuova logica di trading, nessuna ottimizzazione di parametri.

## 1. Extended soak

Il tentativo di un'unica finestra 3 mesi a real-tick (Model=4) continua a bloccarsi nell'ambiente (stesso sintomo riproducibile di Fase A/B: CPU quasi nulla, nessun log Tester prodotto dopo diversi minuti) — come esplicitamente autorizzato, non ho insistito. Copertura ottenuta con **3 finestre non sovrapposte da ~30 giorni (Model=1)** che coprono quasi l'intero periodo della fixture storica (2026-06-01 → 2026-08-26):

| Finestra | Periodo | sha256(NEXUS_trades.csv) | Trade | checks | mismatches | field_mismatches | stale_active | PF | DD max | Net |
|---|---|---|---|---|---|---|---|---|---|---|
| W1 | 2026-06-01 → 06-30 | `979325de0339d2d5...48a9d44` | 73 | 1718 | **0** | **0** | **0** | 0.95 | 82.49 (7.94%) | -12.57 |
| W2 | 2026-07-01 → 07-31 | `eb7293b9d6e6a5b1...52b61509ecb` | 59 | 1410 | **0** | **0** | **0** | 1.02 | 78.59 (7.56%) | +4.65 |
| W3 | 2026-07-31 → 08-25 | `ef9d64d9b5a0a483...4741fde6134ff95` | 58 | 1259 | **0** | **0** | **0** | 0.83 | 90.42 (8.81%) | -34.39 |

`InpLevelRegistry_WickReadPath=true` su tutte e 3 (new-engine autoritativo). W1 riproduce esattamente lo stesso sha256 già visto in Fase B/C/D sulla stessa finestra — coerenza cross-fase confermata anche qui.

**PF/DD/PnL sono riportati SOLO come fingerprint descrittivo, non come criterio di accettazione o di ottimizzazione** — nessun parametro è stato toccato per migliorarli (come esplicitamente vietato dal task). Nota su un dettaglio tecnico non un regressione: il totale di 190 trade (73+59+58) su queste 3 finestre Model=1 non coincide con i 178 trade della fixture storica Model=4 sullo stesso periodo — differenza attesa e già documentata in Fase A/B (Model=1 usa solo i prezzi di apertura barra per la simulazione tick, Model=4 usa i tick reali; granularità diversa produce conteggi diversi a parità di codice, non è una regressione di questa fase).

### Acceptance tecnica

```
decision mismatch = 0   (0/1718, 0/1410, 0/1259)
fallback mismatch = 0   (nessun DECISION_MISMATCH loggato su nessuna delle 3 finestre)
state mismatch    = 0   (field_mismatches=0 su tutte e 3)
stale active      = 0   (su 224, 214, 179 livelli totali rispettivamente)
```

**Tutti i 4 criteri soddisfatti su tutte e 3 le finestre.**

## 2. Research baseline freeze

**WICK_SWEEP_REV RAW / Unified Level Engine è formalmente congelato come negative research baseline**, non come strategia da promuovere o ottimizzare:

- Fixture storica di riferimento (Model=4, real-tick, 2026-06-01→2026-08-26): **178 trade, PF ≈ 0.78, negativo**.
- Fingerprint Model=1 di questa fase (3 finestre, stesso periodo circa): 190 trade, PF per-finestra 0.95/1.02/0.83 — coerente con un edge nullo-o-leggermente-negativo, non un pattern da inseguire.
- **Nessun tentativo di miglioramento è stato fatto né va fatto su questi numeri.** Il valore di questa baseline è come **laboratorio etichettato**: un insieme di eventi di sweep con esito noto (trade reali aperti/chiusi, SL/TP fissi), su cui cercare quali caratteristiche osservabili AL MOMENTO dell'evento separano i pochi esiti positivi dalla maggioranza negativa — non per ottimizzare questa strategia, ma per scoprire feature di livello generalizzabili ad altre famiglie.

## 3. Research dataset readiness — feature availability matrix

Basata sullo schema attuale di `SNXSUnifiedLevel`/`SNXSReactionEvent` (invariato da Fase C, vedi campi esatti in `NXS_LevelRegistry.mqh`/`NXS_ReactionEngine.mqh`):

| Feature | Stato | Fonte / nota |
|---|---|---|
| `level_id` | **AVAILABLE_NOW** | `SNXSUnifiedLevel.level_id` |
| `source` / `source_tf` | **AVAILABLE_NOW** | `SNXSUnifiedLevel.source` (sempre "WICK"), `source_tf` (sempre H4 per questa famiglia) |
| `side` / `direction` | **AVAILABLE_NOW** | `SNXSUnifiedLevel.side`/`direction` |
| `created_time` | **AVAILABLE_NOW** | `SNXSUnifiedLevel.created_time` |
| level age (al momento dello sweep) | **AVAILABLE_NOW** (derivata) | = evento SWEEP.`timestamp` − `created_time`; nessun nuovo hook, solo aritmetica in fase di analisi su due campi già loggati |
| touch count (prima dello sweep) | **AVAILABLE_NOW** | `SNXSUnifiedLevel.touch_count` (incrementato dall'hook TOUCH, già presente prima dello sweep nella sequenza causale) |
| sweep depth / penetration | **AVAILABLE_NOW** | `SNXSUnifiedLevel.max_penetration`/`sweep_depth` + `SNXSReactionEvent.penetration` (evento SWEEP) |
| ATR-normalizzata penetration | **REQUIRES_NEW_CAUSAL_HOOK** | nessun valore ATR è mai scritto nel registro/log eventi oggi; l'EA calcola `g_atr` altrove (`NXS_MarketAnalysis.mqh`, non toccato da questo engine) — servirebbe un nuovo campo osservativo (es. `atr_at_event`) popolato allo stesso istante causale del touch/sweep, letto ma non modificato da `NXS_MarketAnalysis.mqh` |
| `consumed` | **AVAILABLE_NOW** | `SNXSUnifiedLevel.consumed` |
| `invalidated` | **AVAILABLE_NOW** | `SNXSUnifiedLevel.invalidated` |
| reclaim status/time | **AVAILABLE_NOW** (schema), **N/A per WICK_SWEEP_REV** (dato) | `reclaim_time`/tipo evento RECLAIM esistono nello schema ma REV per disegno non aspetta mai un reclaim (fa fade immediato) — il campo resta sempre vuoto per i livelli sorgente di questa strategia; popolato invece per i livelli osservati anche dal path RECLAIM (selector 55, non migrato) |
| distanza dal livello (al momento dello sweep) | **AVAILABLE_NOW** (derivata) | coincide con `penetration` dell'evento SWEEP stesso; per una distanza a un istante diverso dallo sweep servirebbe una serie prezzi esterna (normale per una pipeline di ricerca, non un nuovo hook nell'EA) |
| session/time | **AVAILABLE_NOW** (derivata) | ora/giorno/sessione (Asia/Londra/NY) derivabili da `created_time`/`timestamp` dell'evento in fase di analisi, nessun nuovo hook |
| regime/trend context | **REQUIRES_NEW_CAUSAL_HOOK** | `g_struct.trend`/BOS/CHOCH (canonico, `NXS_Structure.mqh`) è causalmente disponibile in EA al momento di ogni evento WICK ma **non è mai letto né loggato** da questo engine (Fase A-D non hanno mai toccato `NXS_Structure.mqh`, nemmeno in lettura) — servirebbe un nuovo campo osservativo (es. `trend_at_event`) che LEGGE (mai scrive) `g_struct.trend` nello stesso istante causale del touch/sweep |

**Nessuna feature future-looking proposta.** Le due voci `REQUIRES_NEW_CAUSAL_HOOK` sono esplicitamente NON aggiunte in questa fase (fuori scope, solo identificate) — il primo esperimento (§4) è disegnato per essere eseguibile SENZA di esse, usando solo le feature già `AVAILABLE_NOW`.

## 4. Primo esperimento causale — SOLO design, non eseguito

**Domanda**: quali caratteristiche osservabili al momento dello sweep predicono che il prezzo raggiunga +1R prima di -1R (dove 1R = distanza SL configurata, 25 pip)?

| Elemento | Definizione |
|---|---|
| **Observation timestamp** | Il timestamp dell'evento `SNXSReactionEvent` con `type=SWEEP` per ciascun `level_id` sorgente WICK_SWEEP_REV. Nessuna feature può usare dati con timestamp successivo a questo. |
| **Population** | Tutti i `level_id` con `source_strategy` contenente `"WICK_SWEEP_REV"` che raggiungono `state=SWEPT` nel periodo di backtest disponibile (le 3 finestre di §1, o un periodo più ampio se rieseguibile in futuro). Un livello genera al massimo un record (un solo evento SWEEP per livello, per costruzione one-shot del legacy). |
| **Outcome (label)** | Da `entryRef` (prezzo al momento dello sweep, identico a legacy/new per costruzione) si simula il cammino futuro del prezzo: `+1R_first` se il prezzo tocca il livello TP-equivalente (±25 pip a favore) prima di quello SL-equivalente (±25 pip contro); `-1R_first` nel caso opposto; `CENSORED` se nessuno dei due viene toccato entro l'orizzonte massimo osservabile nel dataset (fine finestra). I record `CENSORED` vanno esclusi dal training, mai imputati come positivi o negativi. |
| **Feature set (v1, solo AVAILABLE_NOW)** | `side`, `direction`, `level_age_at_sweep`, `touch_count_before_sweep`, `max_penetration_at_sweep` (=`sweep_depth`), `session_bucket` (Asia/Londra/NY, derivato da `timestamp`), `day_of_week`, `hour_of_day`. `atr_normalized_penetration` e `trend_context` restano fuori dal v1 (richiedono il nuovo hook di §3, non implementato) — esplicitamente rimandabili a un v2 se il v1 mostra segnale. |
| **Exclusion rules** | Escludere: livelli mai arrivati a `SWEPT` (nessun evento da analizzare); livelli `CENSORED` (nessun esito risolto entro l'orizzonte); eventuali run con stato `CURRENT_CODE_GATED_STATE` diverso da quello verificato in Fase A-E (non applicabile oggi, selector 54 apre trade regolarmente in tutte le run di questa fase). |
| **No-lookahead rules** | Ogni feature deve essere calcolabile usando SOLO dati con timestamp ≤ observation timestamp. L'outcome usa dati futuri per costruzione (è l'etichetta), ma non deve MAI entrare nel feature set. Se in un v2 si aggiunge ATR/trend, va usato il valore ESATTO all'istante dell'evento, mai ricalcolato con senno di poi su una finestra che include barre successive. |
| **Minimum sample rule** | Nessuna conclusione da un bucket con meno di **30 esiti risolti** (non censurati); nessuna analisi complessiva se il dataset totale ha meno di **150 esiti risolti** (soglia di partenza dichiarata, non un risultato — sui dati di Fase E, ~190 sweep totali su 3 finestre la soddisfano di misura, ma un periodo più lungo la renderebbe più solida). |
| **Train/OOS separation** | Split **cronologico**, mai casuale (serie storica, autocorrelazione/regime). Primi ~70% degli eventi risolti per tempo = train/esplorazione; ultimi ~30% = OOS, mai guardato durante l'esplorazione delle feature. Qualunque pattern trovato in train va confermato SOLO sull'OOS prima di essere considerato reale. |
| **Output dataset schema** | Una riga per livello swept: `level_id, source_strategy, source_tf, side, direction, created_time, sweep_time, level_age_sec, price, touch_count_before_sweep, max_penetration_pips, session_bucket, day_of_week, hour_of_day, outcome_label (+1R_first/-1R_first/CENSORED), time_to_outcome_sec, split (train/oos)`. |

**Nessun tuning, nessuna nuova strategia, nessun parametro ottimizzato in questo esperimento come disegnato — e non eseguito in questa fase.**

## 5. Blocker

Nessuno bloccante per un v1 del dataset/esperimento. Unico limite dichiarato: le feature ATR-normalizzata e regime/trend restano `REQUIRES_NEW_CAUSAL_HOOK` (v2 eventuale, non necessario per iniziare). La fixture storica a 3 mesi real-tick (Model=4) resta `NOT_EXECUTED` per limite ambientale (non di codice) — mitigato con 3 finestre Model=1 che coprono lo stesso periodo con parità perfetta.

## Verdict

| Criterio per READY_FOR_CAUSAL_RESEARCH | Esito |
|---|---|
| Soak pulito (mismatch/fallback/state/stale = 0) | ✅ su tutte e 3 le finestre |
| Dataset causale realizzabile senza contaminazione futura | ✅ (v1 interamente su feature `AVAILABLE_NOW`, regole no-lookahead esplicite) |

### **VERDICT: READY_FOR_CAUSAL_RESEARCH**

Nessuna rimozione legacy, nessuna migrazione di altre strategie, nessun esperimento causale eseguito in questa fase — solo verificato che sia disegnabile senza contaminazione. La decisione di costruire effettivamente il dataset ed eseguire l'esperimento di §4 resta un task futuro esplicito, non avviato qui.
