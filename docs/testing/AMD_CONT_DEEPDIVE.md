# AMD_CONT — approfondimento completo, protocollo NQROS v3.1

Prima strategia scelta per l'approfondimento serio "una alla volta" (deciso
dall'utente il 04/08). Scelta su AMD_CONT invece degli altri candidati
Fase-1 perché ha il campione più ampio (64 trade su H4) tra quelli con
PF/WR già decenti, ed è una scoperta nuova di questa sessione (prima esclusa
per errore di giudizio — "nessun TF pulito", smentito dalla Fase 1
multi-timeframe).

## Domanda guida (prima di ogni fase)

"Sto capendo meglio la strategia o sto solo spingendo il PF?" — applicata ad
ogni step sotto. Un caso di "solo spingere" c'è stato davvero (vedi Fase 4)
ed è stato bocciato dal gate, non nascosto.

## Fase 1 — Baseline multi-TF

Da `multi_tf_baseline.py`: miglior TF = H4, PF 1.62, 64 trade, WR 50.0%,
ExpR 0.358, MaxDD 6.47% (parametri default: SL 1.5×ATR, TP 3.0×ATR, nessuna
gestione).

## Fase 2 — Anatomia

Da `anatomy_analysis.py`, sullo stesso H4 baseline:
- Uscite vincenti: 29 TP + 3 TIME (durata media 25.3 barre)
- Uscite perdenti: 32 SL (durata media 13.2 barre)
- MFE medio vincite: 2.24R — MAE medio vincite: 0.42R (ingresso pulito quando funziona)
- Perdite "segnale sbagliato" (MFE<0.3R): 12/32 (38%)
- Perdite "quasi vincenti" (MFE≥0.5R, andate a favore poi girate): 14/32 (44%)

Lettura: quasi la metà delle perdite erano trade che si muovevano nella
direzione giusta prima di girare — indizio che il bottleneck è più
probabile in gestione posizione (Fase 6) che nel segnale d'ingresso.

## Fase 3 — Toggle (un parametro alla volta, baseline invariato)

| Toggle | PF | Trade | WR% | ExpR | MaxDD% |
|---|---|---|---|---|---|
| *(baseline)* | 1.62 | 64 | 50.0 | 0.358 | 6.47 |
| htf_filter=True | 1.41 | 54 | 46.3 | 0.256 | 6.42 |
| **confirm_bars=1** | **2.27** | **22** | **59.1** | **0.60** | **2.13** |
| confirm_bars=2 | 0.00 | 1 | — | — | — |
| cooldown_bars=3 | 1.60 | 60 | 50.0 | 0.354 | 6.47 |
| cooldown_bars=6 | 1.54 | 57 | 49.1 | 0.325 | 7.54 |
| loss_cooldown_bars=3 | 1.58 | 62 | 50.0 | 0.334 | 6.47 |
| loss_cooldown_bars=6 | 1.47 | 60 | 48.3 | 0.28 | 7.54 |

`htf_filter` peggiora (ridondante con il filtro EMA200 già interno a
`sig_amd_cont`). `cooldown_bars`/`loss_cooldown_bars` neutri/negativi.
`confirm_bars=1` unico vincitore netto — ma con -66% di trade (64→22),
segnalato subito come sospetto prima ancora del gate.

## Fase 4 — Robustezza (GATE)

Split cronologico 60% in-sample (dove il toggle è stato trovato) / 40%
out-of-sample (mai visto prima), su H4 (~2 anni totali, capped da Yahoo):

| Config | In-sample | Out-of-sample (costi retail) | Out-of-sample (costi stress) |
|---|---|---|---|
| **confirm_bars=1** | PF 3.39, 13tr, WR 69.2% | **PF 1.40, 9tr, WR 44.4%** | PF 1.32, 9tr, WR 44.4% |
| baseline (nessun toggle) | PF 1.58, 43tr, WR 48.8% | **PF 1.55, 22tr, WR 50.0%** | PF 1.47, 22tr, WR 50.0% |

### Verdetto

**`confirm_bars=1` NON supera il gate — bocciato.** Il salto di PF (1.62→2.27
in Fase 3, PF 3.39 nella metà in-sample) non regge fuori campione (crolla a
1.40, WR torna vicino al baseline 44% vs 69% "trovato"): è il segnale
classico di overfitting su un campione già ridotto a 22 trade, esattamente
il rischio segnalato prima di lanciare il test. **Ipotesi smentita** — va in
Fase 10 (diario), non si riprova in altre forme senza un'ipotesi nuova.

**Il baseline di AMD_CONT (nessun toggle) INVECE supera il gate in modo
pulito**: PF pressoché identico in-sample/out-of-sample (1.58 vs 1.55),
WR quasi identico (48.8% vs 50.0%), e resta positivo anche con costi
aumentati (PF 1.47 out-of-sample stress). Non è un caso di "edge sparito" —
è il toggle che era falso, non la strategia.

**Prosegue in Fase 5** (Money Management) con i parametri di baseline
(SL 1.5×ATR, TP 3.0×ATR, nessun toggle d'ingresso) — non con `confirm_bars=1`.

## Fase 5 — Money Management (position sizing)

Unica leva del motore: `risk_pct` (rischio % fisso-frazionario, compounda
sull'equity corrente). Sweep a parità di tutto il resto (baseline Fase 4):

| risk_pct | PF | Return% | MaxDD% | Return/DD | Equity finale (da 10.000) |
|---|---|---|---|---|---|
| 0.25% | 1.65 | 5.84 | 1.65 | 3.54 | 10.584 |
| 0.5% | 1.64 | 11.92 | 3.28 | 3.63 | 11.192 |
| 0.75% | 1.63 | 18.24 | 4.88 | 3.74 | 11.824 |
| 1.0% | 1.62 | 24.81 | 6.47 | 3.83 | 12.481 |
| 1.5% | 1.60 | 38.68 | 9.56 | 4.05 | 13.868 |
| 2.0% | 1.58 | 53.54 | 12.58 | 4.26 | 15.354 |
| 3.0% | 1.55 | 86.25 | 18.35 | 4.70 | 18.625 |
| 4.0% | 1.51 | 122.82 | 23.81 | 5.16 | 22.282 |
| **5.0%** | **1.48** | **162.98** | **28.96** | 5.63 | 26.298 |

Nota: PF cala leggermente e Return/DD sale con `risk_pct` più alto — effetto
di compounding legato alla sequenza storica specifica di vincite/perdite di
*questo* backtest, non una legge generale (una sequenza diversa potrebbe
mostrare l'opposto). Non è un ottimo matematico: è una scelta di tolleranza
al rischio, non qualcosa che il backtest "risolve" da solo.

**Decisione dell'utente (04/08): `risk_pct = 5%`**, esplicitamente sopra la
raccomandazione iniziale (1%, motivata da MaxDD 6.47% e dal fatto che
AMD_CONT sarà una delle diverse strategie attive in parallelo, dove il
rischio si somma). Segnalato prima di fissarlo: **MaxDD 28.96% isolato**
significa un conto che scende quasi a 1/3 sotto il massimo nel punto peggiore
di questi ~2 anni di dati — con una sola strategia attiva; con più strategie
in parallelo allo stesso rischio, il rischio aggregato è più alto. Decisione
registrata come scelta esplicita dell'utente sul proprio capitale, non come
raccomandazione del motore.

## Fase 6 — Trade Management (TP/SL/breakeven/trailing)

Baseline post-Fase 5 (risk_pct=5%): PF 1.48, MaxDD 28.96%. Un parametro alla
volta:

| Parametro | Config | PF | Trade | WR% | ExpR | MaxDD% |
|---|---|---|---|---|---|---|
| SL | 1.0×ATR | 1.48 | 67 | 40.3 | 0.456 | 34.62 |
| SL | 2.0×ATR | 1.39 | 59 | 54.2 | 0.225 | 28.58 |
| SL | 2.5×ATR | 1.67 | 52 | 63.5 | 0.282 | 24.07 |
| TP | 2.0×ATR | 1.12 | 74 | 51.4 | 0.096 | 33.39 |
| TP | 4.0×ATR | 1.73 | 60 | 50.0 | 0.538 | 25.07 |
| TP | 5.0×ATR | 1.68 | 59 | 45.8 | 0.523 | 29.11 |
| Breakeven | 0.5R | 0.60 | 83 | 10.8 | -0.128 | 53.92 |
| Breakeven | 1.0R | 1.44 | 68 | 36.8 | 0.253 | 26.10 |
| Breakeven | 1.5-2.0R | ~1.48-1.49 | 64 | ~49 | ~0.355 | ~25-29 |
| Trailing | 1.0×ATR | 0.50 | 84 | 33.3 | -0.190 | 61.04 |
| Trailing | 1.5×ATR | 1.03 | 73 | 43.8 | 0.042 | 36.70 |
| Trailing | 2.0×ATR | 1.54 | 66 | 45.5 | 0.332 | 23.50 |

**Ipotesi Fase 2 smentita nella forma stretta**: il 44% di perdite "quasi
vincenti" (MFE≥0.5R) NON si risolve stringendo la gestione (breakeven/
trailing stretti sono catastrofici: PF crolla a 0.5-0.6, MaxDD esplode
oltre il 50% — bloccano lo stop troppo presto sui trade che sarebbero
tornati a favore). Si risolve invece dando PIÙ spazio: SL 2.5×ATR e TP
4.0×ATR, ciascuno da solo, sono i due vincitori netti.

### Combinazione dichiarata: SL=2.5×ATR + TP=4.0×ATR

PF 2.00, 51 trade, WR 62.7%, ExpR 0.427, MaxDD 24.07% — il miglior
risultato aggregato finora. Aggiungere trailing_atr=2.0 sopra peggiora
leggermente ExpR (0.427→0.248) in cambio di MaxDD più basso (24.07%→20.54%)
— non chiaramente meglio, scartato per ora.

### Ri-validazione Out-of-Sample (stessa disciplina della Fase 4)

Trovata via ricerca di parametri → stesso rischio di overfitting di
`confirm_bars=1` in Fase 4. Ri-testata con lo stesso split 60/40:

| | PF | Trade | WR% | ExpR | MaxDD% |
|---|---|---|---|---|---|
| In-sample | 2.01 | 33 | 60.6 | 0.395 | 24.07 |
| Out-of-sample (costi retail) | **1.99** | 18 | 66.7 | 0.486 | 12.65 |
| Out-of-sample (costi stress) | 1.93 | 18 | 66.7 | 0.464 | 13.08 |

**Regge** — PF praticamente identico in/out-of-sample (2.01 vs 1.99), WR e
MaxDD migliorano addirittura fuori campione. A differenza di
`confirm_bars=1`, questa combinazione supera il gate.

**Config corrente AMD_CONT**: H4, risk_pct=5%, SL=2.5×ATR, TP=4.0×ATR,
nessun breakeven/trailing.

## Fase 7 — Advanced (pyramiding/grid/recovery)

**Saltata deliberatamente**: il motore Python è a posizione singola, non
supporta piramidazione/grid/recovery. Costruire quella capacità sarebbe un
lavoro di motore vero, non un test — rimandata, non bloccante per il resto
della pipeline.

## Fase 8 — Stability (fatta prima della 7, su richiesta esplicita)

Griglia 3×3 attorno al vincitore SL=2.5/TP=4.0:

| SL\\TP | 3.5 | 4.0 | 4.5 |
|---|---|---|---|
| 2.25 | 2.06 | 1.89 | 1.83 |
| 2.5 | 1.97 | **2.00** | 1.94 |
| 2.75 | 1.82 | 1.84 | 1.77 |

Nessuna scogliera — PF resta in un range compatto (1.77–2.06) su tutti e 9 i
punti. **Config confermata robusta, non un picco isolato.**

## Approfondimento aggiuntivo — segmentazione per sessione

Non nel protocollo originale ma emerso da un'ipotesi Fase-2-style: AMD_CONT
opera su LONDON/OVERLAP/NY (gate interno alla strategia). Segmentando i 51
trade della config vincente per sessione:

| Sessione | Trade | WR% | PF | ExpR medio | NetPnL |
|---|---|---|---|---|---|
| LONDON | 9 | 66.7 | 2.54 | 0.428 | 3.342 |
| NY | 28 | 67.9 | 2.54 | 0.567 | 13.025 |
| OVERLAP | 14 | 50.0 | **1.10** | 0.147 | 619 |

OVERLAP chiaramente il ventre molle. Aggiunto `session_filter` al motore
(gate opzionale generico, riusabile su altre strategie a sessione) e
testato escludendo OVERLAP:

| | PF | Trade | WR% | ExpR | MaxDD% |
|---|---|---|---|---|---|
| Baseline (LONDON+OVERLAP+NY) | 2.00 | 51 | 62.7 | 0.427 | 24.07 |
| session_filter={LONDON,NY} | 2.01 | 48 | 64.6 | 0.413 | **12.64** |

PF invariato, **MaxDD quasi dimezzato**. Nota: i trade scendono solo da 51 a
48 (non a 37 come una sottrazione ingenua farebbe pensare) — togliere i
trade OVERLAP libera "slot" nel motore a posizione singola, riempiti da
segnali LONDON/NY successivi che prima venivano scartati perché una
posizione OVERLAP era già aperta.

### Ri-validazione Out-of-Sample

| | PF | Trade | WR% | ExpR | MaxDD% |
|---|---|---|---|---|---|
| In-sample | 1.92 | 30 | 63.3 | 0.343 | 12.62 |
| Out-of-sample (costi retail) | 1.72 | 18 | 61.1 | 0.386 | 12.64 |
| Out-of-sample (costi stress) | 1.66 | 18 | 61.1 | 0.364 | 13.07 |

**Regge, con un degrado onesto** (1.92→1.72, ~10% relativo — non un crollo
come `confirm_bars=1`, ma meno "di ferro" della combinazione SL/TP che non
si era praticamente mossa). WR e MaxDD restano stabili, resta profittevole
anche con costi aumentati.

**Config corrente AMD_CONT**: H4, risk_pct=5%, SL=2.5×ATR, TP=4.0×ATR,
`session_filter={LONDON,NY}` (esclude OVERLAP), nessun breakeven/trailing.

## Fase 9-10

Da fare.
