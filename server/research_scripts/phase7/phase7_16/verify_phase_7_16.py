#!/usr/bin/env python3
"""Phase 7.16 - verificatore indipendente. Ri-deriva ogni artifact dai
builder, ri-verifica indipendentemente i 4 episodi minimi (eseguendo
le due funzioni sotto esame e confrontando con gli op attesi dichiarati
nell'artifact - i valori attesi sono stati scritti a mano nel builder,
non ricavati eseguendo il codice), verifica che nessun file MQL5 sia
stato toccato e che nessun nuovo run Tester pluriennale sia stato
lanciato in questa fase."""
import os
import subprocess
import sys

PHASE716_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE713_DIR = os.path.abspath(os.path.join(PHASE716_DIR, "..", "phase7_13"))
ROOT = os.path.abspath(os.path.join(PHASE716_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE713_DIR)
from nxs_order_block_replica import OBState, ob_update_side  # noqa: E402

sys.path.insert(0, PHASE716_DIR)
from nxs_order_block_replica_corrected import ob_update_side_corrected  # noqa: E402
import build_semantic_contract_matrix as matrix_builder  # noqa: E402
import build_first_divergence as divergence_builder  # noqa: E402
import build_minimal_episodes as episodes_builder  # noqa: E402
import build_fidelity_classification_and_proposal as classification_builder  # noqa: E402

ARTIFACTS = [
    ("semantic_contract_matrix_v1.json", matrix_builder.build),
    ("first_divergence_v1.json", divergence_builder.build),
    ("minimal_episodes_v1.json", episodes_builder.build),
    ("fidelity_classification_and_proposal_v1.json", classification_builder.build),
]


def verify():
    errors = []

    for fname, build_fn in ARTIFACTS:
        path = os.path.join(PHASE716_DIR, fname)
        if not os.path.exists(path):
            errors.append(f"{fname}: file mancante")
            continue
        saved = load_json(path)
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    # --- Re-esegue i 4 episodi minimi e confronta con gli op attesi dichiarati
    # nell'artifact (i valori attesi sono stati scritti a mano nel builder). ---
    episodes = load_json(os.path.join(PHASE716_DIR, "minimal_episodes_v1.json"))["payload"]["episodes"]
    for ep in episodes:
        dirn = 1 if ep["direction"] == "BUY" else -1
        ob_lo, ob_hi = ep["input_common"]["ob_lo"], ep["input_common"]["ob_hi"]
        bars = [ep["input_common"]["bar_shift1_bars_i"], ep["input_common"]["bar_shift0_bars_i_plus_1"]]
        atr = ep["atr_at_this_point"]
        st_o = OBState()
        st_o.active, st_o.ob_lo, st_o.ob_hi = True, ob_lo, ob_hi
        st_o.bars_waited = ep["state_initial"]["bars_waited"]
        st_o.last_bar_time = ep["state_initial"]["last_bar_time"]
        st_c = OBState()
        st_c.active, st_c.ob_lo, st_c.ob_hi = True, ob_lo, ob_hi
        st_c.bars_waited = ep["state_initial"]["bars_waited"]
        st_c.last_bar_time = ep["state_initial"]["last_bar_time"]
        curbar0 = bars[1]["open_time"]
        _, _, rec_o = ob_update_side(dirn, st_o, bars, 0, atr, curbar0)
        _, _, rec_c = ob_update_side_corrected(dirn, st_c, bars, 0, atr, curbar0)
        exp_o = ep["hand_derivation"]["original_expected_op"]
        exp_c = ep["hand_derivation"]["corrected_expected_op"]
        if rec_o["op"] not in exp_o:
            errors.append(f"{ep['id']}: op originale '{rec_o['op']}' non combacia con atteso "
                          f"'{exp_o}'")
        if rec_c["op"] not in exp_c:
            errors.append(f"{ep['id']}: op corretto '{rec_c['op']}' non combacia con atteso "
                          f"'{exp_c}'")

    # --- Nessun file MQL5 toccato in questa fase (ORDER_BLOCK/OB_MIT non
    # modificati, come richiesto). ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/"],
                            cwd=ROOT, capture_output=True, text=True)
    if result.stdout.strip():
        errors.append(f"file MQL5 risultano modificati: {result.stdout.strip()}")

    # --- Nessun nuovo file .ini di Tester pluriennale creato in questa fase
    # (nessuna nuova campagna lunga). ---
    for fname in os.listdir(PHASE716_DIR):
        if fname.endswith(".ini"):
            errors.append(f"trovato un file .ini di configurazione Tester in phase7_16/ "
                          f"({fname}) - non atteso in questa fase (nessun nuovo run lungo)")

    # --- classificazione finale ammessa. ---
    card = load_json(os.path.join(PHASE716_DIR, "fidelity_classification_and_proposal_v1.json"))["payload"]
    allowed = {"EVENT_LEVEL_PARITY_VALIDATED", "PARTIAL_STRUCTURAL_MODEL",
              "APPROXIMATION_WITH_KNOWN_GAPS", "NOT_SUITABLE_FOR_EVENT_PARITY",
              "INSUFFICIENT_EVIDENCE"}
    if card["classification"] not in allowed:
        errors.append(f"classificazione '{card['classification']}' non ammessa")
    if card.get("order_block_pre_post_fix_validation_preserved") is not True:
        errors.append("la validazione ORDER_BLOCK pre/post-fix (Phase 7.14) non risulta "
                      "esplicitamente preservata")

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
