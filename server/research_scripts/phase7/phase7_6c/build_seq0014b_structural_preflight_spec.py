#!/usr/bin/env python3
"""Phase 7.6C - SEQ-0014B Structural Feasibility Preflight: SPEC COMMIT.

Congela, PRIMA di calcolare qualunque count reale, le decisioni nuove
richieste per questo preflight pooled (nessun outcome letto qui, nessuna
discovery). Riusa senza modifiche: la popolazione di setup (Phase 7.6B,
`fb52168`), il regime/timestamp contract (Phase 7.6B), i tercile cutpoint
di `directional_efficiency` (Phase 7.5C) e di `atr_percentile[t-1]`
(Phase 7.5C), il natural_horizon/embargo di progetto per meccanismi
reversal/continuation su H4 (40/39, gia' usato per SEQ-0009/SEQ-0015/
H006-RECLAIM), e l'infrastruttura di matching (`control_pool_by_event_row`,
gia' introdotta in Phase 7.5B per SEQ-0009).

Concern nuovo (sollevato dal reviewer dopo `fb52168`): un disegno pooled
non puo' verificare la geometria di ogni famiglia isolatamente - due
detector diversi possono scattare sulla stessa barra o a poche barre di
distanza, condividendo quasi tutto l'outcome futuro. Questo modulo
formalizza DUE livelli distinti:
  WITHIN-FAMILY  - geometria EVENT/EPISODE/INDEPENDENT_VIEW per ciascuna
                   delle 6 famiglie, con episode_gap_rule DERIVATO DAL
                   MECCANISMO di ciascun detector (mai copiato fra
                   meccanismi diversi - stessa disciplina gia' imposta in
                   Phase 7.5B per SWEEP, "NON copiato da SEQ-0015").
  CROSS-FAMILY   - un secondo passaggio di declustering applicato
                   all'UNIONE delle righe rappresentative indipendenti di
                   tutte e 6 le famiglie, con la stessa soglia di embargo
                   condivisa (39 barre) - un BREAKOUT e una DISPLACEMENT
                   entro 39 barre l'uno dall'altro condividono la finestra
                   di outcome futura esattamente come due eventi della
                   stessa famiglia.

Unita' di analisi: FAMILY-EVENT (non ROW-FIRST) - decisione motivata
dalla necessita' di preservare `setup_family_id` come variabile di
stratificazione per il contrasto CHOPPY-vs-TRENDING ENTRO la stessa
famiglia (sec.9 della richiesta), non dalla dimensione campionaria
risultante (mai calcolata prima di questa decisione).

Nessun outcome letto. Nessuna discovery. Nessun count reale calcolato in
questo script (rimandato al PREFLIGHT RESULT COMMIT separato, Task #46+)."""
import os
import sys

PHASE76C_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE76C_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE76C_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "fb52168fe2ff27f91abc8671b08992c56e654f4f"

SEQ0014B_SETUP_POP_PATH = os.path.join(PHASE7_DIR, "phase7_6b", "seq0014b_setup_population_spec_v1.json")
SEQ0014A_FROZEN_SPEC_PATH = os.path.join(PHASE7_DIR, "phase7_5c", "seq0014_frozen_structural_spec_v1.json")
SEQ0009_FROZEN_SPEC_PATH = os.path.join(PHASE7_DIR, "phase7_5b", "seq0009_frozen_structural_spec_v1.json")
PHASE71_RUN_RESULTS_PATH = os.path.join(PHASE7_DIR, "phase7_1", "data", "phase7_1_run_results.json") \
    if os.path.exists(os.path.join(PHASE7_DIR, "phase7_1", "data", "phase7_1_run_results.json")) \
    else os.path.join(PHASE7_DIR, "phase7_1", "phase7_1_run_results.json")


def build():
    setup_pop_doc = load_json(SEQ0014B_SETUP_POP_PATH)
    setup_pop = setup_pop_doc["payload"]
    seq0014a = load_json(SEQ0014A_FROZEN_SPEC_PATH)["payload"]
    seq0009 = load_json(SEQ0009_FROZEN_SPEC_PATH)["payload"]

    eligible_families = setup_pop["eligible_setup_families"]
    assert eligible_families == [
        "VOLATILITY_EXPANSION", "DISPLACEMENT", "BREAKOUT", "SWEEP", "COMPRESSION_RELEASE", "PULLBACK",
    ], "popolazione di setup diversa da quella congelata in fb52168 - non ri-derivare qui, verificare l'input."

    # ---- unita' di analisi: FAMILY-EVENT + cross-family dependence clustering obbligatorio ----
    unit_of_analysis_decision = {
        "option_A_row_first_unit": {
            "description": "Una riga di mercato (bar row_index) = una unita'. Se piu' famiglie scattano sulla "
                            "stessa riga, la riga viene taggata con l'INSIEME dei setup_family_id che vi hanno "
                            "sparato (un solo record per riga).",
            "pro": "Elimina per costruzione qualunque doppio conteggio della stessa realizzazione di mercato.",
            "contro_decisivo": "Distrugge 'setup_family_id' come variabile di STRATIFICAZIONE pulita: una riga "
                                "con BREAKOUT+DISPLACEMENT+VOLATILITY_EXPANSION diventerebbe un singolo record "
                                "multi-famiglia, rendendo impossibile il contrasto richiesto 'stessa "
                                "setup_family_id, CHOPPY vs TRENDING' per OGNUNA delle famiglie coinvolte senza "
                                "un secondo schema di disaggregazione ad-hoc - il problema che si voleva evitare "
                                "si ripresenterebbe comunque a valle.",
            "rejected": True,
        },
        "option_B_family_event_unit": {
            "description": "Ogni famiglia mantiene i propri record separati (un record per (setup_family_id, "
                            "row_index) coppia che soddisfa i criteri di eleggibilita' - direction!=0, "
                            "regime!=MED). La dipendenza cross-family NON viene ignorata: viene invece "
                            "modellata con un passaggio di declustering OBBLIGATORIO E SEPARATO, applicato "
                            "esclusivamente al calcolo della geometria POOLED (independent_units pooled), MAI "
                            "al calcolo within-family (che resta per-famiglia, gia' corretto per costruzione).",
            "pro": "Preserva setup_family_id come stratificazione pulita per OGNI famiglia (il contrasto "
                   "CHOPPY-vs-TRENDING resta sempre 'stessa famiglia' per costruzione) E rende conteggiabile "
                   "esplicitamente la sovrapposizione cross-family invece di nasconderla in un tag composito.",
            "selected": True,
        },
        "decision": "OPTION_B_FAMILY_EVENT_UNIT_WITH_MANDATORY_CROSS_FAMILY_DEPENDENCE_CLUSTERING",
        "decision_basis": "Basata sull'estimand MECH-23 (il contrasto richiesto e' sempre 'stessa "
                           "setup_family_id, CHOPPY vs TRENDING', mai cross-family - sec.9/10 della richiesta) "
                           "e sulla necessita' di preservare setup_family_id come variabile di stratificazione "
                           "- NON sulla dimensione campionaria risultante (nessun conteggio reale calcolato "
                           "prima di prendere questa decisione).",
        "decision_not_based_on_sample_size": True,
    }

    # ---- geometria condivisa (natural_horizon/embargo, comuni a tutte e 6 le famiglie) ----
    # RIUSATA senza modifiche dalla convenzione di progetto gia' esplicita in SEQ-0009
    # (seq0009_frozen_structural_spec_v1.json: "CONVENZIONE GENERALE di progetto per l'orizzonte
    # primario H4" per meccanismi reversal/continuation, stesso ordine di grandezza gia'
    # indipendentemente giustificato per H006/RECLAIM e SEQ-0015). Necessaria qui perche' il
    # declustering CROSS-FAMILY richiede una soglia di sovrapposizione dell'outcome window
    # UNICA (la sovrapposizione futura fra due setup di famiglie diverse e' funzione della sola
    # distanza in barre, non della famiglia - non avrebbe senso un embargo diverso per famiglia
    # quando si confrontano righe di famiglie diverse fra loro).
    shared_natural_horizon = seq0009["proposed_natural_horizon"]
    shared_embargo = seq0009["proposed_outcome_overlap_embargo_bars"]
    assert shared_natural_horizon == 40 and shared_embargo == 39

    # ---- episode_gap_rule per-famiglia, derivato dal meccanismo del detector (build_events_p71.py) ----
    # Principio (gia' imposto in Phase 7.5B per SWEEP): l'episode_gap_rule NON e' una costante di
    # progetto copiabile fra meccanismi diversi - deriva da COME il riferimento del detector si
    # muove barra per barra. Due classi meccaniche distinte identificate nell'inventario dei 6
    # detector eleggibili (build_events_p71.py):
    #  (a) confronto ISTANTANEO barra-per-barra contro la PROPRIA ATR di quella barra, nessun
    #      livello di riferimento persistente che si sposta nel tempo (VOLATILITY_EXPANSION,
    #      DISPLACEMENT) -> gap minimo (1): solo barre letteralmente adiacenti condividono la
    #      stessa realizzazione, non c'e' un "livello" che riappare identico su barre successive.
    #  (b) livello di riferimento ROLLING (massimo/minimo su una finestra di N barre che si
    #      sposta di 1 barra ad ogni step: BREAKOUT range_n=20, SWEEP sweep_lookback_n=20,
    #      PULLBACK pullback_trend_lookback=20) -> stessa classe meccanica di SWEEP (gia'
    #      congelato gap=2 in Phase 7.5B: "due SWEEP flag sullo STESSO lato a distanza <=2 barre
    #      sono quasi certamente reazioni alla STESSA zona di liquidita'") - stesso gap=2 riusato
    #      per BREAKOUT e PULLBACK per lo STESSO motivo meccanico (rolling extreme a 1 barra/step).
    #  (c) precondizione a finestra CONDIVISA: COMPRESSION_RELEASE richiede
    #      compression_min_bars=5 barre CONSECUTIVE di compression_percentile sotto soglia PRIMA
    #      del rilascio - due rilasci entro 5 barre l'uno dall'altro hanno finestre di
    #      precondizione necessariamente sovrapposte (condividono la maggioranza delle stesse
    #      barre di "coiling" sottostanti), quindi il gap naturale e' la lunghezza della
    #      precondizione stessa (5), non il range_n di un livello rolling.
    family_specific_episode_gap_rule = {
        "VOLATILITY_EXPANSION": {
            "value": 1,
            "detector_mechanism": "true_range[i] > vol_expansion_atr_mult * atr[i] - confronto ISTANTANEO "
                                   "barra-per-barra, nessun livello di riferimento persistente che si sposta "
                                   "nel tempo.",
            "rationale": "Senza un livello rolling condiviso, non esiste un meccanismo per cui barre a "
                         "distanza >1 possano riferirsi alla 'stessa' soglia in modo piu' stretto di quanto "
                         "non facciano gia' per costruzione (ciascuna barra e' confrontata solo con la "
                         "propria ATR) - solo barre adiacenti (distanza<=1) sono trattate come un'unica "
                         "esplosione di volatilita' continuata.",
        },
        "DISPLACEMENT": {
            "value": 1,
            "detector_mechanism": "abs(close[i]-open[i]) > displacement_atr_mult * atr[i] - stessa classe "
                                   "meccanica di VOLATILITY_EXPANSION (confronto istantaneo, nessun livello "
                                   "rolling).",
            "rationale": "Identica a VOLATILITY_EXPANSION - nessun riferimento persistente che giustifichi un "
                         "gap maggiore di 1.",
        },
        "BREAKOUT": {
            "value": 2,
            "detector_mechanism": "close[i] > max(high[i-21:i-1]) (range_n=20, con offset che esclude le "
                                   "ultime 2 barre) - livello di riferimento ROLLING che si sposta di 1 barra "
                                   "ad ogni step, stessa classe meccanica del detector SWEEP.",
            "rationale": "Stessa logica gia' congelata per SWEEP in Phase 7.5B (episode_rule_rationale): due "
                         "BREAKOUT sullo stesso lato entro <=2 barre sono quasi certamente reazioni allo "
                         "STESSO livello di rottura ancora in fase di conferma/ritest immediato, non due "
                         "rotture indipendenti - il rolling window si e' spostato troppo poco (1-2 barre) per "
                         "rendere il livello materialmente diverso.",
        },
        "SWEEP": {
            "value": seq0009["episode_gap_rule"],
            "detector_mechanism": "Identico al detector gia' formalizzato in SEQ-0009 (Phase 7.5B) - "
                                   "nessuna modifica.",
            "rationale": "RIUSATO SENZA RIDERIVARE: stesso identico detector (sweep_v1_range20), stesso "
                         "episode_gap_rule gia' congelato in seq0009_frozen_structural_spec_v1.json "
                         "(episode_rule_rationale: derivato dal meccanismo del rolling high/low a 20 barre "
                         "che si sposta di 1 barra/step) - ri-derivarlo qui produrrebbe lo stesso valore per "
                         "costruzione, ma il riuso diretto evita qualunque drift accidentale fra le due fasi.",
        },
        "COMPRESSION_RELEASE": {
            "value": 5,
            "detector_mechanism": "Richiede compression_min_bars=5 barre CONSECUTIVE di "
                                   "compression_percentile sotto compression_percentile_threshold=20.0 "
                                   "PRIMA del rilascio (tr[i] > vol_expansion_atr_mult * atr[i]) - "
                                   "precondizione a finestra condivisa, non un livello rolling di prezzo.",
            "rationale": "Due rilasci entro compression_min_bars=5 barre l'uno dall'altro hanno finestre di "
                         "precondizione (le 5 barre di compressione richieste prima di ciascun rilascio) "
                         "necessariamente sovrapposte per la maggior parte della loro estensione - "
                         "condividono lo stesso periodo di 'coiling' sottostante, non sono due episodi di "
                         "compressione indipendenti. Il gap naturale e' quindi la lunghezza della "
                         "precondizione stessa (5), il solo parametro del detector che descrive per quante "
                         "barre lo stato 'compresso' deve persistere.",
        },
        "PULLBACK": {
            "value": 2,
            "detector_mechanism": "trend_context = segno medio di ema_slope su pullback_trend_lookback=20 "
                                   "barre; retrace misurato contro l'estremo (max/min) sulla STESSA finestra "
                                   "rolling di 20 barre che si sposta di 1 barra ad ogni step - stessa classe "
                                   "meccanica di BREAKOUT/SWEEP (livello di riferimento rolling).",
            "rationale": "Stessa logica di BREAKOUT/SWEEP: due PULLBACK sullo stesso lato entro <=2 barre "
                         "condividono con altissima probabilita' lo stesso estremo rolling di riferimento e "
                         "lo stesso contesto di trend - non sono due ritracciamenti indipendenti.",
        },
    }
    assert family_specific_episode_gap_rule["SWEEP"]["value"] == 2

    within_family_geometry_rule = {
        "shared_across_all_6_families": {
            "natural_horizon": shared_natural_horizon,
            "outcome_overlap_embargo_bars": shared_embargo,
            "overlap_policy": seq0009["overlap_policy"],
            "rationale": "Riusato senza modifiche dalla convenzione generale di progetto per meccanismi "
                         "reversal/continuation su H4 (gia' esplicitata in seq0009_frozen_structural_spec_v1."
                         "json.natural_horizon_rationale: 'lo stesso ordine di grandezza temporale (giorni, "
                         "non ore ne' mesi)' - riusato qui identico per SWEEP, e per le prime 5 famiglie "
                         "perche' condividono la stessa classe di meccanismo (setup direzionale su H4, "
                         "risoluzione attesa su orizzonte multi-giorno) e perche' un disegno POOLED richiede "
                         "una scala temporale comune per rendere confrontabile/dichustrable la sovrapposizione "
                         "cross-family (sec. cross_family_dependence_clustering sotto) - un embargo diverso "
                         "per famiglia renderebbe indefinita la nozione stessa di 'sovrapposizione fra "
                         "famiglie diverse'.",
        },
        "family_specific_episode_gap_rule": family_specific_episode_gap_rule,
        "why_gap_rule_is_family_specific_but_horizon_is_shared": (
            "episode_gap_rule descrive quanto velocemente IL PROPRIO meccanismo del detector smette di "
            "riferirsi alla stessa realizzazione (dipende dai parametri specifici di QUEL detector - "
            "range_n, compression_min_bars, ecc. - MAI copiabile fra meccanismi diversi, principio gia' "
            "imposto in Phase 7.5B). natural_horizon/embargo descrivono invece la finestra di OUTCOME "
            "futuro che il disegno pooled intende testare - una proprieta' del CONTRASTO (CHOPPY vs "
            "TRENDING), non del detector - e deve quindi essere UNICA perche' il declustering cross-family "
            "(che confronta righe di famiglie diverse) sia ben definito."
        ),
    }

    cross_family_dependence_clustering = {
        "applies_to": "L'UNIONE delle righe rappresentative INDEPENDENT_VIEW di tutte e 6 le famiglie "
                       "(calcolate separatamente per ciascuna famiglia nel passaggio within-family sopra), "
                       "ri-clusterizzata insieme IGNORANDO l'etichetta di famiglia - un secondo passaggio "
                       "DISTINTO dal declustering within-family, mai un sostituto di esso.",
        "threshold_bars": shared_embargo,
        "threshold_rationale": "Identica alla soglia di embargo condivisa sopra: la sovrapposizione della "
                                "finestra di outcome futura fra due setup e' funzione ESCLUSIVAMENTE della "
                                "loro distanza in barre (outcome window [t+1, t+natural_horizon] per "
                                "costruzione), MAI della loro etichetta di famiglia - un BREAKOUT e una "
                                "DISPLACEMENT a distanza <=39 barre condividono la sovrapposizione della "
                                "finestra di outcome esattamente come farebbero due eventi della stessa "
                                "famiglia alla stessa distanza.",
        "no_double_counting_invariant": {
            "statement": "pooled_independent_units = n_cluster(assign_clusters(unione ordinata delle "
                         "righe rappresentative within-family independent di tutte e 6 le famiglie, "
                         "threshold=39)) - MAI la somma ingenua sum(family.INDEPENDENT_VIEW.n per ogni "
                         "famiglia). pooled_independent_units <= sum(family_independent_units), con "
                         "uguaglianza stretta SOLO se nessuna coppia cross-family di righe rappresentative "
                         "cade entro la soglia di embargo condivisa.",
            "synthetic_regression_required": True,
            "synthetic_case_description": "Famiglia A e famiglia B, ciascuna gia' internamente indipendente "
                                           "(nessuna coppia entro il proprio episode_gap_rule/embargo "
                                           "within-family), MA A e B condividono righe sottostanti vicine "
                                           "(es. A a row=1000, B a row=1010, embargo condiviso=39 -> "
                                           "distanza=10<=39): il conteggio pooled corretto DEVE collassare "
                                           "queste due unita' in UN solo cluster cross-family, non sommarle "
                                           "come 2 unita' indipendenti pooled.",
        },
    }

    # ---- matching_spec: contrasto SEMPRE stessa famiglia, CHOPPY vs TRENDING ----
    tercile_atr = seq0014a["matching_spec"]["state_feature_definitions"]["volatility_state_pre_entry"]
    matching_spec = {
        "match_dimensions": ["volatility_state_pre_setup"],
        "match_dimensions_rationale": "Dimensione minima giustificata (baseline_contract_v4.json), riusata "
                                       "identica da SEQ-0009/SEQ-0014A - contesto di volatilita' ORTOGONALE "
                                       "alla dimensione del contrasto stesso (directional_efficiency/regime), "
                                       "mai la stessa feature che definisce l'esposizione (evita il "
                                       "tautology/double-use risk gia' segnalato in feature_registry_v2.json).",
        "k": seq0014a["matching_spec"]["k"],
        "k_rationale": "Convenzione generale di progetto (baseline_contract_v4.json), non ottimizzata su "
                       "questi dati.",
        "minimum_control_count": seq0014a["matching_spec"]["minimum_control_count"],
        "max_control_reuse_per_run": seq0014a["matching_spec"]["max_control_reuse_per_run"],
        "state_feature_definitions": {
            "volatility_state_pre_setup": {
                "source_feature": tercile_atr["source_feature"],
                "definition": "terzile (LOW/MED/HIGH) di atr_percentile A T-1 (stessa regola causale del "
                               "regime contract stesso: mai leggere la barra t), terzili RIUSATI IDENTICI da "
                               "Phase 7.5C (seq0014_frozen_structural_spec_v1.json), fittati esclusivamente "
                               "su development_discovery - non ri-fittati qui.",
                "tercile_cutpoints_fit_on_discovery_only": tercile_atr["tercile_cutpoints_fit_on_discovery_only"],
                "labels": tercile_atr["labels"],
            },
        },
        "control_pool_construction_policy": (
            "SAME_SETUP_FAMILY_ID_OPPOSITE_REGIME_ONLY: per ogni setup CHOPPY indipendente (INDEPENDENT_VIEW) "
            "della famiglia F, il control_pool_by_event_row e' ristretto ESCLUSIVAMENTE ai setup TRENDING "
            "indipendenti della STESSA famiglia F - MAI setup di una famiglia diversa (vietato "
            "esplicitamente dalla richiesta, sec.10: 'mai cross-family, es. mai BREAKOUT-choppy vs "
            "SWEEP-trending'). Il contrasto CHOPPY-vs-TRENDING e' quindi l'esposizione primaria; "
            "volatility_state_pre_setup e' la SOLA dimensione di matching entro quel pool gia' ristretto - "
            "nessuna dimensione aggiuntiva inventata."
        ),
        "contrast_roles": {
            "event_side": "setup INDEPENDENT_VIEW con regime_at_t_minus_1=CHOPPY, per famiglia",
            "control_pool_side": "setup INDEPENDENT_VIEW con regime_at_t_minus_1=TRENDING, STESSA famiglia",
        },
        "split_boundaries": seq0014a["matching_spec"]["split_boundaries"],
        "additional_matching_dimensions_forbidden_unless_preexisting": True,
        "additional_matching_dimensions_note": "Nessuna dimensione oltre volatility_state_pre_setup e' stata "
                                                "aggiunta - non esiste, ad oggi, un'altra dimensione di "
                                                "matching gia' causal-safe/established nel progetto per "
                                                "questo tipo di contrasto oltre a quella riusata da "
                                                "SEQ-0009/SEQ-0014A.",
    }

    # ---- arm-size policy: nessuna soglia inventata, confermata l'assenza di un requisito canonico ----
    min_ev_gates = load_json(os.path.join(PHASE7_DIR, "policies", "minimum_evidence_gates.json"))
    arm_size_policy = {
        "canonical_per_arm_minimum_exists_in_project": False,
        "checked_against_file": "server/research_scripts/phase7/policies/minimum_evidence_gates.json",
        "checked_against_file_sha256": file_sha256(os.path.join(PHASE7_DIR, "policies", "minimum_evidence_gates.json")),
        "existing_gates_are_candidate_level_not_per_arm": (
            "n_nominal_minimum=%s, cluster_count_minimum=%s, effective_n_minimum=%s, "
            "minimum_controls_per_match=%s sono tutte gate a livello di CANDIDATO complessivo (o di "
            "conteggio di controlli per match), NESSUNA e' definita come 'minimo per braccio di regime "
            "ENTRO una famiglia' - un concetto strutturalmente diverso, mai formalizzato in questo progetto "
            "prima d'ora." % (
                min_ev_gates["gates"]["n_nominal_minimum"]["value"],
                min_ev_gates["gates"]["cluster_count_minimum"]["value"],
                min_ev_gates["gates"]["effective_n_minimum"]["value"],
                min_ev_gates["gates"]["minimum_controls_per_match"]["value"],
            )
        ),
        "flag": "NEEDS_ARM_SIZE_POLICY",
        "flag_meaning": "Nessuna soglia minima per braccio (CHOPPY o TRENDING, entro una famiglia) e' stata "
                        "inventata per questo preflight - il risultato riportera' n_choppy/n_trending/ratio/"
                        "minimum_arm_size per famiglia e pooled COME DATO DESCRITTIVO, senza applicare un "
                        "gate pass/fail su di essi finche' una policy dedicata non viene formalizzata "
                        "separatamente (fuori scope per questa fase).",
        "not_invented": True,
    }

    reclaim_discrepancy_reference = {
        "pointer_only": True,
        "already_documented_in_commit": BASELINE_COMMIT,
        "already_documented_in_file": "server/research_scripts/phase7/phase7_6b/seq0014b_setup_population_spec_v1.json",
        "summary_reference_only": "Il registry descrive RECLAIM come REFUTED_AT_DISCOVERY; l'artifact frozen "
                                   "originale (phase7_1_run_results.json) mostra INSUFFICIENT_SAMPLE per tutti "
                                   "e 3 i candidati - discrepanza gia' documentata in fb52168, NON corretta "
                                   "qui (market_sequence_registry_v1.json non viene toccato in questa fase, "
                                   "esplicitamente fuori scope).",
        "no_impact_on_this_preflight_geometry": True,
        "registry_file_touched_in_this_phase": False,
    }

    payload = {
        "phase": "7.6C",
        "artifact_role": "STRUCTURAL_PREFLIGHT_SPEC_COMMIT",
        "scope_note": "Congela le decisioni nuove necessarie al preflight pooled SEQ-0014B (unita' di "
                       "analisi, geometria within-family/cross-family, matching_spec, arm-size policy) - "
                       "PRIMA di calcolare qualunque count reale. Nessun outcome letto, nessuna discovery, "
                       "nessuna scelta di primary outcome.",
        "baseline_commit": BASELINE_COMMIT,
        "inputs_reused_unchanged": {
            "setup_population_spec_file": "server/research_scripts/phase7/phase7_6b/seq0014b_setup_population_spec_v1.json",
            "setup_population_spec_canonical_sha256": setup_pop_doc["canonical_sha256"],
            "eligible_setup_families": eligible_families,
            "architecture_decision_reused": setup_pop["architecture_decision"]["decision"],
            "regime_contract_reused": setup_pop["regime_contract"],
            "timestamp_contract_reused": setup_pop["timestamp_contract"],
        },
        "unit_of_analysis_decision": unit_of_analysis_decision,
        "within_family_geometry_rule": within_family_geometry_rule,
        "cross_family_dependence_clustering": cross_family_dependence_clustering,
        "matching_spec": matching_spec,
        "arm_size_policy": arm_size_policy,
        "failure_memory_context": {
            "reused_pointer_only": "server/research_scripts/phase7/phase7_6b/seq0014b_setup_population_spec_v1.json#failure_memory_inclusion_policy",
            "used_for_geometry_computation": False,
            "note": "Gli status storici REFUTED_AS_AUTONOMOUS_EDGE (Phase 5.5) sono riportati come "
                    "provenance/contesto nel result commit, MAI usati per alterare o giustificare alcun "
                    "calcolo di geometria in questa fase.",
        },
        "reclaim_discrepancy_reference": reclaim_discrepancy_reference,
        "not_yet_done_deferred_to_result_commit": [
            "Estrazione della tabella di setup reale da development_discovery (6 famiglie, direction!=0, "
            "regime_at_t_minus_1 != MED).",
            "Audit di overlap same-bar/cross-family (1 vs 2+ famiglie per riga, combinazioni, frazione "
            "condivisa).",
            "Geometria within-family EVENT/EPISODE/INDEPENDENT_VIEW per famiglia x regime (CHOPPY/TRENDING).",
            "Geometria pooled cross-family con declustering (no-double-counting invariant + test sintetico).",
            "n_choppy/n_trending/ratio/minimum_arm_size per famiglia e pooled (dato descrittivo, nessun gate "
            "pass/fail - vedi arm_size_policy.flag).",
            "Matching feasibility per famiglia (CHOPPY vs TRENDING, stessa famiglia).",
            "Verdetto strutturale composito finale.",
        ],
        "no_real_counts_computed_in_this_spec": True,
        "no_nexus_outcome_data_accessed": True,
        "no_edge_discovery_performed": True,
        "no_primary_outcome_selected": True,
        "seq0015_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
        "seq0009_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script="server/research_scripts/phase7/phase7_6c/build_seq0014b_structural_preflight_spec.py")
    out_path = os.path.join(PHASE76C_DIR, "seq0014b_structural_preflight_spec_v1.json")
    save_json(out_path, doc)
    print(f"Written {out_path}")
    print(f"canonical_sha256={doc['canonical_sha256']}")


if __name__ == "__main__":
    main()
