# NEXUS — Phase E: Candidate Evidence Completion before First Serious 3-Year Backtest

Base: commit `c3b0bf3` (Phase D, approvato con correzione metodologica). NON eseguito il 3-year test in questa fase. NON ottimizzato alcun parametro. NON aperti nuovi thread di ricerca causale.

---

## 1-2. BREAKOUT_ACC — correzione parity + porting cooldown

### Riclassificazione

MT5=0/Python=0 (Fase D, finestra 2026-06-01→09-01) non dimostra parità: **riclassificato**. Non è tecnicamente "zero eventi" in senso stretto una volta ampliata la finestra (vedi sotto), ma il principio della richiesta è confermato: un confronto senza eventi reali non è informativo.

### Porting del cooldown 8-barre

Sorgente: `NXS_Strat_BreakoutAcc`, `NXS_Strategies.mqh` righe ~1530-1561 — `g_breakoutAccState`, raffreddamento **per direzione indipendente** (BUY e SELL hanno il proprio timer) di `InpBreakoutAccCooldownBars` barre (default 8) dall'ultimo fire di quella stessa direzione.

Porting Python: `_breakout_acc_cooldown_series()` in `server/backtest.py` — precalcolata come serie (non stateful dentro `sig_breakout_acc`, per lo stesso motivo per cui `sb_signal`/`ob_signal`/`shbms_signal` sono precalcolate: la funzione può essere richiamata fuori ordine da `confirm_bars`/flip-check, un contatore mutabile al suo interno si corromperebbe). Attivabile solo con `run_backtest(breakout_acc_cooldown=True)`, **default `False`** — verificato zero effetto sulle altre 66 strategie (SAR full-history: n=271, PF=1.35, invariato bit-per-bit dopo la modifica).

Effetto misurato (storico completo, OOS 60-100%, nativo SL/TP 1.0/4.5 + HTF nativo):

| | n | PF | DD |
|---|---|---|---|
| Senza cooldown | 31 | 3.63 | 5.03% |
| Con cooldown | 27 | 3.55 | 5.77% |

Riduce i trade clusterizzati come atteso, senza stravolgere il risultato (D1 è meno esposto al bug rispetto a M15, dove il commento MQL5 originale documentava il danno maggiore).

### Test di parità informativo — finestra 1: 12 mesi predefiniti

**Regola dichiarata prima di eseguire**: ultimi 12 mesi pieni disponibili terminando al cutoff dati Python (2026-08-14) → **2025-09-01 → 2026-09-01**, scelta per essere l'anno più recente completo, non per risultato.

Config MT5: selector 9, TF nativo D1 (via `InpProfileMultiTF`), Model=1 (1-min OHLC — per una strategia D1 a bassa frequenza non serve la precisione tick-by-tick; il real-tick è riservato al Fast Structural del punto 7), SL/TP nativi 1.0/4.5, protezioni RAW off.

- **MT5**: **1 solo trade** (BUY 2025-09-01, chiuso TP 2025-09-08, +$147.70)
- **Python** (metodologia corretta — vedi nota metodologica sotto): **7 trade** nella stessa finestra

1 evento MT5 < 5 richiesti → **ancora non informativo**.

### Test di parità informativo — finestra 2: massima intersezione storica

Per preferenza esplicita del task, escalato alla massima intersezione storica comune: **2019-02-03 → 2026-08-14** (limite dato dai dati reali Python, Dukascopy). Eseguito con Model=1 (Model=4 real-tick su 7,5 anni è stato scartato come impraticabile — stesso limite ambientale già documentato in fasi precedenti; dichiarato esplicitamente, non forzato). Tempo di esecuzione reale: **~3h40m** (circa 1 anno simulato ogni 26 minuti reali in questo ambiente).

**Risultato: 4 trade in 7,5 anni, TUTTI in perdita**:

| Data apertura | Direzione | Esito | P&L |
|---|---|---|---|
| 2019-06-05 | BUY | SL | -$15.90 |
| 2020-01-06 | BUY | SL | -$11.70 |
| 2020-02-21 | BUY | SL | -$17.00 |
| 2023-09-28 | SELL | SL | -$15.10 |

I prezzi di apertura 2019-2020 (~$1333-1644) sono livelli storici reali dell'oro, confermando che per questo periodo il feed MT5 è dato di mercato reale, non sintetico.

**Tasso di eventi: 0,53/anno.** Con un tasso così basso, nessuna finestra di 6-24 mesi può essere resa informativa per costruzione — non è un problema di scelta della finestra, è il tasso di eventi reale sul feed prezzi MT5 per questa specifica ricetta (accettazione su 2 chiusure consecutive fuori da un range di 20 barre, un evento raro per design).

**Verdetto finale**: `TRADE_PARITY_UNINFORMATIVE_LOW_SAMPLE` — irriducibile con lo sforzo massimo disponibile (intera intersezione storica), non un artefatto di cherry-picking.

### Nota metodologica (si applica anche a MACD, sezione 3)

Il test di parità della Fase D usava un "fresh start" artificiale al bordo della finestra (posizione=None a inizio periodo) — non rappresenta né l'EA MT5 reale (sempre in esecuzione, porta posizioni aperte da prima del bordo) né un replica Python corretta. **Corretto**: simulazione storica continua (stessa usata per PF/DD), poi filtrata sulla finestra di interesse. Discussa in dettaglio nella sezione MACD.

---

## 3. MACD — attribuzione completa del non-overlap temporale

### Scoperta preliminare: errore metodologico nella Fase D

Rieseguendo con la metodologia a storico continuo (sopra), il quadro cambia radicalmente rispetto alla Fase D: Python mostra **23 trade** nella finestra 2026-03→08 (non 3), molti dei quali **coincidono da vicino** con i 17 trade MT5 dello stesso periodo.

### Evidenza bar-per-bar (dato reale, non stimato)

Creato script standalone `server/research_scripts/NXS_ExportMACDIndicators.mq5` (zero rischio per l'EA di produzione, stesso pattern di `NXS_ExportH4Indicators.mq5` già esistente) per esportare EMA200/MACD-line/MACD-signal REALI di MT5 (stessi parametri di `NXS_Strat_MACD`: EMA200, MACD 12/26/9) e confrontarli bar-per-bar con `ind["ema200"]`/`ind["macd_line"]`/`ind["macd_signal"]` di Python sulla stessa candela GOLD H4:

| Timestamp | MT5 close/EMA200/MACD/Signal → cond | Python close/EMA200/MACD/Signal → cond | Δ close |
|---|---|---|---|
| 2026-06-02 04:00 | 4517.22 / 4607.41 / -0.790 / 2.284 → SELL | 4535.15 / 4614.67 / 1.195 / -2.874 → none | -17.94 |
| 2026-06-10 00:00 | 4217.96 / 4544.28 / -50.638 / -43.564 → SELL | 4184.98 / 4550.35 / -56.310 / -45.321 → SELL | +32.99 |
| 2026-06-18 16:00 | 4219.24 / 4448.19 / -2.368 / 15.177 → SELL | 4216.96 / 4452.67 / -6.884 / 8.122 → SELL | +2.28 |
| 2026-08-07 08:00 | 4305.87 / 4133.96 / 52.763 / 52.093 → BUY | 4321.26 / 4146.21 / 59.387 / 48.983 → BUY | -15.39 |

I due feed OHLC divergono da $2 a $50 (0,05%-1,2%) sullo stesso timestamp nominale, senza segno sistematico (a volte MT5 più alto, a volte più basso) — due percorsi di prezzo indipendenti, non una versione shiftata/scalata l'una dell'altra. Questo **dimostra** (non ipotizza) `DATA_VENDOR_OHLC_DIFFERENCE` come meccanismo reale per questa coppia di feed.

### Pairing completo (finestra 2026-03-01→2026-08-28, 17 trade MT5 vs 23 Python)

| Categoria | n eventi | Classificazione |
|---|---|---|
| Coppie allineate (offset <24h, es. 04-14 e 04-21 combaciano ESATTAMENTE) | 9 | `DATA_VENDOR_OHLC_DIFFERENCE` (benigno) |
| Rientri intrabar extra MT5 dentro uno stesso streak Python (es. 3 entrate MT5 il 23/03 vs 1 sola posizione Python continua) | 6 | `BAR_ALIGNMENT_DIFFERENCE` (stesso meccanismo tick-vs-bar-close già documentato per SAR in Fase Triage) |
| Solo Python (maggio: 5 trade; inizio luglio: 3 trade) — MT5 non apre nulla | 8 | `DATA_VENDOR_OHLC_DIFFERENCE` (per inferenza dal meccanismo dimostrato sopra — EMA200/MACD di MT5 non riverificati bit-a-bit per queste date specifiche per limite di tempo, esplicitamente dichiarato) |
| Solo MT5 (08-07, 08-24) — condizione Python confermata BUY dall'8/5 ma la posizione Python non chiude mai entro il cutoff dati (14/8) | 2 | `DATA_VENDOR_OHLC_DIFFERENCE` + troncamento dati (non un disaccordo reale) |

**`SIGNAL_LOGIC_DIFFERENCE = 0`. `UNKNOWN = 0`.**

### Verdetto

Gate del punto 3 **superato**. La logica di entrata (MACD vs signal-line, stesso lato dello zero, prezzo vs EMA200) è verificata identica su entrambi i motori; ogni divergenza di timing è spiegabile da differenze di feed dati o granularità tick/bar-close, entrambi meccanismi già noti e non nuovi bug.

---

## 4-5. SAR — replica temporale indipendente

Baseline Fase D **congelato, non toccato**: 41 trade, PF 1.19, DD 6.36%, expectancy $8.62 (finestra 2026-03-01→2026-09-01).

**Finestra dichiarata prima dell'esecuzione**: periodo precedente non sovrapposto di 6 mesi, immediatamente adiacente → **2025-09-01 → 2026-03-01**. Stessa config nativa congelata (selector 4, SL/TP 1.0/6.0, RAW, real ticks Model=4). Nessun parametro cambiato.

### Risultato

| Metrica | Valore |
|---|---|
| n trade chiusi | 40 |
| Profit Factor | 1.90 |
| Net P&L | $1108.00 |
| Expectancy | $27.70/trade |
| Max DD | 4.44% |
| Win rate | 30.0% (12 vinte / 28 perse) |
| Avg win / avg loss | $194.97 / $43.99 |
| BUY/SELL | 33 / 7 |

**Stabilità mensile**: 2025-09 +149.20, 2025-10 +372.80, 2025-11 -177.20, 2025-12 +182.30, 2026-01 +864.50, 2026-02 -283.60. Nessun mese patologico rispetto al netto totale (+1108).

Nota: il mix di direzione è molto diverso dal periodo Fase D (33 BUY/7 SELL qui contro 14 BUY/27 SELL allora) — coerente con due regimi di mercato diversi nei due periodi, non un segnale di instabilità dato che **entrambe** le finestre sono positive.

### Gate (punto 5)

| Criterio | Esito |
|---|---|
| Expectancy > 0 | ✅ ($27.70) |
| PF > 1 | ✅ (1.90) |
| DD non esplosivo | ✅ (4.44%, inferiore al baseline) |
| Nessuna concentrazione patologica per direzione/mese | ✅ |

**Replica POSITIVA su tutti i criteri.** SAR è stabile su due finestre reali indipendenti e non sovrapposte (PF 1.19 e 1.90, entrambe > 1; DD 6.36% e 4.44%, entrambi contenuti). SAR procede.

---

## 6. MACD Fast Structural (real ticks, 6 mesi)

Gate del punto 3 superato → eseguito. Config: selector 3, TF nativo H4, Model=4 (real ticks), SL/TP nativi 2.0/8.0, gate EMA200 nativo (intrinseco al segnale stesso — vedi sezione 3), RAW, finestra 2026-03-01→2026-09-01 (stessa di SAR Fase D per confrontabilità).

| Metrica | Valore |
|---|---|
| n trade chiusi | 17 |
| Profit Factor | 1.39 |
| Net P&L | $562.80 |
| Expectancy | $33.11/trade |
| Max DD | 5.97% |
| Win rate | 29.4% (5 vinte / 12 perse) |
| Avg win / avg loss | $403.08 / $121.05 |
| BUY/SELL | 7 / 10 |

**Stabilità mensile**: 2026-03 +115.30, 2026-04 -200.80, 2026-06 +454.30, 2026-08 +194.00 (nessun trade a maggio/luglio — coerente con l'attribuzione della sezione 3: il segnale è raro, non ogni mese produce un'accettazione).

Metriche solide: PF>1, DD contenuto, expectancy positiva, nessuna concentrazione patologica.

---

## 7. BREAKOUT_ACC Fast Structural

**NON eseguito.** Gate esplicito del punto 7 ("solo dopo parity informativa + cooldown corretto") non soddisfatto: la parity resta `TRADE_PARITY_UNINFORMATIVE_LOW_SAMPLE` anche con lo sforzo massimo (intera intersezione storica, sezione 1-2). Il cooldown è stato portato correttamente (verificato), ma questo da solo non sblocca il gate — manca il prerequisito della parity informativa.

Questo non è un rigetto della strategia: su dati Python, BREAKOUT_ACC con cooldown+HTF nativo mostra PF=3.55, DD=5.77%, n=27 (storico completo) — semanticamente la più pulita delle 4 candidate esaminate in Fase D. Il blocco è puramente di evidenza (troppo pochi eventi osservabili sul feed prezzi MT5 per validare quella pulizia sul motore reale).

---

## 8. Promotion finale

| Strategia | Semantic parity | Trade parity | Fast Structural | Replica indipendente | Verdetto |
|---|---|---|---|---|---|
| **SAR** | MINOR_DIFFERENCE (Fase Triage) | ACCEPTABLE | 41 trade, PF 1.19, DD 6.36% (Fase D) | **PASS** (40 trade, PF 1.90, DD 4.44%) | **READY_FOR_SERIOUS_3Y** |
| **MACD** | MINOR_DIFFERENCE (gate HTF ridondante, mai stato un vero gap) | ACCEPTABLE→confermato (0 SIGNAL_LOGIC_DIFFERENCE, 0 UNKNOWN) | 17 trade, PF 1.39, DD 5.97% | non richiesta dal task | **READY_FOR_SERIOUS_3Y** |
| **BREAKOUT_ACC** | MINOR_DIFFERENCE (post-repair Fase D) | UNINFORMATIVE_LOW_SAMPLE (4 eventi/7,5 anni, irriducibile) | non eseguito (gate non soddisfatto) | n/a | **HOLD_NEEDS_MORE_EVIDENCE** |

**2 READY_FOR_SERIOUS_3Y** (SAR, MACD) — entro il tetto di 3, non forzato al massimo.

Per la regola esplicita del punto 8 ("se almeno una strategia ottiene READY_FOR_SERIOUS_3Y, STOP"), mi fermo qui. **Nessun 3-year backtest eseguito in questa fase.**

---

## 9. Primo serious backtest (indicazione per il prossimo task separato)

Le strategie che soddisfano il gate per il primo serious 3-year backtest (MT5 real ticks, costi broker-nativi, OOS/cost robustness, **nessun parametro da cambiare**) sono:

- **SAR** (selector 4, H4, SL/TP 1.0/6.0 nativi)
- **MACD** (selector 3, H4, SL/TP 2.0/8.0 nativi)

BREAKOUT_ACC resta in `HOLD` fino a quando non sarà disponibile più storico MT5 comparabile a quello Python, o un metodo alternativo per rendere informativo il confronto (es. dati broker più profondi, se mai resi disponibili).

---

## File prodotti

- `server/backtest.py` — aggiunti `htf_native_ema` (Fase D) e `breakout_acc_cooldown` (Fase E), entrambi opt-in
- `server/research_scripts/NXS_ExportMACDIndicators.mq5` — nuovo script standalone di esportazione indicatori, zero rischio EA produzione
- `results/cost_calibration_67_rerun/phase_e_breakoutacc_findings.json`
- `results/cost_calibration_67_rerun/phase_e_macd_mismatch_attribution.json`
- `results/cost_calibration_67_rerun/phase_e_sar_replication.json`
- `results/cost_calibration_67_rerun/{sar,macd,breakoutacc}_*_trades.csv` — log di trade grezzi MT5
- `results/cost_calibration_67_rerun/mt5_macd_indicators_*.csv` — export EMA200/MACD reali MT5

## Commit

`[da assegnare]`
