#!/usr/bin/env python3
"""Phase 7.6B - MECH-23 Filter Utility (SEQ-0014B) Setup Population
Formalization.

Riguarda SOLO SEQ-0014B (LOW_INFORMATION_STATE_FILTER_UTILITY, il claim
originale MECH-23: "i setup direzionali falliscono/producono piu'
rumore quando nascono in regime choppy rispetto a trending?"). NON
tocca SEQ-0014A (fenomeno state-entry, gia' FEASIBLE, invariato).

NESSUN outcome letto. NESSUNA discovery. NESSUN structural preflight
eseguito qui (la geometria EVENT/EPISODE/INDEPENDENT_VIEW di questa
popolazione sara' calcolata SOLO in una fase separata, dopo questo
commit). Nessuna scelta di eleggibilita'/architettura/regime basata su
performance osservata, PF, win rate, deltaP o probabilita' attesa che
il filtro funzioni - ogni decisione qui e' derivata da criteri
strutturali/causali/meccanici, verificabili leggendo il codice
esistente."""
import os
import sys

PHASE76B_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE76B_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE76B_DIR, "..", "..", "..", ".."))

sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json, file_sha256  # noqa: E402

FROZEN_SEQ0014A_SPEC = os.path.join(PHASE7_DIR, "phase7_5c", "seq0014_frozen_structural_spec_v1.json")
BUILD_EVENTS_OPERATIVE = os.path.join(PHASE7_DIR, "phase7_1", "build_events_p71.py")


# =====================================================================
# SEZIONE 1 - Inventario canonico dei detector direzionali gia' esistenti
# (build_events.py/build_events_p71.py - 9 famiglie, CFG frozen v1,
# verificato leggendo il codice, non assunto dal nome).
# =====================================================================
DETECTOR_INVENTORY = {
    "VOLATILITY_EXPANSION": {
        "detector_exists": True, "direction_defined": "SI - +1/-1 da close vs open, 0/NO_EVENT se doji",
        "observation_point": "bar_close (immediato)", "entry_trigger_defined": "SI - riga i",
        "delayed_confirmation": False,
        "formula": "tr[i] > vol_expansion_atr_mult(1.0) * atr[i]",
        "prior_test_history": "H008_EVENT_VOLATILITY_EXPANSION (Phase 5.5, event_alone, dataset 2019-2022): "
            "REFUTED. H010_INTERACTION_BREAKOUT_x_VOLATILITY_EXPANSION: REFUTED.",
        "already_refuted_as_autonomous_edge": True,
        "detector_quality_caveat": "Usa ATR_t (same-bar) per la soglia - causale ma self-normalizzante/"
            "endogeno rispetto alla propria anomalia (stesso problema gia' documentato e corretto per "
            "SEQ-0015/MOMENTUM_BURST, che ha sostituito ATR_t con ATR_{t-1} per la soglia). Non ricorretto "
            "qui - fuori scope, solo segnalato.",
    },
    "DISPLACEMENT": {
        "detector_exists": True, "direction_defined": "SI - +1/-1 da segno del corpo (body=close-open)",
        "observation_point": "bar_close (immediato)", "entry_trigger_defined": "SI - riga i",
        "delayed_confirmation": False,
        "formula": "abs(body[i]) > displacement_atr_mult(1.5) * atr[i]",
        "prior_test_history": "H006_EVENT_DISPLACEMENT (Phase 5.5, event_alone): REFUTED. "
            "H014_INTERACTION_DISPLACEMENT_x_VOLATILITY_STATE: INSUFFICIENT_SAMPLE.",
        "already_refuted_as_autonomous_edge": True,
    },
    "BREAKOUT": {
        "detector_exists": True, "direction_defined": "SI - +1 se close>rolling_high_20, -1 se close<rolling_low_20",
        "observation_point": "bar_close (immediato)", "entry_trigger_defined": "SI - riga i",
        "delayed_confirmation": False,
        "formula": "close[i] > max(high[i-21:i-1]) oppure close[i] < min(low[i-21:i-1])",
        "prior_test_history": "H001_EVENT_BREAKOUT (Phase 5.5, event_alone): REFUTED. "
            "H010/H011 interazioni: REFUTED. SEQ-0003 (registry Phase 7.2, MECH-06): readiness_status="
            "NEEDS_ADDITIONAL_SPECIFICATION per una formalizzazione PIU' RAFFINATA (richiede TRIGGER_TF "
            "H1/M15) - gap NON applicabile qui: il raw H4 event usato in questa popolazione e' gia' "
            "interamente calcolabile su H4 nativo, nessun gap dati per QUESTO scopo.",
        "already_refuted_as_autonomous_edge": True,
        "tf_gap_scope_note": "Il gap TRIGGER_TF dichiarato per SEQ-0003 riguarda una sequence FUTURA piu' "
            "precisa, non il detector raw gia' frozen usato qui.",
    },
    "FAILED_BREAKOUT": {
        "detector_exists": True, "direction_defined": "SI (eredita da BREAKOUT)",
        "observation_point": "bar_close_delayed", "entry_trigger_defined": "NO come setup indipendente",
        "delayed_confirmation": True,
        "formula": "confirmed_at j in (i, i+5] dove close[j] torna oltre il livello di BREAKOUT",
        "role": "NON un setup indipendente - e' un'ETICHETTA DI ESITO (failure) su un BREAKOUT gia' avvenuto "
                "a riga i, confermata SOLO a una riga j successiva. La sua stessa esistenza non e' nota al "
                "momento del setup (riga i) - includerla come unita' di popolazione separata "
                "duplicherebbe la stessa entrata di BREAKOUT E violerebbe il requisito di timing causale "
                "immediato (sec.2). Candidato per l'outcome 'failure' di BREAKOUT (sec.9), non per la "
                "popolazione di setup (sec.1).",
        "prior_test_history": "H002_EVENT_FAILED_BREAKOUT (Phase 5.5, event_alone): REFUTED (come "
                               "evento a se' stante, non come outcome-label - irrilevante per il ruolo "
                               "qui assegnato).",
    },
    "RETEST": {
        "detector_exists": True, "direction_defined": "SI (eredita da BREAKOUT)",
        "observation_point": "bar_close_delayed", "entry_trigger_defined": "NO come setup indipendente",
        "delayed_confirmation": True,
        "formula": "confirmed_at j in (i, i+10] dove il prezzo ritocca il livello senza richiudere oltre",
        "role": "Stesso ruolo di FAILED_BREAKOUT - etichetta di esito delayed su BREAKOUT, non setup "
                "indipendente.",
        "prior_test_history": "H005_EVENT_RETEST (Phase 5.5, event_alone): REFUTED.",
    },
    "SWEEP": {
        "detector_exists": True, "direction_defined": "SI - HIGH swept->-1(SELL), LOW swept->+1(BUY)",
        "observation_point": "bar_close (immediato)", "entry_trigger_defined": "SI - riga i",
        "delayed_confirmation": False,
        "formula": "high[i]>rolling_high_20 & close[i]<rolling_high_20 (HIGH) / speculare per LOW",
        "prior_test_history": "H003_EVENT_SWEEP (Phase 5.5, event_alone, dataset 2019-2022): REFUTED. "
            "H012_INTERACTION_SWEEP_RECLAIM_x_LOCATION: REFUTED. SEQ-0009 (Phase 7.5B, dataset p71/"
            "development_discovery, come autonomous edge candidate): NOT_TESTABLE_ON_PREREGISTERED_"
            "DISCOVERY (mai nemmeno arrivato a un test - INDEPENDENT_VIEW=10<30, collassato per "
            "clustering, non refutato).",
        "already_refuted_as_autonomous_edge": True,
    },
    "RECLAIM": {
        "detector_exists": True, "direction_defined": "SI (eredita/inverte lo swept_side)",
        "observation_point": "bar_close_delayed", "entry_trigger_defined": "NO come setup indipendente "
                              "(row_index=riga dello SWEEP originario, confirmed_at=riga di conferma reclaim)",
        "delayed_confirmation": True,
        "formula": "confirmed_at j in (i, i+10] dove close[j] richiude oltre il livello swept",
        "role": "Stesso ruolo di FAILED_BREAKOUT/RETEST ma per SWEEP - etichetta di esito delayed "
                "(il reclaim si verifica o no), non setup indipendente. Candidato per l'outcome 'failure/"
                "non-risoluzione' di SWEEP (sec.9).",
        "prior_test_history": "H004_EVENT_RECLAIM (Phase 5.5, dataset 2019-2022): POST_HOC_CANDIDATE "
            "(selezionato fra 14 candidati DOPO aver visto risultati - FAIL-001, MAI un verdetto pulito "
            "ne' REFUTED ne' SUPPORTED). Ri-testato rigorosamente come RECLAIM_FAMILY_P71 (Phase 7.1, "
            "dataset p71/development_discovery, pre-registrato con FDR): "
            "final_lifecycle_states=INSUFFICIENT_SAMPLE per BOTH/BUY/SELL, overall_verdict="
            "NO_SUPPORTED_CANDIDATE - MAI 'REFUTED' nonostante market_sequence_registry_v1.json (nota di "
            "SEQ-0009/SEQ-0010) lo descriva come 'REFUTED_AT_DISCOVERY'. Verificato leggendo "
            "server/research_scripts/phase7/phase7_1/data/phase7_1_run_results.json: EVENT_VIEW mostra "
            "delta_p negativo (~-0.065/-0.07) per tutti e 3 i candidati, ma EPISODE_VIEW mostra delta_p "
            "positivo e sotto soglia di materialita' (dependence_sensitive=true per tutti e 3) - "
            "l'effetto EVENT_VIEW era un artefatto di eventi dipendenti/clusterizzati (179->72, 102->40, "
            "77->34), non un effetto robusto poi refutato. DISCREPANZA DOCUMENTATA, non corretta "
            "silenziosamente nel registry (fuori scope di questa fase) - riportata qui per accuratezza.",
        "note_for_future_reference": "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT (Phase 6, true holdout, "
            "claim piu' specifico sull'asimmetria SELL) - status finale WEAK, non REFUTED ne' SUPPORTED. "
            "Contesto storico piu' ampio su SWEEP+RECLAIM, non direttamente rilevante per l'eleggibilita' "
            "di RECLAIM come outcome-label qui.",
    },
    "COMPRESSION_RELEASE": {
        "detector_exists": True, "direction_defined": "SI - +1/-1 da close vs open, 0/NO_EVENT se doji",
        "observation_point": "bar_close (immediato)", "entry_trigger_defined": "SI - riga i",
        "delayed_confirmation": False,
        "formula": "compressione sostenuta (>=5 barre sotto 20o percentile) poi tr[i]>1.0xATR[i]",
        "prior_test_history": "H007_EVENT_COMPRESSION_RELEASE (Phase 5.5, event_alone): REFUTED. "
            "H013_INTERACTION_COMPRESSION_RELEASE_x_DIRECTIONAL_EFFICIENCY: REFUTED.",
        "already_refuted_as_autonomous_edge": True,
    },
    "PULLBACK": {
        "detector_exists": True, "direction_defined": "SI - trend_sign +1/-1 (mai 0, guardia esplicita nel codice)",
        "observation_point": "bar_close (immediato)", "entry_trigger_defined": "SI - riga i",
        "delayed_confirmation": False,
        "formula": "trend stabilito (20 barre) + ritracciamento>=0.5xATR contro il trend",
        "prior_test_history": "H009_EVENT_PULLBACK (Phase 5.5, event_alone): REFUTED.",
        "already_refuted_as_autonomous_edge": True,
    },
}


def main():
    seq0014a_frozen = load_json(FROZEN_SEQ0014A_SPEC)["payload"]
    build_events_hash = file_sha256(BUILD_EVENTS_OPERATIVE)

    # =================================================================
    # SEZIONE 2 - Regola di eleggibilita' EX-ANTE (nessun criterio di performance)
    # =================================================================
    eligibility_rule = {
        "criteria_include_if_all_true": [
            "C1: direzionale (emette un valore di direzione +-1 non-degenere; casi doji/zero esclusi "
            "PER EVENTO, mai per famiglia intera)",
            "C2: causalmente osservabile a bar_close della propria barra trigger (observation_point="
            "'bar_close', MAI 'bar_close_delayed' - un'esistenza nota solo in retrospettiva non e' un "
            "setup causalmente valido al momento della decisione)",
            "C3: entry/trigger timing univoco (un solo row_index definisce event_a, nessuna dipendenza da "
            "una barra futura per stabilire SE il setup esiste)",
            "C4: detector gia' congelato/esistente nel codice (build_events.py/build_events_p71.py, "
            "invariato, gia' verificato byte-identico in Phase 7.5B)",
            "C5: nessun gap dati/timeframe irrisolto per il calcolo RAW su H4 nativo (un gap dichiarato per "
            "una formalizzazione FUTURA piu' raffinata della stessa famiglia non disqualifica l'uso "
            "dell'evento raw gia' calcolabile)",
            "C6: non semanticamente duplicato di un'altra famiglia gia' inclusa (verificato confrontando "
            "le formule, non assunto)",
        ],
        "criteria_explicitly_forbidden": [
            "PF (profit factor)", "win rate", "deltaP osservato", "risultato storico di qualunque test",
            "probabilita' attesa che il filtro CHOPPY/TRENDING funzioni per quella famiglia",
        ],
        "build_events_source_hash": build_events_hash,
        "build_events_source_ref": "server/research_scripts/phase7/phase7_1/build_events_p71.py (stesso "
                                    "file gia' verificato byte-identico a phase5/build_events.py per il "
                                    "blocco SWEEP in Phase 7.5B - qui esteso a tutte e 9 le famiglie)",
    }

    included = [fam for fam, d in DETECTOR_INVENTORY.items() if not d["delayed_confirmation"]]
    excluded_as_outcome_labels = [fam for fam, d in DETECTOR_INVENTORY.items() if d["delayed_confirmation"]]
    assert included == ["VOLATILITY_EXPANSION", "DISPLACEMENT", "BREAKOUT", "SWEEP",
                         "COMPRESSION_RELEASE", "PULLBACK"], f"inventario inatteso: {included}"
    assert excluded_as_outcome_labels == ["FAILED_BREAKOUT", "RETEST", "RECLAIM"]

    # =================================================================
    # SEZIONE 3 - Failure-memory inclusion policy
    # =================================================================
    failure_memory_policy = {
        "distinction": {
            "REFUTED_AS_AUTONOMOUS_EDGE": "Un test PRECEDENTE ha rifiutato l'ipotesi che QUESTA famiglia, "
                "da sola, preveda un esito migliore del baseline IN MEDIA (effetto marginale/incondizionato).",
            "NOT_USABLE_AS_FILTER_TEST_UNIT": "La famiglia non puo' essere usata come unita' per testare "
                "SEQ-0014B per una ragione STRUTTURALE (non causalmente osservabile, timing ambiguo, gap "
                "dati) - concettualmente indipendente dallo status REFUTED.",
        },
        "policy": "Uno status REFUTED_AS_AUTONOMOUS_EDGE NON disqualifica automaticamente una famiglia "
            "dalla popolazione SEQ-0014B. Il claim filter-utility ('i setup falliscono PIU' SPESSO in "
            "choppy vs trending') e' un'ipotesi CONDIZIONATA/MODERATA, logicamente distinta dal claim "
            "MARGINALE/INCONDIZIONATO gia' rifiutato ('questo setup ha edge positivo in media') - un "
            "effetto medio nullo e' matematicamente compatibile con un effetto condizionale reale "
            "(es. leggermente positivo in trending, negativo in choppy, che si annullano in media - "
            "esattamente il tipo di eterogeneita' che un test incondizionato NON puo' rilevare per "
            "costruzione). Riattivare un'ipotesi gia' refutata SAREBBE vietato (FAIL-002/sec.24 Phase 7.2) "
            "SE il moderatore fosse inventato o ri-tarato per SALVARE quella specifica famiglia - qui il "
            "moderatore (LOW_INFORMATION_STATE, tercili di directional_efficiency) e' GIA' congelato "
            "(Phase 7.5C, invariato) e applicato IDENTICO a TUTTE le famiglie eleggibili, mai scelto o "
            "aggiustato per farne funzionare una specifica.",
        "reclaim_discrepancy_handling": "Il caso RECLAIM (vedi DETECTOR_INVENTORY) mostra che un "
            "aggiornamento di verdetto (da POST_HOC_CANDIDATE/Phase 5.5 a INSUFFICIENT_SAMPLE/Phase 7.1, "
            "MAI 'REFUTED' nonostante la nota narrativa nel registry) e' esattamente il tipo di "
            "informazione che questa policy tratta con cura - nessun setup e' escluso qui sulla base di "
            "una caratterizzazione narrativa non verificata contro l'artifact frozen originale.",
        "applied_to_included_families": "Tutte e 6 le famiglie incluse (VOLATILITY_EXPANSION, DISPLACEMENT, "
            "BREAKOUT, SWEEP, COMPRESSION_RELEASE, PULLBACK) hanno uno status REFUTED_AS_AUTONOMOUS_EDGE "
            "storico (Phase 5.5, dataset 2019-2022, event_alone) - NESSUNA e' disqualificata da questo per "
            "la ragione sopra. Trattare comunque con scetticismo proporzionale (stesso principio gia' "
            "espresso per SEQ-0011 in market_sequence_registry_v1.json) - non promuovere automaticamente "
            "un risultato positivo del filtro come 'edge ritrovato'.",
    }

    # =================================================================
    # SEZIONE 4 - Single-family vs pooled (decisione EX-ANTE, non su risultati)
    # =================================================================
    architecture_decision = {
        "option_A_single_family": {
            "description": "Testare MECH-23 su UNA sola famiglia di setup (es. solo SWEEP).",
            "advantages": ["geometria di campione piu' semplice/pulita", "nessuna eterogeneita' fra "
                           "famiglie", "nessuna complessita' di pooling/stratificazione",
                           "interpretazione diretta e univoca"],
            "confounders": ["il risultato non generalizza al claim ORIGINALE, che parla di 'setup "
                            "direzionali' genericamente, non di una famiglia specifica"],
            "sample_geometry": "Dipende interamente dalla geometria GIA' NOTA di quella famiglia (es. SWEEP "
                                "e' gia' strutturalmente fragile da solo - SEQ-0009, INDEPENDENT_VIEW=10 - "
                                "splittare ulteriormente per regime CHOPPY/TRENDING la assottiglierebbe "
                                "ANCORA di piu').",
            "multiplicity": "Minima (1 famiglia = 1 test primario).",
            "interpretation": "Risposta stretta e specifica ('SWEEP fallisce di piu' in chop?'), non il "
                               "claim MECH-23 generale.",
        },
        "option_B_pooled_stratified": {
            "description": "Testare MECH-23 su una popolazione di PIU' famiglie di setup, con "
                            "setup_family_id come stratificazione/matching obbligatorio (MAI pooling "
                            "ingenuo che tratti eventi di famiglie diverse come intercambiabili).",
            "advantages": ["piu' fedele al claim ORIGINALE (generico su 'setup direzionali')",
                           "campione combinato potenzialmente piu' ampio (mitiga la fragilita' "
                           "strutturale gia' osservata famiglia per famiglia)",
                           "permette di osservare eterogeneita' fra famiglie invece di nasconderla"],
            "confounders": ["famiglie diverse hanno tassi di base/detector diversi - un contrasto "
                            "choppy-vs-trending DEVE essere calcolato ENTRO ciascuna famiglia (matched), "
                            "mai fra osservazioni di famiglie diverse", "un effetto medio pooled puo' "
                            "mascherare eterogeneita' reale (alcune famiglie positive, altre negative, "
                            "che si annullano)"],
            "sample_geometry": "Ogni famiglia contribuisce la PROPRIA geometria EVENT/EPISODE/INDEPENDENT_"
                                "VIEW (da verificare famiglia per famiglia in un futuro structural "
                                "preflight, NON eseguito qui) - il pooling avviene DOPO, non sostituisce "
                                "la verifica strutturale per famiglia.",
            "multiplicity": "1 confronto choppy-vs-trending PER famiglia eleggibile (fino a 6) + "
                            "opzionalmente 1 sintesi aggregata pre-specificata = famiglia inferenziale "
                            "unica, corretta con BH-FDR come un UNICO gruppo (mai testata famiglia per "
                            "famiglia con soglie separate).",
            "interpretation": "Risposta piu' vicina al claim originale, ma richiede modellazione "
                               "gerarchica/stratificata esplicita (da NON costruire ancora in questa fase - "
                               "solo la struttura e' congelata qui).",
        },
        "decision": "OPTION_B_POOLED_STRATIFIED_BY_SETUP_FAMILY_ID",
        "decision_rationale": "Il claim MECH-23 originale (market_sequence_registry_v1.json, Phase 7.2) e' "
            "formulato genericamente su 'setup direzionali', non su una famiglia nominata - un test "
            "single-family risponderebbe a una domanda piu' stretta e diversa. La decisione e' presa QUI, "
            "PRIMA di calcolare qualunque geometria o outcome per nessuna famiglia - non sulla base di "
            "quale famiglia 'sembra promettente'.",
        "no_naive_pooling_enforcement": "setup_family_id e' un campo OBBLIGATORIO su ogni setup eleggibile "
            "(sec.5) - qualunque futura fase di discovery/inferenza DEVE stratificare/raggruppare per "
            "questo campo, mai trattare setup di famiglie diverse come osservazioni intercambiabili dello "
            "stesso fenomeno.",
    }

    # =================================================================
    # SEZIONE 6-7 - Regime contract (CHOPPY riusato invariato, TRENDING nuovo)
    # =================================================================
    de_cut = seq0014a_frozen["state_definition"]["tercile_cutpoints_fit_on_discovery_only"]
    regime_contract = {
        "shared_feature": "directional_efficiency (stessa feature, STESSI tercile cutpoints gia' fittati "
                           "su development_discovery e congelati in Phase 7.5C - MAI ri-fittati qui)",
        "tercile_cutpoints_reused_unchanged": de_cut,
        "CHOPPY": {"definition": "directional_efficiency <= q1_low_med (terzile LOW)",
                    "reused_from": "SEQ-0014A frozen structural spec (Phase 7.5C) - INVARIATO, stessa "
                                    "soglia, non ri-ottimizzata."},
        "TRENDING": {"definition": "directional_efficiency > q2_med_high (terzile HIGH)",
                     "rationale": "Candidato naturale complementare al terzile LOW gia' congelato - stessa "
                                  "feature, stessa distribuzione fit su discovery, nessuna nuova soglia "
                                  "inventata."},
        "MED_tercile_treatment": "EXCLUDED",
        "MED_tercile_rationale": "Il claim originale MECH-23 (verbatim) contrappone esplicitamente 'choppy' "
            "a 'trending' come DUE regimi nominati, non un continuum - il terzile MED rappresenta uno stato "
            "genuinamente intermedio/ambiguo (ne' chiaramente choppy ne' chiaramente trending). Includerlo "
            "con uno dei due lati mescolerebbe una popolazione concettualmente diversa nel contrasto, "
            "indebolendo l'interpretabilita' di un confronto a due gruppi puliti. Nessuna forte "
            "giustificazione contraria identificata - MED e' semplicemente escluso dal confronto "
            "principale (setup che nascono con regime MED non entrano ne' nel braccio CHOPPY ne' in quello "
            "TRENDING).",
    }

    # =================================================================
    # SEZIONE 8 - Setup timestamp contract (anti-endogeneita')
    # =================================================================
    timestamp_contract = {
        "setup_time_t": "row_index del proprio evento raw (bar_close immediato) - unico per costruzione "
                        "(criterio C3 di eleggibilita').",
        "direction": "presa direttamente dal campo 'direction' gia' emesso dal detector (nessuna "
                     "ricostruzione).",
        "prediction_start": "close(t), coincide con l'observation_cutoff (stesso pattern di SEQ-0009/"
                             "SEQ-0014A - nessuna fase di transizione separata per queste famiglie).",
        "regime_read_timestamp": "t-1 (la barra IMMEDIATAMENTE PRECEDENTE al proprio trigger), MAI a t.",
        "endogeneity_risk_identified": "directional_efficiency[t] e' calcolata su una finestra Kaufman "
            "Efficiency Ratio di 20 barre CHE INCLUDE la barra t stessa. Diverse famiglie eleggibili "
            "(VOLATILITY_EXPANSION, DISPLACEMENT, COMPRESSION_RELEASE, BREAKOUT, SWEEP) derivano la "
            "propria direzione/innesco da OHLC della STESSA barra t - leggere il regime a t creerebbe una "
            "sovrapposizione meccanica fra 'cosa fa scattare il setup' e 'come viene classificato il "
            "regime al momento del setup', un rischio di endogeneita' reale (non ipotetico).",
        "resolution": "Leggere il regime (CHOPPY/TRENDING/MED-escluso) a t-1 elimina questa sovrapposizione "
            "- generalizza lo stesso principio anti-circolarita' gia' usato in Phase 7.5B/7.5C per le "
            "dimensioni di MATCHING (stato pre-evento) applicandolo qui alla variabile di ESPOSIZIONE "
            "primaria stessa, che ha una barra di sicurezza causale piu' alta.",
        "not_yet_computed": "Nessun valore di directional_efficiency[t-1] e' stato ancora estratto per "
            "alcun setup reale in questa fase - la regola e' congelata, non ancora applicata a dati.",
    }

    # =================================================================
    # SEZIONE 9 - Candidate failure/noise outcomes (NESSUNA selezione)
    # =================================================================
    candidate_outcomes = {
        "note": "Elencati senza scegliere quale produce il contrasto piu' forte - la scelta e' rimandata a "
                "una fase successiva, dopo aver verificato la fattibilita' strutturale della popolazione.",
        "generic_candidates_from_existing_vocabulary": [
            {"id": "P_PLUS_1ATR_BEFORE_MINUS_1ATR (e varianti a soglia diversa)",
             "represents": "inverso del 'successo' del setup - fallimento = probabilita' di NON raggiungere "
                           "il target prima dello stop"},
            {"id": "MAE", "represents": "escursione avversa massima - candidato diretto per 'adverse "
                                          "excursion'"},
            {"id": "REVERSAL_PROBABILITY", "represents": "probabilita' di inversione contro la direzione "
                                                          "del setup - candidato diretto per 'rumore'"},
            {"id": "TIME_TO_TARGET", "represents": "lentezza/incertezza di risoluzione - candidato per "
                                                    "'rumore' inteso come indecisione"},
            {"id": "PATH_EFFICIENCY", "represents": "inefficienza del percorso verso l'esito - candidato "
                                                     "diretto per 'path inefficiency'"},
        ],
        "family_specific_native_candidates": [
            {"id": "FAILED_BREAKOUT (gia' frozen, delayed)", "applies_to": "BREAKOUT",
             "represents": "definizione di fallimento NATIVA del detector stesso - nessuna soglia "
                           "aggiuntiva da inventare, ma applicabile SOLO a BREAKOUT (non uniforme fra "
                           "famiglie - rilevante se si sceglie option_A o un'analisi family-specific "
                           "secondaria entro option_B)."},
            {"id": "RECLAIM non-occorrenza/risoluzione opposta (gia' frozen, delayed)", "applies_to": "SWEEP",
             "represents": "stesso ruolo di FAILED_BREAKOUT ma per SWEEP."},
        ],
        "uniformity_requirement_for_pooled_design": "Se si procede con OPTION_B (pooled/stratified, gia' "
            "deciso in sec.4), il PRIMARY outcome dovra' essere uno dei candidati GENERICI (applicabile "
            "identico a tutte e 6 le famiglie) - i candidati family-specific nativi (FAILED_BREAKOUT/"
            "RECLAIM) potranno al piu' servire da diagnostica secondaria per le sole famiglie BREAKOUT/"
            "SWEEP, mai da primary outcome pooled (non definiti per le altre 4 famiglie).",
    }

    # =================================================================
    # SEZIONE 13 - Hard stop check
    # =================================================================
    n_eligible = len(included)
    hard_stop_triggered = n_eligible == 0

    payload = {
        "phase": "Phase 7.6B - MECH-23 Filter Utility (SEQ-0014B) Setup Population Formalization",
        "scope_note": "Riguarda SOLO SEQ-0014B - SEQ-0014A (state-entry phenomenon, FEASIBLE, Phase 7.5C) "
                      "resta invariato, non toccato da questo script.",
        "detector_inventory": DETECTOR_INVENTORY,
        "eligibility_rule": eligibility_rule,
        "eligible_setup_families": included,
        "excluded_as_independent_setups_reclassified_as_outcome_labels": excluded_as_outcome_labels,
        "failure_memory_inclusion_policy": failure_memory_policy,
        "architecture_decision": architecture_decision,
        "regime_contract": regime_contract,
        "timestamp_contract": timestamp_contract,
        "candidate_failure_noise_outcomes": candidate_outcomes,

        "structural_feasibility_deferred": "n setups total, n CHOPPY, n TRENDING, n MED-escluso, "
            "distribuzione per famiglia, clustering temporale, unita' indipendenti, fattibilita' del "
            "matching, reuse - NESSUNO di questi e' stato calcolato in questa fase (sec.10 della "
            "richiesta). Verranno calcolati SOLO in una fase separata successiva (structural preflight "
            "dedicato a SEQ-0014B), dopo questo commit.",

        "anti_selection_rule": "Se piu' famiglie di setup vengono testate (gia' deciso: tutte e 6, "
            "sec.4), DEVONO appartenere alla STESSA famiglia inferenziale pre-registrata (BH-FDR unico "
            "su tutte le famiglie insieme) - MAI testare 6 famiglie e poi mantenere solo quella dove il "
            "filtro sembra funzionare. Un'eventuale rimozione di una famiglia PRIMA di calcolare qualunque "
            "outcome deve essere giustificata STRUTTURALMENTE (es. fallimento del gate strutturale di "
            "quella sola famiglia) e documentata, mai perche' 'non promette bene'.",

        "hard_stop_check": {
            "n_eligible_setup_families": n_eligible,
            "hard_stop_triggered": hard_stop_triggered,
            "MECH23_FILTER_CLAIM_STATUS": ("BLOCKED_ON_DIRECTIONAL_SETUP_POPULATION" if hard_stop_triggered
                                            else "SETUP_POPULATION_SPECIFIED_AWAITING_STRUCTURAL_PREFLIGHT"),
        },

        "seq0014a_untouched": "server/research_scripts/phase7/phase7_5c/seq0014_frozen_structural_spec_v1.json "
                               "- nessuna modifica. Il risultato 189->128->49, matching 49/49, FEASIBLE "
                               "resta valido ESCLUSIVAMENTE per SEQ-0014A (fenomeno state-entry), mai "
                               "reinterpretato come evidenza per SEQ-0014B.",
        "no_structural_preflight_executed": True,
        "no_discovery_authorized": True,
        "no_nexus_outcome_data_accessed": True,
        "no_edge_discovery_performed": True,
        "seq0015_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
        "seq0009_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
    }

    out_path = os.path.join(PHASE76B_DIR, "seq0014b_setup_population_spec_v1.json")
    save_json(out_path, wrap_with_provenance(payload, "phase7/phase7_6b/build_seq0014b_setup_population_spec.py"))
    print(f"Scritto {out_path}")
    print(f"eligible_setup_families ({n_eligible}): {included}")
    print(f"excluded_as_outcome_labels: {excluded_as_outcome_labels}")
    print(f"MECH23_FILTER_CLAIM_STATUS: {payload['hard_stop_check']['MECH23_FILTER_CLAIM_STATUS']}")


if __name__ == "__main__":
    main()
