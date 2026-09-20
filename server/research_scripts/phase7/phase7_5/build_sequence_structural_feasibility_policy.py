#!/usr/bin/env python3
"""Phase 7.5A - genera sequence_structural_feasibility_policy_v1.json.
Stesso pattern di minimum_evidence_gates.json: ogni soglia classificata
esplicitamente (POLICY_THRESHOLD vs POLICY_THRESHOLD_WITH_STATISTICAL_
RATIONALE vs STATISTICALLY_JUSTIFIED), mai un numero senza rationale."""
import os
import sys

PHASE75_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE75_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

PAYLOAD = {
    "policy_id": "SEQUENCE_STRUCTURAL_FEASIBILITY_POLICY_V1",
    "disclaimer": (
        "Gate STRUTTURALE, non statistico e non di edge. Nessuna soglia qui stima probabilita' di "
        "successo/profittabilita' - tutte rispondono esclusivamente a 'questa geometria di campione e' "
        "eseguibile sulla partition preregistrata proposta?'. Applicabile a QUALUNQUE sequence family "
        "futura, non specifico a SEQ-0015 (chiusa, vedi failure_memory_registry_v1.json FAIL-009)."
    ),
    "required_family_spec_inputs": {
        "description": "Campi che un family spec DEVE dichiarare esplicitamente prima che il gate possa "
                        "girare - sec.2 Phase 7.5A. Nessun default silenzioso: una family con anche un solo "
                        "campo mancante e' classificata NEEDS_DETECTOR_FORMALIZATION, non fatta girare con "
                        "un valore inventato.",
        "fields": [
            "sequence_family_id", "detector_frozen", "detector_source_ref", "detector_parameters",
            "observation_timing", "event_direction_policy", "episode_gap_rule", "overlap_policy",
            "proposed_natural_horizon", "proposed_outcome_overlap_embargo_bars", "discovery_partition",
            "minimum_evidence_gates", "event_row_indices",
        ],
        "enforcement": "server/research_scripts/phase7/engine/sequence_structural_feasibility_gate.py:"
                        "missing_spec_fields()",
    },
    "verdict_states": {
        "FEASIBLE": "independent_units >= feasible_margin_multiplier * minimum_required_n E "
                    "episode_retention/independence_retention entrambi sopra il floor borderline.",
        "BORDERLINE_FEASIBILITY": "independent_units >= minimum_required_n ma sotto il margine FEASIBLE, "
                                  "oppure margine sufficiente ma retention fragile (molta informazione gia' "
                                  "collassata da un passaggio del funnel).",
        "NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY": "independent_units < minimum_required_n SULLA partition "
                                                    "discovery proposta. Scoped a quella partition (vedi "
                                                    "failure_memory_registry_v1.json FAIL-009/SEQ-0015 gia' "
                                                    "corretto in Phase 7.4A Structural Verdict Semantics Patch) "
                                                    "- MAI un'affermazione di impossibilita' universale del "
                                                    "design per qualunque quantita' futura di dati.",
        "NEEDS_DETECTOR_FORMALIZATION": "uno o piu' campi di required_family_spec_inputs mancano - il gate "
                                        "non e' stato eseguito, non e' un verdetto sulla geometria.",
    },
    "thresholds": {
        "feasible_margin_multiplier": {
            "value": 1.5,
            "status": "POLICY_THRESHOLD",
            "rationale": "Un candidato appena sopra n_nominal_minimum e' strutturalmente fragile a piccole "
                         "differenze di embargo/partition/detector - non equivalente a un margine ampio. "
                         "1.5x e' una scelta di progetto (stesso stile di minimum_evidence_gates.json), non "
                         "derivata da una formula statistica.",
        },
        "episode_retention_borderline_floor": {
            "value": 0.30,
            "status": "POLICY_THRESHOLD",
            "rationale": "Se meno del 30% degli eventi grezzi sopravvive come episodi indipendenti locali, "
                         "la maggioranza dell'informazione e' gia' persa al primo stadio del funnel, a "
                         "prescindere dal conteggio finale - segnalato come fragilita' anche se n finale "
                         "supera il minimo.",
        },
        "independence_retention_borderline_floor": {
            "value": 0.30,
            "status": "POLICY_THRESHOLD",
            "rationale": "Stessa logica di episode_retention_borderline_floor, applicata al secondo stadio "
                         "del funnel (episodi -> osservazioni indipendenti dopo l'embargo outcome-overlap).",
        },
        "minimum_evidence_gates_source": {
            "value": "server/research_scripts/phase7/policies/minimum_evidence_gates.json",
            "status": "REUSED_UNCHANGED",
            "rationale": "n_nominal_minimum (30) e' il gate di campione minimo gia' in uso in tutta la "
                         "Phase 7 (H006/RECLAIM/SEQ-0015) - non un nuovo numero scelto per questo gate.",
        },
    },
    "geometry_based_firing_rate_guard": {
        "closes": "FAIL-004 (failure_memory_registry_v1.json)",
        "signature": "EVENT_FIRING_RATE_ABOVE_INFORMATIVE_THRESHOLD",
        "principle": "Il problema non e' 'quale percentuale fissa di barre attiva il detector' (guard "
                     "esistente, event_firing_rate_guard.py, mantenuto SOLO come diagnostica secondaria, "
                     "MAI l'autorita' che blocca/ammette una family) - e' se il tasso di innesco, combinato "
                     "con l'orizzonte/embargo dichiarati, produce una geometria che soddisfa il requisito "
                     "di unita' indipendenti. Un detector con firing_rate bassissimo puo' comunque essere "
                     "PATHOLOGICAL_FOR_HORIZON se i pochi eventi generati sono concentrati (es. singolo "
                     "periodo di regime) rispetto all'embargo.",
        "mechanical_check": "median_gap_bars (EVENT_VIEW) <= outcome_overlap_embargo_bars proposto => "
                            "PATHOLOGICAL_FOR_HORIZON, riportato ESPLICITAMENTE come causa strutturale "
                            "(non solo osservato a posteriori nel verdetto finale del funnel).",
        "not_arbitrary_rare_is_good": "Nessuna soglia fissa 'evento raro = buono' - un detector molto raro "
                                      "ma con gap tipico ampiamente sopra l'embargo e' COMPATIBLE_WITH_HORIZON "
                                      "quanto uno piu' frequente con la stessa proprieta'.",
    },
    "matching_preflight": {
        "purpose": "Simulare il matching STRUTTURALE (n matched/rejected, reuse, qualita', determinismo del "
                    "tie-break) senza alcun outcome - sec.8. Riusa BaselineEngineV4/ControlReuseLedger senza "
                    "modifiche (nessuna nuova logica di matching introdotta da questa fase).",
        "precondition": "Richiede feature di stato REALI per evento e pool di controllo (provenienti da un "
                        "detector gia' formalizzato) - MAI invocato con feature inventate per una family "
                        "NEEDS_DETECTOR_FORMALIZATION.",
        "checks": ["n_matched", "n_rejected_insufficient_pool", "match_quality_counts", "poor_match_share",
                   "reuse_report (max_reuse_observed, mean_reuse, n_controls_at_cap)",
                   "max_reuse_within_declared_cap (<= max_control_reuse_per_run dichiarato dal family spec)",
                   "tie_break_deterministic (stesso input rigirato -> stesse scelte di controllo)"],
    },
    "provenance_requirements": {
        "description": "sec.12 - ogni esecuzione del gate deve registrare, oltre al verdetto:",
        "fields": ["detector_source_ref", "detector_parameters_hash (sha256 canonico)",
                   "spec_hash (sha256 canonico dello spec, esclusi i soli event_row_indices grezzi)",
                   "discovery_partition (partition_id, n_bars)", "engine_version", "policy_version",
                   "outcome_blind=true", "deterministic=true"],
        "enforcement": "sequence_structural_feasibility_gate.py:evaluate_family_structural_feasibility() - "
                        "sempre incluso nell'output, mai un campo opzionale omesso silenziosamente.",
    },
    "ranking_policy": {
        "rule": "Il ranking del candidate queue e' ESCLUSIVAMENTE strutturale: testabilita' (verdict), "
                "geometria del campione (feasibility_ratios), completezza del detector (missing_degrees_of_"
                "freedom), fattibilita' del matching (matching_preflight, quando disponibile), chiarezza "
                "implementativa (existing_detector_reference presente o assente).",
        "forbidden_inputs": ["probabilita' di edge", "expected profitability", "likelihood of success",
                             "qualunque metrica derivata da outcome"],
    },
}

if __name__ == "__main__":
    out_path = os.path.join(PHASE75_DIR, "sequence_structural_feasibility_policy_v1.json")
    save_json(out_path, wrap_with_provenance(PAYLOAD, "phase7/phase7_5/build_sequence_structural_feasibility_policy.py"))
    print(f"Scritto {out_path}")
