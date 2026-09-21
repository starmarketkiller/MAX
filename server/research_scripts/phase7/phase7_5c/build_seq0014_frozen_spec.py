#!/usr/bin/env python3
"""Phase 7.5C - SEQ-0014 (MECH-23, LOW_INFORMATION_STATE/HIGH_CHOP_RISK)
Minimal State-to-Event Formalization.

SEQ-0014 non e' naturalmente un evento puntuale ma uno STATO
(classificazione continua di regime). Questo script congela il minimo
indispensabile per trasformarlo in un event set sottoponibile al
Sequence Structural Feasibility Gate SENZA trasformare ogni barra
choppy in una falsa osservazione indipendente:

STATE (in_state[t], booleano, per-barra)
  -> STATE-ENTRY EVENT (event_a = prima barra della transizione
     False->True, MAI ogni barra dello stato)
  -> episode_gap_rule (secondo livello: assorbe il flicker vicino al
     confine del terzile, non una nuova regola di reset separata)

Ordine di lavoro imposto (mai invertito): FORMALIZATION COMMIT (questo
script + il suo output) -> structural feasibility run (script separato,
phase7_5c/run_seq0014_structural_feasibility.py) -> RESULT COMMIT.

NESSUN dato di outcome viene letto qui - solo bar OHLC e feature di
stato CAUSAL_SAFE (market_state_dataset_p71.csv), mai outcomes_v1.csv/
outcome_surface_v3.py. Nessuna soglia scelta guardando future return,
conteggio eventi o independent-unit yield - solo la distribuzione
generale della feature su development_discovery (stesso principio gia'
usato per SEQ-0009/SEQ-0015: terzili fit su discovery, congelati PRIMA
di calcolare qualunque evento)."""
import os
import sys

import pandas as pd

PHASE75C_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE75C_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE75C_DIR, "..", "..", "..", ".."))
PHASE71_DATA = os.path.join(PHASE7_DIR, "phase7_1", "data")

sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
sys.path.insert(0, os.path.join(PHASE7_DIR, "phase7_1"))
from canonical_utils import wrap_with_provenance, save_json, file_sha256, canonical_sha256  # noqa: E402
from splits_p71 import SPLIT_BOUNDARIES_DATES, assign_split_p71  # noqa: E402

BARS_PATH = os.path.join(PHASE71_DATA, "xauusd_h4_bars_p71.csv")
STATE_PATH = os.path.join(PHASE71_DATA, "market_state_dataset_p71.csv")
DETECTOR_SOURCE = os.path.join(PHASE75C_DIR, "seq0014_state_entry_detector.py")


def compute_split_row_boundaries():
    bars = pd.read_csv(BARS_PATH, parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    bars["split"] = bars["bar_time_utc"].apply(assign_split_p71)
    boundaries = {}
    for name in SPLIT_BOUNDARIES_DATES:
        idx = bars.index[bars["split"] == name]
        assert (idx.max() - idx.min() + 1) == len(idx), f"split {name} non contiguo in row-index"
        boundaries[name] = [int(idx.min()), int(idx.max()) + 1]
    return boundaries, len(bars)


def compute_tercile_cutpoints(series_values, discovery_row_range):
    start, end = discovery_row_range
    discovery_values = series_values.iloc[start:end]
    assert discovery_values.isna().sum() == 0, "NaN in development_discovery - da investigare"
    q1, q2 = discovery_values.quantile([1 / 3, 2 / 3]).tolist()
    return {"tercile_cutpoints_fit_on_discovery_only": {"q1_low_med": q1, "q2_med_high": q2},
            "labels": ["LOW", "MED", "HIGH"], "n_discovery_rows_used_for_fit": int(len(discovery_values))}


def main():
    split_boundaries, n_bars_total = compute_split_row_boundaries()
    discovery_range = tuple(split_boundaries["discovery"])

    state = pd.read_csv(STATE_PATH, parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    de_tercile_spec = compute_tercile_cutpoints(state["directional_efficiency"], discovery_range)
    atr_pct_t_minus_1 = state["atr_percentile"].shift(1)
    vol_tercile_spec = compute_tercile_cutpoints(atr_pct_t_minus_1, discovery_range)

    detector_source_hash = file_sha256(DETECTOR_SOURCE) if os.path.exists(DETECTOR_SOURCE) else None
    detector_parameters = {"directional_efficiency_lookback_bars": 20,
                            "state_tercile": "LOW",
                            "tercile_cutpoints_fit_on_discovery_only": de_tercile_spec[
                                "tercile_cutpoints_fit_on_discovery_only"]}

    payload = {
        "sequence_family_id": "SEQFAM-SEQ0014-LOWINFO-STATE-STRUCTURAL-V1",
        "sequence_ids": ["SEQ-0014"],
        "mechanism_id": "MECH-23",
        "phase": "Phase 7.5C - SEQ-0014 Minimal State-to-Event Formalization",
        "scope_note": "SOLO formalizzazione strutturale per il Sequence Structural Feasibility Gate - "
                       "NESSUN contratto statistico/outcome surface/BH in questa fase.",

        "central_problem_note": "SEQ-0014 non e' un evento puntuale ma uno STATO (classificazione continua di "
            "regime, per-barra). Se ogni barra con directional_efficiency in tercile LOW venisse trattata come "
            "un evento indipendente, N barre consecutive nello stesso regime produrrebbero N osservazioni "
            "false - non N osservazioni indipendenti. Questo spec formalizza esplicitamente la trasformazione "
            "STATE -> STATE-ENTRY EVENT (sec.1 della richiesta Phase 7.5C) PRIMA di qualunque conteggio.",

        "feature_inspection": {
            "directional_efficiency": {
                "role": "STATE-DEFINING (detector feature) - MAI usata anche come dimensione di matching per "
                        "questo stesso candidato (vedi matching_spec.tautology_avoidance_note sotto).",
                "definition": "|close[i]-close[i-20]| / sum(|close.diff()|, 20 barre) - Kaufman Efficiency Ratio "
                               "(feature_registry_v2.json).",
                "lookback_bars": 20,
                "observation_time": "bar_close",
                "causal_safety_status": "CAUSAL_SAFE", "leakage_risk": "LOW",
                "allowed_for_discovery": True, "allowed_for_baseline": True,
                "missingness_in_discovery": 0,
                "source": "server/research_scripts/phase7/phase7_1/data/market_state_dataset_p71.csv",
            },
            "atr_percentile": {
                "role": "MATCHING/CONTEXT feature (baseline_matching) - asse DISTINTO (livello di volatilita', "
                        "non efficienza direzionale) usato SOLO per il matching, MAI per definire lo stato.",
                "definition": "percentile causale (rolling 252, valore corrente incluso) dell'ATR "
                               "(feature_registry_v2.json).",
                "observation_time": "bar_close",
                "causal_safety_status": "CAUSAL_SAFE", "leakage_risk": "LOW",
                "allowed_for_discovery": True, "allowed_for_baseline": True,
                "missingness_in_discovery_t_minus_1": 0,
            },
            "variance_ratio_proxy": {
                "role": "CONSIDERATA ma NON USATA come feature aggiuntiva di stato - proxy concettualmente "
                        "sovrapposto a directional_efficiency (entrambi misurano 'quanto il prezzo si muove in "
                        "modo persistente vs rumoroso'). Impilare due filtri di choppiness senza una "
                        "giustificazione causale distinta stringerebbe arbitrariamente la definizione di stato "
                        "('poche dimensioni, pochi gradi di liberta'' - stesso principio gia' applicato in "
                        "SEQ-0015/SEQ-0009). Nessuna feature nuova inventata.",
                "definition": "Var(ritorno 4 barre, 60 barre trailing) / (4*Var(ritorno 1 barra, 60 barre "
                               "trailing)) (feature_registry_v2.json).",
                "causal_safety_status": "CAUSAL_SAFE", "leakage_risk": "LOW",
            },
        },

        "state_definition": {
            "state_id": "LOW_INFORMATION_STATE",
            "condition": "directional_efficiency[t] nel terzile LOW della propria distribuzione, terzili "
                          "fittati ESCLUSIVAMENTE su development_discovery.",
            "tercile_cutpoints_fit_on_discovery_only": de_tercile_spec["tercile_cutpoints_fit_on_discovery_only"],
            "n_discovery_rows_used_for_fit": de_tercile_spec["n_discovery_rows_used_for_fit"],
            "rationale": "Il terzile (non una soglia fissa arbitraria come 0.2/0.3) e' la stessa convenzione "
                         "gia' in uso nel progetto per bucket di regime (es. volatility_state_pre_burst di "
                         "SEQ-0015) - relativo alla distribuzione REALE della feature su questo mercato/"
                         "timeframe, non un numero scelto guardando il risultato. Corrisponde direttamente alla "
                         "descrizione MECH-23 in market_sequence_registry_v1.json: 'rapporto volatilita'/"
                         "deriva direzionale (o efficiency ratio) sotto una soglia bassa'.",
            "not_tuned_on": "Nessuna soglia scelta guardando future return, conteggio eventi o independent-"
                            "unit yield - SOLO la distribuzione di directional_efficiency su development_"
                            "discovery, calcolata PRIMA di costruire qualunque evento.",
        },

        "state_entry_event_definition": {
            "event_a": "prima barra t della transizione in_state[t-1]=False -> in_state[t]=True (0->1). "
                       "MAI ogni barra con in_state=True - una corsa di N barre consecutive nello stesso "
                       "regime produce UN SOLO evento (la prima barra della corsa), non N.",
            "exit_definition": "in_state[t]=True -> in_state[t]=False (1->0) - transizione implicita, MAI "
                                "contata come un evento proprio (solo l'ENTRATA e' un sequence_event).",
            "re_entry_and_minimum_reset_rule": "NESSUNA finestra di reset separata e inventata qui - una "
                "ri-entrata dopo una breve uscita (flicker vicino al confine del terzile) e' gestita "
                "ESCLUSIVAMENTE dal secondo livello gia' esistente (episode_gap_rule/build_event_and_episode_"
                "views, riusato senza modifiche) - due eventi di entrata a distanza <=episode_gap_rule sono "
                "collassati nello stesso episodio. Decisione esplicita (sec.4 della richiesta): NON costruire "
                "un meccanismo di reset indipendente che duplicherebbe la stessa funzione gia' svolta da "
                "episode_gap_rule.",
            "observation_cutoff_index": "close(t) - directional_efficiency[t] e' interamente noto a close(t).",
            "prediction_start_index": "close(t)",
            "outcome_window_start_index": "t+1 - nessun prezzo con indice <=t entrera' nel calcolo "
                                           "dell'outcome (outcome NON calcolato in questa fase).",
        },

        "event_direction_policy": "NON_DIRECTIONAL",
        "direction_rationale": "MECH-23 non e' un candidato direzionale (market_sequence_registry_v1.json: "
            "'Non un candidato direzionale - famiglia LOW_INFORMATION_STATE/HIGH_CHOP_RISK, l'obiettivo e' "
            "identificare QUANDO NON tradare, non un edge direzionale'). Nessuna direzione BUY/SELL creata "
            "artificialmente - ogni riga riceve 'BOTH' per costruzione (DIRECTION_POLICY_NON_DIRECTIONAL, "
            "dichiarata esplicitamente, mai un default silenzioso).",

        "episode_gap_rule": 5,
        "episode_rule_rationale": "MECCANICO e SPECIFICO a questo meccanismo - NON copiato da SEQ-0009 "
            "(gap=2, rolling reference shift) ne' da SEQ-0015 (gap=3, burst pluri-barra). directional_"
            "efficiency ha un lookback di 20 barre - due barre a distanza <=5 (25% del lookback) condividono "
            "ANCORA piu' del 75% della stessa finestra di 20 barre sottostante, quindi un breve flicker "
            "sotto/sopra il confine del terzile a quella distanza e' quasi certamente rumore di misura sulla "
            "STESSA porzione di prezzo, non un cambio di regime genuino. Un gap piu' ampio implica che la "
            "finestra si e' gia' rinnovata per piu' di un quarto, riflettendo una storia di prezzo "
            "materialmente diversa.",
        "overlap_policy": "COLLAPSE_TO_FIRST",
        "overlap_policy_rationale": "Stessa convenzione anti-cherry-pick gia' in uso in "
            "sequence_episode_engine.py (riusata senza modifiche) - la prima barra dell'espansione "
            "rappresenta l'episodio (qui: la prima barra della RI-entrata piu' antica nel cluster).",

        "proposed_natural_horizon": 20,
        "natural_horizon_rationale": "Derivato dalla scala temporale del MECCANISMO stesso, non da una "
            "convenzione di progetto generica: directional_efficiency e' calcolata su un lookback di 20 barre "
            "- la domanda scientifica (\"cosa succede DOPO l'ingresso in un regime low-information/choppy?\") "
            "e' valutata su una finestra futura della STESSA ampiezza della finestra usata per rilevare il "
            "regime (simmetria diagnostica: confrontare 20 barre passate 'choppy' con 20 barre future). "
            "Deliberatamente DIVERSO dal default di 40 barre usato per SEQ-0009/SEQ-0015 (meccanismi di "
            "rigetto/rottura con propria scala temporale multi-giorno, non applicabile qui) - non ottimizzato "
            "guardando alcun conteggio di eventi SEQ-0014.",

        "proposed_outcome_overlap_embargo_bars": 19,
        "embargo_derivation": "natural_horizon - 1 = 20 - 1 = 19 (stessa formula matematica di SEQ-0009/"
            "SEQ-0015: outcome window [t+1, t+natural_horizon], due eventi a distanza d hanno outcome window "
            "sovrapposte se e solo se d<natural_horizon). Vincolato dalla formula, non una scelta indipendente.",

        "matching_spec": {
            "match_dimensions": ["volatility_state_pre_entry"],
            "tautology_avoidance_note": "sec.8 della richiesta - VERIFICATO ESPLICITAMENTE: la feature che "
                "DEFINISCE lo stato (directional_efficiency) e' DIVERSA dalla feature usata per il matching "
                "(atr_percentile) - un asse misura l'efficienza/persistenza direzionale, l'altro il LIVELLO di "
                "volatilita' (concettualmente distinti, redundancy_group=UNIQUE per entrambi in "
                "feature_registry_v2.json - non ridondanti). Se avessimo matchato su directional_efficiency "
                "stesso (o un suo derivato), evento e controlli sarebbero stati tautologicamente simili "
                "proprio sulla dimensione che il candidato sta testando (double_use_risk, gia' segnalato "
                "esplicitamente in feature_registry_v2.json per ENTRAMBE le feature).",
            "match_dimensions_rationale": "Dimensione minima giustificata (baseline_contract_v4.json: "
                "'iniziare con il set minimo di dimensioni giustificate'). volatility_state_pre_entry (terzile "
                "di atr_percentile a T-1, fit solo su discovery) e' l'asse di contesto standard gia' "
                "utilizzato per SEQ-0009/SEQ-0015, qui riusato perche' rappresenta un contesto di mercato "
                "genuinamente ORTOGONALE alla definizione dello stato (non perche' 'gia' usato altrove').",
            "k": 5, "k_rationale": "Convenzione generale di progetto (baseline_contract_v4.json: 'il numero di "
                "nearest-neighbour gia' usato (k=5) in Phase 5.5/6') - non una scelta specifica per SEQ-0014.",
            "minimum_control_count": 20,
            "minimum_control_count_rationale": "Default di baseline_contract_v4.json/BaselineEngineV4."
                "MINIMUM_CONTROL_COUNT - riusato senza modifica.",
            "max_control_reuse_per_run": 5,
            "max_control_reuse_per_run_rationale": "Stesso valore di k (5), stessa regola simmetrica generale "
                "gia' congelata per SEQ-0009/SEQ-0015 - non ottimizzata sui dati di questa family.",
            "state_feature_definitions": {
                "volatility_state_pre_entry": {
                    "source_feature": "atr_percentile (feature_registry_v2.json: CAUSAL_SAFE, LOW leakage_risk, "
                                       "allowed_for_baseline=true)",
                    "definition": "terzile (LOW/MED/HIGH) di atr_percentile A T-1 (mai a t - stessa motivazione "
                                   "causale gia' usata per SEQ-0009/SEQ-0015: la barra t e' la barra "
                                   "dell'entrata nello stato, includerla nel proprio contesto di matching "
                                   "sarebbe parzialmente circolare), terzili fittati ESCLUSIVAMENTE su "
                                   "development_discovery.",
                    "tercile_cutpoints_fit_on_discovery_only": vol_tercile_spec["tercile_cutpoints_fit_on_discovery_only"],
                    "labels": vol_tercile_spec["labels"],
                    "n_discovery_rows_used_for_fit": vol_tercile_spec["n_discovery_rows_used_for_fit"],
                },
            },
            "control_pool_construction_policy": "Per un evento SEQ-0014 (state-entry) alla riga t: pool di "
                "controllo = tutte le barre nello STESSO split (discovery) ESCLUSE (1) la barra t stessa; (2) "
                "qualunque barra r con |r-t|<=exclusion_buffer_bars (=proposed_natural_horizon=20, stessa "
                "formula/motivazione gia' usata per SEQ-0009: evita che un controllo condivida il tratto di "
                "prezzo usato per l'outcome dell'evento); (3) qualunque altra barra SEQ-0014 (state-entry) "
                "dello STESSO episode_id. Altre entrate di episodi DIVERSI (fuori dalla finestra di "
                "esclusione) SONO ammesse come controlli - stessa policy gia' usata per SEQ-0009.",
            "split_boundaries": split_boundaries,
            "split_boundaries_source": "server/research_scripts/phase7/phase7_1/splits_p71.py:"
                                        "SPLIT_BOUNDARIES_DATES (date) - tradotte in row-index sullo stesso "
                                        "dataset xauusd_h4_bars_p71.csv.",
        },

        "discovery_partition": {"partition_id": "development_discovery", "n_bars": discovery_range[1] - discovery_range[0]},
        "n_bars_total_dataset": n_bars_total,
        "minimum_evidence_gates": {"n_nominal_minimum": 30},
        "minimum_evidence_gates_source": "server/research_scripts/phase7/policies/minimum_evidence_gates.json "
                                          "- riusato senza modifica.",

        "detector_frozen": True,
        "detector_source_ref": "server/research_scripts/phase7/phase7_5c/seq0014_state_entry_detector.py "
                                "(nuovo - nessun detector MECH-23/SEQ-0014 preesisteva in Phase 5/7.1)",
        "detector_provenance": {
            "detector_version": "seq0014_state_entry_detector.py@v1",
            "parameters": detector_parameters,
            "parameters_hash": canonical_sha256(detector_parameters),
            "source_file": "server/research_scripts/phase7/phase7_5c/seq0014_state_entry_detector.py",
            "source_sha256": detector_source_hash,
            "freeze_decision": "NUOVO DETECTOR MINIMALE - nessun detector MECH-23/SEQ-0014 esisteva in Phase "
                                "5/7.1 da riusare (confermato: nessun file corrispondente trovato). Scritto ORA "
                                "come il minimo indispensabile (tercile fit + regola di transizione "
                                "0->1), congelato PRIMA del gate.",
        },
        "observation_timing": {
            "observation_cutoff": "close(t)",
            "prediction_start": "close(t)",
            "outcome_window_start": "t+1",
        },

        "no_rescue_clause": "Nessuna soglia, gate, dimensione di matching, episode_gap_rule, natural_horizon "
            "o outcome_overlap_embargo dichiarati in questo documento sara' modificata dopo aver visto il "
            "risultato del Sequence Structural Feasibility Gate. Un verdetto non-FEASIBLE su SEQ-0014 con "
            "questi parametri non autorizza un secondo tentativo con parametri diversi sotto la stessa "
            "identita' - una variante richiederebbe una nuova sequence_family_id e una nuova preregistrazione.",

        "no_nexus_outcome_data_accessed": True,
        "no_edge_discovery_performed": True,
        "no_statistical_contract_built": True,
        "seq0015_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
        "seq0009_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
    }

    out_path = os.path.join(PHASE75C_DIR, "seq0014_frozen_structural_spec_v1.json")
    save_json(out_path, wrap_with_provenance(payload, "phase7/phase7_5c/build_seq0014_frozen_spec.py"))
    print(f"Scritto {out_path}")
    print(f"discovery split row range: {discovery_range} (n_bars={discovery_range[1] - discovery_range[0]})")
    print(f"directional_efficiency terciles (fit su discovery): "
          f"{de_tercile_spec['tercile_cutpoints_fit_on_discovery_only']}")
    print(f"atr_percentile[t-1] terciles (fit su discovery): "
          f"{vol_tercile_spec['tercile_cutpoints_fit_on_discovery_only']}")


if __name__ == "__main__":
    main()
