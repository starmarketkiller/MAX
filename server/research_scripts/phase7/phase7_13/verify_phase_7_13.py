#!/usr/bin/env python3
"""Phase 7.13 - verificatore indipendente. Ri-deriva ogni artifact dai
builder, ri-verifica sul codice sorgente attuale che il difetto sia
ancora presente e non applicato (nessuna guardia TF in
NXS_Strat_OrderBlock, OB_MIT ancora wrapper diretto), ri-controlla la
prova sintetica contro i valori attesi calcolati a mano (import diretto
dal builder, non ri-eseguendo la stessa logica in modo circolare), e
verifica che nessun file MQL5/EA sia stato modificato in questa fase."""
import os
import subprocess
import sys

PHASE713_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE713_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json, file_sha256  # noqa: E402

sys.path.insert(0, PHASE713_DIR)
import build_synthetic_causal_proof as synth_builder  # noqa: E402
import build_multi_tf_dataset as mtf_builder  # noqa: E402
import build_ab_simulation as ab_builder  # noqa: E402
import build_state_mutation_trace as trace_builder  # noqa: E402
import build_historical_evidence_impact_map as hist_builder  # noqa: E402
import build_breakout_acc_comparison as cmp_builder  # noqa: E402
import build_decision_card as card_builder  # noqa: E402

ARTIFACTS = [
    ("synthetic_causal_proof_v1.json", synth_builder.build),
    ("multi_tf_dataset_v1.json", mtf_builder.build),
    ("ab_simulation_v1.json", ab_builder.build),
    ("state_mutation_trace_v1.json", trace_builder.build),
    ("historical_evidence_impact_map_v1.json", hist_builder.build),
    ("breakout_acc_comparison_v1.json", cmp_builder.build),
    ("decision_card_order_block_v1.json", card_builder.build),
]


def verify():
    errors = []

    for fname, build_fn in ARTIFACTS:
        path = os.path.join(PHASE713_DIR, fname)
        if not os.path.exists(path):
            errors.append(f"{fname}: file mancante")
            continue
        saved = load_json(path)
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    # --- 1) La prova sintetica combacia con i valori attesi calcolati A MANO
    # (import diretto delle costanti EXPECTED_* dal builder - non una nuova
    # esecuzione della stessa funzione sotto verifica). ---
    trace_a, _ = synth_builder.run_stream_a()
    trace_b, _ = synth_builder.run_stream_b()
    a_sigs = [(e["bar"], e["signal"]) for e in trace_a]
    b_sigs = [(e["bar"], e["signal"]) for e in trace_b]
    if a_sigs != synth_builder.EXPECTED_STREAM_A_SIGNALS:
        errors.append(f"prova sintetica Stream A non combacia con l'attesa a mano: {a_sigs}")
    if b_sigs != synth_builder.EXPECTED_STREAM_B_SIGNALS:
        errors.append(f"prova sintetica Stream B non combacia con l'attesa a mano: {b_sigs}")

    # --- 2) Il difetto e' ANCORA presente e NON corretto nel sorgente reale
    # (nessuna guardia TF), altrimenti l'intera diagnosi sarebbe stale. ---
    strat_path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
    smc_path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies_SMC.mqh")
    strat_text = open(strat_path, encoding="utf-8").read()
    smc_text = open(smc_path, encoding="utf-8").read()
    ob_start = strat_text.find("SNXSSignal NXS_Strat_OrderBlock()")
    ob_end = strat_text.find("\n}\n", ob_start)
    ob_body = strat_text[ob_start:ob_end]
    if "NXS_Profile_TF" in ob_body:
        errors.append("NXS_Strat_OrderBlock() sembra GIA' avere una guardia NXS_Profile_TF - "
                      "il difetto potrebbe essere gia' stato corretto, questa diagnosi e' stale")
    if "g_obBuy" not in ob_body or "g_obSell" not in ob_body:
        errors.append("NXS_Strat_OrderBlock() non referenzia piu' g_obBuy/g_obSell come atteso")
    ob_mit_start = smc_text.find("NXS_Strat_OB_Mitigation_Structural()")
    ob_mit_body = smc_text[ob_mit_start:smc_text.find("\n}\n", ob_mit_start)]
    if "NXS_Strat_OrderBlock()" not in ob_mit_body:
        errors.append("NXS_Strat_OB_Mitigation_Structural() non chiama piu' direttamente "
                      "NXS_Strat_OrderBlock() - il finding OB_MIT andrebbe rivisto")
    # BREAKOUT_ACC deve ancora avere la SUA guardia (precedente architetturale citato)
    ba_start = strat_text.find("SNXSSignal NXS_Strat_BreakoutAcc()")
    ba_end = strat_text.find("\n}\n", ba_start)
    ba_body = strat_text[ba_start:ba_end]
    if 'NXS_Profile_TF("BREAKOUT_ACC")' not in ba_body:
        errors.append("NXS_Strat_BreakoutAcc() non ha piu' la guardia attesa - il confronto "
                      "con BREAKOUT_ACC come precedente architetturale andrebbe rivisto")

    # --- 3) Nessun file MQL5/EA modificato in questa fase (nessuna guardia
    # applicata al sorgente reale, solo proposta). ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/"],
                            cwd=ROOT, capture_output=True, text=True)
    if result.stdout.strip():
        errors.append(f"file MQL5 risultano modificati: {result.stdout.strip()}")

    # --- 4) La fonte M15 usata dal dataset multi-TF non e' stata alterata a
    # meta' analisi (stesso hash dichiarato nell'artifact). ---
    mtf_doc = load_json(os.path.join(PHASE713_DIR, "multi_tf_dataset_v1.json"))
    source_path = os.path.join(ROOT, "server", "research_scripts", "nxs_m15_gold_extended.csv")
    if os.path.exists(source_path):
        actual_hash = file_sha256(source_path)
        declared_hash = mtf_doc["payload"]["source_sha256"]
        if actual_hash != declared_hash:
            errors.append("la fonte M15 e' cambiata rispetto all'hash dichiarato nel dataset - "
                          "ri-eseguire i builder")
    else:
        errors.append("fonte M15 non trovata - impossibile ri-verificare la provenienza")

    # --- 5) Decision Card: decisione, integrita' storica e direzione della
    # distorsione devono essere fra i valori ammessi dal task. ---
    card = load_json(os.path.join(PHASE713_DIR, "decision_card_order_block_v1.json"))["payload"]
    allowed_decisions = {"DEFECT_NOT_REPRODUCED", "DEFECT_CONFIRMED_LOW_IMPACT",
                         "DEFECT_CONFIRMED_MATERIAL_IMPACT", "INSUFFICIENT_EVIDENCE"}
    if card["decision"] not in allowed_decisions:
        errors.append(f"decisione '{card['decision']}' non fra i valori ammessi {allowed_decisions}")
    allowed_distortion = {"FALSE_NEGATIVE_RISK", "FALSE_POSITIVE_RISK", "BOTH", "NONE_KNOWN", "UNKNOWN"}
    if card["distortion_direction"] not in allowed_distortion:
        errors.append(f"distortion_direction '{card['distortion_direction']}' non ammesso")
    if card.get("ea_source_untouched_this_phase") is not True:
        errors.append("decision card: ea_source_untouched_this_phase non True")
    if not card["fix_proposal"]["proposed_only_not_applied"]:
        errors.append("decision card: il fix risulta APPLICATO - non atteso in questa fase")

    # --- 6) La quantificazione reale (ab_simulation) e' coerente con la
    # decisione presa (materiale se la decisione lo dichiara). ---
    ab = load_json(os.path.join(PHASE713_DIR, "ab_simulation_v1.json"))["payload"]
    if card["decision"] == "DEFECT_CONFIRMED_MATERIAL_IMPACT" and not ab["defect_materially_changes_behavior"]:
        errors.append("decision card dichiara impatto materiale ma ab_simulation non lo conferma")
    if len(ab["only_in_a"]) + len(ab["only_in_b"]) == 0:
        errors.append("ab_simulation non mostra alcuna differenza fra Stream A e B - "
                      "incoerente con DEFECT_CONFIRMED_MATERIAL_IMPACT")

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
