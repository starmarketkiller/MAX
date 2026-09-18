# NEXUS - Phase 6: True Holdout Validation of EC-LIQUIDITY_SWEEP_RECLAIM

Obiettivo unico: verificare se EC-LIQUIDITY_SWEEP_RECLAIM passa da **E2 (INTERNAL_VALIDATION / POST_HOC_CANDIDATE)** a **E3 (TRUE_HOLDOUT_VALIDATION)**. Nessun nuovo edge cercato, nessuna modifica al detector, nessuna soglia cambiata, nessun filtro aggiunto, nessuna scelta del periodo dopo aver visto risultati. Questa fase poteva fallire.

Baseline metodologica approvata: Phase 5 (`bd274e1`), Phase 5.5 hardening (`9b1076e`).

---

## 1. Fix leakage Phase 5

Corretto il difetto confermato dal Leakage Guard (Phase 5.5 sec.8): `vol_terc`, `trend_terc`, `EFFICIENCY_TOP_TERCILE`, `VOL_BOTTOM_TERCILE`, `TREND_PERSISTENCE_MEDIAN` in `server/research_scripts/phase5/edge_discovery.py` ora calcolati **solo** su `state.iloc[:split_idx]` (discovery), mai sull'intero dataset.

Verificato: `python leakage_guard.py` → **`LEAKAGE_GUARD_PASS`** (0 finding critici, 0 review) — gate superato prima di qualunque nuova validazione, come richiesto.

**Il rerun di Phase 5 con il fix applicato NON è stato usato come nuova evidenza per RECLAIM** — è servito esclusivamente a verificare che il gate ora passi. Nessuna conclusione su H004/RECLAIM è cambiata o è stata ri-derivata da questo rerun.

## 2. Freeze H006 / True Holdout Hypothesis

Spec congelata **prima** di acquisire qualunque dato di holdout: `server/research_scripts/phase6/H006_frozen_spec.json`. Detector SWEEP/RECLAIM importato/riusato **letteralmente** da `build_events.py` di Phase 5 (copiato senza modifiche in `build_events_holdout.py`, solo path I/O diversi) — zero semantic drift.

Parametri di baseline (terzili, standardizzazione NN) congelati **dalla sola discovery originale di Phase 5** (2019-02-03→2021-03-12), salvati in `frozen_baseline_parameters.json` prima di toccare l'holdout — vedi tabella:

| Parametro | Valore congelato |
|---|---|
| vol_tercile [33.33,66.67] | [24.854, 66.667] |
| trend_tercile [33.33,66.67] | [-0.039, 0.081] |
| efficiency_top_tercile | 0.324 |
| NN match features | atr_percentile, ema_slope_atr_norm, directional_efficiency, position_in_rolling_range, roc |

Pass/fail criteria congelati (§4 del task, riportati integralmente in `H006_frozen_spec.json`): PASS richiede ΔP>0 **e** ΔP≥0.15 **e** CI95 Wilson non sovrapposte **e** n≥30 **e** consistenza di direzione BUY/SELL.

## 3. True Untouched Holdout

Dichiarazione completa (scritta **prima** del fetch): `true_holdout_declaration.json`.

- **Fonte dati**: Dukascopy XAUUSD tick (stessa API/formato di Phase 4/5)
- **Periodo**: 2022-02-04 → 2023-02-03 (un anno esatto, immediatamente successivo alla fine della finestra Phase 5 — 2022-02-03 — senza gap né sovrapposizione)
- **Perché non contaminato**: intervallo mai scaricato prima (verificabile dal manifest Phase 4, che copre solo fino al 2022-02-03); nessuna statistica calcolata su questo periodo prima di questa dichiarazione; detector/baseline/outcome tutti importati/congelati da Phase 5, non scelti guardando questo periodo
- **Campione atteso**: 60-120 eventi RECLAIM
- **Limitazioni note**: stessa fonte dati di Phase 5 (non è cross-feed/E4); un solo anno di mercato; buffer di lookback (2021-11-01→2022-02-03, dati già visti) riusato solo per il warmup delle feature, mai come osservazioni valutate

**`TRUE_HOLDOUT_NOT_AVAILABLE` non applicabile — il periodo esiste ed è stato scaricato.**

## 4. Risultato primario (bloccato PRIMA di qualunque diagnostica)

Dataset di holdout: 1599 barre H4 effettive (2022-02-04→2023-02-03) + 420 barre di buffer (solo warmup feature, mai valutate). Eventi RECLAIM rilevati con detector IDENTICO a Phase 5: **150 totali sull'intera serie, 115 confermati dentro la finestra di holdout** (il resto cade nel buffer, correttamente escluso).

| Metrica | Evento (RECLAIM) | Baseline (matched, frozen) |
|---|---|---|
| n | 115 | 571 |
| wins/losses | 68/47 | 305/266 |
| P osservata | 59.13% | 53.42% |
| Wilson CI95 | [49.99%, 67.68%] | [49.31%, 57.47%] |
| Beta-Binomial posterior mean | 58.97% | 53.40% |

**ΔP = +0.057** (molto più piccolo del +0.24/+0.30 osservato in Phase 5). **ΔE (MFE medio, ATR) = +0.277**. **CI95 SOVRAPPOSTE** (49.99% < 57.47%) — non superano il criterio di non-sovrapposizione richiesto per PASS.

## 5. Baseline Engine v2 — diagnostica di matching

Coarsened matching + nearest-neighbour standardizzato, con soglie/standardizzazione **congelate dalla discovery originale di Phase 5** (mai ricalcolate sull'holdout). Pool di baseline: 571 barre contemporanee (dentro l'holdout), non-SWEEP/non-RECLAIM.

| Qualità match | n | % |
|---|---|---|
| GOOD | 40 | 35.4% |
| FAIR | 72 | 63.7% |
| POOR | 3 | 2.7% |

Distribuzione simile a quella osservata in Phase 5.5 su RECLAIM originale (nessuna dominanza POOR) — il matching resta di buona qualità, la debolezza del risultato non è spiegabile da un baseline mal costruito.

## 6. Probability / uncertainty

Vedi tabella sopra: n/wins/losses/censored/observed_p/Wilson CI95/Beta-Binomial posterior riportati per evento e baseline (mai un win-rate nudo). `censored=0` in entrambi (nessuna osservazione ancora aperta a fine orizzonte 40 barre).

## 7. Multiple testing

`family_size=1` — **una sola ipotesi primaria testata** (H006). Nessuna exploratory branch: BUY/SELL/regime/subperiod erano subgroup pre-registrati (allowed_subgroup_analyses in H006_frozen_spec.json), non nuove ipotesi, nessuna correzione multiple-testing aggiuntiva applicabile o necessaria.

## 8. Robustness diagnostics (eseguiti DOPO il verdetto, non lo cambiano)

**BUY vs SELL — asimmetria netta, causa diretta del fallimento del criterio di consistenza:**

| Lato | n | P osservata | ΔP vs baseline aggregato |
|---|---|---|---|
| BUY | 63 | 52.4% | **-0.010** (nessun edge, leggermente negativo) |
| SELL | 52 | 67.3% | **+0.139** (edge reale e sostanziale) |

L'intero effetto aggregato (+0.057) è generato **esclusivamente dal lato SELL** — il lato BUY non mostra alcun vantaggio sul baseline. Questo è esattamente il tipo di dipendenza unidirezionale non prevista che i criteri congelati in sec.4 dell'H006 erano pensati per catturare.

**Regime breakdown** (soglie congelate dalla discovery originale): HIGH_VOL n=53 (P=58.5%), LOW_VOL n=32 (P=56.3%), TRANSITION n=19 (P=57.9%), TRENDING n=8 (P=75%, campione troppo piccolo per essere letto), RANGING n=3 (troppo piccolo). Nessun regime singolo spiega da solo l'intero effetto; i campioni per regime sono comunque piccoli.

**Stabilità trimestrale**: Q1=58.3% (n=36), Q2=70.0% (n=30), Q3=55.2% (n=29), Q4=50.0% (n=20, **sotto il baseline**). L'effetto non è stabile nel tempo — si indebolisce fino a sparire nell'ultimo trimestre dell'holdout.

**Outlier trimming** (rimozione 10% migliori MFE): P scende da 59.1% a 57.7% — piccola riduzione, l'effetto non dipende da pochi outlier estremi, ma resta comunque debole.

**Bootstrap (2000 resample)**: ΔP medio 0.057, **CI95 bootstrap [-0.049, +0.156] — include lo zero**. Solo l'87.2% dei resample è positivo (non un margine schiacciante). Questo conferma indipendentemente che l'effetto non è statisticamente distinguibile da zero con questo campione.

**Event clustering**: gap mediano 6 barre fra eventi consecutivi, ma **36.8% degli eventi cade entro 3 barre da un altro evento e 60.5% entro 10 barre** — dipendenza temporale non trascurabile fra eventi vicini. I 115 eventi NON sono pienamente indipendenti fra loro, un'ulteriore ragione per trattare con cautela qualunque intervallo di confidenza calcolato assumendo indipendenza.

## 9. Execution separation

`execution_status = NOT_TESTED` mantenuto indipendentemente dal verdetto (nessuna implementazione MT5, nessuna dichiarazione di deployability) — comunque irrilevante qui poiché il verdetto non è PASS.

## 10. Signal-to-Fill feasibility

**Non eseguito** — per disegno esplicito di questa fase, lo studio di fattibilità va eseguito SOLO se H006 passa (PASS). Verdetto = BORDERLINE → non eseguito. Script pronto (`signal_to_fill_feasibility.py`) per un futuro ri-tentativo se una versione futura dell'ipotesi dovesse passare un vero holdout.

## 11. Evidence grade

**EC-LIQUIDITY_SWEEP_RECLAIM resta E2 (INTERNAL_VALIDATION).** Il vero holdout NON ha prodotto un PASS — per la regola congelata in `H006_frozen_spec.json` (`if_FAIL_or_BORDERLINE: resta E2`), non c'è promozione a E3. Nessun grade E4/E5 assegnato (non applicabile).

---

## Risposte finali

**1. Il holdout è realmente indipendente?**
Sì per il criterio dichiarato (mai scaricato/visto prima, detector/baseline/outcome tutti importati da Phase 5 senza guardare questo periodo) — ma resta la STESSA fonte dati (Dukascopy), quindi è un `TEMPORAL_HOLDOUT` pulito, non un `CROSS_FEED_VALIDATION` (E4).

**2. Il detector è rimasto identico?**
Sì — `build_events_holdout.py` è una copia verbatim di `build_events.py` di Phase 5 (stesso CFG dict, stesse funzioni), solo i path di I/O sono cambiati. Zero semantic drift.

**3. Il baseline è comparabile?**
Sì — stesse soglie di coarsening e stessa standardizzazione NN della discovery originale di Phase 5 (mai ricalcolate sull'holdout), applicate a un pool di controllo contemporaneo all'holdout. Qualità di match buona (99% GOOD/FAIR, solo 3% POOR).

**4. ΔP holdout è positivo o no?**
Positivo ma piccolo: **+0.057**, ben sotto la soglia minima di materialità pre-registrata (0.15) e con CI95 sovrapposte — un effetto che non si può distinguere in modo affidabile dal rumore con questo campione (confermato dal bootstrap, la cui CI95 include lo zero).

**5. Il risultato è stabile BUY/SELL?**
**No.** BUY: ΔP=-0.010 (nessun edge). SELL: ΔP=+0.139 (edge reale). L'intero effetto aggregato è generato dal solo lato SELL — esattamente il tipo di collasso unidirezionale che i criteri pre-registrati erano progettati per intercettare.

**6. Il sample è sufficiente?**
Sì in senso stretto (n=115 ≥ minimo pre-registrato di 30, in linea con il campione atteso 60-120) — ma l'event clustering (37% degli eventi entro 3 barre l'uno dall'altro) riduce l'informazione effettiva indipendente sotto n=115 nominale.

**7. Il verdict è PASS / BORDERLINE / FAIL?**
**BORDERLINE.** Non FAIL (ΔP resta positivo, non c'è un'inversione di segno), ma non PASS (sotto la soglia minima di effetto, CI sovrapposte, consistenza direzionale fallita).

**8. Evidence grade finale?**
**E2 — invariato.** Nessuna promozione a E3.

**9. Ha senso procedere a E4 cross-source?**
Non ancora con priorità alta. Con un risultato BORDERLINE (non PASS) sul primo vero holdout, investire in una seconda fonte dati indipendente (E4) prima di capire l'asimmetria BUY/SELL qui trovata rischierebbe di ripetere lo stesso schema con un'altra fonte. Più utile prima capire SE l'asimmetria BUY/SELL è strutturale (es. legata al regime rialzista/ribassista dell'oro nel periodo) o casuale.

**10. Ha senso procedere a E5 execution validation?**
**No, non ora.** E5 richiede un fenomeno che abbia prima superato E3 — qui non è avvenuto. Investire in una validazione di esecuzione per un fenomeno che non ha nemmeno superato un holdout temporale pulito sarebbe prematuro e in contrasto con la sequenza E3→E4→E5 dichiarata esplicitamente all'inizio di questa fase.

---

## Conclusione

Questa fase ha fatto esattamente quello che dice il proprio titolo: ha VERIFICATO, non confermato per default. Il risultato è imperfetto ma onesto: SWEEP+RECLAIM mostra ancora un ΔP positivo su dati mai visti prima, ma l'ampiezza è crollata da +0.24/+0.30 a +0.057, e l'intero effetto residuo è concentrato in un solo lato direzionale. Questo è coerente con l'ipotesi, già sollevata in Phase 5.5, che parte della forza originale del segnale fosse un artefatto della selezione post-hoc da un batch di 14 candidati — la disciplina di un vero holdout l'ha ridimensionato in modo sostanziale, anche se non l'ha azzerato del tutto.

## Artifact prodotti

- `server/research_scripts/phase6/H006_frozen_spec.json` (spec congelata)
- `server/research_scripts/phase6/true_holdout_declaration.json`
- `server/research_scripts/phase6/frozen_baseline_parameters.json`
- `server/research_scripts/phase5_5/leakage_guard_report_v1.json` (rigenerato, ora `LEAKAGE_GUARD_PASS`)
- `server/research_scripts/phase6/h006_primary_result.json`
- `server/research_scripts/phase6/h006_robustness_diagnostics.json`
- Codice: `phase6_holdout_downloader.py`, `build_h4_bars_holdout.py`, `build_market_state_holdout.py` (copia verbatim), `build_events_holdout.py` (copia verbatim), `build_outcomes_holdout.py` (copia verbatim), `run_h006_test.py`, `robustness_diagnostics.py`, `signal_to_fill_feasibility.py` (pronto, non eseguito)
