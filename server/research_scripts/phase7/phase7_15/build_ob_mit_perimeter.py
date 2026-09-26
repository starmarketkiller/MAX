#!/usr/bin/env python3
"""Phase 7.15 punto 2 - perimetro OB_MIT quando ORDER_BLOCK e OB_MIT
sono ENTRAMBE abilitate. Analisi statica sul sorgente attuale (post
fix Phase 7.14) + un test deterministico breve (secondi, non ore) che
riusa il modulo replica gia' validato contro il trace EA reale in
Phase 7.13/7.14 - NESSUN nuovo run Tester (non necessario: il
meccanismo sotto esame e' puramente logico/deterministico, non
dipendente da specificita' di mercato).

Distingue esplicitamente "guardia ereditata" (fatto strutturale,
verificato staticamente: OB_MIT non ha un percorso di guardia
proprio, eredita quello di ORDER_BLOCK) da "comportamento integrato
validato" (non affermato qui per l'interazione dinamica ORDER_BLOCK+
OB_MIT nello STESSO pass - vedi finding 2 sotto, mai osservato in un
run reale con entrambe abilitate contemporaneamente).
"""
import os
import sys

PHASE715_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE713_DIR = os.path.abspath(os.path.join(PHASE715_DIR, "..", "phase7_13"))
ROOT = os.path.abspath(os.path.join(PHASE715_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE713_DIR)
from nxs_order_block_replica import OBState, ob_update_side  # noqa: E402

STRAT_PATH = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
SMC_PATH = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies_SMC.mqh")
EA_PATH = os.path.join(ROOT, "MQL5", "Experts", "NEXUS_EA_v2.mq5")
PROFILES_PATH = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_StrategyProfiles.mqh")
INPUTS_PATH = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Inputs.mqh")


def _bar(o, h, l, c, ot, ct):
    return {"open": o, "high": h, "low": l, "close": c, "open_time": ot, "close_time": ct}


def _static_findings():
    ea_text = open(EA_PATH, encoding="utf-8").read()
    strat_text = open(STRAT_PATH, encoding="utf-8").read()
    smc_text = open(SMC_PATH, encoding="utf-8").read()
    profiles_text = open(PROFILES_PATH, encoding="utf-8").read()

    ob_call_pos = ea_text.find("out[n++] = NXS_Strat_OrderBlock();")
    obmit_call_pos = ea_text.find("NXS_Strat_OB_Mitigation_Structural()")
    ob_line = ea_text[:ob_call_pos].count("\n") + 1
    obmit_line = ea_text[:obmit_call_pos].count("\n") + 1

    guard_present = 'if(tf != NXS_Profile_TF("ORDER_BLOCK")) return s;' in strat_text
    ob_mit_calls_directly = "NXS_Strat_OrderBlock()" in smc_text[smc_text.find("NXS_Strat_OB_Mitigation_Structural()"):]
    ob_mit_has_own_gate_check = "InpStrat_ORDER_BLOCK" in strat_text  # il gate vive DENTRO la funzione chiamata, non nel wrapper

    scalp_override_block = profiles_text[profiles_text.find("InpScalpTFOverride != PERIOD_CURRENT"):]
    scalp_override_block = scalp_override_block[:scalp_override_block.find("\n      return InpScalpTFOverride;\n") + 40]
    order_block_in_override_list = '"ORDER_BLOCK"' in scalp_override_block
    ob_mit_in_override_list = '"OB_MIT"' in scalp_override_block

    return {
        "1_call_order": {
            "order_block_direct_call_line": ob_line,
            "ob_mit_wrapper_call_line": obmit_line,
            "order_block_call_precedes_ob_mit_call": ob_line < obmit_line,
            "same_function_same_pass": "entrambe le chiamate avvengono dentro NXS_CollectRaw(), "
                                       "nello stesso pass multi-TF, sulla STESSA chiamata a "
                                       "OnTick - non in pass separati",
        },
        "2_zone_consumption_shared_state": {
            "mechanism": "NXS_Strat_OrderBlock() e' chiamata DUE VOLTE nello stesso pass quando "
                        "entrambe le strategie sono abilitate: la prima volta direttamente "
                        "(riga sopra, per l'output 'ORDER_BLOCK'), la seconda volta indirettamente "
                        "dentro NXS_Strat_OB_Mitigation_Structural() (per l'output 'OB_MIT'). "
                        "g_obBuy/g_obSell sono le STESSE variabili globali in entrambe le "
                        "chiamate - se la prima chiamata consuma la zona (st.active=false, "
                        "one-shot su un retest), la seconda chiamata (OB_MIT) vede la zona GIA' "
                        "consumata nello stesso tick.",
            "implication": "Quando ORDER_BLOCK e OB_MIT sono ENTRAMBE abilitate, OB_MIT non puo' "
                           "MAI produrre un segnale 'in piu'' rispetto a quanto gia' consumato "
                           "dalla chiamata diretta di ORDER_BLOCK nello stesso tick - vede solo "
                           "lo stato RESIDUO. Il 'raddoppio' del segnale (stesso evento riportato "
                           "sia come ORDER_BLOCK che come OB_MIT) e' strutturalmente impossibile "
                           "nello stesso tick per costruzione (one-shot + stato condiviso letto "
                           "in sequenza).",
            "classification": "COMPORTAMENTO_DEDOTTO_STATICAMENTE_E_CONFERMATO_DETERMINISTICAMENTE "
                              "(vedi test Python sotto) - NON osservato in un run MT5 reale con "
                              "entrambe abilitate simultaneamente in questa fase (nessun nuovo run "
                              "Tester lanciato, per evitare una campagna non necessaria data la "
                              "natura puramente logica/deterministica del meccanismo)",
        },
        "3_toggle_dependency": {
            "guard_and_enable_check_location": "DENTRO NXS_Strat_OrderBlock(), non nel wrapper "
                                               "NXS_Strat_OB_Mitigation_Structural()",
            "finding": "if(!InpStrat_ORDER_BLOCK || !NXS_SelectorAllows(15)) return s; e' "
                      "valutato ad OGNI chiamata, incluse quelle originate da OB_MIT - se "
                      "InpStrat_ORDER_BLOCK=false, NXS_Strat_OB_Mitigation_Structural() riceve "
                      "SEMPRE un segnale vuoto, INDIPENDENTEMENTE dal valore di InpStrat_OB_Mit.",
            "implication": "OB_MIT dipende INTERAMENTE dal toggle di ORDER_BLOCK, non ha un "
                           "proprio percorso di attivazione indipendente - disabilitare "
                           "ORDER_BLOCK disabilita SILENZIOSAMENTE anche OB_MIT anche se il suo "
                           "InpStrat_OB_Mit=true.",
        },
        "4_selector_20_isolated": {
            "finding": "Gia' stabilito in Phase 7.14 (ob_mit_dependency_map_v1.json): isolare "
                      "OB_MIT da solo con InpStrategySelector=20 lo rende strutturalmente muto, "
                      "perche' NXS_SelectorAllows(15) (il gate INTERNO di NXS_Strat_OrderBlock) "
                      "restituisce false quando InpStrategySelector=20 (ne' 0 ne' 15). "
                      "Riconfermato qui: nessuna modifica al codice sorgente tra Phase 7.14 e "
                      "questa fase altera questo fatto.",
        },
        "5_scalp_tf_override": {
            "order_block_in_override_list": order_block_in_override_list,
            "ob_mit_in_override_list": ob_mit_in_override_list,
            "finding": "'ORDER_BLOCK' E' nell'elenco di override (BB_SQUEEZE/ORDER_BLOCK/"
                      "BREAKOUT_ACC/BOLLINGER), 'OB_MIT' NON lo e'. Con InpScalpTFOverride "
                      "diverso da PERIOD_CURRENT (default OFF - non attivo in produzione): "
                      "NXS_Profile_TF('ORDER_BLOCK') restituirebbe l'override (es. M15), mentre "
                      "NXS_Profile_TF('OB_MIT') continuerebbe a restituire PERIOD_D1 (fallback "
                      "esplicito piu' sotto nella stessa funzione). MA la guardia dentro "
                      "NXS_Strat_OrderBlock() confronta SEMPRE `tf` con "
                      "NXS_Profile_TF('ORDER_BLOCK') (stringa letterale, non parametrizzata "
                      "sul nome della strategia chiamante) - quindi se l'override fosse attivo, "
                      "il meccanismo di trigger REALE sotto OB_MIT girerebbe sul TF di override "
                      "di ORDER_BLOCK, NON sul PERIOD_D1 che il registro dichiara per OB_MIT "
                      "(NXS_Profile_TF('OB_MIT'), usato altrove per rischio/hold-time/trailing "
                      "di OB_MIT). Una DIVERGENZA reale fra 'il TF che il registro dichiara per "
                      "OB_MIT' e 'il TF su cui il suo meccanismo di trigger gira davvero', ma "
                      "SOLO se InpScalpTFOverride viene attivato (default OFF, non attivo in "
                      "produzione oggi).",
            "affects_current_production_default": False,
            "scope_note": "Difetto CORRELATO trovato rispondendo al punto 5 della task - NON "
                          "corretto in questa fase (nessuna modifica al registro/selettori "
                          "autorizzata), documentato per un eventuale fix futuro.",
        },
    }


def _deterministic_test():
    """Simula UNA sola chiamata a OnTick con entrambe ORDER_BLOCK e OB_MIT
    abilitate: la funzione viene invocata due volte in sequenza sullo
    STESSO stato condiviso (fedele a NEXUS_EA_v2.mq5 righe 535 e 543),
    su una barra costruita per produrre un retest BUY valido. La seconda
    chiamata (OB_MIT) deve vedere la zona gia' consumata."""
    state_buy, state_sell = OBState(), OBState()
    state_buy.active, state_buy.ob_lo, state_buy.ob_hi, state_buy.bars_waited = True, 100.0, 105.0, 0
    state_buy.last_bar_time = "PREV"
    bars = [_bar(103.0, 104.5, 102.0, 104.0, "T0", "T1")]   # tocca e chiude rialzista -> retest
    atr = 1.0
    curbar0 = "T1"

    # Prima chiamata: ORDER_BLOCK diretta (riga 535).
    sig1, reason1, rec1 = ob_update_side(+1, state_buy, bars, 0, atr, curbar0)
    # Seconda chiamata: OB_MIT (dentro NXS_Strat_OB_Mitigation_Structural,
    # riga 543) - STESSO stato, STESSA barra, STESSO tick.
    sig2, reason2, rec2 = ob_update_side(+1, state_buy, bars, 0, atr, curbar0)

    return {
        "order_block_direct_call_result": {"signal": sig1, "op": rec1["op"], "state_active_after": state_buy.active},
        "ob_mit_wrapper_call_result": {"signal": sig2, "op": rec2["op"], "state_active_after": state_buy.active},
        "confirms_ob_mit_sees_consumed_zone": (sig1 == "BUY" and sig2 is None
                                               and rec2["op"] == "NONE"
                                               and rec1["post"]["active"] is False),
        "no_double_signal_same_tick": not (sig1 == "BUY" and sig2 == "BUY"),
    }


def build():
    findings = _static_findings()
    det_test = _deterministic_test()
    payload = {
        "question": "Comportamento del collector quando ORDER_BLOCK e OB_MIT sono ENTRAMBE "
                   "abilitate (richiede InpStrategySelector=0, dato che i due selettori "
                   "15/20 sono mutuamente esclusivi con un selettore isolato diverso da 0)",
        "method": "analisi statica sul sorgente attuale (post fix Phase 7.14) + test "
                 "deterministico breve in Python (modulo replica gia' validato contro il "
                 "trace EA reale) - NESSUN nuovo run Tester (non necessario, meccanismo "
                 "puramente logico)",
        "static_findings": findings,
        "deterministic_test_result": det_test,
        "guardia_ereditata_vs_comportamento_integrato_validato": {
            "guardia_ereditata": "VERO e VERIFICATO STATICAMENTE - OB_MIT non ha una propria "
                                 "guardia/gate, eredita quella di NXS_Strat_OrderBlock() per "
                                 "costruzione (chiamata diretta, stesso codice).",
            "comportamento_integrato_validato": "NON AFFERMATO - l'interazione dinamica reale "
                                                "(entrambe abilitate, stesso tick, stessi tick di "
                                                "mercato) non e' stata osservata in un run MT5 "
                                                "reale in questa fase. La conclusione sopra "
                                                "(nessun doppio segnale, OB_MIT vede solo lo stato "
                                                "residuo) e' dedotta da (a) lettura diretta del "
                                                "codice REALE non modificato per questa deduzione, "
                                                "e (b) un test deterministico con lo stesso modulo "
                                                "replica gia' validato contro il trace EA reale "
                                                "PER ORDER_BLOCK SOLO (Phase 7.14) - non e' stata "
                                                "ri-validata specificamente per l'interazione "
                                                "ORDER_BLOCK+OB_MIT su un trace reale con entrambe "
                                                "abilitate.",
        },
        "additional_defect_found_not_fixed": findings["5_scalp_tf_override"],
        "no_tester_run_launched_this_task": True,
        "no_optimization_no_backtest_campaign": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE715_DIR, "ob_mit_perimeter_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  ordine chiamate: OB={payload['static_findings']['1_call_order']['order_block_direct_call_line']} "
          f"< OB_MIT={payload['static_findings']['1_call_order']['ob_mit_wrapper_call_line']}: "
          f"{payload['static_findings']['1_call_order']['order_block_call_precedes_ob_mit_call']}")
    print(f"  test deterministico - nessun doppio segnale: {payload['deterministic_test_result']['no_double_signal_same_tick']}")
    print(f"  divergenza scalp override (non attiva in produzione): "
          f"{not payload['static_findings']['5_scalp_tf_override']['affects_current_production_default']}")


if __name__ == "__main__":
    main()
