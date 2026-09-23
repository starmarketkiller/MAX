#!/usr/bin/env python3
"""Phase 7.11 - verificatore indipendente. Ri-deriva ogni artifact dai
builder e ri-verifica le affermazioni chiave direttamente sul codice
sorgente attuale - fallisce chiuso su qualunque discrepanza."""
import json
import os
import re
import subprocess
import sys

PHASE711_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE711_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE711_DIR)
import build_complete_strategy_census as census_builder  # noqa: E402
import build_census_summary as summary_builder  # noqa: E402


def verify():
    errors = []

    census_path = os.path.join(PHASE711_DIR, "complete_strategy_census_v1.json")
    summary_path = os.path.join(PHASE711_DIR, "census_summary_v1.json")
    census_doc = load_json(census_path)
    summary_doc = load_json(summary_path)

    fresh_census = census_builder.build()
    if canonical_sha256(fresh_census) != canonical_sha256(census_doc["payload"]):
        errors.append("census: ricostruzione indipendente differisce dal file salvato")
    fresh_summary = summary_builder.build()
    if canonical_sha256(fresh_summary) != canonical_sha256(summary_doc["payload"]):
        errors.append("summary: ricostruzione indipendente differisce dal file salvato")

    # --- 1) total righe = 83 (fonte combinata attuale). ---
    rows = census_doc["payload"]["census_rows"]
    if len(rows) != 83:
        errors.append(f"attese 83 righe nel census, trovate {len(rows)}")

    # --- 2) nessun duplicato di canonical_strategy_id. ---
    ids = [r["canonical_strategy_id"] for r in rows]
    if len(ids) != len(set(ids)):
        errors.append("trovati canonical_strategy_id duplicati nel census")

    # --- 3) CRT e FVG_MIT_WINDOW: verifica DIRETTA e indipendente sul codice sorgente
    # (non fidarsi del census stesso) che siano implementate, raggiungibili, e assenti da
    # NXS_StrategyKnown(). ---
    smc_path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies_SMC.mqh")
    ea_path = os.path.join(ROOT, "MQL5", "Experts", "NEXUS_EA_v2.mq5")
    reg_path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_StrategyRegistry.mqh")
    smc_text = open(smc_path, encoding="utf-8").read()
    ea_text = open(ea_path, encoding="utf-8").read()
    reg_text = open(reg_path, encoding="utf-8").read()
    known_ids = set(re.findall(r'id=="([A-Z0-9_]+)"', re.search(
        r"bool NXS_StrategyKnown\(string strategyId\)\{(.*?)\n\}", reg_text, re.S).group(1)))

    for sid, fn_name in (("CRT", "NXS_Strat_CRT"), ("FVG_MIT_WINDOW", "NXS_Strat_FVG_Mitigation_Window")):
        if f"SNXSSignal {fn_name}()" not in smc_text:
            errors.append(f"{sid}: funzione {fn_name}() non trovata in NXS_Strategies_SMC.mqh - "
                          "il claim del census non e' verificabile")
        if f"{fn_name}()" not in ea_text:
            errors.append(f"{sid}: nessuna chiamata a {fn_name}() trovata in NEXUS_EA_v2.mq5 - "
                          "non raggiungibile dal router")
        if sid in known_ids:
            errors.append(f"{sid}: risulta PRESENTE in NXS_StrategyKnown() - il gap "
                          "UNKNOWN_STRATEGY_REGISTRY_GAP non e' piu' valido, il census va "
                          "aggiornato")

    # --- 4) i campi live_mql5 corretti per CRT/FVG_MIT_WINDOW devono essere True nel census,
    # con la nota di correzione presente. ---
    rows_by_id = {r["canonical_strategy_id"]: r for r in rows}
    for sid in ("CRT", "FVG_MIT_WINDOW"):
        r = rows_by_id.get(sid)
        if r is None:
            errors.append(f"{sid} non trovato nel census")
            continue
        if r["live_mql5"] is not True:
            errors.append(f"{sid}: live_mql5 dovrebbe essere True (corretto) nel census")
        if "live_mql5_correction_note" not in r:
            errors.append(f"{sid}: manca la nota di correzione live_mql5")

    # --- 5) NXR shadow engine: verifica indipendente zero call site. ---
    nxr_functions = ["NXR_Strat_IFVG_Reversal", "NXR_Strat_FVG_Mitigation",
                     "NXR_Strat_OB_Mitigation", "NXR_Strat_MalaysianSNR"]
    mql5_root = os.path.join(ROOT, "MQL5")
    all_mql5_text = ""
    for dirpath, _, filenames in os.walk(mql5_root):
        for fn in filenames:
            if fn.endswith((".mqh", ".mq5")):
                try:
                    all_mql5_text += open(os.path.join(dirpath, fn), encoding="utf-8", errors="ignore").read()
                except Exception:
                    pass
    for fn_name in nxr_functions:
        call_pattern = fn_name + "("
        occurrences = all_mql5_text.count(call_pattern)
        # 1 occorrenza attesa = solo la propria definizione (SNXSSignal fn_name())
        if occurrences > 1:
            errors.append(f"{fn_name}: trovate {occurrences} occorrenze nell'albero MQL5 "
                          "(attesa 1, solo la definizione) - il census afferma 'zero call site' "
                          "ma potrebbe essere sbagliato, verificare manualmente")

    # --- 6) nessuna correzione applicata a NESSUNA strategia (nessun file MQL5/Python
    # modificato rispetto a HEAD in questa fase). ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "server/backtest.py"],
                            cwd=ROOT, capture_output=True, text=True)
    if result.stdout.strip():
        errors.append(f"file MQL5/Python risultano modificati rispetto a HEAD: {result.stdout.strip()}")

    # --- 7) flag di scope. ---
    for flag in ("no_corrections_or_retests_applied",):
        if census_doc["payload"].get(flag) is not True:
            errors.append(f"census: flag '{flag}' non True")
        if summary_doc["payload"].get(flag) is not True:
            errors.append(f"summary: flag '{flag}' non True")

    # --- 8) coerenza contatori fra census e summary. ---
    live_count = sum(1 for r in rows if r["live_mql5"])
    if live_count != summary_doc["payload"]["output_2_counts_by_category"]["live"]:
        errors.append("conteggio 'live' nel summary non coincide col census")

    # --- 9) artifact Phase 7.10 non modificati. ---
    for rel in (
        "server/research_scripts/phase7/phase7_10/stateful_strategy_static_audit_v1.json",
        "server/research_scripts/phase7/phase7_10/phase_7_10_final_synthesis_report_v1.json",
    ):
        p = os.path.join(ROOT, rel)
        result = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", p], cwd=ROOT)
        if result.returncode != 0:
            errors.append(f"artifact frozen 7.10 risulta modificato: {rel}")

    return errors


def main():
    errors = verify()
    if errors:
        print(f"VERIFY FAILED: {len(errors)} problemi")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("VERIFY OK: tutti i controlli indipendenti passati (0 problemi)")
    sys.exit(0)


if __name__ == "__main__":
    main()
