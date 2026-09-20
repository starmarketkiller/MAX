#!/usr/bin/env python3
"""Phase 7.0B sec.1-3 - Baseline Engine v4: implementazione REALE del
contratto in baseline_contract_v4.json (finora solo dichiarativo).

Garantisce meccanicamente (non solo per policy):
- direction_aware: un evento riceve SOLO controlli della stessa direzione.
- temporally_safe / split_safe: un evento riceve SOLO controlli dello
  stesso split (enforcement via cross_split_safety.py, non aggirabile).
- state_matched: coarsened matching esatto sulle dimensioni categoriche
  dichiarate nel candidate contract (baseline_match_dimensions) - MAI
  aggiunte automaticamente.
- discovery_fitted_only: media/std delle dimensioni numeriche sono
  fittate SOLO su righe del discovery split - un tentativo di fit su
  altre righe solleva FitIsolationViolation, non viene silenziosamente
  accettato.
- auditable: ogni singolo match produce un record con evento, controllo,
  split, direzione, distanza standardizzata, qualita', versione feature
  e versione del contratto.

Nessuna dimensione di matching e' scelta da questo modulo - arriva
dichiarata esplicitamente dal chiamante (baseline_match_dimensions del
candidate contract, sec.2).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cross_split_safety import assign_split, validate_baseline_matches, CrossSplitViolation  # noqa: E402
from control_reuse_ledger import ControlReuseLedger  # noqa: E402

CONTRACT_VERSION = "BASELINE_ENGINE_V4_CONTRACT/schema_version=4"

MATCH_QUALITY_THRESHOLDS = {"GOOD": 0.5, "FAIR": 1.0}  # da baseline_contract_v4.json - POLICY_THRESHOLD
MINIMUM_CONTROL_COUNT = 20  # da baseline_contract_v4.json - POLICY_THRESHOLD


class FitIsolationViolation(Exception):
    pass


class BaselineNotFittedError(Exception):
    pass


def _is_categorical(value) -> bool:
    return isinstance(value, str)


def classify_quality(distance) -> str:
    if distance is None:
        return "GOOD"  # nessuna dimensione numerica dichiarata: il match e' solo sulla cella coarsened
    if distance < MATCH_QUALITY_THRESHOLDS["GOOD"]:
        return "GOOD"
    if distance < MATCH_QUALITY_THRESHOLDS["FAIR"]:
        return "FAIR"
    return "POOR"


class BaselineEngineV4:
    def __init__(self, match_dimensions: list, k: int, split_boundaries: dict,
                 discovery_split_name: str = "discovery", feature_version: str = "feature_registry_v2",
                 minimum_control_count: int = MINIMUM_CONTROL_COUNT, max_control_reuse_per_run: int = None):
        """max_control_reuse_per_run (Phase 7.4A Baseline Matching Integrity
        Patch) - DEVE essere dichiarato esplicitamente dal family spec del
        chiamante (mai un default nascosto per una family nuova). None
        preserva il comportamento storico non-enforced (retrocompatibilita'
        con candidati gia' congelati/conclusi prima di questa patch, es.
        Phase 7.1 RECLAIM - MAI ri-eseguiti, quindi mai da 'correggere' ora)."""
        if k <= 0:
            raise ValueError("k deve essere positivo")
        self.match_dimensions = list(match_dimensions)  # dichiarate dal candidate contract, sec.2
        self.k = k
        self.split_boundaries = split_boundaries
        self.discovery_split_name = discovery_split_name
        self.feature_version = feature_version
        self.minimum_control_count = minimum_control_count
        self.max_control_reuse_per_run = max_control_reuse_per_run
        self._reuse_ledger = ControlReuseLedger(max_control_reuse_per_run) if max_control_reuse_per_run else None
        self._norm_params = None  # {dim: (mean, std)} - solo dimensioni numeriche

    def fit_normalization(self, discovery_features_by_row: dict):
        """discovery_features_by_row: {row_id: {dim: value}}. OGNI riga
        deve appartenere al discovery split - un tentativo di fit su
        internal_validation/locked_validation/final_holdout solleva
        FitIsolationViolation (sec.14, test negativo obbligatorio)."""
        numeric_dims = [d for d in self.match_dimensions
                        if any(not _is_categorical(v[d]) for v in discovery_features_by_row.values() if d in v)]
        for row_id in discovery_features_by_row:
            split = assign_split(row_id, self.split_boundaries)
            if split != self.discovery_split_name:
                raise FitIsolationViolation(
                    f"Tentativo di fit della normalizzazione su riga {row_id} "
                    f"(split={split}) - ammesso SOLO discovery_fitted_only='{self.discovery_split_name}'."
                )
        params = {}
        for d in numeric_dims:
            values = [v[d] for v in discovery_features_by_row.values() if d in v and not _is_categorical(v[d])]
            if not values:
                continue
            mean = sum(values) / len(values)
            var = sum((x - mean) ** 2 for x in values) / len(values) if len(values) > 1 else 0.0
            std = var ** 0.5 or 1.0  # evita divisione per zero se tutte le righe hanno lo stesso valore
            params[d] = (mean, std)
        self._norm_params = params
        return params

    def _standardized_distance(self, event_feat: dict, control_feat: dict, numeric_dims: list):
        if not numeric_dims:
            return None
        if self._norm_params is None:
            raise BaselineNotFittedError("fit_normalization() non ancora chiamato - nessun parametro discovery-fitted disponibile.")
        total = 0.0
        for d in numeric_dims:
            mean, std = self._norm_params.get(d, (0.0, 1.0))
            total += ((event_feat[d] - mean) / std - (control_feat[d] - mean) / std) ** 2
        return total ** 0.5

    def match(self, event_id, event_row: int, event_direction, event_features: dict,
              control_pool: list, control_row_by_id: dict, control_direction_by_id: dict,
              control_features_by_id: dict):
        """Ritorna un dict con lo stato del match per QUESTO evento -
        MAI un pool aggregato senza tracciabilita' per-osservazione
        (sec.1, auditable). Nessun controllo cross-split puo' sfuggire:
        il filtro e' applicato qui E ri-verificato con
        cross_split_safety.validate_baseline_matches come difesa in
        profondita'.

        Selezione dei k controlli (Phase 7.4A Baseline Matching Integrity
        Patch, sec.8-9) - ordine di priorita' DETERMINISTICO, mai
        dipendente implicitamente dall'ordine di 'control_pool':
          1. distanza standardizzata minima (se esistono dimensioni
             numeriche - la metrica di match dichiarata resta primaria,
             il reuse non puo' MAI far preferire un controllo piu' lontano);
          2. a parita' di distanza, minimo utilizzo residuo corrente
             (ControlReuseLedger.usage_count - il discriminante naturale
             quando le dimensioni di match sono tutte categoriche, come
             SEQ-0015, dove ogni distanza e' None/equivalente);
          3. a ulteriore parita', control_id crescente (tie-break stabile,
             deterministico, mai casuale - riproducibilita' garantita
             indipendentemente dall'ordine del dataframe di origine).

        Se max_control_reuse_per_run e' dichiarato, i candidati che hanno
        gia' raggiunto il tetto sono ESCLUSI dal pool PRIMA del controllo
        di minimum_control_count (fail-closed: un pool che scende sotto
        soglia per effetto del tetto di riuso viene correttamente
        rifiutato come REJECTED_INSUFFICIENT_POOL, non silenziosamente
        riempito oltre il tetto)."""
        event_split = assign_split(event_row, self.split_boundaries)
        categorical_dims = [d for d in self.match_dimensions if _is_categorical(event_features.get(d))]
        numeric_dims = [d for d in self.match_dimensions if d not in categorical_dims]

        same_split = [cid for cid in control_pool if assign_split(control_row_by_id[cid], self.split_boundaries) == event_split]
        same_direction = [cid for cid in same_split if control_direction_by_id[cid] == event_direction]
        same_cell = [cid for cid in same_direction
                     if all(control_features_by_id[cid].get(d) == event_features.get(d) for d in categorical_dims)]
        if self._reuse_ledger is not None:
            same_cell = self._reuse_ledger.filter_available_pool(same_cell)
        eligible_candidate_pool = list(same_cell)  # esposto per audit (Phase 7.4A sec.1) - MAI ricostruito a mano dal chiamante

        pool_available = len(same_cell)
        if pool_available < self.minimum_control_count:
            return {
                "event_id": event_id, "event_split": event_split, "event_direction": event_direction,
                "status": "REJECTED_INSUFFICIENT_POOL",
                "rejection_reason": f"pool disponibile ({pool_available}) sotto minimum_control_count ({self.minimum_control_count})",
                "controls_available": pool_available, "controls_used": 0, "matches": [],
                "eligible_candidate_pool": eligible_candidate_pool,
            }

        def _reuse_of(cid):
            return self._reuse_ledger.usage_count(cid) if self._reuse_ledger is not None else 0

        distances = [(cid, self._standardized_distance(event_features, control_features_by_id[cid], numeric_dims))
                     for cid in same_cell]
        distances.sort(key=lambda x: (x[1] is not None, x[1] if x[1] is not None else 0.0, _reuse_of(x[0]), x[0]))
        used = distances[: min(self.k, len(distances))]

        if self._reuse_ledger is not None:
            self._reuse_ledger.register_controls_used([cid for cid, _ in used])

        matches = []
        for cid, dist in used:
            quality = classify_quality(dist)
            matches.append({
                "event_id": event_id, "event_split": event_split, "event_direction": event_direction,
                "control_id": cid, "control_split": assign_split(control_row_by_id[cid], self.split_boundaries),
                "control_direction": control_direction_by_id[cid],
                "match_dimensions": list(self.match_dimensions),
                "standardized_distance": dist, "match_quality": quality,
                "reuse_count_after_this_match": _reuse_of(cid),
                "feature_version": self.feature_version, "baseline_contract_version": CONTRACT_VERSION,
            })

        # Difesa in profondita': se, nonostante il filtro sopra, un
        # controllo cross-split fosse finito nei match, questo DEVE
        # sollevare - non deve mai passare silenziosamente.
        validate_baseline_matches(event_row, [control_row_by_id[m["control_id"]] for m in matches], self.split_boundaries)

        k_shortfall = len(used) < self.k
        return {
            "event_id": event_id, "event_split": event_split, "event_direction": event_direction,
            "status": "MATCHED" if not k_shortfall else "MATCHED_K_SHORTFALL",
            "controls_available": pool_available, "controls_used": len(used), "matches": matches,
            "eligible_candidate_pool": eligible_candidate_pool,
        }

    def reuse_usage_report(self):
        """None se max_control_reuse_per_run non e' stato dichiarato per
        questo engine (nessun ledger attivo) - mai un report fittizio."""
        return self._reuse_ledger.usage_report() if self._reuse_ledger is not None else None


def build_quality_report(results: list) -> dict:
    """results: lista di output di BaselineEngineV4.match() per molti
    eventi. Produce baseline_quality_report_v4.json (sec.3)."""
    n_events = len(results)
    n_matched = sum(1 for r in results if r["status"] in ("MATCHED", "MATCHED_K_SHORTFALL"))
    n_rejected = sum(1 for r in results if r["status"] == "REJECTED_INSUFFICIENT_POOL")
    quality_counts = {"GOOD": 0, "FAIR": 0, "POOR": 0}
    for r in results:
        for m in r["matches"]:
            quality_counts[m["match_quality"]] += 1
    total_matches = sum(quality_counts.values())
    poor_share = (quality_counts["POOR"] / total_matches) if total_matches else 0.0
    return {
        "baseline_contract_version": CONTRACT_VERSION,
        "n_events": n_events,
        "n_matched": n_matched,
        "n_rejected_insufficient_pool": n_rejected,
        "unmatched_events": [r["event_id"] for r in results if r["status"] == "REJECTED_INSUFFICIENT_POOL"],
        "rejected_events": [{"event_id": r["event_id"], "reason": r.get("rejection_reason")}
                             for r in results if r["status"] == "REJECTED_INSUFFICIENT_POOL"],
        "controls_available_per_event": {r["event_id"]: r["controls_available"] for r in results},
        "controls_used_per_event": {r["event_id"]: r["controls_used"] for r in results},
        "match_quality_counts": quality_counts,
        "poor_match_share": poor_share,
        "excessive_poor_matches_flag": poor_share > 0.30,  # POLICY_THRESHOLD - vedi rationale nel chiamante
    }


if __name__ == "__main__":
    # Demo/self-test minimale su dati sintetici in-memory (nessun dato di
    # mercato reale) - il preflight v3 esercita casi piu' completi.
    boundaries = {"discovery": (0, 200), "internal_validation": (200, 280),
                  "locked_validation": (280, 360), "final_holdout": (360, 440)}
    engine = BaselineEngineV4(match_dimensions=["volatility_state"], k=3, split_boundaries=boundaries)

    discovery_feats = {i: {"volatility_state": "HIGH" if i % 2 == 0 else "LOW"} for i in range(0, 200, 2)}
    engine.fit_normalization(discovery_feats)  # nessuna dim numerica qui -> params vuoti, non deve fallire
    print("fit_normalization su discovery: OK, params =", engine._norm_params)

    try:
        engine.fit_normalization({250: {"volatility_state": "HIGH"}})  # riga in internal_validation
        print("ERRORE: fit su non-discovery avrebbe dovuto fallire!")
    except FitIsolationViolation as e:
        print(f"Fit isolation correttamente rifiutato: {e}")

    control_pool = list(range(0, 40, 2))
    control_row_by_id = {cid: cid for cid in control_pool}
    control_direction_by_id = {cid: "BUY" for cid in control_pool}
    control_features_by_id = {cid: {"volatility_state": "HIGH"} for cid in control_pool}
    result = engine.match(event_id="EVT-1", event_row=10, event_direction="BUY",
                           event_features={"volatility_state": "HIGH"},
                           control_pool=control_pool, control_row_by_id=control_row_by_id,
                           control_direction_by_id=control_direction_by_id,
                           control_features_by_id=control_features_by_id)
    print("Match result:", result["status"], "controls_used=", result["controls_used"])
    assert result["status"] in ("MATCHED", "MATCHED_K_SHORTFALL")

    # ---- Phase 7.4A Baseline Matching Integrity Patch: reuse enforcement + tie-break deterministico ----
    print("\n=== Reuse enforcement + tie-break deterministico (sec.7-9) ===")
    pool9 = [100, 102, 104, 106, 108, 110, 112, 114, 116]
    row9 = {c: c for c in pool9}
    dir9 = {c: "BUY" for c in pool9}
    feat9 = {c: {"volatility_state": "HIGH"} for c in pool9}  # nessuna dim numerica -> distanza sempre None, tie-break su reuse+id

    engine9 = BaselineEngineV4(match_dimensions=["volatility_state"], k=3, split_boundaries=boundaries,
                               minimum_control_count=3, max_control_reuse_per_run=2)
    expected_picks = [[100, 102, 104], [106, 108, 110], [112, 114, 116], [100, 102, 104], [106, 108, 110], [112, 114, 116]]
    for i, expected in enumerate(expected_picks):
        r = engine9.match(event_id=f"EVT9-{i}", event_row=120 + i, event_direction="BUY",
                          event_features={"volatility_state": "HIGH"}, control_pool=pool9,
                          control_row_by_id=row9, control_direction_by_id=dir9, control_features_by_id=feat9)
        picked = sorted(m["control_id"] for m in r["matches"])
        assert picked == expected, f"evento {i}: atteso {expected}, ottenuto {picked}"
    print(f"Caso OK: 6 eventi consecutivi si distribuiscono deterministicamente su tutti i 9 controlli in round-robin (least-used poi id) -> {expected_picks}")

    r7 = engine9.match(event_id="EVT9-7", event_row=127, event_direction="BUY",
                       event_features={"volatility_state": "HIGH"}, control_pool=pool9,
                       control_row_by_id=row9, control_direction_by_id=dir9, control_features_by_id=feat9)
    assert r7["status"] == "REJECTED_INSUFFICIENT_POOL"
    print(f"Caso OK: dopo che TUTTI i 9 controlli hanno raggiunto il tetto (2), il 7-esimo evento e' correttamente rifiutato: {r7['status']}")

    report9 = engine9.reuse_usage_report()
    assert report9["max_reuse_observed"] == 2 and report9["n_controls_used"] == 9
    print(f"Caso OK: reuse_usage_report -> {report9} (nessun controllo ha MAI superato il tetto=2).")

    # Stabilita': stesso pool, ORDINE shuffled -> stesso risultato (nessuna dipendenza implicita dall'ordine del dataframe).
    import random as _random
    engine_shuffled = BaselineEngineV4(match_dimensions=["volatility_state"], k=3, split_boundaries=boundaries, minimum_control_count=3)
    shuffled_pool = list(pool9)
    _random.Random(7).shuffle(shuffled_pool)
    r_shuffled = engine_shuffled.match(event_id="EVT9-SHUF", event_row=120, event_direction="BUY",
                                       event_features={"volatility_state": "HIGH"}, control_pool=shuffled_pool,
                                       control_row_by_id=row9, control_direction_by_id=dir9, control_features_by_id=feat9)
    assert sorted(m["control_id"] for m in r_shuffled["matches"]) == [100, 102, 104]
    print(f"Caso OK: pool in ordine shuffled {shuffled_pool} -> stesso risultato deterministico [100, 102, 104] (nessuna dipendenza dall'ordine di input).")

    # Distanza numerica sempre prioritaria sul reuse: un controllo piu' vicino MA gia' riusato batte uno
    # piu' lontano MAI usato - il reuse e' SOLO un tie-break, mai un sostituto della metrica di match dichiarata.
    engine_dist = BaselineEngineV4(match_dimensions=["proximity"], k=1, split_boundaries=boundaries, minimum_control_count=2)
    engine_dist.fit_normalization({50: {"proximity": 0.0}, 52: {"proximity": 10.0}})
    dist_pool = [50, 52]
    dist_row = {50: 50, 52: 52}
    dist_dir = {50: "BUY", 52: "BUY"}
    dist_feat = {50: {"proximity": 0.1}, 52: {"proximity": 9.9}}  # 50 vicinissimo all'evento, 52 lontano (entrambi in discovery: 0-200)
    engine_dist._reuse_ledger = ControlReuseLedger(max_control_reuse_per_run=5)
    engine_dist._reuse_ledger.register_controls_used([50, 50, 50])  # 50 gia' riusato 3 volte, 52 mai
    r_dist = engine_dist.match(event_id="EVT-DIST", event_row=10, event_direction="BUY",
                               event_features={"proximity": 0.0}, control_pool=dist_pool,
                               control_row_by_id=dist_row, control_direction_by_id=dist_dir, control_features_by_id=dist_feat)
    assert r_dist["matches"][0]["control_id"] == 50, "il controllo piu' vicino deve vincere anche se gia' riusato - la distanza resta primaria"
    print(f"Caso OK: controllo piu' vicino (50, gia' riusato 3x) batte quello piu' lontano (52, mai usato) -> {r_dist['matches'][0]['control_id']} (distanza sempre prioritaria sul reuse).")

    print("\nTutti i casi di BaselineEngineV4 (incl. Integrity Patch) verificati.")
