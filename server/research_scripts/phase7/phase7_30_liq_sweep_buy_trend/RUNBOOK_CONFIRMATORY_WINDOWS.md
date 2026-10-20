# Phase 7.30 — Confirmatory forward run (Windows research PC)

Hypothesis: `LIQ-SWEEP-BUY-TREND-RM-001`  
Prereg: `preregistration_v1.json` (committed before this run)  
Window: **2026.09.28 → 2026.10.19**  
Harness identity: selector **7**, **GOLD**, **H4**, fixed lot **0.01**, ResearchMode (same as Phase 7.23/7.25)

Cloud/Linux agents stop at `PREPARED_AWAITING_WINDOWS_MT5`. Only this PC launches Tester.

## 0. Preconditions

- MetaTrader 5 installed at the path in `phase7_23/nxs_research_run_harness.py`
- Repo checked out on the commit that contains the confirmatory scripts
- Prereg file clean and tracked (`git status` shows no dirty `preregistration_v1.json`)
- Do **not** retune SL/TP/SMA/seed after seeing results

## 1. Prepare (or re-prepare) INI + manifest

From repo root (PowerShell or cmd):

```text
python server\research_scripts\phase7\phase7_30_liq_sweep_buy_trend\launch_confirmatory_forward_run.py
```

On Windows with a valid `terminal64.exe`, this launches Tester.  
If you only want the files first:

```text
python server\research_scripts\phase7\phase7_30_liq_sweep_buy_trend\launch_confirmatory_forward_run.py --prepare-only
```

Artifacts land in:

`server/research_scripts/phase7/phase7_30_liq_sweep_buy_trend/runs/liq_sweep_confirmatory_forward/`

## 2. Wait for Tester

- Confirm `terminal64` / Strategy Tester finished (tasklist / Journal)
- Do not open another isolation run into the same Common/Files trades log until collect completes

## 3. Collect

```text
python server\research_scripts\phase7\phase7_30_liq_sweep_buy_trend\collect_confirmatory_forward_run.py
```

Expect `*.trades.csv` + optional certificate copy under the same `runs/` folder.

## 4. Refresh D1 (required for Arm B/C)

Bundled `phase7_9h` D1 CSV ends **2026.08.19** — too early for this window.  
Export/update D1 XAUUSD through at least **2026.10.19**, then:

```text
python server\research_scripts\phase7\phase7_30_liq_sweep_buy_trend\analyze_confirmatory_forward.py --d1-csv path\to\nxs_d1_gold.csv
```

## 5. Read the decision

Output: `confirmatory_forward_result_v1.json`  
Status tracker: `confirmatory_run_status_v1.json`

Frozen labels only:

| Decision | Meaning |
|---|---|
| `INSUFFICIENT_EVIDENCE` | n_B < 30 (expected for ~3 weeks) |
| `HABITAT_ONLY` | enough n; B−C CI includes ≤0 |
| `SIGNAL_SUPPORTED_AS_HYPOTHESIS` | enough n; CI lower > 0 — still **not** live-ready |
| `MIXED` | anything else; no promotion |

Expected for this short window: **INSUFFICIENT_EVIDENCE**. That is a valid confirmatory sample, not a strategy fail.

## 6. Do not

- Live / prop trading
- Promote from exploratory replay (`DISCOVERY_REUSE`)
- Change prereg params after looking at Arm B/C
- Spend premium agent credits to re-run collect/analyze — those are local/deterministic
