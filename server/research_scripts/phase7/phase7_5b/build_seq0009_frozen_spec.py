#!/usr/bin/env python3
"""Phase 7.5B - SEQ-0009 (MECH-18, SWEEP) Minimal Detector Formalization.

Congela il minimo indispensabile per sottoporre SEQ-0009 al Sequence
Structural Feasibility Gate (Phase 7.5A) - NIENTE oltre: nessun
contratto statistico, nessuna outcome surface, nessun BH.

Ordine di lavoro imposto (mai invertito): FORMALIZATION COMMIT (questo
script + il suo output) -> structural feasibility run (script separato,
phase7_5b/run_seq0009_structural_feasibility.py) -> RESULT COMMIT.
Se il gate fallisce, questi parametri NON vengono ritoccati per farlo
passare - una variante richiederebbe una nuova identita'/preregistrazione.

Tutti i numeri riusati da policy Phase 7 gia' esistenti (baseline_
contract_v4.json: k=5, minimum_control_count=20; minimum_evidence_
gates.json: n_nominal_minimum=30) sono dichiarati come tali - non
scelte specifiche per SEQ-0009. episode_gap_rule e natural_horizon
sono invece derivati ex-novo dalla scala temporale/meccanica DI QUESTO
meccanismo (SWEEP), mai copiati da SEQ-0015 (fenomeno diverso).

NESSUN dato di outcome viene letto qui - solo bar OHLC e feature di
stato CAUSAL_SAFE (market_state_dataset_p71.csv), mai outcomes_v1.csv/
outcome_surface_v3.py."""
import os
import sys

import pandas as pd

PHASE75B_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE75B_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE75B_DIR, "..", "..", "..", ".."))
PHASE71_DATA = os.path.join(PHASE7_DIR, "phase7_1", "data")

sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
sys.path.insert(0, os.path.join(PHASE7_DIR, "phase7_1"))
from canonical_utils import wrap_with_provenance, save_json, load_json, file_sha256, canonical_sha256  # noqa: E402
from splits_p71 import SPLIT_BOUNDARIES_DATES, assign_split_p71  # noqa: E402

BARS_PATH = os.path.join(PHASE71_DATA, "xauusd_h4_bars_p71.csv")
STATE_PATH = os.path.join(PHASE71_DATA, "market_state_dataset_p71.csv")
EVENTS_META_PATH = os.path.join(PHASE71_DATA, "events_p71.meta.json")

DETECTOR_SOURCE_OPERATIVE = os.path.join(PHASE7_DIR, "phase7_1", "build_events_p71.py")
DETECTOR_SOURCE_REFERENCE = os.path.join(ROOT, "server", "research_scripts", "phase5", "build_events.py")


def compute_split_row_boundaries():
    """Row-index [start,end) per ciascuno split - stessi confini gia'
    materializzati per DATA in partition_manifest_v1.json/splits_p71.py,
    qui solo tradotti in row-index per BaselineEngineV4.split_boundaries."""
    bars = pd.read_csv(BARS_PATH, parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    bars["split"] = bars["bar_time_utc"].apply(assign_split_p71)
    boundaries = {}
    for name in SPLIT_BOUNDARIES_DATES:
        idx = bars.index[bars["split"] == name]
        assert (idx.max() - idx.min() + 1) == len(idx), f"split {name} non contiguo in row-index"
        boundaries[name] = [int(idx.min()), int(idx.max()) + 1]
    return boundaries, len(bars)


def compute_volatility_terciles_fit_on_discovery(discovery_row_range):
    """Terzili di atr_percentile A T-1 (mai a t - la barra t e' essa
    stessa la barra dello SWEEP, includerla nel proprio stato di
    matching sarebbe circolare - STESSA motivazione causale di SEQ-0015
    volatility_state_pre_burst, non lo stesso NUMERO di parametro
    copiato). Fit ESCLUSIVAMENTE su development_discovery."""
    state = pd.read_csv(STATE_PATH, parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    atr_pct_t_minus_1 = state["atr_percentile"].shift(1)
    start, end = discovery_row_range
    discovery_values = atr_pct_t_minus_1.iloc[start:end]
    assert discovery_values.isna().sum() == 0, "atr_percentile[t-1] ha NaN in development_discovery - da investigare"
    q1, q2 = discovery_values.quantile([1 / 3, 2 / 3]).tolist()
    return {"tercile_cutpoints_fit_on_discovery_only": {"q1_low_med": q1, "q2_med_high": q2},
            "labels": ["LOW", "MED", "HIGH"],
            "n_discovery_rows_used_for_fit": int(len(discovery_values))}


def main():
    split_boundaries, n_bars_total = compute_split_row_boundaries()
    discovery_range = tuple(split_boundaries["discovery"])
    tercile_spec = compute_volatility_terciles_fit_on_discovery(discovery_range)
    events_meta = load_json(EVENTS_META_PATH)

    detector_operative_hash = file_sha256(DETECTOR_SOURCE_OPERATIVE)
    detector_reference_hash = file_sha256(DETECTOR_SOURCE_REFERENCE)
    detector_parameters = {"sweep_lookback_n": 20}

    payload = {
        "sequence_family_id": "SEQFAM-SEQ0009-SWEEP-STRUCTURAL-V1",
        "sequence_ids": ["SEQ-0009"],
        "mechanism_id": "MECH-18",
        "phase": "Phase 7.5B - SEQ-0009 Minimal Detector Formalization",
        "scope_note": "SOLO formalizzazione strutturale per il Sequence Structural Feasibility Gate - "
                       "NESSUN contratto statistico/outcome surface/BH in questa fase.",

        "detector_provenance": {
            "operative_source_file": "server/research_scripts/phase7/phase7_1/build_events_p71.py",
            "operative_source_sha256": detector_operative_hash,
            "reference_source_file": "server/research_scripts/phase5/build_events.py",
            "reference_source_sha256": detector_reference_hash,
            "relationship": "build_events_p71.py e' una copia verbatim del blocco SWEEP di build_events.py "
                             "(stesso CFG['sweep_lookback_n']=20, stessa formula, stesso detector_provenance "
                             "string 'sweep_v1_range20') - solo i path I/O differiscono (dataset Phase 7 reale "
                             "xauusd_h4_bars_p71.csv invece del dataset Phase 5 originale). Verificato leggendo "
                             "entrambi i file riga per riga nel blocco SWEEP, non assunto dal nome del file.",
            "detector_version": "sweep_v1_range20",
            "parameters": detector_parameters,
            "parameters_hash": canonical_sha256(detector_parameters),
            "formula_high_sweep": "sw_hi = max(high[i-20:i]) (slice Python, ESCLUDE l'indice i); evento se "
                                   "high[i] > sw_hi AND close[i] < sw_hi",
            "formula_low_sweep": "sw_lo = min(low[i-20:i]) (slice Python, ESCLUDE l'indice i); evento se "
                                  "low[i] < sw_lo AND close[i] > sw_lo",
            "magnitude_high_sweep": "(high[i] - sw_hi) / atr[i]",
            "magnitude_low_sweep": "(sw_lo - low[i]) / atr[i]",
            "observation_point_declared_in_code": "bar_close",
            "events_csv": "server/research_scripts/phase7/phase7_1/data/events_p71.csv",
            "events_meta": "server/research_scripts/phase7/phase7_1/data/events_p71.meta.json",
            "events_meta_summary": {
                "n_events_total_all_families_all_splits": events_meta["payload"]["n_events_total"]
                                                            if "payload" in events_meta else events_meta.get("n_events_total"),
                "n_sweep_total_all_splits": (events_meta["payload"]["counts_by_family"]["SWEEP"]
                                              if "payload" in events_meta else events_meta["counts_by_family"]["SWEEP"]),
                "note": "Conteggio grezzo SULL'INTERO dataset (tutti gli split) - NON e' il conteggio su "
                        "development_discovery, che verra' calcolato SOLO dal gate strutturale (script "
                        "separato, dopo questo formalization commit).",
            },
            "freeze_decision": "REUSED_UNCHANGED - il detector grezzo SWEEP e' riusabile cosi' com'e', senza "
                                "alcuna modifica, come raw event detector per SEQ-0009: causale (verificato "
                                "sotto), gia' congelato in Phase 5, gia' rieseguito identico sul dataset Phase 7 "
                                "reale (build_events_p71.py). NESSUNA incompatibilita' trovata - non e' stato "
                                "necessario correggere il detector guardando la sua firing geometry.",
        },

        "causal_verification": {
            "inputs_used_at_decision_time_for_row_i": [
                "high[i], low[i], close[i] (la barra CORRENTE - nota: il suo intrabar high/low e' gia' "
                "interamente noto a close(i), nessun dato futuro)",
                "high[i-20:i], low[i-20:i] (20 barre PRECEDENTI, indice i ESPLICITAMENTE escluso dallo slice)",
                "atr[i] (Wilder ATR fino e incluso il bar i - usato SOLO per normalizzare la magnitude "
                "riportata, MAI per la soglia di rilevazione, che confronta prezzi grezzi non normalizzati)",
            ],
            "verified_no_lookahead": "sw_hi/sw_lo sono calcolati SOLO su barre [i-20, i) - la barra i stessa e' "
                                      "esclusa dal proprio riferimento per costruzione dello slice Python "
                                      "(high[i-20:i] si ferma all'indice i-1). Nessun dato con indice >i entra "
                                      "nella detection. Verificato leggendo il codice sorgente, non assunto.",
            "note_on_atr_i_vs_atr_i_minus_1": "A differenza di SEQ-0015 (dove ATR_t e' usato per la soglia e "
                                               "genera un problema di auto-diluizione, risolto con ATR_{t-1} "
                                               "per la SOGLIA), qui atr[i] e' usato SOLO per normalizzare la "
                                               "MAGNITUDE riportata (un campo diagnostico), non per la soglia "
                                               "di detection stessa (che confronta high[i]/low[i]/close[i] "
                                               "direttamente contro sw_hi/sw_lo, senza normalizzazione). Nessun "
                                               "problema di auto-diluizione analogo a SEQ-0015 esiste qui.",
            "observation_cutoff": "close(t) - il detector richiede high[t]/low[t]/close[t], tutti noti a close(t).",
        },

        "event_definition": {
            "event_a": "barra H4 t tale che [HIGH sweep: high[t] > rolling_high_20[t] AND close[t] < "
                       "rolling_high_20[t]] OPPURE [LOW sweep: low[t] < rolling_low_20[t] AND close[t] > "
                       "rolling_low_20[t]], dove rolling_high_20[t]=max(high[t-20:t]), "
                       "rolling_low_20[t]=min(low[t-20:t]) (entrambi escludono la barra t).",
            "observation_cutoff_index": "close(t)",
            "transition_complete_index": "close(t) - nessuna fase di transizione separata (stesso pattern di "
                                          "MOMENTUM_BURST/SEQ-0015: l'evento e' gia' completo alla propria "
                                          "barra di osservazione).",
            "prediction_start_index": "close(t), coincide con transition_complete_index per costruzione.",
            "outcome_window_start_index": "t+1 - NESSUN prezzo con indice <=t entrera' nel calcolo "
                                           "dell'outcome (outcome NON calcolato in questa fase - dichiarato "
                                           "qui solo come contratto per una futura Phase 7.5B/outcome).",
            "ambiguous_double_sweep_same_bar_rule": "Se una barra soddisfa SIMULTANEAMENTE la condizione "
                "HIGH-sweep e LOW-sweep (wick oltre entrambi gli estremi rolling nella stessa barra, poi "
                "richiusura fra i due livelli), la barra e' ESCLUSA dal sequence_event set di SEQ-0009 - "
                "evento composto/ambiguo, non modellato dalla semantica a singola direzione per-evento di "
                "questa formalizzazione minimale. Regola dichiarata EX-ANTE (prima di verificarne la "
                "frequenza) - verificata occorrere su 2/641 barre SWEEP (0.31%) sull'INTERO dataset Phase 7 "
                "(righe 1472 e 4305, conteggio strutturale su row_index - nessun outcome coinvolto).",
            "isolated_from_reclaim": "SEQ-0009 valuta il SOLO SWEEP, MAI condizionato sul verificarsi o meno "
                "di un RECLAIM successivo (famiglia di eventi distinta in build_events.py/build_events_p71.py, "
                "gia' analizzata come prerequisito del claim RECLAIM refutato in Phase 7.1 - vedi "
                "failure_memory_relation=RELATED_TO_PREVIOUS_FAILURE in market_sequence_registry_v1.json per "
                "SEQ-0009). Condizionare su RECLAIM renderebbe questo un test diverso (interazione SWEEP x "
                "RECLAIM), fuori scope di questa formalizzazione minimale.",
        },

        "event_direction_policy": "PER_EVENT_DIRECTION",
        "direction_derivation": {
            "source_field": "swept_side (gia' emesso dal detector - 'HIGH' o 'LOW' - non ricalcolato qui)",
            "mapping": {"HIGH": "SELL", "LOW": "BUY"},
            "rationale": "Coerente con la convenzione di segno GIA' USATA da ogni altro detector in "
                         "build_events.py/build_events_p71.py: direction=+1 = bias rialzista (BUY), "
                         "direction=-1 = bias ribassista (SELL) - verificato leggendo il codice (VOLATILITY_"
                         "EXPANSION/DISPLACEMENT/BREAKOUT/PULLBACK usano tutti la stessa convenzione). Per "
                         "SWEEP: sw_hi swept poi richiuso sotto (direction=-1 nel codice) codifica l'ipotesi "
                         "'rigetto del livello superiore -> aspettativa ribassista' (liquidity-grab-then-"
                         "reversal, il meccanismo causale dichiarato per MECH-18 in market_sequence_registry_"
                         "v1.json: 'prezzo eccede brevemente il livello... poi richiuso all'interno del "
                         "livello originale'); sw_lo swept poi richiuso sopra (direction=+1) l'ipotesi "
                         "opposta. Derivata dalla semantica del meccanismo (rifiuto del livello), MAI da "
                         "alcun outcome storico - nessun dato di outcome e' stato letto per questa decisione.",
            "no_event_handling": "Non esiste un caso NO_EVENT/doji esplicito per SWEEP (a differenza di "
                                  "MOMENTUM_BURST/SEQ-0015) - l'evento e' gia' definito da una condizione "
                                  "booleana composta (wick-oltre AND richiusura-dentro), non esiste uno stato "
                                  "intermedio ambiguo da escludere separatamente oltre al caso double-sweep "
                                  "gia' trattato sopra.",
        },

        "episode_gap_rule": 2,
        "episode_rule_rationale": "MECCANICO e SPECIFICO al meccanismo SWEEP - NON copiato da SEQ-0015 (gap=3, "
            "fenomeno diverso: burst di volatilita' pluri-barra). Il riferimento di uno SWEEP "
            "(rolling_high_20/rolling_low_20) si sposta di UNA barra ad ogni step (esce la barra piu' vecchia, "
            "entra quella nuova) - due SWEEP flag sullo STESSO lato a distanza <=2 barre sono quasi certamente "
            "reazioni alla STESSA zona di liquidita' ancora in fase di rigetto (es. un primo wick-e-richiusura "
            "seguito da un secondo tentativo di rottura 1-2 barre dopo, prima che il prezzo si allontani "
            "decisamente dal livello) - non due raid indipendenti. Un gap piu' ampio implica che il rolling "
            "window si e' gia' spostato abbastanza da rendere il livello di riferimento materialmente diverso.",
        "overlap_policy": "COLLAPSE_TO_FIRST",
        "overlap_policy_rationale": "Stessa convenzione anti-cherry-pick gia' in uso in "
            "sequence_episode_engine.py (riusata senza modifiche) - la prima barra dell'espansione "
            "rappresenta l'episodio, mai quella con l'esito migliore (nessun outcome comunque disponibile in "
            "questa fase).",

        "proposed_natural_horizon": 40,
        "natural_horizon_rationale": "Derivato dalla scala temporale del MECCANISMO (liquidity-sweep-poi-"
            "reversal): un'ipotesi di rigetto/inversione su H4 e' tipicamente attesa risolversi entro un "
            "orizzonte multi-giorno (40 barre H4 = 6.7 giorni di trading) - lo stesso ordine di grandezza "
            "gia' indipendentemente giustificato per altri meccanismi di reversal/continuazione su H4 in "
            "questo progetto (H006/RECLAIM, SEQ-0015), riusato qui come CONVENZIONE GENERALE di progetto per "
            "l'orizzonte primario H4 - non perche' 'gia' usato altrove' meccanicamente, ma perche' lo stesso "
            "ordine di grandezza temporale (giorni, non ore ne' mesi) si applica indipendentemente al "
            "meccanismo SWEEP. NON ottimizzato guardando alcun risultato di SEQ-0009 (nessun evento SEQ-0009 "
            "e' stato ancora contato su development_discovery al momento di questa decisione).",

        "proposed_outcome_overlap_embargo_bars": 39,
        "embargo_derivation": "natural_horizon - 1 = 40 - 1 = 39 (STESSA formula matematica di SEQ-0015: "
            "outcome window [t+1, t+natural_horizon], due eventi a distanza d hanno outcome window sovrapposte "
            "se e solo se d<natural_horizon, quindi l'ultimo d che sovrappone e' natural_horizon-1). Non e' "
            "una scelta indipendente - e' VINCOLATA dalla formula una volta fissato natural_horizon, non "
            "scelta per massimizzare independent_units.",

        "matching_spec": {
            "match_dimensions": ["volatility_state_pre_event"],
            "match_dimensions_rationale": "Dimensione minima giustificata (baseline_contract_v4.json, sez. "
                "overmatching/undermatching: 'iniziare con il set minimo di dimensioni giustificate'). La "
                "magnitude dello SWEEP e' gia' ATR-normalizzata (stessa logica del burst_ratio di SEQ-0015) - "
                "il regime di volatilita' pre-evento (terzile di atr_percentile A T-1, STESSA motivazione "
                "causale di SEQ-0015 volatility_state_pre_burst - la barra t e' essa stessa l'evento, "
                "includerla nel proprio stato di matching sarebbe circolare) e' l'asse di contesto piu' "
                "direttamente giustificato dal meccanismo. trend_state ESCLUSO in questa formalizzazione "
                "minimale: a differenza di SEQ-0015 (dove il trend pre-burst e' concettualmente distinto "
                "dalla direzione dell'espansione), per SWEEP la direzione del setup e' GIA' derivata dal lato "
                "swept (HIGH/LOW) - aggiungere trend_state aumenterebbe i gradi di liberta' del matching "
                "senza una giustificazione causale distinta immediatamente evidente per il minimo "
                "indispensabile richiesto in questa fase (potra' essere aggiunto in una formalizzazione "
                "futura con propria giustificazione esplicita, non ora, e non per far passare il gate).",
            "k": 5,
            "k_rationale": "Convenzione generale di progetto, dichiarata in baseline_contract_v4.json stesso: "
                "'il numero di nearest-neighbour gia' usato (k=5) in Phase 5.5/6' - non una scelta specifica "
                "per SEQ-0009.",
            "minimum_control_count": 20,
            "minimum_control_count_rationale": "Valore di default di baseline_contract_v4.json/"
                "BaselineEngineV4.MINIMUM_CONTROL_COUNT (POLICY_THRESHOLD, motivato nel contratto stesso) - "
                "riusato senza modifica, non una scelta specifica per SEQ-0009.",
            "max_control_reuse_per_run": 5,
            "max_control_reuse_per_run_rationale": "Stesso valore di k (5) - un singolo control bar non puo' "
                "contribuire a piu' matched-set di quanti neighbour vengono normalmente richiesti per un "
                "evento, stessa regola simmetrica gia' congelata per SEQ-0015 (Phase 7.4A Final Statistical "
                "Integrity Patch sez.5) - un tetto semplice e generale, non ottimizzato sui dati di questa "
                "family.",
            "state_feature_definitions": {
                "volatility_state_pre_event": {
                    "source_feature": "atr_percentile (feature_registry_v2.json: causal_safety_status="
                                       "CAUSAL_SAFE, leakage_risk=LOW, allowed_for_baseline=true)",
                    "definition": "terzile (LOW/MED/HIGH) di atr_percentile A T-1 (mai a t), terzili fittati "
                                   "ESCLUSIVAMENTE su development_discovery.",
                    "why_t_minus_1_not_t": "atr_percentile[t] include atr[t] nel proprio calcolo (percentile "
                                            "causale ma con 'valore corrente incluso', per definizione della "
                                            "feature in feature_registry_v2.json) - e la barra t e' essa "
                                            "stessa la barra dello SWEEP. Usare atr_percentile[t] per il "
                                            "matching-state sarebbe quindi parzialmente circolare (la stessa "
                                            "barra anomala contribuirebbe al proprio stato di matching) - "
                                            "stessa motivazione, non lo stesso numero, di SEQ-0015 "
                                            "volatility_state_pre_burst.",
                    "tercile_cutpoints_fit_on_discovery_only": tercile_spec["tercile_cutpoints_fit_on_discovery_only"],
                    "labels": tercile_spec["labels"],
                    "n_discovery_rows_used_for_fit": tercile_spec["n_discovery_rows_used_for_fit"],
                },
            },
            "control_pool_construction_policy": "Per un evento SEQ-0009 alla riga t: pool di controllo = "
                "tutte le barre nello STESSO split (discovery) ESCLUSE (1) la barra t stessa; (2) qualunque "
                "barra r con |r-t|<=exclusion_buffer_bars (=proposed_natural_horizon=40 - stessa formula/"
                "motivazione di SEQ-0015 control_exclusion_window: evita che un controllo condivida il tratto "
                "di prezzo usato per l'outcome dell'evento); (3) qualunque altra barra SEQ-0009 (SWEEP) dello "
                "STESSO episode_id. Altri eventi SWEEP di episodi DIVERSI (fuori dalla finestra di esclusione) "
                "SONO ammessi come controlli - stessa policy di SEQ-0015 (control_temporal_overlap_policy: "
                "impedire la sovrapposizione fra controlli diversi richiederebbe un problema di assegnazione "
                "globale congiunta, fuori scope per una family a poche dimensioni). Enforcement tecnico: "
                "BaselineEngineV4 (split_boundaries, gia' esistente) + esclusione manuale dell'exclusion_"
                "buffer nella costruzione del control_pool PRIMA della chiamata al gate (script separato).",
            "split_boundaries": split_boundaries,
            "split_boundaries_source": "server/research_scripts/phase7/phase7_1/splits_p71.py:"
                                        "SPLIT_BOUNDARIES_DATES (date) - qui tradotte in row-index sullo "
                                        "stesso dataset xauusd_h4_bars_p71.csv usato dal detector.",
        },

        "discovery_partition": {"partition_id": "development_discovery", "n_bars": discovery_range[1] - discovery_range[0]},
        "n_bars_total_dataset": n_bars_total,
        "minimum_evidence_gates": {"n_nominal_minimum": 30},
        "minimum_evidence_gates_source": "server/research_scripts/phase7/policies/minimum_evidence_gates.json "
                                          "- riusato senza modifica (n_nominal_minimum=30, gia' motivato li').",

        "detector_frozen": True,
        "detector_source_ref": "server/research_scripts/phase7/phase7_1/build_events_p71.py:SWEEP "
                                "(sweep_v1_range20)",
        "observation_timing": {
            "observation_cutoff": "close(t)",
            "prediction_start": "close(t)",
            "outcome_window_start": "t+1",
        },

        "no_rescue_clause": "Nessuna soglia, gate, dimensione di matching, episode_gap_rule, natural_horizon "
            "o outcome_overlap_embargo dichiarati in questo documento sara' modificata dopo aver visto il "
            "risultato del Sequence Structural Feasibility Gate (script separato, eseguito SOLO dopo il "
            "commit di questo file). Un verdetto NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY, NEEDS_MATCHING_"
            "FORMALIZATION o MATCHING_STRUCTURALLY_INFEASIBLE su SEQ-0009 con questi parametri non autorizza "
            "un secondo tentativo con parametri diversi sotto la stessa identita' - una variante richiederebbe "
            "una nuova sequence_family_id e una nuova preregistrazione, mai una modifica silenziosa di questa.",

        "no_nexus_outcome_data_accessed": True,
        "no_edge_discovery_performed": True,
        "no_statistical_contract_built": True,
        "seq0015_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
    }

    out_path = os.path.join(PHASE75B_DIR, "seq0009_frozen_structural_spec_v1.json")
    save_json(out_path, wrap_with_provenance(payload, "phase7/phase7_5b/build_seq0009_frozen_spec.py"))
    print(f"Scritto {out_path}")
    print(f"discovery split row range: {discovery_range} (n_bars={discovery_range[1] - discovery_range[0]})")
    print(f"volatility terciles (fit su discovery, atr_percentile a t-1): "
          f"{tercile_spec['tercile_cutpoints_fit_on_discovery_only']}")


if __name__ == "__main__":
    main()
