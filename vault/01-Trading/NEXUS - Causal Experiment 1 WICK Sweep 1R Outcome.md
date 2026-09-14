# NEXUS Causal Research — Experiment 1: WICK Sweep +1R-before−1R

Segue [[NEXUS - Unified Level Engine Phase E Final Soak and Research Handoff]] (commit `5c40233`, READY_FOR_CAUSAL_RESEARCH). Primo esperimento di **discovery**, non di ottimizzazione. `WICK_SWEEP_REV` resta una negative research baseline: nessun parametro della strategia è stato toccato, nessuna nuova strategia creata, execution/risk invariati.

## 0. File prodotti

| File | Contenuto |
|---|---|
| `server/research_scripts/NXS_ResearchExportBars.mq5` | **nuovo**, script standalone (NON parte di `NEXUS_EA_v2.mq5`, zero rischio per l'EA di produzione) — esporta barre M1/M15 storiche in CSV per calcolare offline il path di prezzo futuro |
| `server/research_scripts/causal_experiment_1_wick_sweep_1r.py` | **nuovo** — costruisce il dataset causale dagli eventi `[LEVELENGINE][EVENT]` + barre M1 |
| `server/research_scripts/causal_experiment_1_analysis.py` | **nuovo** — analisi univariata, train/OOS, albero diagnostico |
| `results/causal_experiment_1/wick_sweep_1r_dataset.csv` / `.json` | **nuovo** — dataset machine-readable, 195 record |
| `MQL5/Include/NEXUS_v1/NXS_ReactionEngine.mqh` | **modificato** — aggiunti i campi `price` e `touch_count` al log diagnostico `[LEVELENGINE][EVENT]` (già esistente da Fase B, gate `InpLevelRegistry_WickEventLog`, default `false`): valori già scritti da hook causali esistenti (Fase A/C), solo non ancora stampati. Nessuna nuova decisione, nessun nuovo hook di scrittura. Verificato: sha256(NEXUS_trades.csv) identico prima/dopo la modifica su W1 (`979325de...48a9d44`) — zero effetto sul trading. |

Nessun'altra modifica di codice. Legacy, execution, risk, strategy registry, Global New-Bar Gate, `NXS_Structure.mqh`, `NXS_Reaction.mqh`: invariati.

## 1. Dataset schema

Una riga per **evento di sweep valido** (livello WICK_SWEEP_REV che raggiunge `state=SWEPT`), colonne:

```
event_id, level_id, timestamp, side, direction, level_price, entry_ref,
created_time, level_age_seconds, touch_count_before_sweep, penetration_pips,
sweep_depth_pips, session_bucket, hour, day_of_week, source_tf, window_id,
outcome, time_to_outcome_seconds
```

`level_id`/`event_id` sono prefissati per finestra (`W1_23`, `W2_5`, ...) — negli eventi grezzi vengono azzerati a ogni run del Tester, quindi il prefisso `window_id` è indispensabile per evitare collisioni nel dataset combinato.

**Fonte dati**: 3 finestre Phase E (Model=1, `InpLevelRegistry_WickReadPath=true`, stesse già validate: W1 2026-06-01→06-30, W2 07-01→07-31, W3 07-31→08-25), rieseguite con `InpLevelRegistry_WickEventLog=true` per ottenere il log evento-per-evento. sha256(NEXUS_trades.csv) di W1 riverificato identico alla fixture già nota — nessuna deriva introdotta dal logging aggiuntivo.

## 2. Causal integrity audit

Ogni feature è stata verificata esplicitamente contro il rischio di lookahead:

| Feature | Fonte | Timestamp di disponibilità causale | Verifica |
|---|---|---|---|
| `level_id`, `side`, `direction`, `level_price` | evento SWEEP stesso | = observation timestamp | scritti dall'hook causale nello stesso istante dello sweep (Fase A/C), mai modificati dopo |
| `entry_ref` | ricalcolato da `level_price ± penetration_pips*pip` | = observation timestamp | **stessa identica formula** usata dal codice per `s.entryRef` (mai un calcolo indipendente nuovo) |
| `created_time` | evento CREATE dello stesso `level_id` | < observation timestamp (per costruzione, la creazione precede sempre lo sweep) | verificato `created_time <= sweep_timestamp` per ogni record (0 incoerenze, vedi §3) |
| `level_age_seconds` | derivata (`sweep_timestamp - created_time`) | = observation timestamp | pura aritmetica su due timestamp già causali |
| `touch_count_before_sweep` | campo `touch_count` del registro, letto AL MOMENTO dell'evento SWEEP (non a fine vita del livello) | = observation timestamp | **critico**: il campo è mutabile nel tempo (continua a incrementare dopo lo sweep se il livello viene ritoccato) — qui è stato catturato lo snapshot esatto al print dell'evento SWEEP stesso, non letto a posteriori dallo stato finale del livello |
| `penetration_pips` / `sweep_depth_pips` | campo `pen` dell'evento SWEEP | = observation timestamp | per definizione di schema (Fase A), congelato al primo sweep, non più aggiornato dopo |
| `session_bucket`, `hour`, `day_of_week` | derivati da `timestamp` dell'evento SWEEP | = observation timestamp | pura funzione del timestamp causale |
| **OUTCOME** (`+1R`/`-1R`/`CENSORED`) | cammino barre M1 **strettamente successive** all'observation timestamp | > observation timestamp (futuro, per definizione — è l'etichetta) | **mai** usato come feature |

**Esplicitamente NON usati come feature** (avrebbero introdotto lookahead): massimo/minimo successivo allo sweep, risultato del trade legacy, exit reason, MFE/MAE futuro, reclaim successivo (il campo `reclaim_time` del registro non è mai letto per costruire feature — per WICK_SWEEP_REV resta comunque sempre vuoto, la strategia non attende reclaim), stato finale del livello (`consumed`/`invalidated` a fine run — MAI letti, solo lo stato AL MOMENTO dello sweep).

**`state` finale del livello (SWEPT/RECLAIMED/CONSUMED/INVALIDATED a fine run)**: marcato **NOT_CAUSALLY_RECOVERABLE come feature di questo esperimento** — il campo esiste nel registro ma rappresenta uno stato *successivo* allo sweep per definizione (un livello passa a CONSUMED solo dopo che il trade legacy è stato aperto, evento posteriore all'observation timestamp) — non è mai stato usato.

**Label calcolato separatamente dal trade legacy** (come richiesto): 1R = 25 pip simmetrico dal prezzo di sweep, indipendente dal vecchio SL25/TP100 asimmetrico della strategia. Il trade reale aperto dal legacy (quando non bloccato da throttle/duplicateRetrigger) NON è mai stato usato come sorgente della label — la label deriva esclusivamente dal cammino delle barre M1.

## 3. Data quality report

| Metrica | Valore |
|---|---|
| Eventi sweep totali (livelli con almeno 1 evento SWEEP) | **195** |
| Con label risolto (+1R o -1R) | **190** |
| Censored (nessuna soglia raggiunta entro i dati disponibili) | **0** |
| Ambiguous same-bar (entrambe le soglie nella stessa barra M1 — non imputato, escluso) | **5** |
| Livelli con sweep duplicati (stesso `level_id`, >1 evento SWEEP) | **0** |
| `level_id` duplicati nel dataset finale (dopo prefisso finestra) | **0** |
| `event_id` duplicati nel dataset finale | **0** |
| Missing `created_time` | **0** |
| Record incoerenti (`created_time` dopo lo sweep) | **0** |
| Livelli totali creati (per contesto, non tutti arrivano a SWEPT) | 617 |

**Nessuna imputazione silenziosa**: i 5 ambiguous e gli eventuali censored (0 in questo caso) sono esclusi dall'analisi di esito, mai forzati a +1R o -1R.

### Distribuzione per finestra
`W1=75, W2=60, W3=60` (195 totali)

### Distribuzione per sessione (su 195)
`NY=90, ASIA=68, LONDON=30, LATE=7`

### Distribuzione long/short (su 195)
`BUY=100, SELL=95`

## 4. Train / OOS split

Split **cronologico**, dichiarato prima di guardare i risultati per-feature (coerente con la preferenza di Phase E): **TRAIN = W1+W2** (n=133 risolti), **OOS = W3** (n=57 risolti).

**Dichiarazione esplicita**: n=57 in OOS è sotto la soglia di robustezza ideale per confronti multi-bucket — alcuni bucket OOS scendono a n=6-10 (es. `Friday & YOUNG`, `LATE`). Ogni confronto train/OOS con bucket OOS <30 va letto come indicativo, non conclusivo — segnalato caso per caso sotto.

## 5. Base rate incondizionato

**104/190 = 0.547** (+1R prima di -1R, su tutti gli eventi risolti, entrambe le direzioni).

Nota di coerenza (non un edge): un base rate simmetrico leggermente sopra 0.5 **non contraddice** il PF storico <1 della strategia reale — il legacy usa SL25/TP100 (asimmetrico 1:4), quindi deve raggiungere +4R prima di -1R, una soglia molto più difficile da toccare per prima di quanto non lo sia +1R simmetrico. I due numeri misurano cose diverse e sono entrambi corretti.

## 6. Analisi per feature (univariata)

Formato: `n | rate | uplift vs base | CI95 (Wilson) | train / OOS | stessa direzione`.

| Feature | Bucket | n | rate | uplift | CI95 | train | OOS | stessa direz. |
|---|---|---|---|---|---|---|---|---|
| **Direction** | BUY | 99 | 0.556 | +0.008 | [0.457,0.650] | 0.539 | 0.609 | NO |
| | SELL | 91 | 0.538 | −0.009 | [0.437,0.637] | 0.544 | 0.529 | SI |
| **Session** | ASIA | 66 | 0.545 | −0.002 | [0.426,0.660] | 0.511 | 0.632 | NO |
| | LONDON | 30 | 0.533 | −0.014 | [0.361,0.698] | 0.609 | 0.286 | NO |
| | NY | 87 | 0.563 | +0.016 | [0.459,0.663] | 0.550 | 0.593 | SI |
| | LATE | 7 | 0.429 | −0.119 | [0.158,0.750] | — | — | n/a (n troppo piccolo) |
| **Day of week** | **Friday** | **35** | **0.657** | **+0.110** | **[0.492,0.792]** | **0.636** | **0.692** | **SI** |
| | Monday | 44 | 0.545 | −0.002 | [0.401,0.683] | 0.567 | 0.500 | NO |
| | Tuesday | 38 | 0.579 | +0.032 | [0.422,0.721] | 0.480 | 0.769 | NO |
| | Wednesday | 41 | 0.463 | −0.084 | [0.321,0.613] | 0.516 | 0.300 | SI (OOS n=10, sotto soglia) |
| | Thursday | 32 | 0.500 | −0.047 | [0.336,0.664] | 0.520 | 0.429 | SI |
| **Hour bucket** | 00-06 | 57 | 0.526 | −0.021 | [0.399,0.650] | 0.474 | 0.632 | NO |
| | 06-12 | 37 | 0.541 | −0.007 | [0.384,0.690] | 0.600 | 0.286 | NO |
| | 12-18 | 67 | 0.582 | +0.035 | [0.463,0.693] | 0.587 | 0.571 | SI |
| | 18-24 | 29 | 0.517 | −0.030 | [0.344,0.686] | 0.474 | 0.600 | NO |
| **Level age** (soglia = mediana 5.8h) | OLD (≥median) | 102 | 0.578 | +0.031 | [0.481,0.670] | 0.556 | 0.633 | SI |
| | YOUNG (<median) | 88 | 0.511 | −0.036 | [0.409,0.613] | 0.525 | 0.481 | SI |
| **Touch count** | touch=1 (100% dei casi) | 190 | 0.547 | 0.000 | [0.476,0.617] | 0.541 | 0.561 | — (nessuna varianza) |
| **Penetration** (soglia = mediana 73 pip, range 35-590) | SHALLOW (<median) | 95 | 0.547 | 0.000 | [0.447,0.644] | 0.523 | 0.600 | NO |
| | DEEP (≥median) | 95 | 0.547 | 0.000 | [0.447,0.644] | 0.559 | 0.519 | NO |

### Osservazioni chiave

- **Touch count è degenere in questo dataset**: il 100% degli eventi ha esattamente `touch_count=1` prima dello sweep (nessuna varianza) — per come è costruito il codice legacy, un tocco del livello grezzo precede quasi sempre lo sweep in una singola sequenza continua. La feature non può discriminare nulla qui, non per assenza di segnale ma per assenza di variazione da misurare.
- **Penetration è nettamente nulla**: SHALLOW e DEEP danno **esattamente** lo stesso rate aggregato (0.547=0.547) — nessuna relazione osservabile tra quanto il prezzo sfonda il livello e l'esito a 1R simmetrico.
- **Direction, Session, Hour**: tutti i bucket restano entro rumore del base rate (CI ampiamente sovrapposti a 0.5 e al base rate), nessuna direzione stabile di rilievo (la maggior parte cambia segno tra train e OOS).
- **Day of week — Friday** è l'unico pattern con: campione ≥30 (35), uplift materialmente diverso dal base rate (+0.110, ~20% relativo), **stessa direzione in train e OOS**. Discusso come ipotesi in §9.
- **Level age**: direzione stabile (OLD sopra il base rate, YOUNG sotto, in entrambi train e OOS) ma magnitudo debole e CI ampiamente sovrapposto a 0.5.

## 7. Modello diagnostico (albero shallow manuale, depth 2)

Nessuna libreria ML disponibile in questo ambiente (no sklearn) — implementato a mano un albero shallow interpretabile (split1 = Friday/NotFriday, split2 = level age vs mediana), esclusivamente diagnostico, non una strategia:

**TRAIN (W1+W2)**
```
Friday                n=22  rate=0.636
  Friday & OLD        n=14  rate=0.571
  Friday & YOUNG      n=8   rate=0.750
NotFriday              n=111 rate=0.523
  NotFriday & OLD     n=58  rate=0.552
  NotFriday & YOUNG   n=53  rate=0.491
```

**OOS (W3)**
```
Friday                n=13  rate=0.692
  Friday & OLD        n=7   rate=0.857
  Friday & YOUNG      n=6   rate=0.500
NotFriday              n=44  rate=0.523
  NotFriday & OLD     n=23  rate=0.565
  NotFriday & YOUNG   n=21  rate=0.476
```

**Lettura**: lo split di primo livello (Friday) è stabile (direzione concorde train/OOS, come già visto in univariata). Lo split di secondo livello (age dentro Friday) **si inverte** tra train (YOUNG migliore) e OOS (OLD migliore) su campioni di 6-14 osservazioni — chiara evidenza di overfitting/rumore al secondo livello, non un pattern reale. Il modello conferma quindi Friday come UNICO split degno di nota, e scoraggia esplicitamente di andare più in profondità con questi dati.

## 8. Strongest positive / negative findings

**Più forte (positivo)**: Friday, +0.110 di uplift, direzione stabile train/OOS, ma CI95 [0.492,0.792] include ancora 0.5.
**Più forte (negativo/nullo)**: Penetration — nullo quasi esatto (uplift 0.000 su entrambi i bucket); Touch count — degenere (zero varianza).

## 9. Confounders / limitazioni

1. **Model=1, non real-tick**: questo intero dataset deriva dalle 3 finestre Phase E eseguite in Model=1 (barre open-price per la simulazione strategica). Il path di prezzo per l'etichetta usa barre M1 reali (più fine della simulazione Model=1 della strategia stessa), ma la STRATEGIA che genera gli eventi di sweep è comunque quella osservata sotto Model=1. Qualunque `PROMISING_HYPOTHESIS`/`WEAK_HINT` qui **richiede conferma su dati più rigorosi (real-tick, Model=4, se/quando eseguibile)** prima di diventare candidata per qualunque strategia. Discovery evidence ≠ execution evidence.
2. **Confronti multipli**: 7 feature × 2-5 bucket ciascuna = ~25 confronti univariati eseguiti. Nessuna correzione formale per test multipli è stata applicata — con questo numero di confronti, trovare per caso un bucket con uplift moderato e direzione concorde train/OOS non è sorprendente. Questo pesa esplicitamente contro l'elevare Friday a `PROMISING_HYPOTHESIS` (vedi §10).
3. **Campione assoluto piccolo**: 190 eventi risolti su 3 mesi. OOS = 57 (alcuni bucket OOS <30).
4. **Possibile autocorrelazione seriale**: gli eventi entro la stessa finestra/periodo di mercato non sono necessariamente indipendenti (regimi di volatilità condivisi) — gli intervalli di confidenza di Wilson assumono osservazioni iid, assunzione probabilmente violata in parte.
5. **`session_bucket` è un'approssimazione**: bucket su ora del server MT5, non convertita a un fuso broker/UTC verificato con certezza.
6. **5 eventi ambiguous_same_bar esclusi**: a risoluzione M1 restano comunque 5 casi (2.6%) dove entrambe le soglie ±1R cadono nella stessa barra — non decidibile con questi dati, correttamente escluso invece di indovinato.

## 10. Anti-data-mining gate — shortlist

| Pattern | Sample | Uplift | Direzione train/OOS | Plausibilità economica | Nessun lookahead | Non da combinazione post-hoc | Classificazione |
|---|---|---|---|---|---|---|---|
| Friday | 35 (22+13) | +0.110 | Concorde | Plausibile (posizionamento pre-weekend, minor follow-through) | Sì | Sì (day-of-week era una feature pre-dichiarata in Phase E, Friday è una categoria naturale non scelta dopo aver visto il risultato) | **WEAK_HINT** (non promosso a PROMISING_HYPOTHESIS: CI95 include ancora 0.5, e la scoperta emerge da uno scan di ~25 confronti senza correzione — troppo vicino al rumore per un impegno più forte) |
| Level age (OLD > YOUNG) | 102/88 | +0.031/−0.036 | Concorde | Debole (nessuna narrativa economica forte proposta) | Sì | Sì | **WEAK_HINT** (magnitudo troppo debole) |
| Direction, Session, Hour, Penetration, Touch count | vari | ~0 o incoerente | Perlopiù discorde o nulla | — | Sì | — | **NO_SIGNAL** |

**Nessun `PROMISING_HYPOTHESIS` dichiarato in questa fase.** Nessun `CONFIRMED_EDGE` (vietato dal task, e comunque non ci sarebbe stata base per dichiararlo).

## Verdict finale

### **HYPOTHESES_FOUND_NEED_CONFIRMATION**

Motivazione: 2 pattern (Friday, level age) mostrano direzione dell'effetto stabile tra train e OOS con una spiegazione economica non implausibile, ma **nessuno dei due supera la soglia di `PROMISING_HYPOTHESIS`** dichiarata (CI95 include sempre 0.5, campioni modesti, nessuna correzione per confronti multipli). Non è un `NO_DISCOVERABLE_SIGNAL` puro (ci sono fili da tirare, non solo rumore piatto), ma richiedono esplicitamente più dati (finestre aggiuntive, idealmente real-tick) prima di qualunque ulteriore passo — che resta, in ogni caso, fuori scope per questo task (nessuna strategia va implementata da questi risultati).
