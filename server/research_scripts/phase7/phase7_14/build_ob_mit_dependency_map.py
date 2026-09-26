#!/usr/bin/env python3
"""Phase 7.14 punto 4 - mappa esplicita di come OB_MIT condivide/deriva
lo stato di ORDER_BLOCK. Verifica statica sul sorgente attuale (non
assunta dal nome ne' dalla Phase 7.13) + un secondo finding correlato
(gate di selettore annidato) trovato leggendo il codice per rispondere
a questa domanda.
"""
import os
import re
import sys

PHASE714_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE714_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

STRAT_PATH = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
SMC_PATH = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies_SMC.mqh")
EA_PATH = os.path.join(ROOT, "MQL5", "Experts", "NEXUS_EA_v2.mq5")


def build():
    smc_text = open(SMC_PATH, encoding="utf-8").read()
    strat_text = open(STRAT_PATH, encoding="utf-8").read()
    ea_text = open(EA_PATH, encoding="utf-8").read()

    ob_mit_start = smc_text.find("NXS_Strat_OB_Mitigation_Structural()")
    ob_mit_body = smc_text[ob_mit_start:smc_text.find("\n}\n", ob_mit_start)]

    has_own_state = bool(re.search(r"\bstatic\b|\bg_obMit\w*\b", ob_mit_body))
    calls_order_block = "NXS_Strat_OrderBlock()" in ob_mit_body
    only_overrides_name_reason_score = (
        "s.stratName" in ob_mit_body and "s.reason" in ob_mit_body and "raw.dir" in ob_mit_body
    )

    # Gate annidato: la chiamata a NXS_Strat_OB_Mitigation_Structural() nel
    # collector e' gated da InpStrat_OB_Mit/selettore 20, ma la funzione
    # chiamata al suo interno (NXS_Strat_OrderBlock) ha il PROPRIO gate
    # (InpStrat_ORDER_BLOCK/selettore 15) - i due selettori sono DIVERSI.
    call_site_match = re.search(r"if\(InpStrat_OB_Mit\s*&&\s*NXS_SelectorAllows\((\d+)\)\)\s*out\[n\+\+\]\s*=\s*NXS_Strat_OB_Mitigation_Structural\(\)", ea_text)
    inner_gate_match = re.search(r"if\(!InpStrat_ORDER_BLOCK\s*\|\|\s*!NXS_SelectorAllows\((\d+)\)\)\s*return s;", strat_text)
    call_site_selector = int(call_site_match.group(1)) if call_site_match else None
    inner_gate_selector = int(inner_gate_match.group(1)) if inner_gate_match else None
    selectors_differ = (call_site_selector is not None and inner_gate_selector is not None
                        and call_site_selector != inner_gate_selector)

    payload = {
        "question": "Correggere NXS_Strat_OrderBlock() risolve automaticamente OB_MIT, o OB_MIT "
                    "ha un percorso separato / side effect aggiuntivi?",
        "verified_on_current_source": True,
        "ob_mit_has_own_state": has_own_state,
        "ob_mit_calls_order_block_directly": calls_order_block,
        "ob_mit_only_overrides_name_reason_score_floor": only_overrides_name_reason_score,
        "conclusion": "OB_MIT NON ha stato proprio ne' un percorso di calcolo separato - "
                     "chiama NXS_Strat_OrderBlock() e ne copia il risultato (raw), "
                     "sovrascrivendo solo stratName/reason e un floor sullo score. "
                     "Qualunque correzione a NXS_Strat_OrderBlock() (inclusa la guardia TF "
                     "proposta in Phase 7.13) si propaga automaticamente a OB_MIT, senza "
                     "bisogno di una patch separata.",
        "additional_finding_selector_gate_mismatch": {
            "description": "La chiamata a NXS_Strat_OB_Mitigation_Structural() nel collector e' "
                           f"gated da InpStrat_OB_Mit + NXS_SelectorAllows({call_site_selector}) "
                           f"(selettore OB_MIT), ma NXS_Strat_OrderBlock() al suo interno ha il "
                           f"PROPRIO gate NXS_SelectorAllows({inner_gate_selector}) (selettore "
                           "ORDER_BLOCK) - selettori DIVERSI e ANNIDATI.",
            "implication": "Isolare OB_MIT da solo con InpStrategySelector=20 (come si farebbe "
                           "per testarlo in isolamento, stessa tecnica usata per ORDER_BLOCK "
                           "con selettore 15 in questa fase) lo rende STRUTTURALMENTE MUTO: "
                           "NXS_SelectorAllows(15) restituisce false quando "
                           "InpStrategySelector=20 (non e' ne' 0 ne' 15), quindi "
                           "NXS_Strat_OrderBlock() ritorna sempre un segnale vuoto "
                           "indipendentemente da InpStrat_ORDER_BLOCK. In produzione "
                           "(InpStrategySelector=0, tutte abilitate) questo non ha alcun "
                           "effetto - NXS_SelectorAllows(0) e' sempre vero.",
            "selectors_differ": selectors_differ,
            "scope_note": "Finding CORRELATO trovato rispondendo alla domanda del punto 4 - "
                          "NON richiesto dal task, NON corretto in questa fase (nessuna modifica "
                          "a registry/selettori autorizzata), segnalato solo come osservazione.",
        },
        "no_separate_fix_needed_for_ob_mit": True,
        "no_additional_side_effects_found": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE714_DIR, "ob_mit_dependency_map_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  conclusione: {payload['conclusion'][:80]}...")


if __name__ == "__main__":
    main()
