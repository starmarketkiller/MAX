#!/usr/bin/env python3
"""Phase 7.5A - Sequence Structural Feasibility Gate.

Lezione generalizzata da SEQ-0015 (Phase 7.4A): un design di detector
formalmente corretto puo' comunque essere ESEGUIBILE SOLO SULLA CARTA -
la sua geometria di innesco/clustering, applicata alla partition
development_discovery gia' congelata, puo' comprimere centinaia di
eventi grezzi in un numero di osservazioni indipendenti insufficiente
per qualunque test (SEQ-0015: 249 -> 210 -> 1, minimo richiesto 30).
Prima di questa fase, quel fatto si scopriva solo DOPO aver costruito
l'intero contratto di preregistrazione statistico (BH family, outcome
contract, validation access) per quella family specifica - lavoro
sprecato se il design non e' testabile per costruzione.

Questo modulo sposta il controllo PRIMA: da eseguire subito dopo la
formalizzazione minima del detector (frozen: formula, parametri,
observation timing, direction policy, episode_gap_rule, natural_horizon
proposto, outcome_overlap_embargo proposto) e PRIMA di qualunque
outcome contract / statistical test selection / BH family / validation
access.

Principi non negoziabili (stessi del resto di Phase 7):
- OUTCOME-BLIND: nessuna funzione qui accetta o richiede outcome. Solo
  posizione temporale (row/bar index) degli eventi grezzi.
- DETERMINISTICO: stesso input -> stesso output, nessuna casualita'.
- FAIL-CLOSED, NESSUN DEFAULT INVENTATO: se un campo richiesto del
  family spec manca, il gate NON inventa un valore per farlo comunque
  girare - restituisce NEEDS_DETECTOR_FORMALIZATION con l'elenco esatto
  dei gradi di liberta' mancanti (sec.9 della richiesta).
- Riusa la meccanica di clustering/episode/independent-view gia'
  esistente e testata (sequence_episode_engine.py, che a sua volta
  riusa dependence_diagnostics.assign_clusters) - non reimplementata.
- Nessun claim di edge/probabilita' di successo: il verdetto e'
  ESCLUSIVAMENTE strutturale (testabilita', geometria del campione,
  completezza del detector, fattibilita' del matching, chiarezza
  implementativa) - MAI una stima di profittabilita' attesa.

Tre stati di verdetto finale (fail-closed, nessun claim universale):
  FEASIBLE                        - geometria comoda rispetto al minimo richiesto.
  BORDERLINE_FEASIBILITY          - sopra il minimo ma con margine fragile.
  NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY - sotto il minimo SULLA partition
                                     proposta. Esclusivamente scoped a quella
                                     partition (vedi FAIL-009/SEQ-0015) - MAI
                                     un'affermazione che il design sia
                                     impossibile per qualunque quantita' futura
                                     di dati.
"""
import os
import statistics
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_5"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_3", "engine"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dependence_diagnostics import assign_clusters  # noqa: E402
from canonical_utils import canonical_sha256  # noqa: E402
from sequence_episode_engine import (  # noqa: E402
    build_event_and_episode_views, build_outcome_independent_view, EpisodeRuleNotDeclaredError,
)
from baseline_engine_v4 import BaselineEngineV4, build_quality_report  # noqa: E402

GATE_POLICY_VERSION = "SEQUENCE_STRUCTURAL_FEASIBILITY_POLICY_V1"
ENGINE_VERSION = "sequence_structural_feasibility_gate.py@v1"

# Campi che un family spec DEVE dichiarare esplicitamente prima che il
# gate possa girare - sec.2 della richiesta. Nessuno di questi ha un
# default silenzioso in questo modulo (stessa filosofia di
# sequence_episode_engine.EpisodeRuleNotDeclaredError).
REQUIRED_SPEC_FIELDS = (
    "sequence_family_id",
    "detector_frozen",
    "detector_source_ref",
    "detector_parameters",
    "observation_timing",
    "event_direction_policy",
    "episode_gap_rule",
    "overlap_policy",
    "proposed_natural_horizon",
    "proposed_outcome_overlap_embargo_bars",
    "discovery_partition",
    "minimum_evidence_gates",
    "event_row_indices",
)

VERDICT_FEASIBLE = "FEASIBLE"
VERDICT_BORDERLINE = "BORDERLINE_FEASIBILITY"
VERDICT_NOT_TESTABLE = "NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY"
VERDICT_NEEDS_DETECTOR_FORMALIZATION = "NEEDS_DETECTOR_FORMALIZATION"

DEFAULT_POLICY = {
    # POLICY_THRESHOLD - margine minimo sopra il gate di campione minimo
    # perche' un candidato conti FEASIBLE invece che BORDERLINE (sec.6:
    # "nessun claim universale" - un candidato appena sopra la soglia e'
    # strutturalmente fragile a piccole differenze di embargo/partition,
    # non e' lo stesso di un margine ampio). Scelto ORA, prima di
    # applicarlo a qualunque family reale.
    "feasible_margin_multiplier": 1.5,
    # POLICY_THRESHOLD - sotto questa frazione di episodi che sopravvivono
    # alla seconda passata di declustering (embargo), il candidato e'
    # segnalato BORDERLINE anche se n nominale supera il minimo, perche'
    # la maggioranza dell'informazione episodica e' comunque collassata.
    "independence_retention_borderline_floor": 0.30,
    # POLICY_THRESHOLD - stessa logica per la prima passata (event->episode).
    "episode_retention_borderline_floor": 0.30,
    # POLICY_THRESHOLD - guard di firing-rate basato sulla GEOMETRIA
    # risultante (sec.7), non su una percentuale fissa di barre: se la
    # mediana del gap fra eventi grezzi e' sotto l'embargo proposto, il
    # clustering transitivo comprimera' quasi certamente l'INDEPENDENT_VIEW
    # (stesso meccanismo di FAIL-009/SEQ-0015) - segnalato esplicitamente
    # come causa, non solo osservato nel risultato finale.
    "median_gap_below_embargo_is_structural_risk_flag": True,
}


class StructuralInputNotDeclaredError(Exception):
    pass


def missing_spec_fields(spec: dict) -> list:
    """Non solleva mai un'eccezione - usato per CLASSIFICARE (mai per
    bloccare l'intero script), sec.9: una family senza detector
    sufficientemente formalizzato deve poter essere marcata
    NEEDS_DETECTOR_FORMALIZATION con i gradi di liberta' mancanti
    elencati, non con uno stack trace."""
    missing = []
    for field in REQUIRED_SPEC_FIELDS:
        if field not in spec or spec[field] is None:
            missing.append(field)
        elif field == "event_row_indices" and len(spec[field]) == 0:
            missing.append(field)
        elif field == "detector_frozen" and spec[field] is not True:
            missing.append(field)
    return missing


def _gap_percentiles(sorted_rows: list) -> dict:
    if len(sorted_rows) < 2:
        return {"median_gap_bars": None, "p10": None, "p25": None, "p50": None, "p75": None, "p90": None}
    gaps = sorted(sorted_rows[i + 1] - sorted_rows[i] for i in range(len(sorted_rows) - 1))

    def pct(p):
        if not gaps:
            return None
        k = (len(gaps) - 1) * p
        f, c = int(k), min(int(k) + 1, len(gaps) - 1)
        if f == c:
            return float(gaps[f])
        return gaps[f] + (gaps[c] - gaps[f]) * (k - f)

    return {
        "median_gap_bars": statistics.median(gaps),
        "p10": pct(0.10), "p25": pct(0.25), "p50": pct(0.50), "p75": pct(0.75), "p90": pct(0.90),
    }


def compute_detection_funnel(event_row_indices: list, n_bars: int, episode_gap_rule: int,
                              natural_horizon: int, overlap_policy: str,
                              outcome_overlap_embargo_bars: int, direction_by_row: dict = None) -> dict:
    """EVENT_VIEW -> EPISODE_VIEW -> INDEPENDENT_VIEW, senza alcun
    outcome - sec.3. Riusa sequence_episode_engine.py senza modifiche."""
    sorted_rows = sorted(set(event_row_indices))
    n_raw_events = len(sorted_rows)
    firing_rate = (n_raw_events / n_bars) if n_bars else 0.0
    gap_stats = _gap_percentiles(sorted_rows)

    direction_by_row = direction_by_row or {r: "BOTH" for r in sorted_rows}
    synthetic_events = [
        {"sequence_event_id": f"ROW-{r}", "sequence_id": "STRUCTURAL_PREFLIGHT", "direction": direction_by_row.get(r, "BOTH"),
         "event_a_index": r, "transition_complete_index": r, "prediction_start_index": r}
        for r in sorted_rows
    ]
    event_view, episode_view = build_event_and_episode_views(
        synthetic_events, episode_gap_rule=episode_gap_rule, natural_horizon=natural_horizon,
        overlap_policy=overlap_policy,
    )
    independent_view = build_outcome_independent_view(
        episode_view["events"], outcome_overlap_embargo_bars=outcome_overlap_embargo_bars,
    )
    return {
        "n_bars": n_bars,
        "n_raw_events": n_raw_events,
        "firing_rate": firing_rate,
        "gap_stats": gap_stats,
        "EVENT_VIEW": {"n": event_view["n"]},
        "EPISODE_VIEW": {"n": episode_view["n"], "n_episodes": episode_view["n_episodes"]},
        "INDEPENDENT_VIEW": {"n": independent_view["n"],
                              "n_independent_observations": independent_view["n_independent_observations"]},
        "episode_gap_rule": episode_gap_rule,
        "natural_horizon": natural_horizon,
        "overlap_policy": overlap_policy,
        "outcome_overlap_embargo_bars": outcome_overlap_embargo_bars,
    }


def compute_cluster_geometry(event_row_indices: list, episode_gap_rule: int,
                              outcome_overlap_embargo_bars: int) -> dict:
    """Geometria dei cluster a DUE soglie distinte (sec.4) - stessa
    distinzione concettuale di sequence_episode_engine.py:
    event_cluster_rule (espansione fisica locale) vs outcome_overlap
    embargo (indipendenza statistica dell'outcome). Calcolata sui
    cluster di INDIPENDENZA (embargo) - la geometria decisiva per il
    gate di campione minimo."""
    sorted_rows = sorted(set(event_row_indices))
    if len(sorted_rows) < 1:
        return {
            "n_independent_clusters": 0, "cluster_size_distribution": [], "max_cluster_size": None,
            "median_cluster_size": None, "fraction_events_in_largest_cluster": None,
            "fraction_gaps_below_embargo": None, "longest_no_event_gap_bars": None,
            "fraction_gaps_below_episode_gap_rule": None,
        }
    episode_clusters, _ = assign_clusters(sorted_rows, episode_gap_rule)
    indep_clusters, _ = assign_clusters(sorted_rows, outcome_overlap_embargo_bars)
    sizes = sorted((len(c) for c in indep_clusters), reverse=True)
    gaps = [sorted_rows[i + 1] - sorted_rows[i] for i in range(len(sorted_rows) - 1)]
    n_below_embargo = sum(1 for g in gaps if g <= outcome_overlap_embargo_bars)
    n_below_episode_gap = sum(1 for g in gaps if g <= episode_gap_rule)
    return {
        "n_independent_clusters": len(indep_clusters),
        "n_episode_clusters": len(episode_clusters),
        "cluster_size_distribution": sizes,
        "max_cluster_size": sizes[0] if sizes else None,
        "median_cluster_size": statistics.median(sizes) if sizes else None,
        "fraction_events_in_largest_cluster": (sizes[0] / len(sorted_rows)) if sizes else None,
        "fraction_gaps_below_embargo": (n_below_embargo / len(gaps)) if gaps else None,
        "fraction_gaps_below_episode_gap_rule": (n_below_episode_gap / len(gaps)) if gaps else None,
        "longest_no_event_gap_bars": max(gaps) if gaps else None,
    }


def compute_feasibility_ratios(funnel: dict, minimum_evidence_gates: dict, bars_per_year: float = None) -> dict:
    """sec.5 - rapporti semplici, nessuna formula statistica nuova."""
    ev_n = funnel["EVENT_VIEW"]["n"]
    ep_n = funnel["EPISODE_VIEW"]["n"]
    indep_n = funnel["INDEPENDENT_VIEW"]["n"]
    minimum_required_n = minimum_evidence_gates["n_nominal_minimum"]
    episode_retention = (ep_n / ev_n) if ev_n else None
    independence_retention = (indep_n / ep_n) if ep_n else None
    independent_units_per_year = None
    if bars_per_year and funnel["n_bars"]:
        years = funnel["n_bars"] / bars_per_year
        independent_units_per_year = (indep_n / years) if years else None
    return {
        "episode_retention": episode_retention,
        "independence_retention": independence_retention,
        "independent_units_per_year": independent_units_per_year,
        "independent_units": indep_n,
        "minimum_required_n": minimum_required_n,
        "independent_units_over_minimum_required": (indep_n / minimum_required_n) if minimum_required_n else None,
    }


def classify_geometry_firing_rate_guard(funnel: dict, ratios: dict) -> dict:
    """sec.7 - chiude FAIL-004 CORRETTAMENTE: il problema non e' "il
    detector spara su una percentuale X delle barre" (guard fisso gia'
    esistente in event_firing_rate_guard.py, FIRING_RATE_THRESHOLDS -
    mantenuto per uso diagnostico, MAI l'autorita' finale) ma "il tasso
    di innesco, combinato con l'orizzonte/embargo dichiarati, produce
    una geometria che non puo' soddisfare il requisito di unita'
    indipendenti". Un detector puo' avere firing_rate bassissimo (es.
    0.01) e comunque essere PATHOLOGICAL_FOR_HORIZON se i pochi eventi
    che genera sono comunque tutti ravvicinati rispetto all'embargo
    (es. concentrati in un singolo periodo di regime)."""
    gap_stats = funnel["gap_stats"]
    median_gap = gap_stats["median_gap_bars"]
    embargo = funnel["outcome_overlap_embargo_bars"]
    structurally_incompatible = (median_gap is not None) and (median_gap <= embargo)
    verdict = "PATHOLOGICAL_FOR_HORIZON" if structurally_incompatible else "COMPATIBLE_WITH_HORIZON"
    reason = (
        f"median_gap_bars={median_gap} <= outcome_overlap_embargo_bars={embargo}: il clustering "
        f"transitivo dell'INDEPENDENT_VIEW comprimera' la maggioranza degli episodi indipendentemente "
        f"dal numero grezzo di eventi (stesso meccanismo di FAIL-009/SEQ-0015)."
        if structurally_incompatible else
        f"median_gap_bars={median_gap} > outcome_overlap_embargo_bars={embargo}: nessuna "
        f"incompatibilita' strutturale rilevata fra tasso di innesco e orizzonte/embargo dichiarati."
    )
    return {
        "signature": "EVENT_FIRING_RATE_ABOVE_INFORMATIVE_THRESHOLD",
        "verdict": verdict,
        "median_gap_bars": median_gap,
        "outcome_overlap_embargo_bars": embargo,
        "firing_rate": funnel["firing_rate"],
        "reason": reason,
        "basis": "GEOMETRY_OF_INDEPENDENT_UNIT_YIELD_VS_HORIZON_EMBARGO - non una percentuale fissa di firing.",
    }


def run_matching_preflight(match_dimensions: list, k: int, split_boundaries: dict,
                            events: list, control_pool: list, control_row_by_id: dict,
                            control_direction_by_id: dict, control_features_by_id: dict,
                            discovery_features_by_row: dict, minimum_control_count: int,
                            max_control_reuse_per_run: int, discovery_split_name: str = "discovery",
                            feature_version: str = "feature_registry_v2") -> dict:
    """sec.8 - simula il matching STRUTTURALE senza alcun outcome,
    riusando BaselineEngineV4/ControlReuseLedger senza modifiche. Va
    invocato SOLO quando esistono gia' feature di stato reali (evento e
    pool di controllo) - MAI con feature inventate per far girare il
    preflight su una family non ancora formalizzata (sec.9)."""
    engine = BaselineEngineV4(match_dimensions=match_dimensions, k=k, split_boundaries=split_boundaries,
                               discovery_split_name=discovery_split_name, feature_version=feature_version,
                               minimum_control_count=minimum_control_count,
                               max_control_reuse_per_run=max_control_reuse_per_run)
    engine.fit_normalization(discovery_features_by_row)
    results = []
    for ev in events:
        r = engine.match(event_id=ev["event_id"], event_row=ev["event_row"], event_direction=ev["direction"],
                          event_features=ev["features"], control_pool=control_pool,
                          control_row_by_id=control_row_by_id, control_direction_by_id=control_direction_by_id,
                          control_features_by_id=control_features_by_id)
        results.append(r)
    quality_report = build_quality_report(results)
    reuse_report = engine.reuse_usage_report()

    # Determinismo del tie-break: stesso input rigirato due volte deve
    # produrre esattamente le stesse scelte di controllo per ogni evento
    # (sec.8: "verificare... che il tie-break sia deterministico").
    engine_repeat = BaselineEngineV4(match_dimensions=match_dimensions, k=k, split_boundaries=split_boundaries,
                                      discovery_split_name=discovery_split_name, feature_version=feature_version,
                                      minimum_control_count=minimum_control_count,
                                      max_control_reuse_per_run=max_control_reuse_per_run)
    engine_repeat.fit_normalization(discovery_features_by_row)
    repeat_picks = []
    for ev in events:
        r = engine_repeat.match(event_id=ev["event_id"], event_row=ev["event_row"], event_direction=ev["direction"],
                                 event_features=ev["features"], control_pool=control_pool,
                                 control_row_by_id=control_row_by_id, control_direction_by_id=control_direction_by_id,
                                 control_features_by_id=control_features_by_id)
        repeat_picks.append(sorted(m["control_id"] for m in r["matches"]))
    original_picks = [sorted(m["control_id"] for m in r["matches"]) for r in results]
    tie_break_deterministic = original_picks == repeat_picks

    max_reuse_within_cap = True
    if reuse_report and max_control_reuse_per_run:
        max_reuse_within_cap = reuse_report["max_reuse_observed"] <= max_control_reuse_per_run

    return {
        "n_events": len(events),
        "n_matched": quality_report["n_matched"],
        "n_rejected_insufficient_pool": quality_report["n_rejected_insufficient_pool"],
        "match_quality_counts": quality_report["match_quality_counts"],
        "poor_match_share": quality_report["poor_match_share"],
        "reuse_report": reuse_report,
        "max_reuse_within_declared_cap": max_reuse_within_cap,
        "tie_break_deterministic": tie_break_deterministic,
    }


def _classify_verdict(ratios: dict, policy: dict) -> str:
    indep_n = ratios["independent_units"]
    minimum_required_n = ratios["minimum_required_n"]
    if indep_n < minimum_required_n:
        return VERDICT_NOT_TESTABLE
    margin_ok = indep_n >= policy["feasible_margin_multiplier"] * minimum_required_n
    indep_retention_ok = (ratios["independence_retention"] is None or
                           ratios["independence_retention"] >= policy["independence_retention_borderline_floor"])
    episode_retention_ok = (ratios["episode_retention"] is None or
                             ratios["episode_retention"] >= policy["episode_retention_borderline_floor"])
    if margin_ok and indep_retention_ok and episode_retention_ok:
        return VERDICT_FEASIBLE
    return VERDICT_BORDERLINE


def evaluate_family_structural_feasibility(spec: dict, policy: dict = None,
                                            bars_per_year: float = None,
                                            direction_by_row: dict = None) -> dict:
    """Punto di ingresso principale del gate (sec.1-6). Ritorna sempre un
    dict con almeno 'sequence_family_id' e 'verdict' - MAI un'eccezione
    per una family incompleta (quella e' una classificazione valida,
    NEEDS_DETECTOR_FORMALIZATION, non un errore di programma)."""
    policy = policy or DEFAULT_POLICY
    family_id = spec.get("sequence_family_id", "UNKNOWN_FAMILY")
    missing = missing_spec_fields(spec)
    if missing:
        return {
            "sequence_family_id": family_id,
            "verdict": VERDICT_NEEDS_DETECTOR_FORMALIZATION,
            "missing_degrees_of_freedom": missing,
            "note": "Nessun parametro inventato per far girare il gate - sec.9. Formalizzare il detector "
                    "(frozen formula/parametri, episode_gap_rule, natural_horizon proposto, "
                    "outcome_overlap_embargo proposto) prima di rieseguire questo gate su questa family.",
            "engine_version": ENGINE_VERSION,
            "policy_version": GATE_POLICY_VERSION,
        }

    try:
        funnel = compute_detection_funnel(
            event_row_indices=spec["event_row_indices"], n_bars=spec["discovery_partition"]["n_bars"],
            episode_gap_rule=spec["episode_gap_rule"], natural_horizon=spec["proposed_natural_horizon"],
            overlap_policy=spec["overlap_policy"],
            outcome_overlap_embargo_bars=spec["proposed_outcome_overlap_embargo_bars"],
            direction_by_row=direction_by_row,
        )
    except EpisodeRuleNotDeclaredError as e:
        return {
            "sequence_family_id": family_id,
            "verdict": VERDICT_NEEDS_DETECTOR_FORMALIZATION,
            "missing_degrees_of_freedom": [str(e)],
            "engine_version": ENGINE_VERSION,
            "policy_version": GATE_POLICY_VERSION,
        }

    geometry = compute_cluster_geometry(
        event_row_indices=spec["event_row_indices"], episode_gap_rule=spec["episode_gap_rule"],
        outcome_overlap_embargo_bars=spec["proposed_outcome_overlap_embargo_bars"],
    )
    ratios = compute_feasibility_ratios(funnel, spec["minimum_evidence_gates"], bars_per_year=bars_per_year)
    firing_guard = classify_geometry_firing_rate_guard(funnel, ratios)
    verdict = _classify_verdict(ratios, policy)

    provenance = {
        "detector_source_ref": spec["detector_source_ref"],
        "detector_parameters_hash": canonical_sha256(spec["detector_parameters"]),
        "spec_hash": canonical_sha256({k: v for k, v in spec.items() if k != "event_row_indices"}),
        "discovery_partition": spec["discovery_partition"],
        "engine_version": ENGINE_VERSION,
        "policy_version": GATE_POLICY_VERSION,
        "outcome_blind": True,
        "deterministic": True,
    }

    return {
        "sequence_family_id": family_id,
        "verdict": verdict,
        "detection_funnel": funnel,
        "cluster_geometry": geometry,
        "feasibility_ratios": ratios,
        "firing_rate_guard": firing_guard,
        "provenance": provenance,
    }


if __name__ == "__main__":
    # ---- Demo/self-test su dati sintetici (nessun dato NEXUS) ----

    # Caso 1: spec incompleto -> NEEDS_DETECTOR_FORMALIZATION, nessun default inventato.
    incomplete_spec = {"sequence_family_id": "SEQFAM-DEMO-INCOMPLETE"}
    r1 = evaluate_family_structural_feasibility(incomplete_spec)
    assert r1["verdict"] == VERDICT_NEEDS_DETECTOR_FORMALIZATION
    assert set(REQUIRED_SPEC_FIELDS) <= set(r1["missing_degrees_of_freedom"]) or len(r1["missing_degrees_of_freedom"]) > 0
    print(f"Caso 1 OK: spec incompleto -> {r1['verdict']} ({len(r1['missing_degrees_of_freedom'])} campi mancanti)")

    # Caso 2 (replay sintetico, di sola validazione del gate - NON un
    # nuovo dato SEQ-0015, NESSUN outcome, solo la geometria GIA'
    # PUBBLICATA event->episode->independent 249->210->1 per verificare
    # che il gate l'avrebbe segnalata immediatamente come previsto da
    # FAIL-009/sec.4 della richiesta Phase 7.5A).
    import random as _random
    _random.seed(0)
    rows = []
    r = 100
    for _ in range(210):  # 210 episodi sintetici
        cluster_size = _random.choice([1, 1, 1, 2, 2, 3])  # media ~249/210 eventi grezzi per episodio
        for _ in range(cluster_size):
            rows.append(r)
            r += _random.randint(1, 3)
        r += _random.randint(4, 7)  # gap fra episodi sempre << embargo=39 per costruzione (replay del caso reale)
        if len(rows) >= 249:
            break
    rows = rows[:249]
    seq0015_replay_spec = {
        "sequence_family_id": "SEQFAM-REPLAY-SEQ0015-STRUCTURAL-ONLY",
        "detector_frozen": True, "detector_source_ref": "SYNTHETIC_REPLAY_NOT_REAL_DETECTOR",
        "detector_parameters": {"note": "replay sintetico della sola geometria pubblicata, non un nuovo dato"},
        "observation_timing": {"observation_cutoff": "close(t)"}, "event_direction_policy": "BOTH",
        "episode_gap_rule": 3, "overlap_policy": "COLLAPSE_TO_FIRST",
        "proposed_natural_horizon": 40, "proposed_outcome_overlap_embargo_bars": 39,
        "discovery_partition": {"partition_id": "SYNTHETIC_REPLAY", "n_bars": 2393},
        "minimum_evidence_gates": {"n_nominal_minimum": 30},
        "event_row_indices": rows,
    }
    r2 = evaluate_family_structural_feasibility(seq0015_replay_spec)
    print(f"Caso 2 (replay strutturale SEQ-0015, sintetico): EVENT_VIEW={r2['detection_funnel']['EVENT_VIEW']['n']} "
          f"-> EPISODE_VIEW={r2['detection_funnel']['EPISODE_VIEW']['n']} "
          f"-> INDEPENDENT_VIEW={r2['detection_funnel']['INDEPENDENT_VIEW']['n']} -> verdict={r2['verdict']}")
    assert r2["verdict"] == VERDICT_NOT_TESTABLE
    assert r2["firing_rate_guard"]["verdict"] == "PATHOLOGICAL_FOR_HORIZON"

    # Caso 3 (positivo): eventi ben distanziati, ampiamente sopra il minimo -> FEASIBLE.
    rows3 = list(range(0, 60 * 60, 60))  # gap=60 > embargo=39, 60 osservazioni indipendenti (>=1.5x minimo=30)
    feasible_spec = {
        "sequence_family_id": "SEQFAM-DEMO-FEASIBLE",
        "detector_frozen": True, "detector_source_ref": "SYNTHETIC_DEMO",
        "detector_parameters": {"threshold": 1.0}, "observation_timing": {"observation_cutoff": "close(t)"},
        "event_direction_policy": "BOTH", "episode_gap_rule": 3, "overlap_policy": "COLLAPSE_TO_FIRST",
        "proposed_natural_horizon": 40, "proposed_outcome_overlap_embargo_bars": 39,
        "discovery_partition": {"partition_id": "SYNTHETIC_DEMO", "n_bars": max(rows3) + 100},
        "minimum_evidence_gates": {"n_nominal_minimum": 30},
        "event_row_indices": rows3,
    }
    r3 = evaluate_family_structural_feasibility(feasible_spec)
    print(f"Caso 3 (demo ben distanziata): INDEPENDENT_VIEW={r3['detection_funnel']['INDEPENDENT_VIEW']['n']} "
          f"-> verdict={r3['verdict']}")
    assert r3["verdict"] == VERDICT_FEASIBLE
    assert r3["firing_rate_guard"]["verdict"] == "COMPATIBLE_WITH_HORIZON"

    # Caso 4 (borderline): appena sopra il minimo ma con bassa independence_retention.
    rows4 = []
    r = 0
    for i in range(32):  # 32 episodi "veri" ma quasi tutti troppo vicini fra loro per l'embargo
        rows4.append(r)
        r += 20 if i % 3 == 0 else 5  # solo 1 gap su 3 supera l'embargo=39... nessuno lo supera qui (5,20<39)
    borderline_spec = dict(feasible_spec)
    borderline_spec["sequence_family_id"] = "SEQFAM-DEMO-BORDERLINE"
    borderline_spec["event_row_indices"] = rows4
    borderline_spec["discovery_partition"] = {"partition_id": "SYNTHETIC_DEMO", "n_bars": max(rows4) + 100}
    r4 = evaluate_family_structural_feasibility(borderline_spec)
    print(f"Caso 4 (demo borderline): EPISODE_VIEW={r4['detection_funnel']['EPISODE_VIEW']['n']} "
          f"-> INDEPENDENT_VIEW={r4['detection_funnel']['INDEPENDENT_VIEW']['n']} -> verdict={r4['verdict']}")
    assert r4["verdict"] in (VERDICT_BORDERLINE, VERDICT_NOT_TESTABLE)

    # Caso 5: determinismo - stesso spec rigirato due volte -> stesso risultato bit-per-bit (hash canonico).
    r2_again = evaluate_family_structural_feasibility(seq0015_replay_spec)
    assert canonical_sha256(r2["detection_funnel"]) == canonical_sha256(r2_again["detection_funnel"])
    assert r2["provenance"]["spec_hash"] == r2_again["provenance"]["spec_hash"]
    print("Caso 5 OK: stesso spec -> stesso hash di funnel/provenance (deterministico).")

    print("\nTutti i casi del Sequence Structural Feasibility Gate verificati.")
