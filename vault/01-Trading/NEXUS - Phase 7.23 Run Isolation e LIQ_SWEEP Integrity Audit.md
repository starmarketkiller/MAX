# NEXUS - Phase 7.23 — Run Isolation Harness + LIQ_SWEEP Integrity Audit

**Baseline:** `7aba39a` (Phase 7.22, ORDER_BLOCK EDGE_VALIDATION_V1). HEAD e working tree verificati puliti all'avvio, nessun processo residuo. **BREAKOUT_ACC e ORDER_BLOCK non toccate** (diff zero verificato). Nessuna edge validation, nessun tuning, nessun deploy in questa fase — audit di integrità puro, in due fasi sequenziali (A poi B).

**Obiettivo Fase A**: impedire che `NEXUS_trades.csv`, i certificati o altri artifact persistenti (lezione chiave di Phase 7.22, dove un run precedente aveva silenziosamente contaminato l'estrazione) possano confondere run futuri, con provenance completa e zero modifiche alla logica delle strategie.

**Obiettivo Fase B**: stabilire se `LIQ_SWEEP` — la strategia con il miglior PF storico del corpus (PF 1.04, sweep37) — rappresenta davvero la sua identità canonica attuale, o se quel PF è un artefatto di un'implementazione/detector diversi da quelli oggi in uso.

---

## Fase A — Run Isolation Harness

### 1. Meccanismi riusati (zero modifica MQL5)

Scoperti due input EA già esistenti ma mai usati insieme:

- **`InpResetTradesLogOnInit`** (`NXS_Inputs.mqh:737`, default `false`): se `true`, **archivia** (mai cancella) `NEXUS_trades.csv` con timestamp prima di ripartire vuoto.
- **`InpBuildGitCommit`** (`NXS_Inputs.mqh:270`, default `"UNKNOWN"`): inietta lo SHA git reale nel Test Validity Certificate.

L'harness (`nxs_research_run_harness.py`) li attiva entrambi automaticamente in ogni `.ini` generato, senza toccare una riga di codice della strategia.

### 2. Provenance per run

Ogni run produce: `run_id` univoco (`{strategy}_{period_from}_{period_to}_{config_hash}_{timestamp}_{nonce}` — nonce UUID aggiunto dopo che un test ha rilevato collisioni allo stesso secondo), directory dedicata, timestamp start/end, strategy identity, `code_git_sha` (SHA reale, non "UNKNOWN"), `config_hash` (sha256 canonico dell'ini), periodo testato, file trade dedicato (copia, non spostamento — l'originale persiste), certificato dedicato (identificato per **delta** pre/post-run sulla directory certificati, unico meccanismo possibile: non esiste un reset per i certificati), riconciliazione trade CSV↔certificato con lo stesso run_id.

### 3. Test di isolamento (12/12 pass)

Coperti: file persistente preesistente, due run consecutivi, run interrotto, timestamp duplicati (replica lo scenario reale trovato in Phase 7.22 ORDER_BLOCK), mismatch certificato/CSV, delta certificato ambiguo (0 o >1 nuovi certificati → warning esplicito, mai silenzioso). Nessun artifact storico cancellato in nessun caso.

### 4. Bug reale trovato dall'harness stesso (durante l'uso in Fase B)

La riconciliazione automatica ha segnalato `n_trade_closes_in_csv=0` contro `n_opened_per_certificate=43` sul run diagnostico reale — mismatch palese. Causa: `NXS_LogTradeCSV` apre il file con `FILE_CSV` (senza `FILE_ANSI`) → MQL5 scrive **UTF-16LE con BOM**, non UTF-8; il parser dell'harness era hardcoded su `utf-8-sig`. **Fix** (harness, non strategia): `_detect_text_encoding()` — sniffing del BOM. Trovata e corretta una **seconda istanza dello stesso bug** in `build_liq_sweep_diagnostic_run.py` (funzione `_load_trades` duplicata, non riusava l'harness) più un bug di risoluzione path separato (path relativo nel manifest risolto rispetto alla working directory sbagliata). Entrambi correzioni al research harness, nessuna modifica a `MQL5/`.

---

## Fase B — LIQ_SWEEP Integrity Audit

### 5. Identità canonica

`NXS_Strat_LiqSweep()` (`NXS_Strategies.mqh:1455-1480`), selettore 7, TF canonico D1, **STATELESS** (nessuna variabile globale propria mutata — riceve `SNXSSweepExt &sw` già calcolato). Trigger: `sw.confirmed` + filtro delivery-candle `|close[1]-open[1]| >= 0.7*ATR` (aggiunto commit `6052636`, 16/07) + direzione coerente con `sw.dir`. Uscita: `NXS_DefaultSLTP()` → ATR fisso da `NXS_Profile_SLTP('LIQ_SWEEP')` (SL×1.5, TP×3.0, R:R=2.0).

### 6. Ipotesi HTF verificata e respinta

Il task chiedeva esplicitamente di verificare un sospetto mismatch nel filtro HTF (`NXS_Profile_HTF`, che confronta `px200` con `g_ema200` globale). Tracciata riga per riga la sequenza `NXS_ActivateTF()` (righe 225-233) → chiama `NXS_UpdateIndicators()` (riga 232) che **ricalcola** `g_ema200` sulla TF appena attivata, **immediatamente prima** che `NXS_CollectRaw()` legga `px200` nella stessa pass. Nessuna altra `ActivateTF`/`UpdateIndicators` si interpone. **Conclusione: px200 e g_ema200 sono sempre sulla stessa TF — ipotesi respinta**, non per assenza di verifica ma per verifica positiva esplicita.

### 7. Mismatch reale confermato: uscita MQL5 vs Python

MQL5 usa ATR fisso (§5). Il proxy Python (`_liq_sweep_target()`) usa un target dinamico su pool di liquidità opposti (PDH/PDL/Asia/swing_ext) — **esplicitamente documentato nel commento del codice Python stesso** come sostituzione "di un moltiplicatore ATR fisso", cioè di ciò che MQL5 realmente fa. **Severità ALTA**: qualunque confronto diretto di PF/P&L fra le due implementazioni non è valido. L'ingresso (sweep + delivery-candle + direzione) resta invece strutturalmente equivalente.

### 8. Evidenza storica: tutta CONTAMINATA (date verificate via git, non assunte)

| Evidenza | Data | Verdetto |
|---|---|---|
| Commento `NXS_StrategyProfiles.mqh:109` "PF2.48 R2.0" | 10/07/2026 | CONTAMINATED — precede il filtro delivery-candle (16/07) |
| `sweep37` S07 LIQ_SWEEP, PF 1.04 (baseline `e6ce816`, 2019-2025) | 18/07/2026 | CONTAMINATED — `merge-base --is-ancestor` conferma che precede il fix di integrità del detector (14/09) |
| Commento Python "IS 0.91 sotto pareggio" | 12/08/2026 | CONTAMINATED — precede lo stesso fix |
| `server/backtest.py::sig_liq_sweep` (superseded, "26 trade in 8 anni") | — | CONTAMINATED — implementazione superata |

Il fix "Detector Integrity" (`9b77f83`, 14/09/2026) ha corretto un bug in `NXS_DetectSweepExt()` (struct locale non azzerata in ~1/7 chiamate, usato da 10+ strategie incl. LIQ_SWEEP): **nessuna evidenza quantitativa esistente rappresenta l'identità canonica attuale post-fix**. Il PF 1.04 non è usato come prova di edge (né a favore né contro) — solo come motivo per aver investigato, come richiesto.

### 9. Run diagnostico fresco (nuovo harness, post-fix)

Periodo minimo scelto (non pluriennale automatico, come da istruzione esplicita): 2023.10.02–2026.06.30 (~2.9 anni, stessa finestra già nota da Phase 7.14/7.22). Eseguito con isolamento completo (run_id `LIQ_SWEEP_2023.10.02_2026.06.30_66767008acee43f3_20260927T211708Z_882af939`, `code_git_sha=7aba39a`). Risultato: **43 OPEN / 42 CLOSE / 41 eventi appaiati**, net P&L totale +$1.101,90. Riconciliazione CSV↔certificato: 42 vs 43 — scarto residuo di 1 non risolto (analogo al gap non risolto già visto in Phase 7.22 ORDER_BLOCK), dichiarato esplicitamente, non nascosto. Questo è un run **diagnostico**, non un'edge validation: nessun cost stress, concentrazione, OOS o bootstrap eseguiti qui.

### 10. Classificazione Python

`PARTIAL_STRUCTURAL_MODEL_FOR_ENTRY_ONLY`: l'ingresso è strutturalmente utile per confronti di segnale, l'uscita no. Non "event-level faithful" nel complesso.

---

## Decision Card finale

**`INTEGRITY_PARTIALLY_VALIDATED`**

MQL5 è internamente coerente (nessuna contaminazione cross-TF, nessun mismatch HTF confermato, entry trigger verificato) e un primo run diagnostico fresco post-fix-detector è stato raccolto con successo — MA resta un mismatch strutturale confermato fra MQL5 (uscita ATR fissa) e Python (uscita dinamica su liquidità) che impedisce piena fiducia nella parità Python, e il campione fresco è diagnostico, non un'edge validation completa.

**Fix proposto, non applicato** (solo raccomandazione metodologica, fuori scope di questa fase): allineare `_liq_sweep_target()` all'uscita ATR fissa reale, oppure ri-etichettarlo esplicitamente come "variante di ricerca indipendente".

**Prossimo passo se promossa**: un run economico completo (non solo diagnostico) su periodo sufficiente, poi `EDGE_VALIDATION_V1` con lo stesso protocollo già usato per BREAKOUT_ACC/ORDER_BLOCK — task futuro dedicato, non iniziato qui.

## Deliverables

`nxs_research_run_harness.py`, `test_run_isolation.py` (12/12), `build_run_isolation_spec.py`, `build_liq_sweep_identity_map.py`, `build_liq_sweep_historical_evidence_map.py`, `build_liq_sweep_semantic_parity_matrix.py`, `build_liq_sweep_diagnostic_findings.py`, `build_liq_sweep_diagnostic_run.py`, `build_liq_sweep_decision_card.py` + i rispettivi JSON, artifact del run diagnostico reale (`runs/liq_sweep_diagnostic/`: `.ini`, `.manifest.json`, `.trades.csv`, `.certificate.txt`), `verify_phase_7_23.py` (VERIFY OK), `test_phase_7_23.py`, questo vault report. 38/38 test totali (12 isolamento + 26 integrazione/Fase B).

## Vincoli preservati

Nessuna modifica a `MQL5/`, `Product-Platform/`, `contracts/` (diff zero verificato dal verificatore stesso). BREAKOUT_ACC (Phase 7.21) e ORDER_BLOCK (Phase 7.22) non toccate. Nessuna optimization, nessun edge tuning, nessun deploy. Nessuna edge validation LIQ_SWEEP eseguita in questa fase.

## Regressione

Suite completa Phase 7 (`pytest server/research_scripts/phase7/ -q`): **728 passed, 7 failed** (208.69s). Nessun nuovo fallimento causato da questa fase — verificato `git diff` zero su ogni directory coinvolta. I 7 fallimenti sono tutti self-check di staleness pre-esistenti, indipendenti da Phase 7.23 (i file coinvolti non hanno diff rispetto a HEAD): phase7_12, phase7_13, phase7_15 (×2), phase7_17 — già noti dalle fasi precedenti — più **phase7_9h (×2, nuovo rispetto all'ultimo controllo)**, un dataset canonico event-level la cui ricostruzione ora diverge dal file salvato, quasi certamente per lo stesso pattern (fix successivi al codice MQL5 — es. il fix di integrità del detector del 14/09 — che invalidano un self-check scritto prima di quei fix). Non indagato/corretto in questa fase (fuori perimetro: nessuna modifica a phase7_9h autorizzata qui). Effetto collaterale noto e reintegrato: la suite tocca sempre `phase7_9c/breakout_acc_{mt5,python}_event_stream_v1.json` (solo timestamp) — revertito con `git checkout --` prima del commit.

---

```
7.22: ORDER_BLOCK EDGE_VALIDATION_V1 - EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION (congelata)
7.23: RUN ISOLATION HARNESS + LIQ_SWEEP INTEGRITY AUDIT - COMPLETATO

FASE A - Run Isolation:
  riusati 2 input EA esistenti (InpResetTradesLogOnInit,
    InpBuildGitCommit) - zero modifica MQL5
  provenance completa per run: run_id univoco, dir dedicata, SHA,
    config hash, periodo, riconciliazione trade/certificato
  12/12 test isolamento pass (preesistente, 2 run consecutivi,
    interrotto, timestamp duplicati, mismatch, delta ambiguo)
  bug harness trovato DAL proprio meccanismo di riconciliazione:
    NEXUS_trades.csv e' UTF-16LE (FILE_CSV senza FILE_ANSI), non
    UTF-8 - fix con BOM-sniffing, trovata 2a istanza duplicata +
    bug di risoluzione path - entrambi fix solo al research harness

FASE B - LIQ_SWEEP Integrity Audit:
  identita': selettore 7, D1, STATELESS, entry=sweep+delivery-candle
    0.7xATR+direzione, exit=ATR fisso (SL 1.5x/TP 3.0x da profilo)
  ipotesi HTF mismatch: VERIFICATA E RESPINTA (px200/g_ema200 sempre
    stessa TF - tracciato riga per riga NXS_ActivateTF->
    NXS_UpdateIndicators->NXS_CollectRaw)
  mismatch REALE confermato: MQL5 uscita ATR fissa vs Python uscita
    dinamica su liquidita' (dichiarato nel commento Python stesso) -
    severita' ALTA, invalida confronto diretto P&L
  evidenza storica: TUTTA CONTAMINATA (date verificate via git) -
    PF2.48 (10/07) e PF1.04 sweep37 (18/07) precedono il filtro
    delivery-candle (16/07) e/o il fix detector (14/09); IS 0.91
    Python (12/08) precede il fix detector
  PF 1.04 NON usato come prova di edge - solo motivo di indagine
  run diagnostico fresco post-fix (2023.10.02-2026.06.30, harness
    isolato): 43 OPEN/42 CLOSE/41 eventi, net +$1.101,90 - scarto
    residuo 1 non risolto (dichiarato, analogo a ORDER_BLOCK)
  classificazione Python: PARTIAL_STRUCTURAL_MODEL_FOR_ENTRY_ONLY

DECISIONE: INTEGRITY_PARTIALLY_VALIDATED
  (MQL5 internamente coerente + run fresco raccolto)
  (MA mismatch strutturale exit MQL5<->Python confermato, non solo
   diagnostico non edge validation)
FIX PROPOSTO NON APPLICATO: allineare o ri-etichettare
  _liq_sweep_target() - fuori scope, richiede fase dedicata
PROSSIMO: nessuna edge validation LIQ_SWEEP iniziata qui - se si
  procede, prima run economico completo poi EDGE_VALIDATION_V1
  (stesso protocollo di BREAKOUT_ACC/ORDER_BLOCK)
```
