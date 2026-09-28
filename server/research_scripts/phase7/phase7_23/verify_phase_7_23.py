#!/usr/bin/env python3
"""Phase 7.23 - verificatore indipendente. Ri-deriva ogni artifact dai
builder; verifica staticamente sul sorgente MQL5 attuale i claim chiave
dell'audit (NXS_Strat_LiqSweep e' stateless, NXS_ActivateTF chiama
NXS_UpdateIndicators, il detector integrity fix e' presente); verifica
che nessuna logica di strategia sia stata modificata; verifica che il
manifest del run diagnostico sia coerente con la sua raccolta."""
import json
import os
import re
import subprocess
import sys

PHASE723_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE723_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE723_DIR)
import build_run_isolation_spec as spec_builder  # noqa: E402
import build_liq_sweep_identity_map as identity_builder  # noqa: E402
import build_liq_sweep_historical_evidence_map as historical_builder  # noqa: E402
import build_liq_sweep_semantic_parity_matrix as parity_builder  # noqa: E402
import build_liq_sweep_diagnostic_findings as diagnostic_builder  # noqa: E402
import build_liq_sweep_diagnostic_run as run_builder  # noqa: E402
import build_liq_sweep_decision_card as decision_builder  # noqa: E402

STRAT_PATH = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
EA_PATH = os.path.join(ROOT, "MQL5", "Experts", "NEXUS_EA_v2.mq5")

ARTIFACTS = [
    ("run_isolation_spec_v1.json", spec_builder.build),
    ("liq_sweep_identity_map_v1.json", identity_builder.build),
    ("liq_sweep_historical_evidence_map_v1.json", historical_builder.build),
    ("liq_sweep_semantic_parity_matrix_v1.json", parity_builder.build),
    ("liq_sweep_diagnostic_findings_v1.json", diagnostic_builder.build),
    ("liq_sweep_diagnostic_run_v1.json", run_builder.build),
    ("liq_sweep_decision_card_v1.json", decision_builder.build),
]

ALLOWED_DECISIONS = {"INTEGRITY_VALIDATED_READY_FOR_EDGE_VALIDATION", "INTEGRITY_PARTIALLY_VALIDATED",
                     "IMPLEMENTATION_DEFECT_CONFIRMED", "INSUFFICIENT_EVIDENCE"}


def verify():
    errors = []

    for fname, build_fn in ARTIFACTS:
        path = os.path.join(PHASE723_DIR, fname)
        if not os.path.exists(path):
            errors.append(f"{fname}: file mancante")
            continue
        saved = load_json(path)
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    # --- claim chiave 1: NXS_Strat_LiqSweep e' stateless (nessuna variabile
    # globale propria mutata, solo il parametro sw). ---
    strat_text = open(STRAT_PATH, encoding="utf-8").read()
    ls_start = strat_text.find("SNXSSignal NXS_Strat_LiqSweep(")
    ls_end = strat_text.find("\n}\n", ls_start)
    ls_body = strat_text[ls_start:ls_end]
    if re.search(r"g_liqSweep\w*\s*=", ls_body):
        errors.append("NXS_Strat_LiqSweep sembra mutare uno stato globale proprio (g_liqSweep*) - "
                      "il claim 'stateless' di questa fase andrebbe rivisto")

    # --- claim chiave 2: NXS_ActivateTF chiama NXS_UpdateIndicators DOPO lo
    # scambio di handle (base della verifica 'nessun mismatch HTF'). ---
    ea_text = open(EA_PATH, encoding="utf-8").read()
    at_start = ea_text.find("bool NXS_ActivateTF(")
    at_end = ea_text.find("\n}\n", at_start)
    at_body = ea_text[at_start:at_end]
    if "NXS_UpdateIndicators()" not in at_body:
        errors.append("NXS_ActivateTF non chiama piu' NXS_UpdateIndicators() - il claim "
                      "'nessun mismatch HTF' di questa fase e' basato su questo, andrebbe rivisto")

    # --- claim chiave 3: il fix di integrita' del detector (init esplicita)
    # e' presente nel sorgente attuale. ---
    ma_path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_MarketAnalysis.mqh")
    ma_text = open(ma_path, encoding="utf-8").read()
    if 's.confirmed = false;' not in ma_text or 's.levelTag = "";' not in ma_text:
        errors.append("NXS_DetectSweepExt non sembra piu' avere l'inizializzazione esplicita "
                      "dei campi (fix 'Detector Integrity' del 2026-09-14) - verificare")

    # --- claim chiave 4: il filtro delivery-candle 0.7xATR e' presente. ---
    if "0.7 * g_atr" not in strat_text and "0.7*g_atr" not in strat_text:
        errors.append("Filtro delivery-candle 0.7xATR non trovato in NXS_Strategies.mqh - "
                      "verificare il claim sull'entry trigger")

    # --- claim chiave 5: NXS_DefaultSLTP usa un moltiplicatore ATR fisso dal
    # profilo, non un target dinamico su liquidita'. ---
    dsl_start = strat_text.find("void NXS_DefaultSLTP(")
    dsl_end = strat_text.find("\n}\n", dsl_start)
    dsl_body = strat_text[dsl_start:dsl_end]
    if "NXS_Profile_SLTP" not in dsl_body or "liquidity" in dsl_body.lower():
        errors.append("NXS_DefaultSLTP non corrisponde piu' al comportamento atteso (SL/TP fisso "
                      "da profilo) - il mismatch con Python andrebbe riverificato")

    # --- nessuna modifica a logica di strategia (solo research harness). ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/",
                            "contracts/"], cwd=ROOT, capture_output=True, text=True)
    modified = [l for l in result.stdout.strip().splitlines() if l.strip()]
    if modified:
        errors.append(f"file MQL5/Product-Platform/contracts risultano modificati: {modified}")

    # --- se il run diagnostico e' stato raccolto, il manifest deve essere
    # coerente (run_id presente, status=COLLECTED). ---
    run_payload = load_json(os.path.join(PHASE723_DIR, "liq_sweep_diagnostic_run_v1.json"))["payload"]
    if run_payload.get("status") == "COLLECTED":
        manifest_path = run_payload.get("run_isolation_manifest")
        if not manifest_path or not os.path.exists(manifest_path):
            errors.append("run diagnostico marcato COLLECTED ma il manifest referenziato non esiste")
        else:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            if manifest.get("status") != "COLLECTED":
                errors.append("manifest del run diagnostico non e' in stato COLLECTED nonostante "
                              "il riepilogo lo dichiari tale")

    # --- decisione ammessa. ---
    decision = load_json(os.path.join(PHASE723_DIR, "liq_sweep_decision_card_v1.json"))["payload"]
    if decision["decision"] not in ALLOWED_DECISIONS:
        errors.append(f"decisione '{decision['decision']}' non ammessa")
    if decision.get("not_ready_for_edge_validation_yet") is not True:
        errors.append("decision card: manca la dichiarazione not_ready_for_edge_validation_yet")

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
