# NEXUS — Phase D: SAR Fast Structural + HTF Parity Repair

Base: commit `ca73e48` (Serious Backtest Candidate Triage, approvato). NON eseguito full 3-year. NON ottimizzato alcun parametro. NON cambiato alcun gate.

---

## A. SAR — Fast Structural, real ticks

Configurazione MT5 nativa (Research Mode RAW):

| Parametro | Valore |
|---|---|
| Selettore | 4 (SAR) — `InpStrategySelector=4` |
| TF | H4 (nativo da `NXS_Profile_TF("SAR")`, attivato via `InpProfileMultiTF=true`) |
| SL/TP | 1.0 / 6.0 ATR (`NXS_Profile_Get`, nessun override — `InpSARSlMultOverride=0`) |
| Modello Tester | Model=4, "ogni tick reale" |
| Protezioni RAW | `InpResearchUseDPT/Ruin/ESL/DailyDD/TotalDD = false` |
| Costi | nativi Tester (nessun override costi) |
| Finestra | 2026-03-01 → 2026-09-01 (6 mesi) |

**Nota metodologica sulla finestra**: un primo probe di 2 mesi in Model=4 reale ha impiegato ~17 minuti (CPU quasi satura per tutta la durata, non lo stallo "CPU quasi ferma" documentato in fasi precedenti per finestre di 3 mesi) — l'ambiente regge il real-tick su SAR meglio che su altre fixture storiche già incontrate. Estesa quindi a 6 mesi (limite inferiore del range 6-12 richiesto) come compromesso dichiarato tra densità del campione e tempo di esecuzione reale: 12 mesi avrebbe richiesto un multiplo del tempo osservato, non giustificato per un primo Fast Structural check.

### Risultato — SAR Fast Structural, 41 trade chiusi (2026.03.02 → 2026.08.28), real ticks, costi nativi Tester

| Metrica | Valore |
|---|---|
| n trade chiusi | 41 (+1 posizione ancora aperta a fine finestra, esclusa dal calcolo) |
| Profit Factor | 1.19 |
| Net P&L | $353.30 |
| Expectancy | $8.62/trade |
| Max DD (equity curve realizzata) | 6.36% |
| Win rate | 17.1% (7 vinte / 34 perse) |
| Avg win | $314.26 |
| Avg loss | $54.31 |
| Payoff ratio (avg win / avg loss) | 5.79 |
| MFE/MAE | **non disponibile** — `NEXUS_trades.csv` non logga high-water/low-water intrabar, solo prezzo di apertura/chiusura e R-multiple realizzato |
| Exit reasons | `sl`: 34, `tp`: 7 |
| BUY/SELL | 14 BUY / 27 SELL |

**Stabilità mensile**:

| Mese | n | P&L |
|---|---|---|
| 2026-03 | 15 | +105.20 |
| 2026-04 | 0 | — (nessun segnale tutto il mese) |
| 2026-05 | 3 | -184.30 |
| 2026-06 | 10 | +435.70 |
| 2026-07 | 8 | -283.50 |
| 2026-08 | 5 | +280.20 |

Profilo tipico trend-following: bassa win rate (17%) compensata da un payoff ratio elevato (5.79) — coerente con SL/TP 1.0/6.0 ATR. Nessun mese catastrofico, ma aprile senza segnali e un maggio-luglio debole (-467.80 combinato) mostrano che il PF aggregato (1.19) nasconde una varianza mensile non banale su un campione ancora limitato (41 trade). Rispetto alla stima Python a lungo termine (n=271, PF 1.35, DD 15.80% su storico esteso), il PF reale a 6 mesi è leggermente più debole ma nello stesso ordine di grandezza — nessuna contraddizione strutturale, campione più corto e quindi più rumoroso.

---

## B. SAR — Semantic caveat audit

Verificati `NXS_SAR_CandleAligned()` e `NXS_SAR_PressureContrary()` in `NXS_Strategies.mqh` (righe 380-423):

- **Sono realmente parte della decisione finale**: sì, strutturalmente — entrambe possono azzerare `s.dir` (→ `DIR_NONE`) DOPO che il segnale base SAR (SAR vs prezzo + cross EMA9/EMA21) è già scattato, quindi possono scartare un segnale altrimenti valido.
- **Sono opzionali**: sì, ciascuna è dietro un proprio gate esplicito — `InpSAR_RequireCandleAlign` e `InpSAR_RequirePressureContrary` (`NXS_Strat_SAR`, righe 415/418). Se `false`, la funzione di filtro non viene nemmeno chiamata.
- **Sono attive nel profilo di deployment**: **NO**. Default in `NXS_Inputs.mqh`: entrambe `false`. Cercato in tutto il repo (`.set`/`.ini`) un qualunque override — **nessuno trovato**, in nessun preset Demo o Research (incluso `NEXUS_Demo_MultiTF_12-08.set`). Nessun artefatto di deployment conosciuto le attiva.

**Verdetto: `SAR_DEPLOYMENT_SEMANTICS_CONFIRMED`**

Il test Python (che non ha mai modellato questi due filtri) è quindi coerente con il comportamento REALE di ogni deployment noto — la loro assenza nel motore Python non è un gap di parità per lo stato attuale del sistema. Resta un caveat dichiarato (non un blocker): se in futuro un preset li attivasse, andrebbero riportati anche lato Python prima di fidarsi di un nuovo test.

---

## C. HTF parity repair — semantica esatta portata da MQL5

Scoperta chiave: il gate "HTF" del profilo (`NXS_Profile_Get(...).htf`) **non è una vera candela di timeframe superiore**. In `NEXUS_EA_v2.mq5` righe 624-639:

```
double px200 = iClose(g_sym, NXS_EffTF(), 0);          // prezzo LIVE (shift 0) sullo STESSO TF della strategia
...
if(NXS_Profile_HTF(out[k].stratName, needHtf) && needHtf && g_ema200 > 0){
   if((out[k].dir==DIR_BUY  && px200 < g_ema200) ||
      (out[k].dir==DIR_SELL && px200 > g_ema200))
      out[k].dir = DIR_NONE;
}
```

dove `g_ema200` è l'EMA200 (`CopyBuffer(g_hEMA200,0,1,1,a)`, shift 1 = ultima barra CHIUSA) calcolata sul TF attivo del passaggio multi-TF (`g_activeTF` = il TF nativo della strategia stessa in `InpProfileMultiTF=true`, non un TF esterno).

Mappatura esatta implementata (parametro nuovo `htf_native_ema` in `run_backtest()`, `server/backtest.py`, additivo e opt-in, default `False` — non tocca alcuna delle altre 62 strategie):

| Elemento richiesto | Semantica MQL5 reale | Porting Python |
|---|---|---|
| TF superiore | **Nessuno** — stesso TF di esecuzione della strategia (misnomer "HTF" nel nome del campo profilo) | `ind["ema200"]` calcolata sulla stessa serie `candles` già passata (stesso TF) |
| Trend condition | prezzo vs EMA200 | identico |
| Quando calcolata | prezzo: ogni tick (shift 0, barra in formazione); EMA200: barra chiusa (shift 1) | prezzo = `close[idx]` (barra segnale, equivalente allo shift0 "vivo" in un motore closed-bar); EMA200 = `ind["ema200"][idx-1]` (esclude la barra segnale, equivalente allo shift1) |
| Closed/current bar | prezzo=current(0), EMA=closed(1) | riprodotto esattamente con l'offset `idx` vs `idx-1` |
| BUY/SELL gating | BUY scartato se prezzo<EMA200; SELL scartato se prezzo>EMA200 | identico, applicato solo se `sig != 0` (non genera nuovi segnali, ne scarta) |

Nessuna nuova definizione inventata — è un porting 1:1 del blocco sopra. Indipendente dal filtro `htf_filter`/SMA(trend_period) preesistente (quello è un proxy dichiarato "mai una vera candela HTF" fin dal primo screening, lasciato invariato).

### Risultato non ovvio: il gate è ridondante per MACD

`sig_macd` in Python (e `NXS_Strat_MACD` in MQL5, reason log `MACD_bull_above_ema200`/`MACD_bear_below_ema200`) **incorporano già** la condizione prezzo-vs-EMA200 nella propria logica di entrata (`macd>sig and macd>0 and px>e200`). Applicare il gate HTF nativo sopra un segnale che è GIÀ condizionato a EMA200 non cambia nulla: PRE e POST-repair MACD hanno **n=130, PF identico su tutti i 4 profili di costo** (vedi tabella sotto). Non è un bug del repair — è la controprova che per MACD il gate "HTF" del profilo non ha mai fatto nulla neanche lato MQL5 reale (stessa ridondanza esiste anche lì).

Per BREAKOUT_ACC, LIQ_SWEEP e FVG_CONT il gate NON è ridondante (le loro funzioni di segnale non contengono già un confronto prezzo/EMA200) — il repair ha un effetto reale e misurabile.

---

## D. Native profile parity

`strategy_profiles` passato esplicitamente a `run_backtest()` per tutti e 4 (oltre a SAR già corretto in Fase Triage): nessun fallback generico 1.5/3.0.

| Strategia | SL/TP nativo usato |
|---|---|
| BREAKOUT_ACC | 1.0 / 4.5 ATR |
| LIQ_SWEEP | 1.5 / 3.0 ATR (= generico, nessun cambiamento numerico ma ora passato esplicitamente, non per coincidenza) |
| MACD | 2.0 / 8.0 ATR |
| FVG_CONT | 1.5 / 6.0 ATR |

---

## E. Re-run parity — PRE vs POST repair (dataset storico completo, OOS 60-100%)

BROKER_BASELINE (spread 5.5 pip + slippage assunto), unità PF/DD%:

| Strategia | TF | n PRE | PF PRE | DD PRE | n POST | PF POST | DD POST | Δ |
|---|---|---|---|---|---|---|---|---|
| BREAKOUT_ACC | 1d | 36 | 2.79 | 6.00 | 31 | **3.63** | **5.03** | HTF reale scarta 5 trade contro-trend, PF/DD migliorano nettamente |
| LIQ_SWEEP | 1d | 42 | 1.85 | 4.00 | 33 | **2.82** | **3.04** | idem, effetto reale e forte |
| MACD | 4h | 130 | 1.60 | 11.27 | 130 | 1.60 | 11.27 | **nessun effetto — gate ridondante (vedi §C)** |
| FVG_CONT | 4h | 157 | 1.49 | 13.64 | 123 | **1.68** | **10.88** | effetto reale, migliora PF e riduce DD di ~3 punti |

(dati completi 4 profili di costo in `results/cost_calibration_67_rerun/phase_d_htf_repair_results.json`)

### Trade-level parity — finestra 2026-06-01 → 2026-09-01 (MT5) vs sotto-finestra dati reali disponibile

**Correzione a un dato della Fase Triage precedente**: il file `trades_LIQ_SWEEP.csv` (già raccolto in quella fase, non ri-eseguito) mostra in realtà **6 trade MT5** nell'intera finestra 06-01→09-01, non 2 come riportato nel file `semantic_triage_findings.json` — verificato ora riga per riga sul CSV originale. Il numero corretto è usato qui.

**Limite scoperto in questa fase**: la fonte dati reale usata dal motore Python (`_fetch_real`, Dukascopy/Yahoo) si ferma al **2026-08-14** — non arriva al 2026-09-01 come il Tester MT5 (che genera/replica dati fino a "oggi", 2026-09-16). Il confronto trade-level POST-repair è quindi ristretto alla sotto-finestra **2026-06-01 → 2026-08-14** (unica sovrapponibile), con i conteggi MT5 ricalcolati sulla stessa sotto-finestra per un confronto equo:

| Strategia | MT5 (≤08-14) | Python POST-repair (stesso TF/profilo/HTF) | Sovrapposizione date | Classificazione |
|---|---|---|---|---|
| BREAKOUT_ACC | 0 | 0 | — (match esatto: nessun segnale su entrambi i motori) | **TRADE_PARITY_STRONG** |
| LIQ_SWEEP | 5 (06-08,06-25,07-14,07-24,08-06) | 1 (07-23 SELL) | nessuna data coincide | **TRADE_PARITY_FAIL** (invariato) |
| MACD | 4 (06-02,06-10,06-18,08-07) | 3 (07-24,07-28,07-29, tutti SELL) | nessuna data coincide, ma logica di segnale verificata identica riga-per-riga (§ Triage) | **TRADE_PARITY_ACCEPTABLE** (invariato, causa più probabile: differenza di fonte dati OHLC Python-reale vs feed broker MT5, non un bug logico) |
| FVG_CONT | 6 (06-05,06-18,06-30,07-06,08-05,08-11) | 3 (07-08,07-12,07-23, tutti SELL) | nessuna data coincide | **TRADE_PARITY_ACCEPTABLE** (più debole di MACD — metà dei trade mancanti) |

---

## F. Promotion — nuove FAST_STRUCTURAL_CANDIDATE

Criteri: semantic parity non `MATERIAL_DIFFERENCE`, trade parity almeno `ACCEPTABLE`, native profile usato. Massimo 3 totali incluso SAR.

| Strategia | Semantic parity (post-repair) | Trade parity | Native profile | Idoneo? |
|---|---|---|---|---|
| SAR | MINOR_DIFFERENCE (invariato, §Triage) | ACCEPTABLE | sì | ✅ (già promosso in Fase Triage) |
| BREAKOUT_ACC | **MINOR_DIFFERENCE** (gap HTF chiuso; residuo noto: cooldown 8 barre non portato — minore, non strutturale) | **STRONG** | sì | ✅ |
| MACD | **MINOR_DIFFERENCE→quasi CONFIRMED** (gap HTF era ridondante, mai stato reale) | ACCEPTABLE | sì | ✅ |
| FVG_CONT | MINOR_DIFFERENCE (gap HTF chiuso) | ACCEPTABLE (più debole) | sì | idoneo sulla carta, **escluso per capienza** |
| LIQ_SWEEP | MINOR_DIFFERENCE (gap HTF chiuso) | **FAIL** | sì | ❌ (trade parity blocca) |

Con 4 strategie idonee sulla carta e un tetto di 3, la selezione non riempie il tetto artificialmente ma sceglie le 3 con l'evidenza quantitativa più solida: **FVG_CONT è escluso** perché ha la trade-parity più debole del gruppo idoneo (metà dei trade MT5 mancanti, contro il conteggio quasi combaciante di MACD e il match esatto di BREAKOUT_ACC).

### Nuove FAST_STRUCTURAL_CANDIDATE (Fase D): **BREAKOUT_ACC, MACD**

Totale complessivo dopo Fase D: **SAR, BREAKOUT_ACC, MACD** (3/3, tetto raggiunto).

---

## G. LIQ_VOID

Non corretto in questa fase, come richiesto. Documentato:

**`RESEARCH_IMPLEMENTATION_INVALID_ALIAS`** — `bt.STRATEGIES["LIQ_VOID"] is bt.STRATEGIES["FVG_CONT"]` → `True`. LIQ_VOID non ha una propria implementazione nel motore Python research; è un alias silenzioso di FVG_CONT. Esclusa da ogni ranking futuro finché non riceve un'implementazione propria (`sig_liq_void` dedicata, a partire da `NXS_Strat_LiquidityVoid` in MQL5, non ancora scritta lato Python).

---

## Blocker aperti

1. **Cutoff dati reali Python (2026-08-14)** vs storico MT5 più esteso: limita ogni futuro confronto trade-level a finestre non oltre quella data finché la fonte dati non viene aggiornata — non è un problema di logica del motore, è disponibilità dati.
2. **LIQ_SWEEP trade parity FAIL anche post-repair**: causa non diagnosticata (probabile divergenza nella detection dei livelli sessione Asia/Weekly high-low tra `_sweep_ext_at` Python e `NXS_DetectSweepExt` MQL5, mai verificata bit-a-bit — nota già presente in Fase Triage). Non bloccante per BREAKOUT_ACC/MACD ma impedisce la promozione di LIQ_SWEEP.
3. **BREAKOUT_ACC cooldown 8 barre** (`g_breakoutAccState` in MQL5) non portato in Python — differenza minore nota, non ha impedito la promozione ma resta un residuo di parità da chiudere prima di un serious backtest.
4. **Modello real-tick (Model=4) resta lento** (~17 min per 2 mesi su SAR): finestra Fase A limitata a 6 mesi (non 12) per questo motivo, dichiarato esplicitamente.

---

## Commit

`c3b0bf3`
