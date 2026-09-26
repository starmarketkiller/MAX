#!/usr/bin/env python3
"""Phase 7.9K - BREAKOUT_ACC_INTENDED_D1_V1, dataset schema V2. Corregge
il difetto di indicizzazione forward (offset di +1 barra) confermato in
Phase 7.9J, mantenendo l'identita' di strategia (BREAKOUT_ACC_INTENDED_
D1_V1 - il nome NON cambia: cambia lo SCHEMA del dataset derivato, non
la strategia). event_id CONSERVATI dal dataset V1 (stessi eventi).
Funnel e collegamenti ai fill INVARIATI rispetto a V1 (nessun nuovo
difetto trovato li').

Preserva integralmente Phase 7.9H (V1) e tutti i raw data - nessuna
scrittura su quei file.
"""
import os
import sys
from datetime import datetime

PHASE79K_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79H_DIR = os.path.abspath(os.path.join(PHASE79K_DIR, "..", "phase7_9h"))
PHASE79I_DIR = os.path.abspath(os.path.join(PHASE79K_DIR, "..", "phase7_9i"))
ROOT = os.path.abspath(os.path.join(PHASE79K_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

sys.path.insert(0, PHASE79K_DIR)
sys.path.insert(0, PHASE79I_DIR)
import nxs_forward_path_v2 as fp  # noqa: E402
import nxs_mechanism_context as ctx  # noqa: E402

V1_DATASET_PATH = os.path.join(PHASE79H_DIR, "breakout_acc_intended_d1_v1_dataset.json")


def build():
    v1_doc = load_json(V1_DATASET_PATH)
    v1_payload = v1_doc["payload"]
    v1_sha = v1_doc["canonical_sha256"]
    v1_events = v1_payload["events"]

    d1_bars = fp.load_d1_bars()
    real_signal_timestamps = fp.load_real_signal_timestamps()

    # Riusa la feature table di Phase 7.9J (causal_ema gia' corretta, c1 gia'
    # verificato causalmente pulito) per breakout_close_c1 per TUTTI i 75 eventi.
    feat_rows = {r["event_id"]: r for r in ctx.build_feature_table()["rows"]}

    events_v2 = []
    for e in v1_events:
        event_id = e["event_id"]
        feat = feat_rows[event_id]
        row = dict(e)  # copia ESATTA di ogni campo V1 - funnel/fill invariati

        # --- Misurazione A (post-segnale): TUTTI i 75 eventi, timestamp reale del
        # segnale dove disponibile (67), sintetico ESPLICITAMENTE etichettato per gli
        # 8 B-only. Prezzo = c1, uniforme, MAI il fill. ---
        ref_time_a, ref_price_a, ts_source_a = fp.measurement_a_reference(
            feat, real_signal_timestamps)
        if ref_price_a is not None:
            path_a = fp.path_anatomy_v2(d1_bars, ref_time_a, ref_price_a, e["direction"])
            path_a["reference_timestamp"] = ref_time_a.strftime("%Y.%m.%d %H:%M:%S")
            path_a["reference_timestamp_source"] = ts_source_a
            path_a["reference_price"] = ref_price_a
            path_a["reference_price_source"] = ("breakout_close_c1 (chiusura della barra "
                "precedente il segnale - causalmente pulita, Phase 7.9J)")
        else:
            path_a = {"status": "NO_REFERENCE_PRICE_AVAILABLE"}
        row["measurement_A_post_signal_path"] = path_a

        # --- Misurazione B (post-fill): SOLO i 47 OPENED, fill reale verificato. Tenuta
        # SEPARATA da A - mai fusa, mai usata per BLOCKED/BROKER_REJECT/B-only. ---
        ref_time_b, ref_price_b = fp.measurement_b_reference(feat)
        if ref_time_b is not None:
            path_b = fp.path_anatomy_v2(d1_bars, ref_time_b, ref_price_b, e["direction"])
            path_b["reference_timestamp"] = ref_time_b.strftime("%Y.%m.%d %H:%M:%S")
            path_b["reference_timestamp_source"] = "REAL_FILL_TIMESTAMP_VERIFIED"
            path_b["reference_price"] = ref_price_b
            path_b["reference_price_source"] = ("entry_fill_price (HistoryDealGetDouble, "
                "deal reale verificato, Phase 7.9H)")
        else:
            path_b = {"status": "NOT_APPLICABLE_NOT_OPENED"}
        row["measurement_B_post_fill_path"] = path_b

        # --- Il vecchio campo 'post_entry_path_anatomy' (V1, offset di +1 barra
        # confermato in 7.9J) resta presente per confronto diretto prima/dopo, ma
        # MARCATO come superseded. ---
        row["post_entry_path_anatomy_V1_SUPERSEDED"] = e.get("post_entry_path_anatomy")
        if "post_entry_path_anatomy" in row:
            del row["post_entry_path_anatomy"]

        events_v2.append(row)

    return {
        "phase": "7.9K", "dataset_name": "BREAKOUT_ACC_INTENDED_D1_V1",
        "dataset_schema_version": "V2",
        "supersedes_dataset_schema_version": "V1",
        "supersedes_path": "server/research_scripts/phase7/phase7_9h/"
            "breakout_acc_intended_d1_v1_dataset.json",
        "supersedes_sha256": v1_sha,
        "identity_note": (
            "Il NOME della strategia/dataset (BREAKOUT_ACC_INTENDED_D1_V1) NON cambia - "
            "cambiare la versione dello schema del dataset derivato non cambia "
            "l'identita' della strategia. event_id CONSERVATI da V1 (stessi eventi, "
            "stessa identita' causale sha256(strategia|direzione|data))."
        ),
        "defect_corrected": (
            "Phase 7.9J aveva confermato un offset di +1 barra nel calcolo del percorso "
            "forward (post_entry_path_anatomy di V1): la ricerca della prima barra D1 "
            "con apertura >= reference_time trovava correttamente la prima barra "
            "COMPLETA, ma il codice poi la scartava come 'barra 0 di riferimento' e "
            "iniziava a contare da 'bar 1' sulla barra SUCCESSIVA - un ritardo spurio "
            "di 1 giorno di mercato su ogni MFE/MAE/forward return/bars_to_mfe/"
            "bars_to_mae. Corretto in questa versione: 'bar 1' = la prima barra D1 "
            "completa stessa (nxs_forward_path_v2.py)."
        ),
        "funnel_and_fill_links_unchanged": True,
        "funnel_and_fill_links_note": (
            "generated_detail, funnel_terminal_stage, entry_fill_price/time, "
            "exit_fill_price/time, realized_pnl, signal_price, signal_to_fill_slippage "
            "sono COPIATI IDENTICI da V1 - nessun nuovo difetto trovato in questi campi "
            "in questa fase."
        ),
        "two_separate_measurements": {
            "measurement_A_post_signal": "Tutti i 75 eventi (67 con timestamp REALE del "
                "segnale dal trace live, 8 B-only con timestamp SINTETICO esplicitamente "
                "etichettato SYNTHETIC_NOT_OBSERVED_NOON_PLACEHOLDER) - prezzo c1 "
                "uniforme, MAI il fill reale.",
            "measurement_B_post_fill": "Solo i 47 OPENED - fill reale verificato "
                "(prezzo e timestamp). MAI fusa con la misurazione A.",
        },
        "total_events": len(events_v2),
        "events": events_v2,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79K_DIR, "breakout_acc_intended_d1_v2_dataset.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"total_events={payload['total_events']}")
    print(f"supersedes_sha256={payload['supersedes_sha256']}")
    return doc


if __name__ == "__main__":
    main()
