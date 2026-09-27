#!/usr/bin/env python3
"""Phase 7.17 punti 7-8 - Decision Card finale TSI e proposta di fix
(SOLO se giustificata, NON applicata)."""
import os
import sys

PHASE717_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE717_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402


def build():
    impact = load_json(os.path.join(PHASE717_DIR, "tsi_impact_comparison_v1.json"))["payload"]
    minimal = load_json(os.path.join(PHASE717_DIR, "tsi_minimal_cases_v1.json"))["payload"]

    decision = "DEFECT_CONFIRMED_MATERIAL_IMPACT"
    decision_basis = [
        "Formalizzazione matematica (punto 2): TSI e' un filtro ricorsivo continuo (IIR, "
        "doppio EMA) senza guardia TF - a differenza di ORDER_BLOCK (stato discreto "
        "'ricreabile'), la contaminazione non puo' mai autoripararsi, si prevede quindi "
        "UNIVERSALE (ogni lettura D1, non solo alcune date).",
        "Caso minimo con aritmetica razionale ESATTA (punto 3): sulla STESSA barra D1 "
        f"chiusura, Stream A produce TSI={minimal['divergence_at_D1_2']['tsi_stream_A']:.6f} "
        f"contro Stream B TSI={minimal['divergence_at_D1_2']['tsi_stream_B']:.6f} - una "
        "divergenza del VALORE dell'indicatore, non solo del segnale finale, verificata "
        "indipendentemente dalla funzione sotto test.",
        f"Quantificazione su dati reali gia' disponibili (2023-10-02..2026-08-25, nessun "
        f"nuovo run): {impact['tsi_value_divergence']['n_d1_bars_tsi_value_different']}/"
        f"{impact['tsi_value_divergence']['n_d1_bars_with_tsi_computed_both_streams']} "
        f"barre D1 ({impact['tsi_value_divergence']['pct_d1_bars_tsi_different']:.0f}%) "
        f"mostrano un TSI numericamente diverso fra Stream A (contaminato) e Stream B "
        f"(TF-scoped) - CONFERMA EMPIRICA della predizione teorica di universalita'.",
        f"A livello di segnale: {impact['signal_level_comparison']['n_generated_a']} "
        f"segnali A vs {impact['signal_level_comparison']['n_generated_b']} B, solo "
        f"{impact['signal_level_comparison']['n_matched_same_date_direction']} coincidono "
        f"esattamente su {impact['signal_level_comparison']['n_generated_a'] + impact['signal_level_comparison']['n_generated_b']} "
        f"totali - divergenza MOLTO piu' estesa di quella osservata per ORDER_BLOCK "
        f"(coerente con la natura continua/mai-autoriparante del filtro TSI contro la "
        f"natura discreta/parzialmente-autoriparante della zona ORDER_BLOCK).",
    ]

    historical_evidence_integrity = "PARTIALLY_COMPROMISED_FOR_MT5_REAL_TICK_RESULTS"
    historical_evidence_integrity_note = (
        "Il motore Python e' UNAFFECTED dal difetto cross-TF per costruzione, ma non "
        "rappresentativo del comportamento live (identita' diversa, dimostrato "
        "materialmente diverso sopra). I tre riferimenti MT5 reali trovati (sweep37 S05, "
        "results/phase2_baseline, results/phase_partB) sono tutti POSSIBLY_CONTAMINATED - "
        "configurazione esatta non verificabile dagli artifact disponibili. Nessun PF/WR "
        "storico viene qui reinterpretato come prova a favore o contro la strategia "
        "canonica."
    )
    distortion_direction = "BOTH"
    distortion_direction_note = (
        f"La contaminazione sia sopprime segnali D1 genuini che si sarebbero verificati "
        f"sotto la logica TF-scoped ({impact['signal_level_comparison']['n_only_in_b']} casi) "
        f"SIA crea segnali che non sarebbero mai esistiti senza la contaminazione "
        f"({impact['signal_level_comparison']['n_only_in_a']} casi) - entrambe le direzioni "
        f"sono dimostrate, con magnitudo quasi identica fra le due (a differenza di "
        f"ORDER_BLOCK dove la creazione spuria dominava nettamente) - coerente con un "
        f"meccanismo di corruzione CONTINUO e simmetrico piuttosto che un evento discreto "
        f"a senso unico."
    )
    confidence = "HIGH"
    confidence_reasoning = (
        "Il meccanismo e' interamente matematico/deterministico (nessun branching "
        "condizionale su soglie di prezzo nella mutazione dello stato, a differenza di "
        "ORDER_BLOCK) - la dimostrazione nei casi minimi usa aritmetica razionale esatta "
        "(non float, nessuna ambiguita' di arrotondamento), e la quantificazione su dati "
        "reali mostra un effetto universale (100% delle barre), non marginale o "
        "borderline. L'unica riserva e' l'assenza di un trace EA live reale (a differenza "
        "di ORDER_BLOCK, Phase 7.14) - la materialita' e' quindi confermata su dati REALI "
        "ma RICAMPIONATI (M15->D1/H4/H1/M30), non su tick nativi del broker."
    )

    fix_proposal = {
        "proposed_only_not_applied": True,
        "patch_proposta": {
            "file": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh",
            "funzione": "NXS_Strat_TSI() (righe 1366-1414)",
            "punto_di_inserimento": "subito dopo `ENUM_TIMEFRAMES tf = NXS_EffTF();` (riga "
                                    "1369), PRIMA di qualunque lettura/scrittura di "
                                    "g_tsiState",
            "riga_proposta": 'if(tf != NXS_Profile_TF("TSI")) return s;',
            "precedente_diretto": "identica forma alla guardia gia' applicata per "
                                  "BREAKOUT_ACC (NXS_Strategies.mqh:1548) e ORDER_BLOCK "
                                  "(NXS_Strategies.mqh, Phase 7.14) - vedi differenze di "
                                  "sostanza nel semantic/mechanism formalization di questa "
                                  "fase (filtro continuo vs stato discreto)",
            "effetto_su_altre_identita'": "NESSUNO - grep esaustivo conferma che nessun'altra "
                                          "strategia riusa g_tsiState o chiama "
                                          "NXS_Strat_TSI() (a differenza di OB_MIT per "
                                          "ORDER_BLOCK)",
        },
        "invarianti_da_preservare": [
            "Nessun cambiamento al comportamento sui passaggi D1 (la guardia agisce solo "
            "sui passaggi non-D1)",
            "Formula del doppio EMA, periodi (25/13/7), soglia di warmup (75 aggiornamenti) "
            "invariati",
            "SL/TP (NXS_DefaultSLTP) invariato",
        ],
        "test_necessari": [
            "Unit test della sola condizione di guardia in isolamento",
            "Trace diagnostico (stesso pattern non comportamentale di Phase 7.14) raccolto "
            "PRIMA e DOPO il fix su un ambiente demo/Tester, per confermare che post-fix "
            "nessuna mutazione di g_tsiState avviene su passaggi non-D1",
            "Confronto della sequenza TSI/segnali D1 post-fix osservata dal vivo con la "
            "ricostruzione Stream B di questa fase, sulla porzione di periodo che si "
            "sovrappone",
        ],
        "piano_di_parity_pre_post": [
            "Stesso schema gia' validato per ORDER_BLOCK (Phase 7.14): trace pre-fix "
            "(contaminato) + trace post-fix (atteso: solo mutazioni su passaggi D1) sullo "
            "STESSO periodo/stessi tick reali",
            "Verificare causalmente (non per PF/WR) che i valori TSI post-fix corrispondano "
            "esattamente a cio' che la ricostruzione Stream B di questa fase produce sugli "
            "stessi dati",
        ],
        "rollback_criteria": [
            "Se il trace post-fix mostra ANCORA mutazioni di stato su passaggi non-D1",
            "Se il volume di segnali D1 post-fix diverge in modo non spiegabile dalla "
            "ricostruzione Stream B di questa fase sulla stessa finestra",
        ],
        "separazione_esplicita": {
            "verifica_implementazione": "la guardia elimina strutturalmente la "
                                        "lettura/scrittura di stato sui passaggi non "
                                        "canonici - verificabile direttamente sul codice e "
                                        "col trace, INDIPENDENTEMENTE da qualunque esito "
                                        "economico",
            "validita_evidenza": "qualunque PF/WR storico pre-fix (incluso sweep37 S05, PF "
                                 "0.76) resta storico e classificato come in "
                                 "tsi_historical_evidence_map_v1.json - non viene "
                                 "'corretto retroattivamente' dal fix",
            "redditivita": "NON PRESUNTA - correggere il meccanismo di stato NON implica che "
                          "la strategia diventi profittevole; elimina solo una fonte di "
                          "rumore strutturale MOLTO piu' pervasiva di quella di ORDER_BLOCK "
                          "(100% delle barre contro un sottoinsieme) - la profittabilita' "
                          "resta una domanda separata e successiva, fuori scope di questa "
                          "fase",
        },
    }

    payload = {
        "candidate": "TSI",
        "baseline_commit": "9d674e6",
        "decision": decision,
        "decision_basis": decision_basis,
        "historical_evidence_integrity": historical_evidence_integrity,
        "historical_evidence_integrity_note": historical_evidence_integrity_note,
        "distortion_direction": distortion_direction,
        "distortion_direction_note": distortion_direction_note,
        "confidence": confidence,
        "confidence_reasoning": confidence_reasoning,
        "defect_exists_vs_material_impact": {
            "defect_exists": True,
            "defect_materially_changes_behavior": True,
            "note": "Come per ORDER_BLOCK, entrambe le domande hanno risposta affermativa - "
                    "qui con un'universalita' (100% delle barre) ancora piu' netta, coerente "
                    "con la natura di filtro ricorsivo continuo (mai autoriparante) invece "
                    "che di stato a fasi discrete.",
        },
        "scope_limits_declared": [
            "Nessun trace EA live reale raccolto in questa fase (a differenza di "
            "ORDER_BLOCK) - la quantificazione usa dati M15 ricampionati gia' disponibili, "
            "scelta esplicita giustificata dalla natura puramente matematica/deterministica "
            "del meccanismo (verificato con aritmetica esatta nei casi minimi)",
            "Periodo reale coperto: 2023-10-02 -> 2026-08-25 (fonte M15 disponibile), non "
            "l'intero storico 2019-2026 del sweep37",
            "Passaggio M5 escluso dalla quantificazione - limite INFERIORE, non sovrastima",
        ],
        "fix_proposal": fix_proposal,
        "no_optimization_no_sltp_tuning_no_parameter_sweep_no_profitability_no_promotion": True,
        "no_ea_modification_this_phase": True,
        "next_step_not_decided_here": "Nessuna promozione live, nessuna ottimizzazione. Se "
                                      "si decide di procedere: costruire il trace EA live "
                                      "reale mancante (stesso schema di Phase 7.14) prima di "
                                      "autorizzare la patch, oppure valutare se "
                                      "l'evidenza gia' raccolta qui (aritmetica esatta + dati "
                                      "reali ricampionati, 100% di universalita') sia gia' "
                                      "sufficiente per autorizzare direttamente il fix "
                                      "minimale - decisione dell'utente, non presa qui.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE717_DIR, "tsi_decision_card_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  DECISIONE: {payload['decision']}")
    print(f"  distortion_direction: {payload['distortion_direction']}")
    print(f"  confidence: {payload['confidence']}")


if __name__ == "__main__":
    main()
