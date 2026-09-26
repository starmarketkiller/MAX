#!/usr/bin/env python3
"""Phase 7.14 punto 6 - parity A (EA pre-fix) vs B (EA post-fix) vs C
(ricostruzione TF-scoped, Phase 7.13). Obiettivo dichiarato: NON forzare
B=C, spiegare ogni residuo importante.
"""
import csv
import os
import sys
from collections import Counter

PHASE714_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE713_DIR = os.path.abspath(os.path.join(PHASE714_DIR, "..", "phase7_13"))
ROOT = os.path.abspath(os.path.join(PHASE714_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json, file_sha256  # noqa: E402

PRE_CSV = os.path.join(PHASE714_DIR, "nxs_orderblock_realtrace_diag_prefix.csv")
POST_CSV = os.path.join(PHASE714_DIR, "nxs_orderblock_realtrace_diag_postfix.csv")


def _load(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _summarize(rows, label):
    by_tf = {}
    n_signals_canonical = 0
    n_signals_non_canonical = 0
    canonical_tf = rows[0]["canonical_tf"] if rows else None
    canonical_events = []
    for r in rows:
        by_tf[r["tf"]] = by_tf.get(r["tf"], 0) + 1
        if r["signal_dir"] in ("BUY", "SELL"):
            if r["tf"] == canonical_tf:
                n_signals_canonical += 1
                canonical_events.append({"close_time_srv": r["close_time_srv"], "side": r["side"],
                                         "signal_dir": r["signal_dir"]})
            else:
                n_signals_non_canonical += 1
    return {
        "label": label, "n_rows_total": len(rows), "rows_by_tf": by_tf,
        "canonical_tf": canonical_tf,
        "n_signals_canonical_kept": n_signals_canonical,
        "n_signals_non_canonical_discarded": n_signals_non_canonical,
        "canonical_events": canonical_events,
    }


def build():
    pre_rows = _load(PRE_CSV)
    post_rows = _load(POST_CSV)
    A = _summarize(pre_rows, "A_EA_PRE_FIX")
    B = _summarize(post_rows, "B_EA_POST_FIX")

    # C: ricostruzione TF-scoped di Phase 7.13 (ab_simulation_v1.json, Stream B) -
    # periodo IDENTICO (M15-derivato 2023-10-02..2026-08-25), ma dati/orario di
    # riferimento COSTRUITI per resampling deterministico da M15, non gli stessi
    # tick reali del Tester - quindi un confronto A/B vs C e' STRUTTURALE
    # (stesso meccanismo, stessa forma), non un confronto evento-per-evento
    # sugli stessi timestamp esatti.
    ab13 = load_json(os.path.join(PHASE713_DIR, "ab_simulation_v1.json"))["payload"]
    C = {
        "label": "C_TF_SCOPED_RECONSTRUCTION_PHASE_7_13",
        "source": "server/research_scripts/phase7/phase7_13/ab_simulation_v1.json (Stream B)",
        "n_signals_canonical_kept": ab13["stream_b_generated_d1_total"],
        "period_covered": ab13["period_covered"],
        "data_basis": "serie M15 ricampionata deterministicamente (non gli stessi tick MT5 del "
                      "Tester) - confronto STRUTTURALE, non evento-per-evento sugli stessi timestamp",
    }

    # B vs C: B ha eliminato ogni mutazione non canonica? (verifica diretta,
    # falsificabile: post-fix, l'unico TF che deve comparire nelle righe e' il canonico)
    non_canonical_rows_in_B = sum(v for tf, v in B["rows_by_tf"].items() if tf != B["canonical_tf"])
    guard_fully_effective = (non_canonical_rows_in_B == 0)

    # A vs B: quanto e' cambiato il conteggio dei segnali D1 tenuti fra pre e post fix
    # sullo STESSO periodo/stessi tick reali (confronto diretto, stessi timestamp).
    #
    # NOTA IMPORTANTE scoperta in questa fase: pre-fix, alcuni giorni D1 mostrano
    # PIU' di un evento RETEST_SIGNAL_FIRED con la STESSA data (fino a 6 nello
    # stesso giorno) - NON e' un artefatto del Tester: post-fix questo fenomeno
    # scompare COMPLETAMENTE (0 duplicati su 8 eventi). Causa identificata:
    # lastBarTime e' un campo dello stesso SNXSOBState condiviso da TUTTI i
    # passaggi TF - un passaggio H4/H1/M30/M15/M5 che tocca lo stato SOVRASCRIVE
    # lastBarTime con il PROPRIO timestamp, cosi' il gate "nuova barra" del
    # passaggio D1 stesso viene disfatto: al richiamo successivo D1 vede
    # lastBarTime != curBar0 (perche' un TF piu' veloce lo ha appena
    # sovrascritto) ed entra di nuovo nel ramo "nuova barra" PIU' VOLTE nello
    # stesso giorno solare - una manifestazione ANCORA PIU' severa della
    # contaminazione di quanto descritto in Phase 7.13 (non solo "una zona
    # rubata da un TF veloce", ma "il gate temporale di D1 stesso e' rotto").
    # Ogni occorrenza e' comunque un candidate signal REALE che il router
    # avrebbe valutato - non deduplichiamo, contiamo con un multiset (Counter).
    a_events = Counter((e["close_time_srv"], e["side"], e["signal_dir"]) for e in A["canonical_events"])
    b_events = Counter((e["close_time_srv"], e["side"], e["signal_dir"]) for e in B["canonical_events"])
    a_keys_only_date_side = Counter((e["close_time_srv"], e["side"]) for e in A["canonical_events"])
    b_keys_only_date_side = Counter((e["close_time_srv"], e["side"]) for e in B["canonical_events"])
    matched_same_dir_count = sum((a_events & b_events).values())
    a_key_multiset = Counter((e["close_time_srv"], e["side"]) for e in A["canonical_events"])
    b_key_multiset = Counter((e["close_time_srv"], e["side"]) for e in B["canonical_events"])
    only_in_a_count = sum((a_key_multiset - b_key_multiset).values())
    only_in_b_count = sum((b_key_multiset - a_key_multiset).values())
    n_days_with_multiple_fires_prefix = sum(1 for k, v in a_keys_only_date_side.items() if v > 1)
    max_fires_same_day_prefix = max(a_keys_only_date_side.values()) if a_keys_only_date_side else 0
    n_days_with_multiple_fires_postfix = sum(1 for k, v in b_keys_only_date_side.items() if v > 1)

    payload = {
        "A_pre_fix": A,
        "B_post_fix": B,
        "C_tf_scoped_reconstruction": C,
        "guard_effectiveness_check": {
            "non_canonical_rows_present_in_B": non_canonical_rows_in_B,
            "guard_fully_effective_zero_non_canonical_mutations": guard_fully_effective,
            "note": "Verifica diretta e falsificabile: con la guardia applicata, il router non "
                    "deve MAI raggiungere il punto di lettura/scrittura dello stato su un "
                    "passaggio non canonico - quindi zero righe non-D1 nel trace post-fix.",
        },
        "a_vs_b_same_real_ticks_comparison": {
            "a_total_canonical_kept_raw_events": A["n_signals_canonical_kept"],
            "b_total_canonical_kept_raw_events": B["n_signals_canonical_kept"],
            "n_matched_same_date_side_direction_multiset": matched_same_dir_count,
            "n_only_in_a_suppressed_post_fix_multiset": only_in_a_count,
            "n_only_in_b_appeared_post_fix_multiset": only_in_b_count,
            "note": "Conteggio a multiset (Counter), non deduplicato per data - vedi "
                    "'repeated_fires_same_day_finding' per la spiegazione causale del perche' "
                    "un singolo giorno D1 puo' comparire piu' volte pre-fix.",
        },
        "repeated_fires_same_day_finding": {
            "description": "Pre-fix, alcuni giorni D1 mostrano PIU' di un evento "
                           "RETEST_SIGNAL_FIRED nello stesso giorno solare (fino a "
                           f"{max_fires_same_day_prefix} volte) - post-fix questo fenomeno "
                           "scompare completamente.",
            "n_distinct_d1_days_with_multiple_fires_pre_fix": n_days_with_multiple_fires_prefix,
            "max_fires_same_calendar_day_pre_fix": max_fires_same_day_prefix,
            "n_distinct_d1_days_with_multiple_fires_post_fix": n_days_with_multiple_fires_postfix,
            "causal_explanation": "lastBarTime e' un campo dello STESSO SNXSOBState condiviso da "
                                  "tutti i passaggi TF - un passaggio non canonico (H4/H1/M30/M15/"
                                  "M5) che tocca lo stato sovrascrive lastBarTime con il PROPRIO "
                                  "timestamp, disfacendo il gate 'nuova barra' del passaggio D1 "
                                  "stesso: alla chiamata D1 successiva, lastBarTime != curBar0 "
                                  "(sovrascritto da un TF piu' veloce) e D1 rientra nel ramo "
                                  "'nuova barra' piu' volte nello stesso giorno solare - una "
                                  "manifestazione ANCORA PIU' severa della contaminazione di "
                                  "quanto descritto in Phase 7.13 (non solo 'una zona rubata da "
                                  "un TF veloce', ma 'il gate temporale di D1 stesso e' rotto').",
            "confirms_guard_fixes_this_too": n_days_with_multiple_fires_postfix == 0,
        },
        "b_vs_c_structural_comparison": {
            "b_count": B["n_signals_canonical_kept"],
            "c_count": C["n_signals_canonical_kept"],
            "difference": B["n_signals_canonical_kept"] - C["n_signals_canonical_kept"],
            "goal_is_not_b_equals_c": True,
            "explanation_of_residual": (
                "B usa tick reali MT5 (Model=4) sullo storico effettivo del broker per il "
                "simbolo GOLD; C usa una serie M15 derivata per resampling deterministico "
                "(fonte diversa, granularita' diversa, convenzione di confine giorno dedotta "
                "empiricamente - vedi phase7_13/build_multi_tf_dataset.py). Entrambi confermano "
                "STRUTTURALMENTE lo stesso meccanismo (guardia TF-scoped elimina la "
                "contaminazione) - la vicinanza numerica (8 vs 7) resta un'osservazione valida."
            ),
            "residual_causally_isolated": False,
            "correction_note_phase_7_15": (
                "REVISIONE TRACCIATA (Phase 7.15, ea_python_comparison_classification_v1.json): "
                "l'affermazione originale di questo campo ('un residuo diverso da zero e' atteso "
                "e non invalida la correzione... non devono coincidere evento-per-evento') era "
                "un'asserzione GENERICA sulla diversita' delle fonti, non una ricostruzione "
                "causale. Verificato in Phase 7.15: SOLO 1 degli 8 eventi B e 7 eventi C "
                "condivide la stessa data+direzione (2025-06-26 BUY) - gli altri cadono su date "
                "COMPLETAMENTE diverse. Un confronto diretto delle barre D1 sulle date contestate "
                "fra due fonti indipendenti (export MT5 reale phase7_9h vs serie M15 ricampionata "
                "phase7_13) mostra barre NUMERICAMENTE IDENTICHE (diff=0.0 su tutte le 13 date "
                "verificate) - ESCLUDE che 'quel giorno ha un prezzo diverso' sia la spiegazione. "
                "Classificazione corretta: CANDIDATE_CAUSE_NOT_ISOLATED (path-dependence della "
                "state machine su un punto imprecisato a monte nella storia pluriennale, mai "
                "isolato) - non piu' 'residuo spiegato dalla diversita' delle fonti'. Il fix "
                "resta comunque validato dal confronto A/B (livello 1, stessi tick reali, "
                "MAI rimesso in discussione) - questa correzione riguarda SOLO il confronto "
                "strutturale di livello 2 (B vs C, fonti diverse)."
            ),
        },
        "not_a_backtest_campaign": True,
        "not_used_for_profitability": True,
        "not_used_for_optimization": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE714_DIR, "parity_comparison_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  A (pre-fix) canonici tenuti: {payload['A_pre_fix']['n_signals_canonical_kept']}")
    print(f"  B (post-fix) canonici tenuti: {payload['B_post_fix']['n_signals_canonical_kept']}")
    print(f"  C (ricostruzione 7.13) canonici: {payload['C_tf_scoped_reconstruction']['n_signals_canonical_kept']}")
    print(f"  righe non canoniche in B: {payload['guard_effectiveness_check']['non_canonical_rows_present_in_B']}")
    print(f"  guardia efficace al 100%: {payload['guard_effectiveness_check']['guard_fully_effective_zero_non_canonical_mutations']}")
    ab = payload['a_vs_b_same_real_ticks_comparison']
    print(f"  A/B multiset: {ab['n_matched_same_date_side_direction_multiset']} uguali, "
          f"{ab['n_only_in_a_suppressed_post_fix_multiset']} solo in A, "
          f"{ab['n_only_in_b_appeared_post_fix_multiset']} solo in B")
    rf = payload['repeated_fires_same_day_finding']
    print(f"  giorni D1 con fire multipli pre-fix: {rf['n_distinct_d1_days_with_multiple_fires_pre_fix']} "
          f"(max {rf['max_fires_same_calendar_day_pre_fix']}x) -> post-fix: "
          f"{rf['n_distinct_d1_days_with_multiple_fires_post_fix']}")


if __name__ == "__main__":
    main()
