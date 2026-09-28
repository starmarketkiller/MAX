#!/usr/bin/env python3
"""Phase 7.24 punto 4 - separazione esplicita trigger/exit semantics e
classificazione formale di COSA Python puo' e NON puo' essere usato
per fare, riusando (non ri-derivando) i findings gia' stabiliti in
Phase 7.23 (liq_sweep_semantic_parity_matrix_v1.json). Nessuna modifica
al codice Python: la regola del progetto resta 'MT5 = ground truth,
Python analizza gli eventi esportati' quando l'exit diverge."""
import os
import sys

PHASE724_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE724_DIR, "..", "..", "..", ".."))
PHASE723_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_23")
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402


def build():
    parity = load_json(os.path.join(PHASE723_DIR, "liq_sweep_semantic_parity_matrix_v1.json"))["payload"]

    payload = {
        "canonical_exit_definition": {
            "mql5": "NXS_DefaultSLTP() - uscita FISSA: SL = entry -/+ 1.5*ATR, TP = entry +/- "
                    "3.0*ATR (R:R=2.0 costante, da NXS_Profile_SLTP('LIQ_SWEEP')). Questa e' "
                    "l'unica logica di uscita realmente eseguita dal vivo/nel Tester per "
                    "LIQ_SWEEP - fonte di ogni P&L nel dataset canonico di questa fase.",
            "python_historical_proxy": "_liq_sweep_target() - uscita DINAMICA su pool di "
                    "liquidita' opposti (PDH/PDL/Asia/swing_ext), min_rr=1.2, sl_mult=1.5. "
                    "Dichiarata nel codice stesso come sostituzione di 'un multiplo fisso di "
                    "ATR' - cioe' esplicitamente NON un tentativo di replicare l'exit MQL5, ma "
                    "una variante di ricerca indipendente.",
        },
        "consequence": [
            "Python NON puo' essere usato per validare PF/expectancy/P&L della strategia "
            "canonica LIQ_SWEEP (qualunque numero economico calcolato da Python misura una "
            "strategia con lo stesso ingresso ma un'uscita diversa, non quella che gira dal "
            "vivo).",
            "Python PUO' essere usato solo per confronti compatibili col livello di fedelta' "
            "dimostrato in Phase 7.23: identita' dell'ingresso (sweep detection, delivery-candle "
            "filter, direction gate - tutti EVENT_LEVEL_FAITHFUL_FOR_THIS_SUBCOMPONENT o "
            "PARTIAL_STRUCTURAL_MODEL per lettura diretta del codice). Un uso legittimo futuro "
            "sarebbe un confronto di SEGNALI (date/direzioni dei trigger), mai di P&L.",
        ],
        "fidelity_classification_per_component": {
            k: v["parity_status"] for k, v in parity["funnel_levels_compared"].items()
        },
        "overall_classification": parity["overall_python_suitability"],
        "no_python_code_modified_to_force_pnl_match": True,
        "rule_applied": "MT5 e' ground truth quando Python non replica fedelmente "
                        "execution/lifecycle (regola di progetto gia' stabilita) - il dataset "
                        "canonico di questa fase (liq_sweep_canonical_dataset_v1.json) e' "
                        "costruito ESCLUSIVAMENTE da MT5, zero dipendenza da Python.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE724_DIR, "liq_sweep_python_fidelity_classification_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
