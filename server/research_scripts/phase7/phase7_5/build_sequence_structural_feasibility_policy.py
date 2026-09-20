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
                        "calcolare la GEOMETRIA (livello 1: DETECTOR_GEOMETRY_READY). Nessun default "
                        "silenzioso: una family con anche un solo campo mancante e' classificata "
                        "NEEDS_DETECTOR_FORMALIZATION, non fatta girare con un valore inventato.",
        "fields": [
            "sequence_family_id", "detector_frozen", "detector_source_ref", "detector_parameters",
            "observation_timing", "event_direction_policy", "episode_gap_rule", "overlap_policy",
            "proposed_natural_horizon", "proposed_outcome_overlap_embargo_bars", "discovery_partition",
            "minimum_evidence_gates", "event_row_indices",
        ],
        "enforcement": "server/research_scripts/phase7/engine/sequence_structural_feasibility_gate.py:"
                        "missing_spec_fields()",
    },
    "direction_derivation_contract": {
        "description": "CORREZIONE (Directional Matching Fidelity Final Patch, 2026-09-20): "
                        "event_direction_policy NON e' piu' una stringa narrativa libera (i vecchi valori "
                        "\"BOTH\"/\"CONTEXT_DEPENDENT\" ereditati da market_sequence_registry_v1.json non sono "
                        "piu' ammessi per QUESTO gate) - deve essere uno dei 4 valori canonici sotto. La "
                        "versione precedente accettava direction_by_row come parametro OPZIONALE di "
                        "evaluate_family_structural_feasibility() con fallback silenzioso a {r: 'BOTH' ...} - "
                        "una family con event_direction_policy=BUY poteva quindi essere testata come "
                        "non-direzionale senza alcun errore. Il parametro e' stato RIMOSSO: la direzione per "
                        "riga e' ORA sempre e solo derivata meccanicamente da spec['event_direction_policy'] "
                        "(+ spec['direction_by_row'] se PER_EVENT_DIRECTION).",
        "canonical_values": {
            "FIXED_BUY": "ogni riga grezza riceve direzione 'BUY'.",
            "FIXED_SELL": "ogni riga grezza riceve direzione 'SELL'.",
            "NON_DIRECTIONAL": "nessun asse di direzione per questa sequence (es. classificatore di stato "
                               "choppy/laterale) - ogni riga riceve 'BOTH', ma dichiarato esplicitamente, mai "
                               "un default silenzioso. NON equivalente al vecchio valore narrativo 'BOTH' del "
                               "registry Phase 7.2 (che significava 'sia BUY sia SELL testati come candidati "
                               "separati', un concetto diverso - quasi sempre PER_EVENT_DIRECTION per questo gate).",
            "PER_EVENT_DIRECTION": "la direzione varia per evento (es. SWEEP: HIGH vs LOW; MOMENTUM_BURST: "
                                   "close vs open) - richiede spec['direction_by_row'] COMPLETO per ogni riga "
                                   "grezza, nessun fallback per righe mancanti (fail-closed).",
        },
        "enforcement": "sequence_structural_feasibility_gate.py:resolve_direction_by_row(), "
                        "missing_spec_fields() (valida l'enum + presenza di direction_by_row quando richiesto)",
    },
    "required_matching_spec_inputs": {
        "description": "INTEGRAZIONE (Structural Gate Integration & Geometry Semantics Patch, 2026-09-20): "
                        "campi che un family spec DEVE dichiarare in spec['matching_spec'] prima che il gate "
                        "possa calcolare il MATCHING (livello 2: MATCHING_PREFLIGHT_READY). Nomi canonici "
                        "allineati ai parametri gia' esistenti di BaselineEngineV4/baseline_contract_v4.json "
                        "(match_dimensions, k, minimum_control_count, max_control_reuse_per_run, "
                        "split_boundaries) - non reinventati. Anche con matching_spec completo, il gate "
                        "richiede ULTERIORMENTE matching_runtime_data (feature di stato REALI per eventi e "
                        "pool di controllo) prima di poter eseguire il preflight per davvero - senza, resta "
                        "DECLARED_AWAITING_DATA (mai simulato con dati inventati).",
        "fields": [
            "match_dimensions", "k", "minimum_control_count", "max_control_reuse_per_run",
            "state_feature_definitions", "control_pool_construction_policy", "split_boundaries",
        ],
        "enforcement": "server/research_scripts/phase7/engine/sequence_structural_feasibility_gate.py:"
                        "missing_matching_spec_fields(), evaluate_matching_feasibility()",
    },
    "formalization_levels": {
        "description": "CORREZIONE (Directional Matching Fidelity Final Patch): il bug precedente classificava "
                        "DECLARED_AWAITING_DATA (matching_spec completo ma nessun dato reale) come "
                        "MATCHING_PREFLIGHT_READY - come se il preflight fosse gia' stato eseguito. Introdotto "
                        "un terzo livello esplicito.",
        "NONE": "campi geometrici (livello 1) mancanti - nessuna geometria calcolata.",
        "DETECTOR_GEOMETRY_READY": "geometria calcolabile, ma matching_spec assente/incompleto (matching."
                                    "status=NOT_DECLARED).",
        "MATCHING_SPEC_READY_AWAITING_RUNTIME_DATA": "matching_spec completo, ma matching_runtime_data "
                                                      "(feature di stato REALI) non ancora disponibile - il "
                                                      "preflight NON e' ancora stato eseguito (matching."
                                                      "status=DECLARED_AWAITING_DATA).",
        "MATCHING_PREFLIGHT_READY": "il preflight e' stato REALMENTE eseguito (matching.status="
                                     "EXECUTED_FEASIBLE o EXECUTED_INFEASIBLE) - MAI solo perche' matching_spec "
                                     "e' dichiarato.",
    },
    "verdict_states": {
        "FEASIBLE": "geometry_verdict=FEASIBLE E matching eseguito con esito EXECUTED_FEASIBLE (o matching non "
                    "applicabile solo perche' la geometria e' gia' sufficiente E il matching e' EXECUTED_FEASIBLE - "
                    "MAI senza aver eseguito per davvero il matching).",
        "BORDERLINE_FEASIBILITY": "geometry_verdict=BORDERLINE_FEASIBILITY E matching EXECUTED_FEASIBLE.",
        "NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY": "independent_units < minimum_required_n SULLA partition "
                                                    "discovery proposta (geometria da sola gia' insufficiente - "
                                                    "il matching non viene nemmeno valutato). Scoped a quella "
                                                    "partition (vedi failure_memory_registry_v1.json FAIL-009/"
                                                    "SEQ-0015) - MAI un'affermazione di impossibilita' "
                                                    "universale del design per qualunque quantita' futura di dati.",
        "NEEDS_DETECTOR_FORMALIZATION": "uno o piu' campi di required_family_spec_inputs mancano - il gate "
                                        "non ha calcolato nessuna geometria.",
        "NEEDS_MATCHING_FORMALIZATION": "geometria FEASIBLE o BORDERLINE_FEASIBILITY, ma matching_spec "
                                        "incompleto oppure matching_runtime_data non ancora disponibile - "
                                        "CORREZIONE CENTRALE della patch di integrazione: una geometria "
                                        "comoda NON basta piu' da sola per un verdetto finale FEASIBLE.",
        "MATCHING_STRUCTURALLY_INFEASIBLE": "matching_spec completo, preflight ESEGUITO REALMENTE (con "
                                            "feature vere), ma fallisce almeno una condizione fail-closed: "
                                            "reuse oltre il tetto dichiarato, tie-break non deterministico, o "
                                            "independent_units_with_valid_match (SOLO le osservazioni "
                                            "indipendenti che hanno ottenuto un match valido, non il conteggio "
                                            "grezzo di INDEPENDENT_VIEW) sotto minimum_required_n.",
    },
    "composite_verdict_composition": {
        "rule": "Il verdetto finale e' SEMPRE una funzione di ENTRAMBI i livelli, mai della sola geometria: "
                "geometry_verdict=NOT_TESTABLE => finale=NOT_TESTABLE (matching non valutato, nulla da "
                "matchare); altrimenti matching.status in (NOT_DECLARED, DECLARED_AWAITING_DATA) => finale="
                "NEEDS_MATCHING_FORMALIZATION; matching.status=EXECUTED_INFEASIBLE => finale="
                "MATCHING_STRUCTURALLY_INFEASIBLE; matching.status=EXECUTED_FEASIBLE => finale eredita "
                "geometry_verdict (FEASIBLE o BORDERLINE_FEASIBILITY).",
        "enforcement": "sequence_structural_feasibility_gate.py:_compose_final_verdict()",
        "regression_test": "test_geometry_feasible_without_matching_spec_is_not_feasible (garantisce che "
                            "questa correzione non regredisca silenziosamente).",
    },
    "sample_gate_recalculation_on_matched_units": {
        "rule": "Quando il matching viene eseguito per davvero, il gate di campione minimo NON e' piu' "
                "valutato sul conteggio grezzo di INDEPENDENT_VIEW ma su independent_units_with_valid_match "
                "(le sole osservazioni indipendenti che hanno ottenuto un match MATCHED/MATCHED_K_SHORTFALL, "
                "non REJECTED_INSUFFICIENT_POOL) - un evento strutturalmente indipendente ma senza baseline "
                "valida non puo' entrare nell'esperimento.",
        "enforcement": "evaluate_matching_feasibility() - independent_units_with_valid_match = "
                        "preflight['n_matched'], confrontato con minimum_required_n indipendentemente dal "
                        "conteggio di geometria gia' passato.",
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
        "corrected_semantics_note": "CORREZIONE (Structural Gate Integration & Geometry Semantics Patch, "
                                    "2026-09-20): la prima versione di questa policy dichiarava "
                                    "'median_gap_bars<=embargo => PATHOLOGICAL_FOR_HORIZON' come se fosse "
                                    "un'implicazione SUFFICIENTE - non lo e'. Controesempio: 100 gap totali, "
                                    "60 piccoli (10 barre) + 40 grandi (100 barre) - la mediana e' sotto "
                                    "l'embargo=39 (60>50) ma i 40 gap grandi possono generare 41 cluster "
                                    "indipendenti (assign_clusters, clustering transitivo), ben sopra un "
                                    "minimo=30. La mediana del gap NON dimostra da sola incompatibilita' "
                                    "strutturale.",
        "principle": "L'AUTORITA' meccanica e' ESCLUSIVAMENTE independent_units (calcolato dai cluster REALI "
                     "via assign_clusters/INDEPENDENT_VIEW, gia' presenti nel detection funnel) confrontato "
                     "con minimum_required_n - MAI un proxy. Il gap mediano fra eventi grezzi resta un FLAG "
                     "DIAGNOSTICO di rischio (classify_firing_geometry_risk_flag -> risk_flag: bool), "
                     "riportato ACCANTO al verdetto ma mai sostituito ad esso. Il guard a percentuale fissa "
                     "gia' esistente (event_firing_rate_guard.py) resta una diagnostica ULTERIORMENTE "
                     "secondaria - ne' l'uno ne' l'altro sono mai l'autorita' che blocca/ammette una family.",
        "mechanical_check": "geometry_verdict deriva da compute_feasibility_ratios/independent_units "
                            "(cluster reali), non da median_gap_bars. classify_firing_geometry_risk_flag() "
                            "calcola SEPARATAMENTE risk_flag = (median_gap_bars<=embargo) come segnale "
                            "diagnostico che NON puo' da solo declassare o promuovere un verdetto.",
        "not_arbitrary_rare_is_good": "Nessuna soglia fissa 'evento raro = buono' ne' 'gap mediano basso = "
                                      "cattivo' - un detector con gap mediano sotto l'embargo puo' comunque "
                                      "essere geometricamente FEASIBLE (controesempio A, "
                                      "test_phase7_5_structural_feasibility_gate.py) se abbastanza gap grandi "
                                      "spezzano la catena transitiva.",
    },
    "matching_preflight": {
        "purpose": "Simulare il matching STRUTTURALE (n matched/rejected, reuse, qualita', determinismo del "
                    "tie-break) senza alcun outcome. Riusa BaselineEngineV4/ControlReuseLedger senza "
                    "modifiche (nessuna nuova logica di matching introdotta da questa fase).",
        "integration_note": "INTEGRAZIONE (Structural Gate Integration & Geometry Semantics Patch, "
                            "2026-09-20): run_matching_preflight() esisteva gia' ma NON partecipava al "
                            "verdetto finale - una family poteva ottenere FEASIBLE basandosi solo sulla "
                            "geometria, anche se il matching reale l'avrebbe respinta. Ora e' invocato "
                            "DENTRO evaluate_family_structural_feasibility() (via evaluate_matching_"
                            "feasibility()) ogni volta che matching_spec e matching_runtime_data sono "
                            "entrambi disponibili, ed entra direttamente nella composizione del verdetto "
                            "finale (vedi composite_verdict_composition).",
        "precondition": "Richiede feature di stato REALI per evento e pool di controllo (provenienti da un "
                        "detector gia' formalizzato) - MAI invocato con feature inventate per una family "
                        "NEEDS_DETECTOR_FORMALIZATION o NEEDS_MATCHING_FORMALIZATION.",
        "checks": ["n_matched (ridefinisce independent_units_with_valid_match, vedi "
                   "sample_gate_recalculation_on_matched_units)", "n_rejected_insufficient_pool",
                   "match_quality_counts", "poor_match_share (riusa le soglie GOOD/FAIR/POOR gia' esistenti "
                   "in baseline_contract_v4.json/BaselineEngineV4.MATCH_QUALITY_THRESHOLDS - nessuna nuova "
                   "soglia di qualita' inventata qui)",
                   "reuse_report (max_reuse_observed, mean_reuse, n_controls_at_cap)",
                   "max_reuse_within_declared_cap (<= max_control_reuse_per_run dichiarato dal family spec)",
                   "tie_break_deterministic (stesso input rigirato -> stesse scelte di controllo)"],
        "direction_fidelity_fix": {
            "description": "CORREZIONE (Directional Matching Fidelity Final Patch, 2026-09-20): la versione "
                           "precedente accettava un control_direction_by_id GLOBALE, unico per l'intero run - "
                           "ma la pipeline reale (sequence_baseline_adapter_v1.py:SequenceBaselineAdapter."
                           "match_sequence_event) costruisce una baseline controfattuale condizionata alla "
                           "direzione DI OGNI SINGOLO EVENTO ({cid: event_direction for cid in pool}, "
                           "ricostruita ad ogni chiamata) - per una family con eventi sia BUY sia SELL, lo "
                           "STESSO control bar deve poter essere valutato come ipotetico BUY per un evento e "
                           "ipotetico SELL per un altro, impossibile con una mappa statica.",
            "fix": "run_matching_preflight() non accetta piu' control_direction_by_id - lo costruisce "
                   "internamente per ogni evento (_match_one_event()), replicando esattamente la regola "
                   "dell'adapter reale.",
            "verification": "test_matching_preflight_replicates_sequence_baseline_adapter_direction_semantics "
                            "- parita' diretta (stessi status/control-picks) contro un'istanza REALE di "
                            "SequenceBaselineAdapter su uno scenario misto BUY/SELL, piu' una dimostrazione "
                            "forzata (pool==k) che lo stesso control bar riceve control_direction diverse per "
                            "eventi diversi.",
        },
        "matched_k_shortfall_semantics": {
            "description": "AUDIT ESPLICITO (sez.8 della review, congelato non cambiato automaticamente): "
                           "n_matched (quality_report, riusato senza modifiche) conta MATCHED + "
                           "MATCHED_K_SHORTFALL insieme - stessa definizione gia' in uso in TUTTO il resto di "
                           "Phase 7. DECISIONE: k e' un obiettivo di ricchezza/riduzione-varianza del "
                           "baseline, non un requisito di correttezza stretto - un evento matchato con meno "
                           "di k controlli (ma comunque >= minimum_control_count disponibili nel pool) ha "
                           "comunque un baseline statisticamente valido, solo a varianza piu' alta. "
                           "independent_units_with_valid_match INCLUDE quindi le unita' K_SHORTFALL.",
            "transparency": "n_matched_full_k e n_matched_k_shortfall riportati SEPARATAMENTE nel risultato "
                            "del preflight per audit - mai nascosti nell'aggregato n_matched.",
            "not_changed_automatically": True,
        },
    },
    "provenance_requirements": {
        "description": "Ogni esecuzione del gate deve registrare, oltre al verdetto:",
        "fields": ["detector_source_ref", "detector_parameters_hash (sha256 canonico)",
                   "spec_hash (sha256 canonico dello spec, esclusi event_row_indices grezzi e "
                   "matching_runtime_data)",
                   "discovery_partition (partition_id, n_bars)", "engine_version", "policy_version",
                   "outcome_blind=true", "deterministic=true",
                   "direction_derivation (event_direction_policy, direction_map_hash - sempre presente, "
                   "Directional Matching Fidelity Final Patch)"],
        "matching_fields_when_executed": {
            "description": "INTEGRAZIONE - quando il matching preflight viene REALMENTE eseguito "
                            "(matching.status in EXECUTED_FEASIBLE/EXECUTED_INFEASIBLE), provenance['matching'] "
                            "registra ULTERIORMENTE:",
            "fields": ["baseline_engine_version (BaselineEngineV4.CONTRACT_VERSION)",
                       "matching_spec_hash (sha256 canonico di spec['matching_spec'])",
                       "max_control_reuse_per_run (dichiarato dal family spec)",
                       "matching_result_hash (sha256 canonico del risultato completo del preflight)",
                       "event_direction_policy (Directional Matching Fidelity Final Patch)",
                       "direction_source (== event_direction_policy - come la direzione e' stata derivata)",
                       "direction_map_hash (sha256 canonico della mappa row->direction risolta)",
                       "counterfactual_direction_semantics=true (conferma esplicita che il matching ha usato "
                       "la semantica direction-conditioned counterfactual per-evento, mai una mappa globale)"],
        },
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
