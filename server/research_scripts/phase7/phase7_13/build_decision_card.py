#!/usr/bin/env python3
"""Phase 7.13 punti 7-8 - Decision Card finale e proposta di fix (SOLO
se giustificata, NON applicata al sorgente). Aggrega gli esiti di:
  synthetic_causal_proof_v1.json, multi_tf_dataset_v1.json,
  ab_simulation_v1.json, state_mutation_trace_v1.json,
  historical_evidence_impact_map_v1.json, breakout_acc_comparison_v1.json
"""
import os
import sys

PHASE713_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE713_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402


def build():
    ab = load_json(os.path.join(PHASE713_DIR, "ab_simulation_v1.json"))["payload"]
    synth = load_json(os.path.join(PHASE713_DIR, "synthetic_causal_proof_v1.json"))["payload"]
    hist = load_json(os.path.join(PHASE713_DIR, "historical_evidence_impact_map_v1.json"))["payload"]

    decision = "DEFECT_CONFIRMED_MATERIAL_IMPACT"
    decision_basis = [
        "Dimostrazione causale pulita su serie sintetica calcolabile a mano "
        "(synthetic_causal_proof_v1.json): chiamata su TF non canonico (H4) -> mutazione dello "
        "stato condiviso -> segnale scartato dal router -> soppressione di un segnale D1 "
        "genuino futuro. Le 4 fasi richieste dal task sono tutte dimostrate separatamente "
        "nello stesso scenario minimo.",
        f"Quantificazione su dati reali (ab_simulation_v1.json, periodo "
        f"{ab['period_covered'][0][:10]}..{ab['period_covered'][1][:10]}): "
        f"{ab['stream_a_generated_d1_total']} segnali D1 generati in Stream A (implementato) "
        f"contro {ab['stream_b_generated_d1_total']} in Stream B (TF-scoped) su "
        f"{ab['n_d1_events_evaluated']} chiusure D1 valutate - "
        f"SOVRAPPOSIZIONE ZERO fra i due insiemi ({len(ab['only_in_a'])} solo in A, "
        f"{len(ab['only_in_b'])} solo in B, 0 uguali).",
        f"{ab['stream_a_raw_triggers_non_canonical_total']} raw trigger su passaggi non "
        f"canonici (H4/H1/M30/M15) nello stesso periodo, contro soli "
        f"{ab['stream_a_raw_triggers_by_tf'].get('D1', {}).get('BUY', 0) + ab['stream_a_raw_triggers_by_tf'].get('D1', {}).get('SELL', 0)} "
        f"sul passaggio canonico D1 - la mutazione dello stato condiviso avviene quasi "
        f"esclusivamente a un ritmo NON canonico.",
    ]

    historical_evidence_integrity = "PARTIALLY_COMPROMISED_FOR_MT5_REAL_TICK_RESULTS"
    historical_evidence_integrity_note = (
        "L'evidenza Python (server/backtest.py::_ob_series) e' UNAFFECTED da questo specifico "
        "difetto per costruzione (single-TF), ma NON rappresentativa del comportamento live "
        "(identita' diversa, dimostrato materialmente diverso sopra). I due CSV di risultati "
        "MT5 a tick reali trovati (results/phase2_baseline_20260705_v2.0.27.csv, "
        "results/phase_partB_silent_diagnostic_20260706.csv) sono POSSIBLY_CONTAMINATED - "
        "configurazione esatta (multi-TF on/off) non verificabile dai soli CSV. Nessun PF/WR "
        "storico viene qui reinterpretato come prova a favore o contro la strategia canonica."
    )
    distortion_direction = "BOTH"
    distortion_direction_note = (
        f"La contaminazione sia SOPPRIME segnali D1 genuini che si sarebbero verificati sotto "
        f"la logica TF-scoped ({len(ab['only_in_b'])} casi, FALSE_NEGATIVE_RISK: la strategia "
        f"sembra 'non tradare' quando invece dovrebbe) SIA CREA segnali D1 che non sarebbero mai "
        f"esistiti senza la contaminazione ({len(ab['only_in_a'])} casi, FALSE_POSITIVE_RISK: la "
        f"strategia tradа su rumore intraday che il design D1 dichiarato non prevede) - entrambe "
        f"le direzioni sono dimostrate, con la creazione spuria (A) numericamente piu' frequente "
        f"della soppressione (B) in questo periodo."
    )

    fix_proposal = {
        "proposed_only_not_applied": True,
        "patch_proposta": {
            "file": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh",
            "funzione": "NXS_Strat_OrderBlock() (righe 2141-2161)",
            "punto_di_inserimento": "subito dopo `ENUM_TIMEFRAMES tf = NXS_EffTF();` (riga 2144), "
                                    "PRIMA di qualunque lettura di g_atr/g_obBuy/g_obSell",
            "riga_proposta": 'if(tf != NXS_Profile_TF("ORDER_BLOCK")) return s;',
            "precedente_diretto": "identica forma alla guardia gia' applicata per BREAKOUT_ACC "
                                  "(NXS_Strategies.mqh:1548) - vedi breakout_acc_comparison_v1.json "
                                  "per le differenze di sostanza (non di forma)",
            "effetto_su_ob_mit": "automatico - OB_MIT chiama NXS_Strat_OrderBlock() direttamente, "
                                 "nessuna patch separata necessaria ne' possibile in modo indipendente",
        },
        "invarianti_da_preservare": [
            "Nessun cambiamento al comportamento sui passaggi D1 (la guardia agisce solo sui "
            "passaggi non-D1, che oggi mutano stato ma vengono comunque scartati dal router)",
            "SL/TP (NXS_DefaultSLTP), gate HTF (g_structH1.trend), gate SMC reaction "
            "(NXS_SMCReactionOK) invariati",
            "Struttura SNXSOBState invariata",
            "Nessuna modifica a OB_MIT oltre l'effetto automatico ereditato",
        ],
        "test_necessari": [
            "Unit test della sola condizione di guardia (tf vs NXS_Profile_TF) in isolamento",
            "Trace Decision/Gate/Execution (gia' esistente a livello router, Phase 7.12) raccolto "
            "PRIMA e DOPO il fix su un ambiente demo/Tester, per confermare che post-fix nessuna "
            "mutazione di g_obBuy/g_obSell avviene su passaggi non-D1",
            "Verifica di non-regressione su OB_MIT (stesso trace, stessa aspettativa)",
            "Confronto fra la sequenza segnali D1 post-fix osservata dal vivo e la ricostruzione "
            "Stream B di questa fase (ab_simulation_v1.json), sulla porzione di periodo che si "
            "sovrappone",
        ],
        "piano_di_parity_pre_post": [
            "Congelare un intervallo di osservazione demo/Tester (stessa disciplina "
            "outcome-blind delle fasi precedenti)",
            "Raccogliere il trace router-level PRIMA del fix (comportamento contaminato, per "
            "confronto) e DOPO il fix (comportamento atteso TF-scoped)",
            "Verificare causalmente (non per PF/WR) che i segnali D1 post-fix corrispondano "
            "esattamente a cio' che una ricostruzione Stream B produrrebbe sugli stessi dati",
        ],
        "rollback_criteria": [
            "Se il trace post-fix mostra ANCORA mutazioni di stato su passaggi non-D1 (patch "
            "applicata in modo scorretto o bypassata da un altro percorso di chiamata non "
            "individuato in questa fase)",
            "Se OB_MIT mostra un comportamento anomalo rispetto al suo storico (i suoi "
            "moltiplicatori SL/TP, NXS_StrategyProfiles.mqh:143, potrebbero essere stati "
            "implicitamente calibrati - se mai - sul comportamento contaminato, non verificato "
            "in questa fase - CANNOT_DETERMINE in historical_evidence_impact_map_v1.json)",
            "Se il volume di segnali D1 post-fix diverge in modo non spiegabile dalla "
            "ricostruzione Stream B di questa fase sulla stessa finestra",
        ],
        "separazione_esplicita": {
            "verifica_implementazione": "la guardia elimina strutturalmente la lettura/scrittura "
                                        "di stato sui passaggi non canonici - verificabile "
                                        "direttamente sul codice e col trace, INDIPENDENTEMENTE "
                                        "da qualunque esito economico",
            "validita_evidenza": "qualunque PF/WR storico pre-fix resta storico e classificato "
                                 "come in historical_evidence_impact_map_v1.json - non viene "
                                 "'corretto retroattivamente' dal fix",
            "redditivita": "NON PRESUNTA - correggere il meccanismo di stato NON implica che la "
                          "strategia diventi profittevole; elimina solo una fonte di rumore "
                          "strutturale, la profittabilita' resta una domanda separata e "
                          "successiva, fuori scope di questa fase",
        },
    }

    payload = {
        "candidate": "ORDER_BLOCK",
        "propagates_to": "OB_MIT",
        "baseline_commit": "dc1874e",
        "decision": decision,
        "decision_basis": decision_basis,
        "historical_evidence_integrity": historical_evidence_integrity,
        "historical_evidence_integrity_note": historical_evidence_integrity_note,
        "distortion_direction": distortion_direction,
        "distortion_direction_note": distortion_direction_note,
        "defect_exists_vs_material_impact": {
            "defect_exists": True,
            "defect_materially_changes_behavior": True,
            "note": "Entrambe le domande hanno risposta affermativa in questo caso - a "
                    "differenza del principio generale enunciato nel task (un difetto puo' "
                    "esistere senza impatto materiale), qui l'impatto e' totale nel periodo "
                    "studiato (0 sovrapposizione Stream A/B)",
        },
        "scope_limits_declared": [
            "Confronto al livello di raw trigger pre-gate (H1 trend, SMC reaction gate NON "
            "replicati) - non e' una stima di trade eseguiti/redditivita'",
            "Periodo reale coperto: 2023-10-02 -> 2026-08-25 (fonte M15 disponibile), non "
            "l'intero storico 2019-2026",
            "Passaggio M5 (LEVEL_CONFLUENCE_M5/LEVEL_REACTION_M5) escluso dalla simulazione - "
            "limite INFERIORE, non sovrastima, dell'esposizione reale",
            "Semplificazione touched/rejection valutati per barra chiusa, non per tick",
        ],
        "fix_proposal": fix_proposal,
        "no_optimization_no_sltp_tuning_no_sweep_no_profitability_no_rescue_no_live_promotion": True,
        "ea_source_untouched_this_phase": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE713_DIR, "decision_card_order_block_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  DECISIONE: {payload['decision']}")
    print(f"  historical_evidence_integrity: {payload['historical_evidence_integrity']}")
    print(f"  distortion_direction: {payload['distortion_direction']}")


if __name__ == "__main__":
    main()
