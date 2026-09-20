#!/usr/bin/env python3
"""Phase 7.5A - Sequence Structural Feasibility Gate (Integration &
Geometry Semantics Patch).

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
formalizzazione minima del detector e PRIMA di qualunque outcome
contract / statistical test selection / BH family / validation access.

Patch di integrazione (post-review, 2026-09-20): la prima versione di
questo gate calcolava la geometria dell'evento (EVENT/EPISODE/
INDEPENDENT_VIEW) ma NON integrava mai `run_matching_preflight()` nel
verdetto finale - una family poteva ricevere FEASIBLE basandosi
solo sulla geometria, anche se il matching reale (BaselineEngineV4)
avrebbe respinto meta' degli eventi per pool insufficiente. Corretto
qui: il verdetto finale e' ORA un composito di DUE livelli distinti,
ciascuno con i propri gradi di liberta' richiesti:

  DETECTOR_GEOMETRY_READY   - detector formula/parametri/timing/direction
                              congelati + episode_gap_rule/natural_horizon/
                              outcome_overlap_embargo proposti (livello
                              gia' presente nella prima versione).
  MATCHING_PREFLIGHT_READY  - IN PIU': baseline_match_dimensions/k/
                              minimum_control_count/max_control_reuse_per_run/
                              state_feature_definitions/control_pool_
                              construction_policy/split_boundaries
                              dichiarati (matching_spec) E feature di
                              stato REALI disponibili per eseguirlo
                              (matching_runtime_data) - mai simulato con
                              dati inventati.

Una family con SOLO il primo livello ottiene NEEDS_MATCHING_FORMALIZATION
(mai FEASIBLE) - il verdetto FEASIBLE/BORDERLINE_FEASIBILITY richiede
ENTRAMBI i livelli passati. Il campione minimo indipendente e' inoltre
ricalcolato sulle sole osservazioni INDEPENDENT_VIEW che hanno
REALMENTE ottenuto un match valido (MATCHED/MATCHED_K_SHORTFALL, non
REJECTED_INSUFFICIENT_POOL) quando il matching e' stato eseguito - un
evento strutturalmente indipendente ma senza baseline valida non entra
nell'esperimento.

Patch di semantica geometrica (stesso commit): il firing-rate guard
originale dichiarava `median_gap_bars <= embargo => PATHOLOGICAL_FOR_
HORIZON`, un'implicazione NON matematicamente sufficiente - un detector
puo' avere gap mediano sotto l'embargo e comunque produrre >minimo
osservazioni indipendenti se abbastanza gap GRANDI spezzano la catena
transitiva (es. 60 gap piccoli + 40 gap grandi su 100 totali: la
mediana e' sotto l'embargo ma i 40 gap grandi possono generare 41+
cluster indipendenti). L'AUTORITA' primaria resta SEMPRE la geometria
REALE dei cluster (`assign_clusters`/INDEPENDENT_VIEW, gia' calcolata):
`classify_firing_geometry_risk_flag()` produce ora un `risk_flag`
booleano DIAGNOSTICO (rinominato da un verdetto pseudo-autorevole),
mai l'autorita' che classifica una family PATHOLOGICAL - quella
classificazione deriva ESCLUSIVAMENTE da independent_units (calcolato
sui cluster reali) confrontato con minimum_required_n.

Principi non negoziabili (invariati):
- OUTCOME-BLIND: nessuna funzione qui accetta o richiede outcome. Solo
  posizione temporale (row/bar index) e feature di STATO (mai di
  outcome) per il matching preflight.
- DETERMINISTICO: stesso input -> stesso output, nessuna casualita'.
- FAIL-CLOSED, NESSUN DEFAULT INVENTATO: campi/feature mancanti non
  vengono mai sostituiti da un placeholder - la classificazione
  corrispondente (NEEDS_DETECTOR_FORMALIZATION / NEEDS_MATCHING_
  FORMALIZATION) e' la risposta corretta, non un errore da nascondere.
- Riusa la meccanica gia' esistente e testata (sequence_episode_engine.py,
  dependence_diagnostics.assign_clusters, BaselineEngineV4,
  ControlReuseLedger) - non reimplementata.
- Nessun claim di edge/probabilita' di successo: il verdetto e'
  ESCLUSIVAMENTE strutturale.

Stati di verdetto finale (fail-closed, nessun claim universale):
  FEASIBLE                                - geometria E matching entrambi feasible.
  BORDERLINE_FEASIBILITY                   - geometria borderline, matching feasible.
  NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY  - geometria sotto il minimo SULLA
                                              partition proposta (il matching
                                              non viene nemmeno valutato in
                                              questo caso - non c'e' nulla da
                                              matchare). Scoped a quella
                                              partition (vedi FAIL-009).
  NEEDS_DETECTOR_FORMALIZATION             - campi geometrici (livello 1) mancanti.
  NEEDS_MATCHING_FORMALIZATION             - geometria ok, matching_spec/dati
                                              di matching reali mancanti o
                                              incompleti (livello 2).
  MATCHING_STRUCTURALLY_INFEASIBLE         - matching_spec completo e preflight
                                              eseguito REALMENTE, ma fallisce
                                              una condizione fail-closed
                                              (reuse oltre il tetto, tie-break
                                              non deterministico, o unita'
                                              indipendenti con match valido
                                              sotto il minimo richiesto).
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
from baseline_engine_v4 import BaselineEngineV4, build_quality_report, CONTRACT_VERSION as BASELINE_ENGINE_CONTRACT_VERSION  # noqa: E402

GATE_POLICY_VERSION = "SEQUENCE_STRUCTURAL_FEASIBILITY_POLICY_V1"
ENGINE_VERSION = "sequence_structural_feasibility_gate.py@v2"

# ---- Livello 1: geometria del detector (sec.2 Phase 7.5A originale) ----
# Campi che un family spec DEVE dichiarare esplicitamente prima che il
# gate possa calcolare QUALUNQUE geometria. Nessuno di questi ha un
# default silenzioso in questo modulo.
REQUIRED_DETECTOR_GEOMETRY_FIELDS = (
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
REQUIRED_SPEC_FIELDS = REQUIRED_DETECTOR_GEOMETRY_FIELDS  # alias retro-compatibile, stessa tupla

# ---- Livello 2: matching preflight (sec.2-3 di questa patch) ----
# Nomi canonici allineati ai parametri REALI gia' usati da BaselineEngineV4
# (match_dimensions, k, minimum_control_count, max_control_reuse_per_run,
# split_boundaries) invece di reinventarne di nuovi - solo
# state_feature_definitions e control_pool_construction_policy sono
# concetti nuovi (dichiarazione, non nuova logica).
REQUIRED_MATCHING_SPEC_FIELDS = (
    "match_dimensions",
    "k",
    "minimum_control_count",
    "max_control_reuse_per_run",
    "state_feature_definitions",
    "control_pool_construction_policy",
    "split_boundaries",
)

FORMALIZATION_LEVEL_NONE = "NONE"
FORMALIZATION_LEVEL_DETECTOR_GEOMETRY_READY = "DETECTOR_GEOMETRY_READY"
FORMALIZATION_LEVEL_MATCHING_PREFLIGHT_READY = "MATCHING_PREFLIGHT_READY"

MATCHING_STATUS_NOT_DECLARED = "NOT_DECLARED"
MATCHING_STATUS_DECLARED_AWAITING_DATA = "DECLARED_AWAITING_DATA"
MATCHING_STATUS_EXECUTED_FEASIBLE = "EXECUTED_FEASIBLE"
MATCHING_STATUS_EXECUTED_INFEASIBLE = "EXECUTED_INFEASIBLE"

VERDICT_FEASIBLE = "FEASIBLE"
VERDICT_BORDERLINE = "BORDERLINE_FEASIBILITY"
VERDICT_NOT_TESTABLE = "NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY"
VERDICT_NEEDS_DETECTOR_FORMALIZATION = "NEEDS_DETECTOR_FORMALIZATION"
VERDICT_NEEDS_MATCHING_FORMALIZATION = "NEEDS_MATCHING_FORMALIZATION"
VERDICT_MATCHING_STRUCTURALLY_INFEASIBLE = "MATCHING_STRUCTURALLY_INFEASIBLE"

DEFAULT_POLICY = {
    # POLICY_THRESHOLD - margine minimo sopra il gate di campione minimo
    # perche' un candidato conti FEASIBLE invece che BORDERLINE (nessun
    # claim universale - un candidato appena sopra la soglia e'
    # strutturalmente fragile a piccole differenze di embargo/partition).
    "feasible_margin_multiplier": 1.5,
    # POLICY_THRESHOLD - sotto questa frazione di episodi che sopravvivono
    # alla seconda passata di declustering (embargo), il candidato e'
    # segnalato BORDERLINE anche se n nominale supera il minimo.
    "independence_retention_borderline_floor": 0.30,
    # POLICY_THRESHOLD - stessa logica per la prima passata (event->episode).
    "episode_retention_borderline_floor": 0.30,
}


class StructuralInputNotDeclaredError(Exception):
    pass


class MatchingRuntimeDataIncompleteError(Exception):
    """sec.9 - sollevata se matching_runtime_data e' dichiarato ma manca
    la feature di stato per anche una sola osservazione INDEPENDENT_VIEW.
    MAI riempita con un valore inventato - il chiamante deve fornire
    feature reali per OGNI osservazione indipendente o non dichiarare
    affatto matching_runtime_data (in tal caso il gate risponde
    correttamente DECLARED_AWAITING_DATA, non un errore)."""
    pass


def missing_spec_fields(spec: dict) -> list:
    """Livello 1 (geometria) - non solleva mai un'eccezione, usato per
    CLASSIFICARE: una family senza detector sufficientemente formalizzato
    e' NEEDS_DETECTOR_FORMALIZATION con i gradi di liberta' mancanti
    elencati, non uno stack trace."""
    missing = []
    for field in REQUIRED_DETECTOR_GEOMETRY_FIELDS:
        if field not in spec or spec[field] is None:
            missing.append(field)
        elif field == "event_row_indices" and len(spec[field]) == 0:
            missing.append(field)
        elif field == "detector_frozen" and spec[field] is not True:
            missing.append(field)
    return missing


def missing_matching_spec_fields(matching_spec: dict) -> list:
    """Livello 2 (matching) - stessa filosofia fail-closed di
    missing_spec_fields(), applicata a spec["matching_spec"]."""
    missing = []
    for field in REQUIRED_MATCHING_SPEC_FIELDS:
        if field not in matching_spec or matching_spec[field] is None:
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
    outcome. Riusa sequence_episode_engine.py senza modifiche.
    INDEPENDENT_VIEW.representative_rows e' esposto esplicitamente (non
    solo il conteggio) - necessario al matching preflight (sec.4: il
    sample gate va ricalcolato sulle unita' indipendenti CON match
    valido, quindi serve sapere ESATTAMENTE quali row sono le
    rappresentanti indipendenti da passare al matcher)."""
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
    representative_rows = [e["event_a_index"] for e in independent_view["events"]]
    return {
        "n_bars": n_bars,
        "n_raw_events": n_raw_events,
        "firing_rate": firing_rate,
        "gap_stats": gap_stats,
        "EVENT_VIEW": {"n": event_view["n"]},
        "EPISODE_VIEW": {"n": episode_view["n"], "n_episodes": episode_view["n_episodes"]},
        "INDEPENDENT_VIEW": {"n": independent_view["n"],
                              "n_independent_observations": independent_view["n_independent_observations"],
                              "representative_rows": representative_rows,
                              "direction_by_row": {r: direction_by_row.get(r, "BOTH") for r in representative_rows}},
        "episode_gap_rule": episode_gap_rule,
        "natural_horizon": natural_horizon,
        "overlap_policy": overlap_policy,
        "outcome_overlap_embargo_bars": outcome_overlap_embargo_bars,
    }


def compute_cluster_geometry(event_row_indices: list, episode_gap_rule: int,
                              outcome_overlap_embargo_bars: int) -> dict:
    """Geometria dei cluster a DUE soglie distinte - stessa distinzione
    concettuale di sequence_episode_engine.py: event_cluster_rule
    (espansione fisica locale) vs outcome_overlap embargo (indipendenza
    statistica dell'outcome). Calcolata sui cluster di INDIPENDENZA
    (embargo) - la geometria decisiva per il gate di campione minimo,
    e l'AUTORITA' primaria per qualunque classificazione di
    incompatibilita' strutturale (mai un proxy come il gap mediano da
    solo - vedi classify_firing_geometry_risk_flag)."""
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
    """Rapporti semplici, nessuna formula statistica nuova."""
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


def classify_firing_geometry_risk_flag(funnel: dict) -> dict:
    """Diagnostica SECONDARIA (correzione di semantica, post-review
    2026-09-20): `median_gap_bars <= embargo` e' un segnale di RISCHIO,
    non una prova di incompatibilita' strutturale - un detector con gap
    mediano sotto l'embargo puo' comunque produrre abbastanza unita'
    indipendenti se un numero sufficiente di gap GRANDI spezza la
    catena transitiva (es. 60 gap piccoli + 40 gap grandi su 100: la
    mediana e' sotto embargo ma i 40 gap grandi possono generare 41+
    cluster indipendenti - controesempio verificato in
    test_phase7_5_structural_feasibility_gate.py, caso A). L'AUTORITA'
    che decide incompatibilita' strutturale resta ESCLUSIVAMENTE
    independent_units (dai cluster REALI, assign_clusters) confrontato
    con minimum_required_n - MAI questo flag da solo."""
    gap_stats = funnel["gap_stats"]
    median_gap = gap_stats["median_gap_bars"]
    embargo = funnel["outcome_overlap_embargo_bars"]
    risk_flag = (median_gap is not None) and (median_gap <= embargo)
    reason = (
        f"median_gap_bars={median_gap} <= outcome_overlap_embargo_bars={embargo}: segnale di RISCHIO "
        f"che il clustering transitivo possa comprimere l'INDEPENDENT_VIEW - NON una prova da sola "
        f"(gap grandi intermedi possono comunque produrre abbastanza cluster indipendenti). "
        f"Verificare SEMPRE independent_units nel funnel/geometry reale, non fermarsi a questo flag."
        if risk_flag else
        f"median_gap_bars={median_gap} > outcome_overlap_embargo_bars={embargo}: nessun segnale di "
        f"rischio dal proxy del gap mediano (comunque non l'unica fonte di verita' - vedi cluster_geometry)."
    )
    return {
        "signature": "EVENT_FIRING_RATE_ABOVE_INFORMATIVE_THRESHOLD",
        "risk_flag": risk_flag,
        "median_gap_bars": median_gap,
        "outcome_overlap_embargo_bars": embargo,
        "firing_rate": funnel["firing_rate"],
        "reason": reason,
        "authority": "DIAGNOSTIC_ONLY - l'autorita' strutturale e' independent_units (assign_clusters/"
                     "INDEPENDENT_VIEW) vs minimum_required_n, mai questo proxy da solo.",
    }


def run_matching_preflight(match_dimensions: list, k: int, split_boundaries: dict,
                            events: list, control_pool: list, control_row_by_id: dict,
                            control_direction_by_id: dict, control_features_by_id: dict,
                            discovery_features_by_row: dict, minimum_control_count: int,
                            max_control_reuse_per_run: int, discovery_split_name: str = "discovery",
                            feature_version: str = "feature_registry_v2") -> dict:
    """Simula il matching STRUTTURALE senza alcun outcome, riusando
    BaselineEngineV4/ControlReuseLedger senza modifiche. Va invocato
    SOLO quando esistono gia' feature di stato reali (evento e pool di
    controllo) - MAI con feature inventate per far girare il preflight
    su una family non ancora formalizzata."""
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
    # produrre esattamente le stesse scelte di controllo per ogni evento.
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
        "excessive_poor_matches_flag": quality_report["excessive_poor_matches_flag"],
        "reuse_report": reuse_report,
        "max_reuse_within_declared_cap": max_reuse_within_cap,
        "tie_break_deterministic": tie_break_deterministic,
    }


def evaluate_matching_feasibility(funnel: dict, spec: dict, minimum_evidence_gates: dict) -> dict:
    """Livello 2 del gate (sec.1-4 della patch) - il matching preflight
    partecipa ORA al verdetto composito. Fail-closed a 4 stati:
      NOT_DECLARED           - matching_spec assente o incompleto.
      DECLARED_AWAITING_DATA - matching_spec completo ma nessuna feature
                                REALE ancora disponibile (mai simulato).
      EXECUTED_FEASIBLE      - preflight eseguito, condizioni fail-closed
                                soddisfatte (sec.4: reuse<=tetto, tie-break
                                deterministico, independent_units CON match
                                valido >= minimum_required_n - ricalcolato
                                sulle sole osservazioni REALMENTE matchate,
                                non sul conteggio grezzo di INDEPENDENT_VIEW).
      EXECUTED_INFEASIBLE    - preflight eseguito, almeno una condizione
                                fail-closed violata."""
    matching_spec = spec.get("matching_spec")
    if not matching_spec:
        return {"status": MATCHING_STATUS_NOT_DECLARED,
                "missing_matching_degrees_of_freedom": list(REQUIRED_MATCHING_SPEC_FIELDS)}
    missing = missing_matching_spec_fields(matching_spec)
    if missing:
        return {"status": MATCHING_STATUS_NOT_DECLARED, "missing_matching_degrees_of_freedom": missing}

    runtime = spec.get("matching_runtime_data")
    if not runtime:
        return {"status": MATCHING_STATUS_DECLARED_AWAITING_DATA, "missing_matching_degrees_of_freedom": []}

    representative_rows = funnel["INDEPENDENT_VIEW"]["representative_rows"]
    event_features_by_row = runtime.get("event_features_by_row", {})
    event_direction_by_row = funnel["INDEPENDENT_VIEW"]["direction_by_row"]
    missing_features = [r for r in representative_rows if r not in event_features_by_row]
    if missing_features:
        raise MatchingRuntimeDataIncompleteError(
            f"matching_runtime_data dichiarato ma event_features_by_row manca per "
            f"{len(missing_features)}/{len(representative_rows)} osservazioni INDEPENDENT_VIEW "
            f"(prime mancanti: {missing_features[:5]}) - nessuna feature inventata per completare il preflight."
        )
    events = [
        {"event_id": f"INDEP-{r}", "event_row": r, "direction": event_direction_by_row.get(r, "BOTH"),
         "features": event_features_by_row[r]}
        for r in representative_rows
    ]
    preflight = run_matching_preflight(
        match_dimensions=matching_spec["match_dimensions"], k=matching_spec["k"],
        split_boundaries=matching_spec["split_boundaries"], events=events,
        control_pool=runtime["control_pool"], control_row_by_id=runtime["control_row_by_id"],
        control_direction_by_id=runtime["control_direction_by_id"],
        control_features_by_id=runtime["control_features_by_id"],
        discovery_features_by_row=runtime["discovery_features_by_row"],
        minimum_control_count=matching_spec["minimum_control_count"],
        max_control_reuse_per_run=matching_spec["max_control_reuse_per_run"],
    )
    minimum_required_n = minimum_evidence_gates["n_nominal_minimum"]
    independent_units_with_valid_match = preflight["n_matched"]
    fail_reasons = []
    if not preflight["tie_break_deterministic"]:
        fail_reasons.append("TIE_BREAK_NOT_DETERMINISTIC")
    if not preflight["max_reuse_within_declared_cap"]:
        fail_reasons.append("MAX_CONTROL_REUSE_EXCEEDS_DECLARED_CAP")
    if independent_units_with_valid_match < minimum_required_n:
        fail_reasons.append(
            f"INDEPENDENT_UNITS_WITH_VALID_MATCH({independent_units_with_valid_match})_BELOW_"
            f"MINIMUM_REQUIRED_N({minimum_required_n})"
        )
    status = MATCHING_STATUS_EXECUTED_INFEASIBLE if fail_reasons else MATCHING_STATUS_EXECUTED_FEASIBLE
    return {
        "status": status,
        "missing_matching_degrees_of_freedom": [],
        "preflight": preflight,
        "independent_units_with_valid_match": independent_units_with_valid_match,
        "minimum_required_n": minimum_required_n,
        "fail_reasons": fail_reasons,
    }


def _classify_geometry_verdict(ratios: dict, policy: dict) -> str:
    """Verdetto del SOLO livello 1 (geometria) - invariato nella logica
    rispetto alla prima versione del gate, isolato in una funzione
    propria perche' ora e' solo UNA delle due componenti del verdetto
    composito finale."""
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


def _compose_final_verdict(geometry_verdict: str, matching_result: dict) -> str:
    """sec.3 della patch - il verdetto finale richiede ENTRAMBI i
    livelli. Se la geometria da sola e' gia' NOT_TESTABLE, il matching
    non viene nemmeno valutato (non c'e' nulla di indipendente da
    matchare)."""
    if geometry_verdict == VERDICT_NOT_TESTABLE:
        return VERDICT_NOT_TESTABLE
    status = matching_result["status"]
    if status in (MATCHING_STATUS_NOT_DECLARED, MATCHING_STATUS_DECLARED_AWAITING_DATA):
        return VERDICT_NEEDS_MATCHING_FORMALIZATION
    if status == MATCHING_STATUS_EXECUTED_INFEASIBLE:
        return VERDICT_MATCHING_STRUCTURALLY_INFEASIBLE
    return geometry_verdict  # EXECUTED_FEASIBLE: eredita FEASIBLE o BORDERLINE_FEASIBILITY dalla geometria


def evaluate_family_structural_feasibility(spec: dict, policy: dict = None,
                                            bars_per_year: float = None,
                                            direction_by_row: dict = None) -> dict:
    """Punto di ingresso principale del gate. Ritorna sempre un dict con
    almeno 'sequence_family_id' e 'verdict' - MAI un'eccezione per una
    family incompleta (quella e' una classificazione valida, non un
    errore di programma). Ora integra ENTRAMBI i livelli (geometria +
    matching preflight) nel verdetto finale - vedi docstring di modulo."""
    policy = policy or DEFAULT_POLICY
    family_id = spec.get("sequence_family_id", "UNKNOWN_FAMILY")
    missing = missing_spec_fields(spec)
    if missing:
        return {
            "sequence_family_id": family_id,
            "verdict": VERDICT_NEEDS_DETECTOR_FORMALIZATION,
            "formalization_level": FORMALIZATION_LEVEL_NONE,
            "missing_degrees_of_freedom": missing,
            "note": "Nessun parametro inventato per far girare il gate. Formalizzare il detector "
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
            "formalization_level": FORMALIZATION_LEVEL_NONE,
            "missing_degrees_of_freedom": [str(e)],
            "engine_version": ENGINE_VERSION,
            "policy_version": GATE_POLICY_VERSION,
        }

    geometry = compute_cluster_geometry(
        event_row_indices=spec["event_row_indices"], episode_gap_rule=spec["episode_gap_rule"],
        outcome_overlap_embargo_bars=spec["proposed_outcome_overlap_embargo_bars"],
    )
    ratios = compute_feasibility_ratios(funnel, spec["minimum_evidence_gates"], bars_per_year=bars_per_year)
    firing_flag = classify_firing_geometry_risk_flag(funnel)
    geometry_verdict = _classify_geometry_verdict(ratios, policy)

    matching_result = (
        {"status": MATCHING_STATUS_NOT_DECLARED, "missing_matching_degrees_of_freedom": None}
        if geometry_verdict == VERDICT_NOT_TESTABLE
        else evaluate_matching_feasibility(funnel, spec, spec["minimum_evidence_gates"])
    )
    final_verdict = _compose_final_verdict(geometry_verdict, matching_result)
    formalization_level = (FORMALIZATION_LEVEL_DETECTOR_GEOMETRY_READY
                            if matching_result["status"] == MATCHING_STATUS_NOT_DECLARED
                            else FORMALIZATION_LEVEL_MATCHING_PREFLIGHT_READY)

    provenance = {
        "detector_source_ref": spec["detector_source_ref"],
        "detector_parameters_hash": canonical_sha256(spec["detector_parameters"]),
        "spec_hash": canonical_sha256({k: v for k, v in spec.items()
                                       if k not in ("event_row_indices", "matching_runtime_data")}),
        "discovery_partition": spec["discovery_partition"],
        "engine_version": ENGINE_VERSION,
        "policy_version": GATE_POLICY_VERSION,
        "outcome_blind": True,
        "deterministic": True,
    }
    if matching_result["status"] in (MATCHING_STATUS_EXECUTED_FEASIBLE, MATCHING_STATUS_EXECUTED_INFEASIBLE):
        provenance["matching"] = {
            "baseline_engine_version": BASELINE_ENGINE_CONTRACT_VERSION,
            "matching_spec_hash": canonical_sha256(spec["matching_spec"]),
            "max_control_reuse_per_run": spec["matching_spec"]["max_control_reuse_per_run"],
            "matching_result_hash": canonical_sha256(matching_result["preflight"]),
        }

    return {
        "sequence_family_id": family_id,
        "verdict": final_verdict,
        "formalization_level": formalization_level,
        "geometry_verdict": geometry_verdict,
        "detection_funnel": funnel,
        "cluster_geometry": geometry,
        "feasibility_ratios": ratios,
        "firing_geometry_risk_flag": firing_flag,
        "matching": matching_result,
        "provenance": provenance,
    }


if __name__ == "__main__":
    # ---- Demo/self-test su dati sintetici (nessun dato NEXUS) ----
    import random as _random

    def _base_spec(event_row_indices, **overrides):
        s = {
            "sequence_family_id": "SEQFAM-DEMO", "detector_frozen": True, "detector_source_ref": "SYNTHETIC_DEMO",
            "detector_parameters": {"threshold": 1.0}, "observation_timing": {"observation_cutoff": "close(t)"},
            "event_direction_policy": "BUY", "episode_gap_rule": 3, "overlap_policy": "COLLAPSE_TO_FIRST",
            "proposed_natural_horizon": 40, "proposed_outcome_overlap_embargo_bars": 39,
            "discovery_partition": {"partition_id": "SYNTHETIC_DEMO", "n_bars": max(event_row_indices) + 100},
            "minimum_evidence_gates": {"n_nominal_minimum": 30},
            "event_row_indices": event_row_indices,
        }
        s.update(overrides)
        return s

    # Caso 1: spec incompleto -> NEEDS_DETECTOR_FORMALIZATION, nessun default inventato.
    r1 = evaluate_family_structural_feasibility({"sequence_family_id": "SEQFAM-DEMO-INCOMPLETE"})
    assert r1["verdict"] == VERDICT_NEEDS_DETECTOR_FORMALIZATION
    assert r1["formalization_level"] == FORMALIZATION_LEVEL_NONE
    print(f"Caso 1 OK: spec incompleto -> {r1['verdict']} ({len(r1['missing_degrees_of_freedom'])} campi mancanti)")

    # Caso 2 (replay strutturale SEQ-0015, sintetico - solo geometria GIA' pubblicata, nessun outcome).
    _random.seed(0)
    rows = []
    r = 100
    for _ in range(210):
        cluster_size = _random.choice([1, 1, 1, 2, 2, 3])
        for _ in range(cluster_size):
            rows.append(r)
            r += _random.randint(1, 3)
        r += _random.randint(4, 7)
        if len(rows) >= 249:
            break
    rows = rows[:249]
    r2 = evaluate_family_structural_feasibility(_base_spec(rows))
    print(f"Caso 2 (replay strutturale SEQ-0015): INDEPENDENT_VIEW={r2['detection_funnel']['INDEPENDENT_VIEW']['n']} "
          f"-> verdict={r2['verdict']}")
    assert r2["verdict"] == VERDICT_NOT_TESTABLE
    assert r2["matching"]["status"] == MATCHING_STATUS_NOT_DECLARED  # geometria gia' NOT_TESTABLE, matching non valutato

    # Caso 3: geometria ampiamente sopra il minimo MA nessun matching_spec -> NEEDS_MATCHING_FORMALIZATION (non FEASIBLE!).
    rows3 = list(range(0, 60 * 60, 60))
    r3 = evaluate_family_structural_feasibility(_base_spec(rows3))
    print(f"Caso 3 (geometria ampia, NESSUN matching_spec): geometry_verdict={r3['geometry_verdict']} "
          f"-> verdict finale={r3['verdict']}")
    assert r3["geometry_verdict"] == VERDICT_FEASIBLE
    assert r3["verdict"] == VERDICT_NEEDS_MATCHING_FORMALIZATION, (
        "questa e' esattamente la correzione della patch: geometria FEASIBLE da sola non basta piu'"
    )
    assert r3["formalization_level"] == FORMALIZATION_LEVEL_DETECTOR_GEOMETRY_READY

    # Caso 4: stesso spec MA con matching_spec completo e matching_runtime_data reale con pool AMPIO -> FEASIBLE.
    boundaries = {"discovery": (0, 1_000_000)}
    control_pool = list(range(500_000, 500_040))
    control_row_by_id = {c: c for c in control_pool}
    control_direction_by_id = {c: "BOTH" for c in control_pool}  # default direction_by_row is "BOTH" per riga
    control_features_by_id = {c: {"state": "A"} for c in control_pool}
    discovery_feats = {c: {"state": "A"} for c in control_pool}
    event_features_by_row = {row: {"state": "A"} for row in rows3}
    spec4 = _base_spec(
        rows3,
        matching_spec={"match_dimensions": ["state"], "k": 3, "minimum_control_count": 5,
                        "max_control_reuse_per_run": 10, "state_feature_definitions": {"state": {"source": "TEST"}},
                        "control_pool_construction_policy": "TEST_SAME_SPLIT_SAME_DIRECTION",
                        "split_boundaries": boundaries},
        matching_runtime_data={"control_pool": control_pool, "control_row_by_id": control_row_by_id,
                                "control_direction_by_id": control_direction_by_id,
                                "control_features_by_id": control_features_by_id,
                                "discovery_features_by_row": discovery_feats,
                                "event_features_by_row": event_features_by_row},
    )
    r4 = evaluate_family_structural_feasibility(spec4)
    print(f"Caso 4 (geometria + matching entrambi validi): matching.status={r4['matching']['status']} "
          f"-> verdict finale={r4['verdict']}")
    assert r4["verdict"] == VERDICT_FEASIBLE
    assert r4["formalization_level"] == FORMALIZATION_LEVEL_MATCHING_PREFLIGHT_READY
    assert r4["matching"]["status"] == MATCHING_STATUS_EXECUTED_FEASIBLE
    assert "matching" in r4["provenance"]

    # Caso 5: stessa geometria MA pool di controllo insufficiente -> MATCHING_STRUCTURALLY_INFEASIBLE.
    tiny_pool = control_pool[:2]  # sotto minimum_control_count=5
    spec5 = dict(spec4)
    spec5["matching_runtime_data"] = dict(spec4["matching_runtime_data"])
    spec5["matching_runtime_data"]["control_pool"] = tiny_pool
    r5 = evaluate_family_structural_feasibility(spec5)
    print(f"Caso 5 (geometria valida, pool insufficiente): matching.status={r5['matching']['status']} "
          f"-> verdict finale={r5['verdict']}")
    assert r5["verdict"] == VERDICT_MATCHING_STRUCTURALLY_INFEASIBLE
    assert r5["matching"]["status"] == MATCHING_STATUS_EXECUTED_INFEASIBLE

    # Caso 6: determinismo - stesso spec rigirato due volte -> stesso hash.
    r2_again = evaluate_family_structural_feasibility(_base_spec(rows))
    assert canonical_sha256(r2["detection_funnel"]) == canonical_sha256(r2_again["detection_funnel"])
    print("Caso 6 OK: stesso spec -> stesso hash di funnel (deterministico).")

    print("\nTutti i casi del Sequence Structural Feasibility Gate (v2, integrato) verificati.")
