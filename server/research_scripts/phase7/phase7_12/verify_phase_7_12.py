#!/usr/bin/env python3
"""Phase 7.12 - verificatore indipendente. Ri-deriva ogni artifact dai
builder e ri-verifica sul codice sorgente attuale le affermazioni
chiave (FVG_MIT_WINDOW stateful, OB_MIT wrapper di ORDER_BLOCK, CRT
stateless, assenza di guardia TF in ORDER_BLOCK, flag di abilitazione
di default) - fallisce chiuso su qualunque discrepanza. Verifica anche
che Phase 7.10/7.11 e i file MQL5/Python restino invariati."""
import os
import subprocess
import sys

PHASE712_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE712_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE712_DIR)
import build_coverage_gaps_and_candidates as gaps_builder  # noqa: E402
import build_coverage_matrix as matrix_builder  # noqa: E402
import build_diagnostic_protocol_order_block as protocol_builder  # noqa: E402
import build_priority_queue as queue_builder  # noqa: E402

ARTIFACTS = [
    ("strategy_coverage_matrix_v1.json", matrix_builder.build),
    ("coverage_gaps_and_new_candidates_v1.json", gaps_builder.build),
    ("strategy_priority_queue_v1.json", queue_builder.build),
    ("diagnostic_protocol_order_block_v1.json", protocol_builder.build),
]


def verify():
    errors = []

    for fname, build_fn in ARTIFACTS:
        saved = load_json(os.path.join(PHASE712_DIR, fname))
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    strat_path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
    smc_path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies_SMC.mqh")
    inputs_path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Inputs.mqh")
    strat_text = open(strat_path, encoding="utf-8").read()
    smc_text = open(smc_path, encoding="utf-8").read()
    inputs_text = open(inputs_path, encoding="utf-8").read()

    # --- 1) FVG_MIT_WINDOW: stato globale realmente presente, NXS_EffTF() dinamico,
    # nessuna guardia TF prima della mutazione. ---
    if "g_fvgMitWBull[" not in smc_text or "g_fvgMitWBear[" not in smc_text:
        errors.append("g_fvgMitWBull/g_fvgMitWBear non trovati in NXS_Strategies_SMC.mqh "
                      "- il finding FVG_MIT_WINDOW non e' verificabile")
    update_fn_start = smc_text.find("void NXS_FvgMitWindow_Update()")
    update_fn_body = smc_text[update_fn_start:smc_text.find("\n}\n", update_fn_start)]
    if "NXS_EffTF()" not in update_fn_body:
        errors.append("NXS_FvgMitWindow_Update() non usa NXS_EffTF() - il finding "
                      "andrebbe rivisto")
    if "NXS_Profile_TF" in update_fn_body:
        errors.append("NXS_FvgMitWindow_Update() sembra GIA' avere una guardia "
                      "NXS_Profile_TF - il finding SUSPECT potrebbe essere obsoleto")

    # --- 2) OB_MIT: chiamata diretta a NXS_Strat_OrderBlock(), nessuna logica di
    # stato propria. ---
    ob_mit_start = smc_text.find("NXS_Strat_OB_Mitigation_Structural()")
    ob_mit_body = smc_text[ob_mit_start:smc_text.find("\n}\n", ob_mit_start)]
    if "NXS_Strat_OrderBlock()" not in ob_mit_body:
        errors.append("NXS_Strat_OB_Mitigation_Structural() non chiama piu' "
                      "direttamente NXS_Strat_OrderBlock() - il finding OB_MIT "
                      "andrebbe rivisto")

    # --- 3) CRT: nessuno stato globale/static referenziato nel corpo della funzione. ---
    crt_start = smc_text.find("SNXSSignal NXS_Strat_CRT()")
    crt_body = smc_text[crt_start:smc_text.find("\n}\n", crt_start)]
    if "static " in crt_body or "g_crt" in crt_body.lower():
        errors.append("NXS_Strat_CRT() sembra avere stato (static/g_crt*) - il "
                      "finding 'CRT verificato stateless' andrebbe rivisto")

    # --- 4) ORDER_BLOCK: nessuna guardia TF prima della lettura/mutazione dello
    # stato g_obBuy/g_obSell. ---
    ob_start = strat_text.find("SNXSSignal NXS_Strat_OrderBlock()")
    ob_end = strat_text.find("\n}\n", ob_start)
    ob_body = strat_text[ob_start:ob_end]
    if "NXS_Profile_TF" in ob_body:
        errors.append("NXS_Strat_OrderBlock() sembra GIA' avere una guardia "
                      "NXS_Profile_TF - il finding ORDER_BLOCK/priorita' andrebbe "
                      "rivisto (il difetto potrebbe essere gia' stato corretto)")
    if "g_obBuy" not in ob_body or "g_obSell" not in ob_body:
        errors.append("NXS_Strat_OrderBlock() non referenzia piu' g_obBuy/g_obSell "
                      "come atteso")
    if "NXS_EffTF()" not in ob_body:
        errors.append("NXS_Strat_OrderBlock() non usa piu' NXS_EffTF() come atteso")

    # --- 5) flag di abilitazione di default citati nella coda delle priorita' -
    # ri-verificati direttamente su NXS_Inputs.mqh. ---
    expected_flags = {
        "InpStrat_ORDER_BLOCK": "true", "InpStrat_OB_Mit": "false",
        "InpStrat_TSI": "true", "InpStrat_BarUpDn": "false",
        "InpStrat_BOLLINGER": "true", "InpStrat_PMax": "false",
        "InpStrat_BB_SQUEEZE": "true", "InpStrat_SH_BMS_RTO": "true",
        "InpStrat_SH_BMS_RTO_V2": "true", "InpStrat_SilverBullet": "true",
        "InpUseStrat_RangeFade": "false", "InpStrat_PivotWick": "false",
    }
    import re
    for flag, expected in expected_flags.items():
        m = re.search(rf"input\s+bool\s+{re.escape(flag)}\s*=\s*(true|false)", inputs_text)
        if m is None:
            errors.append(f"flag {flag} non trovato in NXS_Inputs.mqh")
        elif m.group(1) != expected:
            errors.append(f"flag {flag} atteso {expected}, trovato {m.group(1)}")

    # --- 6) totale identita' nella matrice = 83 (invariato dal census 7.11). ---
    matrix_doc = load_json(os.path.join(PHASE712_DIR, "strategy_coverage_matrix_v1.json"))
    if matrix_doc["payload"]["total_identities"] != 83:
        errors.append(f"attese 83 identita' nella matrice, trovate "
                      f"{matrix_doc['payload']['total_identities']}")

    # --- 7) nessuna modifica a Phase 7.10/7.11 (frozen) ne' a file MQL5/Python. ---
    for rel in ("server/research_scripts/phase7/phase7_10",
               "server/research_scripts/phase7/phase7_11"):
        result = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=ROOT)
        if result.returncode != 0:
            errors.append(f"{rel} risulta modificato rispetto a HEAD - non atteso in "
                          "questa fase")
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "server/backtest.py"],
                            cwd=ROOT, capture_output=True, text=True)
    if result.stdout.strip():
        errors.append(f"file MQL5/Python risultano modificati: {result.stdout.strip()}")

    # --- 8) coda delle priorita': ORDER_BLOCK in testa, BAR_UPDN e TSI non in testa
    # senza giustificazione (verificato che la giustificazione sia presente). ---
    queue_doc = load_json(os.path.join(PHASE712_DIR, "strategy_priority_queue_v1.json"))
    if queue_doc["payload"]["top_priority"] != "ORDER_BLOCK":
        errors.append("top_priority atteso ORDER_BLOCK")
    bar_updn_entry = next((q for q in queue_doc["payload"]["queue"]
                           if q["candidate"] == "BAR_UPDN"), None)
    if bar_updn_entry is None or "rank_rationale" not in bar_updn_entry:
        errors.append("BAR_UPDN senza rank_rationale esplicito - richiesto per "
                      "giustificare la sua posizione non-prioritaria")
    tsi_entry = next((q for q in queue_doc["payload"]["queue"]
                      if q["candidate"] == "TSI"), None)
    if tsi_entry is None or "rank_rationale" not in tsi_entry:
        errors.append("TSI senza rank_rationale esplicito")

    # --- 9) protocollo diagnostico non presume redditivita'. ---
    protocol_doc = load_json(os.path.join(PHASE712_DIR, "diagnostic_protocol_order_block_v1.json"))
    if protocol_doc["payload"].get("no_ea_modification_this_phase") is not True:
        errors.append("protocollo diagnostico: flag no_ea_modification_this_phase non True")
    if "not_assumed" not in protocol_doc["payload"]:
        errors.append("protocollo diagnostico: manca la dichiarazione esplicita che "
                      "non si presume redditivita'")

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
