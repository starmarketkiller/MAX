#!/usr/bin/env python3
"""Phase 7.17 - verificatore indipendente. Ri-deriva ogni artifact dai
builder, ri-verifica sul sorgente MQL5 attuale che TSI non abbia una
guardia TF (difetto ancora presente/non corretto), ri-verifica i casi
minimi con la reference esatta (aritmetica razionale, non la funzione
sotto test), verifica che nessun file MQL5 sia stato modificato e che
nessun nuovo run Tester sia stato lanciato in questa fase."""
import os
import subprocess
import sys
from fractions import Fraction

PHASE717_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE717_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE717_DIR)
import build_tsi_semantic_map as map_builder  # noqa: E402
import build_tsi_mechanism_formalization as mech_builder  # noqa: E402
import build_tsi_minimal_cases as cases_builder  # noqa: E402
import build_tsi_impact_comparison as impact_builder  # noqa: E402
import build_tsi_python_fidelity as fidelity_builder  # noqa: E402
import build_tsi_historical_evidence_map as hist_builder  # noqa: E402
import build_tsi_decision_card as card_builder  # noqa: E402

ARTIFACTS = [
    ("tsi_semantic_map_v1.json", map_builder.build),
    ("tsi_mechanism_formalization_v1.json", mech_builder.build),
    ("tsi_minimal_cases_v1.json", cases_builder.build),
    ("tsi_impact_comparison_v1.json", impact_builder.build),
    ("tsi_python_fidelity_v1.json", fidelity_builder.build),
    ("tsi_historical_evidence_map_v1.json", hist_builder.build),
    ("tsi_decision_card_v1.json", card_builder.build),
]


def verify():
    errors = []

    for fname, build_fn in ARTIFACTS:
        path = os.path.join(PHASE717_DIR, fname)
        if not os.path.exists(path):
            errors.append(f"{fname}: file mancante")
            continue
        saved = load_json(path)
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    # --- Difetto TSI ancora presente nel sorgente reale (nessuna guardia TF) -
    # altrimenti l'intera diagnosi sarebbe stale. ---
    strat_path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
    strat_text = open(strat_path, encoding="utf-8").read()
    ts_start = strat_text.find("SNXSSignal NXS_Strat_TSI()")
    ts_end = strat_text.find("\n}\n", ts_start)
    ts_body = strat_text[ts_start:ts_end]
    if "NXS_Profile_TF" in ts_body:
        errors.append("NXS_Strat_TSI() sembra GIA' avere una guardia NXS_Profile_TF - il "
                      "difetto potrebbe essere gia' stato corretto, questa diagnosi e' stale")
    if "g_tsiState" not in ts_body:
        errors.append("NXS_Strat_TSI() non referenzia piu' g_tsiState come atteso")

    # --- Re-verifica indipendente dei casi minimi con aritmetica razionale esatta
    # (NON la funzione tsi_update sotto test). ---
    A_L, A_S, A_G = Fraction(2, 26), Fraction(2, 14), Fraction(2, 8)

    def _ref_step(sm1, sm1a, sm2, sm2a, sig, prev_c, close):
        pc = Fraction(close) - Fraction(prev_c)
        apc = abs(pc)
        sm1n = pc * A_L + Fraction(sm1) * (1 - A_L)
        sm1an = apc * A_L + Fraction(sm1a) * (1 - A_L)
        sm2n = sm1n * A_S + Fraction(sm2) * (1 - A_S)
        sm2an = sm1an * A_S + Fraction(sm2a) * (1 - A_S)
        tsi = Fraction(100) * sm2n / sm2an if sm2an != 0 else Fraction(0)
        sign = tsi * A_G + Fraction(sig) * (1 - A_G)
        return sm1n, sm1an, sm2n, sm2an, tsi, sign

    s0 = _ref_step(1.0, 3.0, 1.0, 3.0, Fraction(100, 3), 2000.0, 2010.0)
    sa1 = _ref_step(*s0[:4], s0[5], 2010.0, 2008.0)
    sa2 = _ref_step(*sa1[:4], sa1[5], 2008.0, 2015.0)
    sa3 = _ref_step(*sa2[:4], sa2[5], 2015.0, 2020.0)
    sb1 = _ref_step(*s0[:4], s0[5], 2010.0, 2020.0)

    minimal = load_json(os.path.join(PHASE717_DIR, "tsi_minimal_cases_v1.json"))["payload"]
    if abs(float(sa3[4]) - minimal["divergence_at_D1_2"]["tsi_stream_A"]) > 1e-9:
        errors.append("TSI stream A ricalcolato indipendentemente non combacia con "
                      "l'artifact salvato")
    if abs(float(sb1[4]) - minimal["divergence_at_D1_2"]["tsi_stream_B"]) > 1e-9:
        errors.append("TSI stream B ricalcolato indipendentemente non combacia con "
                      "l'artifact salvato")
    if abs(float(sa3[4]) - float(sb1[4])) < 1e-6:
        errors.append("stream A e B risultano numericamente uguali nel caso minimo - "
                      "atteso invece una divergenza dimostrabile")

    # --- Nessun file MQL5 toccato in questa fase. ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/"],
                            cwd=ROOT, capture_output=True, text=True)
    if result.stdout.strip():
        errors.append(f"file MQL5 risultano modificati: {result.stdout.strip()}")

    # --- Nessun nuovo file .ini di Tester pluriennale creato in questa fase. ---
    for fname in os.listdir(PHASE717_DIR):
        if fname.endswith(".ini"):
            errors.append(f"trovato un file .ini di configurazione Tester in phase7_17/ "
                          f"({fname}) - non atteso in questa fase")

    # --- decisione e campi richiesti ammessi. ---
    card = load_json(os.path.join(PHASE717_DIR, "tsi_decision_card_v1.json"))["payload"]
    allowed_decisions = {"DEFECT_NOT_REPRODUCED", "DEFECT_CONFIRMED_LOW_IMPACT",
                         "DEFECT_CONFIRMED_MATERIAL_IMPACT", "INSUFFICIENT_EVIDENCE"}
    if card["decision"] not in allowed_decisions:
        errors.append(f"decisione '{card['decision']}' non ammessa")
    allowed_distortion = {"FALSE_NEGATIVE_RISK", "FALSE_POSITIVE_RISK", "BOTH",
                          "NONE_KNOWN", "UNKNOWN"}
    if card["distortion_direction"] not in allowed_distortion:
        errors.append(f"distortion_direction '{card['distortion_direction']}' non ammesso")
    if "confidence" not in card:
        errors.append("decision card: manca il campo confidence")
    if card.get("no_ea_modification_this_phase") is not True:
        errors.append("decision card: no_ea_modification_this_phase non True")
    if not card["fix_proposal"]["proposed_only_not_applied"]:
        errors.append("decision card: il fix risulta APPLICATO - non atteso in questa fase")

    # --- coerenza fra impact comparison e decisione. ---
    impact = load_json(os.path.join(PHASE717_DIR, "tsi_impact_comparison_v1.json"))["payload"]
    if card["decision"] == "DEFECT_CONFIRMED_MATERIAL_IMPACT" and not impact["defect_materially_changes_behavior"]:
        errors.append("decision card dichiara impatto materiale ma tsi_impact_comparison non lo conferma")
    if not impact["no_new_tester_run_launched"]:
        errors.append("tsi_impact_comparison dichiara un nuovo run Tester lanciato - non atteso")

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
