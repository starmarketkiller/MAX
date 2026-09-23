#!/usr/bin/env python3
"""Phase 7.9F - punti 2, 3, 4, 5: risposta esplicita sulla semantica del
cooldown, analisi dell'architettura side-effect-prima-del-filtro con
esempio causale reale, replica esatta bit-per-bit dell'ordine dei pass
del router reale, e le due identita' esplicite (implementata vs intesa)."""
import csv
import os
import re
import sys

PHASE79F_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79F_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "e78a17e4c738586c4c16805ae8915c6e29874354"
ALLFIRES_CSV = os.path.join(PHASE79F_DIR, "raw_data", "nxs_breakoutacc_sharedstate_allfires.csv")
SUMMARY_TXT = os.path.join(PHASE79F_DIR, "raw_data", "nxs_breakoutacc_sharedstate_diag_exactorder_summary.txt")


def compute_exact_pass_order():
    profiles_path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_StrategyProfiles.mqh")
    registry_path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_StrategyRegistry.mqh")
    with open(profiles_path, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r'ENUM_TIMEFRAMES NXS_Profile_TF\(const string name\)\{(.*?)\n\}', text, re.S)
    body = m.group(1)
    pairs = re.findall(r'if\(name == "([A-Z0-9_]+)"\)\s*return (PERIOD_[A-Z0-9]+);', body)
    tfmap = dict(pairs)

    with open(registry_path, encoding="utf-8") as f:
        reg = f.read()
    idpairs = re.findall(r'if\(i==(\d+)\) return "([A-Z0-9_]+)";', reg)
    ids = [name for _, name in sorted(idpairs, key=lambda t: int(t[0]))]

    passes = []
    seen = set()
    for sid in ids:
        tf = tfmap.get(sid, "PERIOD_CURRENT")
        if tf == "PERIOD_CURRENT" or tf in seen:
            continue
        seen.add(tf)
        passes.append({"tf": tf, "first_declared_by_strategy": sid})
    return passes, len(ids)


def find_causal_example():
    with open(ALLFIRES_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # cerca la prima catena: un FIRED su TF non-D1 seguito (stessa direzione)
    # da un blocco D1 in una data nota (2019.04.18, uno dei 3 eventi gia'
    # forensicati in 7.9E).
    target_date_prefix = "2019.04.18"
    d1_blocks = [r for r in rows if r["tf"] == "PERIOD_D1" and r["bar_time"].startswith(target_date_prefix)]
    if not d1_blocks:
        return None
    first_block = d1_blocks[0]
    target_dir = first_block["raw_dir"]
    # trova l'ultimo FIRE su un TF non-D1, stessa direzione, PRIMA di questa data
    prior_fires = [r for r in rows if r["tf"] != "PERIOD_D1" and r["raw_dir"] == target_dir
                   and r["event"] == "FIRED_UPDATED_SHARED_STATE" and r["bar_time"] < first_block["bar_time"]]
    trigger = prior_fires[-1] if prior_fires else None
    return {
        "d1_blocked_event": dict(first_block),
        "triggering_non_d1_fire": dict(trigger) if trigger else None,
        "n_repeated_d1_block_log_lines_same_day": len(d1_blocks),
        "narrative": (
            f"Il {trigger['bar_time']} il pass {trigger['tf']} trova una propria Acceptance "
            f"(direzione {trigger['raw_dir']}) sui SUOI bar e aggiorna "
            f"g_breakoutAccState.lastFireTime[{'BUY' if trigger['raw_dir']=='1' else 'SELL'}] "
            f"con questo timestamp - PRIMA che questo pass venga scartato dal filtro "
            f"NXS_Profile_TF(strat)==passes[p] (perche' BREAKOUT_ACC appartiene a D1, non a "
            f"{trigger['tf']}). Il {first_block['bar_time']}, quando il pass D1 REALE trova una "
            f"propria Acceptance genuina (stessa direzione), il cooldown condiviso appare "
            f"ancora attivo a causa del fire di {trigger['tf']} - il segnale D1 viene bloccato "
            f"{len(d1_blocks)} volte nello stesso giorno (rivalutato ad ogni tick M15 finche' "
            f"la barra D1 resta la stessa)."
        ) if trigger else "nessun fire precedente trovato sullo stesso verso",
    }


def build():
    passes, n_registry = compute_exact_pass_order()
    with open(SUMMARY_TXT, encoding="utf-16") as f:
        summary = dict(ln.split("=", 1) for ln in f.read().strip().splitlines() if "=" in ln)
    causal_example = find_causal_example()

    cooldown_semantics_answer = {
        "question": "InpBreakoutAccCooldownBars=8 significa 8 barre del TF DICHIARATO della "
            "strategia (D1) o 8 barre di QUALUNQUE g_activeTF sia attivo al momento della "
            "chiamata?",
        "code_behavior_today": "8 barre di QUALUNQUE g_activeTF sia attivo al momento della "
            "chiamata (cooldownSec = 8 * PeriodSeconds(NXS_EffTF()), NXS_EffTF() cambia ad "
            "ogni pass multi-TF) - CONFERMATO dalla lettura diretta del codice "
            "(NXS_Strategies.mqh:1550-1551).",
        "documented_intent": "8 barre D1 (il timeframe dichiarato della strategia) - "
            "NESSUNA fonte documentale (vedi breakout_acc_strategy_identity_authority_v1.json) "
            "menziona o giustifica un significato diverso da questo in NESSUN momento della "
            "storia del progetto.",
        "verdict": "DISCREPANZA CONFERMATA fra comportamento del codice e intento documentato - "
            "non UNKNOWN: l'evidenza documentale e' univoca e non ambigua su questo punto "
            "specifico.",
    }

    side_effect_architecture = {
        "exact_sequence_verified": [
            "1. NXS_ActivateTF(passes[p]) - attiva gli handle indicatori per il TF del pass, "
            "imposta g_activeTF=passes[p] (NEXUS_EA_v2.mq5:225-233)",
            "2. NXS_CollectRaw(...) -> NXS_Strat_BreakoutAcc() chiamata INCONDIZIONATAMENTE "
            "(il suo gate e' solo NXS_SelectorAllows(9), indipendente dal TF attivo) - legge/"
            "scrive g_breakoutAccState USANDO tf=NXS_EffTF()=passes[p] CORRENTE",
            "3. dentro NXS_CollectRaw, righe 634-646: gate HTF applicato anch'esso con "
            "NXS_EffTF() corrente - MA questo non muta stato persistente, solo filtra out[]",
            "4. tornati a NXS_CollectAllSignals (riga 710): "
            "if(NXS_Profile_TF(tmp[k].stratName) != passes[p]) continue; - SOLO QUI il "
            "risultato del pass NON-D1 viene scartato da out[] - MA lo stato "
            "g_breakoutAccState.lastFireTime GIA' MUTATO al passo 2 NON viene ripristinato o "
            "annullato da questo scarto",
        ],
        "legitimate_purpose_for_non_d1_calls": "NESSUNO identificato. NXS_Strat_BreakoutAcc() "
            "non ha alcun ruolo dichiarato o utile durante i pass M5/M15/M30/H1/H4 - il suo "
            "risultato viene sempre scartato in quei pass (il filtro TF lo garantisce). L'unico "
            "effetto osservabile della sua esecuzione durante quei pass e' la mutazione dello "
            "stato condiviso - un side-effect puro, senza controparte funzionale.",
        "classification": "discard output, keep side effect - un anti-pattern chiaro: la "
            "funzione viene chiamata per il suo VALORE DI RITORNO (che viene scartato nei pass "
            "sbagliati), ma ha un effetto collaterale (mutazione di stato globale) che "
            "sopravvive allo scarto.",
        "minimal_causal_example_from_real_run": causal_example,
    }

    exact_router_replication = {
        "method": "Calcolato PROGRAMMATICAMENTE (non a mano) attraversando NXS_StrategyIdAt(0.."
            f"{n_registry - 1}) in ordine e NXS_Profile_TF(id) per ciascuno, deduplicando al "
            "primo TF distinto incontrato - IDENTICA logica del router reale "
            "(NEXUS_EA_v2.mq5:683-689).",
        "exact_pass_order_verified": passes,
        "diagnostic_rerun_with_exact_order": {
            "script": "server/research_scripts/NXS_BreakoutAccSharedStateDiagnostic.mq5 "
                "(aggiornato in questa fase con l'ordine esatto: {})".format(
                    ",".join(p["tf"].replace("PERIOD_", "") for p in passes)),
            "n_d1_raw_accept_isolated": int(summary["n_d1_raw_accept_isolated"]),
            "n_d1_cooldown_pass_isolated": int(summary["n_d1_cooldown_pass_isolated"]),
            "n_d1_fired_with_shared_state_exact_order": int(summary["n_d1_fired_with_shared_state"]),
            "n_other_tf_fires": int(summary["n_other_tf_fires_that_touched_shared_state"]),
        },
        "target_declared": "actual EA GENERATED = 4, replica = 4, timestamp/direzione esatti 4/4",
        "target_achieved": False,
        "actual_result": f"replica con ordine ESATTO produce {summary['n_d1_fired_with_shared_state']} "
            "(non 4) - il meccanismo dominante e' confermato con l'ordine reale (collasso "
            "quasi totale, stessa direzione/ordine di grandezza), ma la cifra ESATTA non e' "
            "riprodotta. Cause plausibili non verificate in questa fase: tassi di successo "
            "dell'attivazione indicatori diversi da 100% sui TF non-D1 (mai testati "
            "individualmente, a differenza di D1 - vedi 7.9E Esperimento A), o altre "
            "differenze minori non isolate. Dichiarato onestamente come limite - NON forzato "
            "a coincidere.",
        "diagnostic_only_disclaimer": "Questo esperimento NON stabilisce che il comportamento "
            "sia scientificamente corretto - stabilisce solo che il MECCANISMO (contaminazione "
            "cross-TF dello stato) e' la causa dominante e verificabile del collasso "
            "80(/95/75)->4.",
    }

    two_identities = {
        "BREAKOUT_ACC_IMPLEMENTED_V1": {
            "description": "Semantica LIVE corrente, inclusa la condivisione cross-TF dello "
                "stato di cooldown.",
            "setup": "range D1, 20 barre, offset shift[3..22]",
            "trigger": "doppia chiusura D1 consecutiva oltre il range",
            "cooldown_scope": "condiviso fra M5/M15/M30/H1/H4/D1 - un fire su QUALUNQUE di "
                "questi timeframe blocca il cooldown per la direzione corrispondente su TUTTI "
                "gli altri, incluso D1",
            "empirical_result_this_window": "4 trade in 7,5 anni (verificato riproducibile, "
                "7.9D)",
            "validated": False,
        },
        "BREAKOUT_ACC_INTENDED_D1_V1": {
            "description": "Semantica scoped a D1 come documentato da TUTTE le fonti "
                "identificate (vedi breakout_acc_strategy_identity_authority_v1.json) - "
                "supportata da evidenza documentale, non congetturata.",
            "setup": "range D1, 20 barre, offset shift[3..22] (identico)",
            "trigger": "doppia chiusura D1 consecutiva oltre il range (identico)",
            "cooldown_scope": "isolato a D1 - solo le valutazioni sul pass D1 leggono/scrivono "
                "il proprio stato di cooldown",
            "empirical_result_this_window": "95 post-cooldown / 75 post-HTF (7.9E Esperimento A, "
                "isolato) - MAI eseguito come Serious backtest, solo come esperimento "
                "diagnostico bar-based",
            "validated": False,
        },
        "note": "Nessuna delle due e' dichiarata 'validata' in questa fase - la scelta di quale "
            "sia la strategia canonica e' oggetto del verdetto, non un fatto gia' assunto.",
    }

    return {
        "phase": "7.9F", "candidate": "BREAKOUT_ACC", "baseline_commit": BASELINE_COMMIT,
        "no_live_ea_modification": True, "no_python_modification": True,
        "no_performance_backtest": True, "no_optimization": True,
        "2_cooldown_semantics_answer": cooldown_semantics_answer,
        "3_side_effect_before_filter_architecture": side_effect_architecture,
        "4_exact_router_replication": exact_router_replication,
        "5_two_identities": two_identities,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79F_DIR, "breakout_acc_implemented_vs_intended_semantics_v1.json"), doc)
    save_json(os.path.join(PHASE79F_DIR, "breakout_acc_exact_router_replication_v1.json"),
              wrap_with_provenance(payload["4_exact_router_replication"], os.path.basename(__file__)))
    print(f"canonical_sha256={doc['canonical_sha256']}")
    return doc


if __name__ == "__main__":
    main()
