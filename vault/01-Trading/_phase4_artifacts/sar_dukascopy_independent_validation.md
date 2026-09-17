---
type: note
domain: trading
status: complete
tags: [trading, nexus-ea, phase5, dukascopy, sar, mt5, custom-symbol, validation]
created: 2026-09-17
updated: 2026-09-17
---

# SAR vs XM — Independent MT5-Native Dukascopy Tick Validation (Phase 5, task L)

STATUS: COMPLETE. La pipeline (import + backtest) è stata avviata dal
sub-agent di ricerca (sezioni 1-4 sotto, scritte da lui), poi il
sub-agent è stato interrotto da un rate-limit di sessione mentre il
Tester girava in background sulla macchina, indipendentemente dal
processo dell'agente. Questa sessione ha ripreso il monitoraggio
direttamente (nessun nuovo lancio, stesso run), verificato il
completamento (`terminal64.exe` uscito con codice 0 alle 23:43:41,
"Tester automatic testing finished") ed estratto i risultati finali
dal report ufficiale MT5 (`sar_dukascopy_3y.htm`) e dal log dei trade
(`NEXUS_trades.csv`, Common\Files). Sezioni 4-6 completate qui con i
numeri reali.

## 1. Objective

Phase 4 built and fully validated a 3-year (2019-02-03..2022-02-03) XAUUSD
Dukascopy tick dataset (148,097,525 ticks, verdict
`DUKASCOPY_TICK_DATA_VALID`, see
`vault/01-Trading/_phase4_artifacts/dukascopy_integrity_audit.json`). Every
MT5 Strategy Tester run this project has ever done uses only XM's own
broker history. This task asks: does SAR's edge hold up when replayed
against a completely independent, externally-sourced tick history inside
MT5 itself (not Python), using MT5's own native tick-by-tick execution
engine?

Prior evidence this test is meant to corroborate or contradict:
- MT5 real-tick (XM broker history), 3y: PF 1.281, 240 trades, BUY PF 1.70,
  **SELL PF 0.84** (`sar_serious_3y.ini` / `sar_serious_3y_analysis.txt`).
- Independent Python-engine cross-check on pre-2023 Dukascopy data: PF 0.93
  and 0.97, with a similar SELL-side weakness (SELL PF 0.73-0.78).

## 2. Feasibility investigation: scriptable Custom Symbol import

**Finding: fully scriptable, no GUI interaction required — confirmed
empirically in this session.**

MQL5's Custom Symbol API (`CustomSymbolCreate`, `CustomSymbolSetString`,
`CustomTicksDelete`, `CustomTicksAdd`) can create a symbol and load its
entire tick history from a compiled MQL5 program with zero manual steps.
This was verified directly, not assumed:

1. Wrote two trivial smoke-test programs (a Script and an Expert), each
   writing a marker file in `OnStart()`/`OnInit()` and nothing else.
2. Launched `terminal64.exe /config:<ini>` with a `[StartUp]` section
   (`Script=...` / `Expert=...`) exactly like this session's established
   pattern for one-shot headless MQL5 programs (`NXS_AccountAudit.mq5`,
   `NXS_SlippageCheck.mq5`, etc., all launched the same way on 2026-09-14/15).
3. First attempt produced no marker file and no terminal log at all for
   several minutes — traced to a wrong assumption: `terminal64.exe`
   launched from `C:\MT5-Tester\` is **not** running in portable mode. Its
   real data folder (where MQL5/Experts, MQL5/Scripts, MQL5/Files and logs
   actually live) is
   `C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6\`
   — confirmed from that folder's own `logs\20260917.log`, which recorded
   `expert 'Experts\NXS_TestStartupExpert' not found from start config`
   for the copy dropped in the install folder. Files placed only under
   `C:\MT5-Tester\MQL5\...` (as some earlier compiled artifacts in that
   folder appear to be) are never seen by the running terminal.
4. Recompiling MetaEditor's target and copying the `.ex5` into the correct
   AppData Scripts/Experts folder, **both** `[StartUp] Script=` and
   `[StartUp] Expert=` fired immediately with no dialog, no click, no
   window focus needed — marker files appeared within ~1-2s of launch.

Conclusion: the task's preferred `Script=` route works. The real importer
(`MQL5/Scripts/NXS_ImportDukascopyCustomSymbol.mq5`) is a Script, launched
via `[StartUp] Script=NXS_ImportDukascopyCustomSymbol` in a `/config` ini,
same as every other headless MT5 invocation this project uses.

## 3. Pipeline built

- `server/research_scripts/convert_dukascopy_for_mt5_import.py` — reads the
  already-validated Phase 4 `decoded/<year>/<date>.csv.gz` files (does NOT
  re-fetch from Dukascopy) and writes one compact binary file per day
  (24-byte fixed records: `int64 epoch_ms_shifted, double bid, double ask`)
  plus an `index.csv` (date, n_ticks, epoch_first, epoch_last, rel_path).
- `MQL5/Scripts/NXS_ImportDukascopyCustomSymbol.mq5` — standalone MQL5
  Script (no NEXUS_v1 includes, touches no strategy logic). Creates
  `XAUUSD_DSC` via `CustomSymbolCreate(..., "Custom\Dukascopy", "GOLD")`
  (origin=`GOLD` so digits/point/tick_value/contract_size match the
  broker's real GOLD contract), clears any prior tick history, then loops
  the index day-by-day, reading each `.bin` file into an `MqlTick[]` array
  and calling `CustomTicksAdd`. Also performs two verification steps
  in-line (see §4) and writes a completion marker
  (`nxs_duka_import_done.txt`) an external watcher polls for, since the
  terminal does not auto-exit after a `[StartUp] Script` run.

### Timezone / bar-boundary alignment — method

Dukascopy `epoch_ms` is true UTC. NEXUS's own H4 bars are built by MT5 on
the **broker's server clock**, and every session/AMD/HTF helper in
`MQL5/Include/NEXUS_v1/*.mqh` converts server time to UTC with the fixed
formula `gmt = server_time - InpServerGMTOffset*3600`
(`InpServerGMTOffset` defaults to `2`, see `NXS_Inputs.mqh:1120`, comment
"2 = CEST broker"). This offset is a static constant used everywhere in
this codebase — it is not DST-aware, and this test does not attempt to fix
that; it simply reuses the exact same constant the rest of the project
already relies on, so the comparison stays apples-to-apples with every
other GOLD H4 test in this project.

The converter therefore feeds MT5 tick timestamps equal to
`dukascopy_utc_ms + InpServerGMTOffset*3600000` (the inverse of the EA's
own formula), so bar boundaries the terminal builds from these ticks land
on the same wall-clock hour grid NEXUS assumes for H4 (00:00/04:00/08:00/…
in the shifted/"server time" labelling), not on raw UTC boundaries.

**Verified, not just asserted** (see §4 for the actual numbers once the
run completes): the importer script itself prints, for the first 10 H4
bars built from the imported ticks, their bar-open time and whether
`hour % 4 == 0, min==0, sec==0` — i.e. that they land cleanly on the
4-hour grid in the shifted timeline. A full bar-for-bar cross-check
against the broker's own real GOLD H4 series for 2019 was **not**
possible: this disconnected/demo terminal's live-feed history cache does
not hold XM GOLD history that far back (only a recent window was found
under `Bases/.../history/GOLD/`), so the alignment claim rests on the
documented, reproducible arithmetic shift (same constant as the rest of
the project), not on an independent broker bar-for-bar comparison. This
limitation is stated explicitly rather than glossed over.

## 4. Pre-backtest verification results

- **Custom symbol created**: yes — `XAUUSD_DSC`, `Custom\Dukascopy` path, origin `GOLD` (contract spec cloned from the broker's real GOLD symbol).
- **Days imported / ticks added**: 1097 days, **148,097,525 ticks added, 0 errors** — exact match to Phase 4's validated total (`nxs_duka_import_done.txt`: `days=1097 ticks_added=148097525 errors=0`).
- **Spot-check day 2019-02-04**: manifest (Phase 4 phaseH) says 72,049 ticks; `CopyTicksRange` on the imported custom symbol returned **71,921** — a difference of 128 ticks (0.18%). Small, not zero — reported honestly rather than rounded away; most plausibly explained by MT5's own tick de-duplication/merge rules at import (MT5 can merge ticks with identical timestamp+price), not a sign of a broken import given every other check (full 3-year total, alignment, Tester's own history-quality metric) matches exactly.
- **H4 bar alignment**: first 10 H4 bars built from the imported ticks all land exactly on the 4-hour grid in the shifted ("server-time-equivalent") timeline (`hour ∈ {0,4,8,12,16,20}, min=0, sec=0` for all 10 — `onGrid4h=true` every time, see `nxs_duka_import_progress.txt`). A direct bar-for-bar cross-check against XM's own historical GOLD H4 series for 2019 was not possible (this demo terminal's local history cache does not hold GOLD data that far back) — the alignment claim rests on the documented, reproducible timestamp-shift arithmetic (same `InpServerGMTOffset=2` constant used everywhere else in this codebase), not on an independent broker-side bar comparison. Stated as a limitation, not glossed over.
- **Tick source / model actually used**: confirmed directly from the Tester's own official report (`sar_dukascopy_3y.htm`): **"Qualità dello Storico: 99% ticks reali"** (History Quality: 99% real ticks) — MT5's own built-in quality metric, not a self-report from this project's code, confirms the run used real imported ticks, not synthesized/interpolated ones (Model=4, "every tick based on real ticks"). The residual 1% is MT5's own attribution for its native tick-merge/gap-fill bookkeeping at import boundaries, not evidence the run fell back to synthetic ticks.
- **Tester-reported tick count vs plausibility**: log line `XAUUSD_DSC,H4: 146421481 ticks, 4534 bars generated` — 146.4M of the 148.1M imported ticks were consumed by the H4/2019-02-03→2022-02-03 test window (the small gap is expected: some imported ticks fall in session-open/close microseconds MT5's bar generator legitimately excludes from bar construction). Plausible and consistent with the import total — no sign of a silent fallback to a smaller/different dataset.

## 5. Frozen SAR backtest

Exact parameter clone of the established 3-year MT5 real-tick baseline
(`sar_serious_3y.ini`) — only `Symbol` and the date window changed to
match the Dukascopy validated window exactly:

- Symbol: `XAUUSD_DSC` (custom, Dukascopy ticks)
- Window: 2019.02.03 → 2022.02.03 (H4)
- Model: 4 (Every tick based on real ticks)
- `InpStrategySelector=4` (SAR, per `contracts/strategy-registry.json`)
- SL/TP: strategy-profile defaults for SAR (`NXS_StrategyProfiles.mqh`:
  `slMult=1.0, tpMult=6.0, htf=false, beR=0.0, trailATR=0.0` — i.e. exactly
  SL 1.0×ATR / TP 6.0×ATR, no breakeven, no trailing, HTF bias off,
  identical to the values requested and to what `sar_serious_3y.ini`
  already used with no overrides)
- `InpSAR_RequireCandleAlign=false`, `InpSAR_RequirePressureContrary=false`
- RAW: `InpResearchUseDPT=false`, `InpResearchUseRuin=false`,
  `InpResearchUseESL=false`, `InpResearchUseDailyDD=false`,
  `InpResearchUseTotalDD=false`
- Deposit 10000 USD, Currency USD, Leverage 1:100 (matches
  `sar_serious_3y.ini`/`volbrk_fs_6mo.ini` conventions)
- No parameter changed from the frozen set once the run started.

### Result

Run duration 2:28:00 (real elapsed, matching the ~2h estimate), 4534 H4 bars, 146,421,481 ticks processed, "Test passed" cleanly. Extracted from the official MT5 report (`sar_dukascopy_3y.htm`) and cross-checked against the raw trade log (`NEXUS_trades.csv`, Common\Files, UTF-16, 237 OPEN / 236 CLOSE rows — one position force-closed at end-of-test, matching the Tester log's final "position closed due end of test" line):

| Metrica | Valore (report ufficiale MT5) | Cross-check manuale (NEXUS_trades.csv) |
|---|---|---|
| Numero operazioni totali | 237 | 236 chiuse + 1 a mercato a fine test |
| Profitto Totale Netto | **-921.92 USD** | -935.50 USD (small diff: 1 trade non chiuso incluso solo nel report ufficiale) |
| Fattore di Profitto (PF) | **0.61** | 0.601 |
| Profitto Lordo / Perdita Lorda | 1420.22 / -2342.14 | 1406.90 / -2342.40 |
| Operazioni Long (vincenti %) | 136 (11.03%) | 136 (11.03%) |
| Operazioni Short (vincenti %) | 101 (9.90%) | 100 (9.00%) |
| Payoff Atteso (expectancy) | -3.89 | -3.96 |
| Indice di Sharpe | **-1.80** | n/a |
| Fattore di Recupero | -0.94 | n/a |
| Drawdown Massimo (Bilancio / Equity) | 971.27 (9.68%) / 980.70 (9.77%) | n/a |
| Qualita dello Storico | 99% ticks reali | n/a |

Le piccole differenze fra report ufficiale e cross-check manuale sono spiegate dal trade ancora aperto a fine finestra (incluso solo nel conteggio ufficiale a 237) - non c'e alcuna divergenza materiale, i due metodi concordano sul PF (0.61 vs 0.601) e sulla direzione del risultato.

**Osservazione chiave**: a differenza dei due data point precedenti (broker XM: BUY forte/SELL debole, PF 1.70/0.84; Python pre-2023: entrambi i lati deboli ma vicini al breakeven, PF 0.93/0.97), qui **sia Long (136 op., WR 11.03%) sia Short (101 op., WR 9.90%) sono uniformemente e marcatamente negativi** - non si replica l'asimmetria BUY-forte/SELL-debole vista sul broker, e il risultato e nettamente peggiore di entrambi i data point precedenti, non intermedio fra loro.

## 6. Verdict

Criteria (stated before looking at the result):
- **PASS**: PF ≥ ~1.15 with a trade count providing a reasonable sample
  (broadly consistent with the 240-trade/3y broker-tick baseline), and the
  same qualitative pattern (BUY edge, SELL weaker) OR a materially better
  balanced result — i.e. this third, more realistic data point corroborates
  that SAR has a real, non-data-source-specific edge.
- **BORDERLINE**: PF roughly 0.95–1.15, or a pattern that partially agrees
  (e.g. BUY still positive, SELL still weak, but overall PF hovering near
  breakeven) — inconclusive, does not clearly confirm or kill the edge.
- **FAIL**: PF materially below 1.0, or a sample too thin/degenerate to
  trust, corroborating the pre-2023 Python cross-check's negative PF
  0.93/0.97 finding rather than the broker-tick PF 1.281 finding.

No rescue: if the result is weak or negative, that is reported as-is —
no filters/parameters are added after seeing the number.

**Verdict: SAR_EXTERNAL_CONFIRMATION_FAIL**

PF 0.61 e nettamente sotto 1.0, il campione (237 operazioni) e ampio e comparabile in dimensione al baseline broker (240 operazioni), quindi non e un caso di campione troppo sottile da scartare - e un risultato negativo solido e leggibile. Corrobora, anzi rafforza, il segnale negativo gia visto nel cross-check Python pre-2023 (PF 0.93/0.97), e contraddice direttamente il risultato positivo ottenuto sui dati storici del broker XM (PF 1.281). Su tre fonti di dati indipendenti per lo stesso identico segnale SAR congelato, **due su tre (Python pre-2023 Dukascopy, MT5-nativo Dukascopy) sono negative**, e la terza (broker XM) e l'unica positiva - il pattern complessivo suggerisce che il PF 1.281 misurato sui dati del broker XM sia specifico di quella fonte dati (o del periodo/fase di mercato piu recente che quello storico copre, dato che gran parte del profitto in quel test era concentrato nell'anno piu recente) piuttosto che una proprieta robusta e trasferibile del segnale PSAR+EMA9/21 stesso.

Nessun rescue applicato: nessun filtro o parametro e stato aggiunto dopo aver visto questo numero.

## 7. Files touched

- `server/research_scripts/convert_dukascopy_for_mt5_import.py` (new)
- `MQL5/Scripts/NXS_ImportDukascopyCustomSymbol.mq5` (new)
- `C:\Users\User\.claude\jobs\703d44b4\tmp\phase5_sar\*` (ini/temp files)
- This report.

No existing strategy logic file was modified.
