#!/usr/bin/env python3
"""Phase 7.9G - punto 3: BAR_UPDN ha lo STESSO pattern strutturale
(g_barUpDnState, struct globale non scoped per-TF, introdotto nello
STESSO commit del fix di BREAKOUT_ACC) - segnalato come backlog item,
NON corretto in questa fase."""
import os
import sys

PHASE79G_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79G_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "8d2cde76f4233aa0da3ffa83778eee421a60093c"


def build():
    return {
        "phase": "7.9G", "backlog_item": "POSSIBLE_SAME_SCOPING_DEFECT_BAR_UPDN",
        "baseline_commit": BASELINE_COMMIT,
        "not_fixed_in_this_phase": True,
        "structural_sibling": {
            "strategy": "BAR_UPDN", "profile_tf": "PERIOD_M15",
            "state_variable": "g_barUpDnState (struct SNXSBarUpDnState: lastBarTime + "
                "lastFireTime[2]) - NXS_Strategies.mqh",
            "introduced_in_same_commit_as_breakout_acc_cooldown": "7871e96c6ae8f5d9d2c173f515060cd04834ef0c (02/09)",
            "same_missing_guard": "NXS_Strat_BarUpDn() non verifica NXS_EffTF() contro il "
                "proprio timeframe di profilo (M15) prima di leggere/scrivere "
                "g_barUpDnState - identico difetto strutturale a quello confermato "
                "(IMPLEMENTATION_DEFECT_CONFIRMED, Phase 7.9F) per BREAKOUT_ACC.",
        },
        "why_not_fixed_here": "L'autorizzazione dell'utente per questa fase copre "
            "esplicitamente e solo BREAKOUT_ACC ('correggere il difetto implementativo "
            "confermato di BREAKOUT_ACC'). BAR_UPDN non ha attraversato lo stesso processo "
            "di adjudication (identita' documentale, esperimenti diagnostici dedicati) - "
            "estendere il fix per analogia senza quel processo violerebbe la disciplina "
            "'nessuna optimization/rescue mascherata' e il principio 'fix minimale, un "
            "difetto alla volta, verificato'.",
        "recommended_next_step_not_executed": "Ripetere per BAR_UPDN lo stesso processo "
            "gia' applicato a BREAKOUT_ACC (Phase 7.9C-7.9F): verificare identita' "
            "documentale del suo cooldown, misurare sperimentalmente l'effetto della "
            "contaminazione cross-TF con un esperimento diagnostico dedicato, solo poi "
            "decidere se e come correggere.",
        "other_strategies_with_similar_pattern_not_audited": "Non e' stata condotta in "
            "questa fase una ricerca esaustiva di TUTTE le strategie con stato "
            "stateful-per-direzione potenzialmente soggette allo stesso pattern (solo "
            "BAR_UPDN e' stato notato perche' introdotto nello stesso commit) - "
            "dichiarato come limite noto, non un'affermazione che BAR_UPDN sia l'unico "
            "altro caso.",
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79G_DIR, "breakout_acc_bar_updn_structural_warning_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    return doc


if __name__ == "__main__":
    main()
