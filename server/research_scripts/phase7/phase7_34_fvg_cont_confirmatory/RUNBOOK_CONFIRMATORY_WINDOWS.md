# Phase 7.34 — FVG_CONT confirmatory forward (PC-MT5)

Hypothesis (frozen in 7.33): `FVG-CONT-HABITAT-RM-001`  
Window: **2026.07.01 → 2026.10.19** · GOLD · H4 · selector **8** · lot 0.01 · ResearchMode  

Exploratory 7.33 was **NOT_PROMOTABLE**. This is the first confirmatory sample.

Expected: densità ~2.5 trade/mese ⇒ n_B spesso **&lt;30** → `INSUFFICIENT_EVIDENCE` è un esito onesto, non un fail della strategia.

## PowerShell (repo root)

```powershell
cd C:\Users\User\ClaudeWork\MAX
git pull origin cursor/edge-freeze-credit-safe-loop-5198
python server\research_scripts\phase7\phase7_34_fvg_cont_confirmatory\launch_confirmatory_forward_run.py
```

Attendi Tester **successfully finished** (demo OK; niente live/prop).

```powershell
python server\research_scripts\phase7\phase7_34_fvg_cont_confirmatory\collect_confirmatory_forward_run.py
python server\research_scripts\phase7\phase7_34_fvg_cont_confirmatory\analyze_confirmatory_forward.py --d1-csv server\research_scripts\phase7\phase7_30_liq_sweep_buy_trend\runs\liq_sweep_confirmatory_forward\nxs_d1_gold_refresh_20261019.csv
git add server\research_scripts\phase7\phase7_34_fvg_cont_confirmatory
git commit -m "research(phase7.34): FVG_CONT confirmatory forward result"
git push origin cursor/edge-freeze-credit-safe-loop-5198
```

Se il D1 non copre fino al 2026.10.19, rinfrescalo prima di analyze.

## Decisioni (prereg 7.33)

`INSUFFICIENT_EVIDENCE` | `HABITAT_ONLY` | `SIGNAL_SUPPORTED_AS_HYPOTHESIS` | `MIXED`  
Nessuna di queste = live-ready / promozione registry.
