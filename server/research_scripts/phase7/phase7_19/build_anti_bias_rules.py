#!/usr/bin/env python3
"""Phase 7.19 punto 23 - ANTI_BIAS_RULES_V1."""
import os
import sys

PHASE719_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE719_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

RULES = [
    {
        "id": "AB01", "rule": "No future bars nella blind review",
        "enforcement": "multi_timeframe_context.bars_by_timeframe[tf].subsequent_bars deve "
                       "essere assente/vuoto in qualunque packet usato per Stage A - vedi "
                       "ANTI_LEAKAGE_SPECIFICATION_V1",
    },
    {
        "id": "AB02", "rule": "No outcome nel matched sampling",
        "enforcement": "MATCHED_NON_EVENT_V1.outcome_used_in_selection vincolato a false nello "
                       "schema - vedi SAMPLING_PROTOCOL_V1",
    },
    {
        "id": "AB03", "rule": "No selezione dei 'casi interessanti' usando PnL senza dichiararlo",
        "enforcement": "Qualunque selezione informata dall'esito deve essere etichettata "
                       "esplicitamente come tale (es. dataset_split_tag o una nota dedicata) - "
                       "mai presentata come campione neutro/casuale",
    },
    {
        "id": "AB04", "rule": "No modifica delle feature dopo aver visto holdout",
        "enforcement": "edge_discovery_compatibility.dataset_split_tag deve essere assegnato "
                       "PRIMA di qualunque analisi - una feature aggiunta/modificata dopo aver "
                       "osservato risultati su HOLDOUT invalida lo split (richiede un nuovo "
                       "hypothesis_id e un nuovo split)",
    },
    {
        "id": "AB05", "rule": "Visual review blind PRIMA del reveal",
        "enforcement": "VISUAL_AUDIT_PROTOCOL_V1: Stage A deve essere bloccato/versionato "
                       "(conclusions_versioned) prima che Stage B sia accessibile - vedi "
                       "stage_b_future_reveal.revealed_after_stage_a_locked",
    },
    {
        "id": "AB06", "rule": "Reviewer conclusions versionate",
        "enforcement": "VISUAL_AUDIT_RESULT_V1.conclusions_versioned + superseded_by - una "
                       "revisione successiva non sovrascrive mai silenziosamente, crea un "
                       "nuovo record collegato",
    },
    {
        "id": "AB07", "rule": "Distinzione observation vs hypothesis vs validated result",
        "enforcement": "VISUAL_AUDIT_RESULT_V1.observation_vs_hypothesis_vs_validated "
                       "obbligatorio - un risultato a fidelity C/D non puo' mai dichiararsi "
                       "VALIDATED_RESULT (vedi FIDELITY_FRAMEWORK_V1.downstream_constraint)",
    },
]


def build():
    payload = {
        "rules_name": "ANTI_BIAS_RULES_V1",
        "rules": RULES,
        "n_rules": len(RULES),
        "principle": "Ogni regola ha un meccanismo di ENFORCEMENT verificabile in uno schema o "
                    "in un controllo automatico dichiarato - non solo un principio astratto.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE719_DIR, "anti_bias_rules_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
