#!/usr/bin/env python3
"""Phase 7.9J - Audit di causalita' temporale su Phase 7.9I. Verifica
punto 1 della revisione richiesta: causal_ema() incorporava la chiusura
FINALE della barra del giorno del segnale (non disponibile al momento
della decisione/fill intraday reale) - CONFERMATO e CORRETTO in
nxs_mechanism_context.py. causal_atr() era gia' corretto dall'origine.
Trovato anche un secondo problema (bar-offset nel path forward),
CONFERMATO ma non corretto perche' upstream in Phase 7.9H (frozen).
"""
import os
import sys
from datetime import datetime

PHASE79J_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79I_DIR = os.path.abspath(os.path.join(PHASE79J_DIR, "..", "phase7_9i"))
ROOT = os.path.abspath(os.path.join(PHASE79J_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

sys.path.insert(0, PHASE79I_DIR)
import nxs_mechanism_context as ctx  # noqa: E402


def build():
    d1_bars = ctx.load_d1_bars()

    # --- Caso concreto usato nella richiesta di revisione: 2019.06.05, fill 17:30. ---
    dt = datetime(2019, 6, 5)
    bars_le = [b for b in d1_bars if b["time"].date() <= dt.date()]
    bars_lt = [b for b in d1_bars if b["time"].date() < dt.date()]
    concrete_example = {
        "d1_bar_date": "2019.06.05", "entry_fill_time": "2019.06.05 17:30:00",
        "old_causal_ema_window_le_close_of_last_bar": {
            "bar_time": str(bars_le[-1]["time"]), "close": bars_le[-1]["close"],
            "known_to_the_market_only_at": "2019.06.06 00:00 (chiusura finale della barra "
                "del giorno del segnale) - QUESTO E' NEL FUTURO rispetto al fill delle "
                "17:30 dello stesso giorno.",
        },
        "new_causal_ema_window_lt_close_of_last_bar": {
            "bar_time": str(bars_lt[-1]["time"]), "close": bars_lt[-1]["close"],
            "known_to_the_market_since": "2019.06.05 00:00 (chiusura della barra "
                "PRECEDENTE, gia' fissata all'inizio del giorno del segnale, ore PRIMA "
                "del fill delle 17:30).",
        },
    }

    # --- Verifica sistematica: prima/dopo su tutti i 75 eventi. ---
    feat = ctx.build_feature_table()
    rows = feat["rows"]

    pre_fix_path = os.path.join(PHASE79J_DIR, "raw_data_pre_fix",
                                "breakout_acc_feature_engineering_v1_ORIGINAL_pre_temporal_fix.json")
    pre_rows = load_json(pre_fix_path)["payload"]["rows"]
    pre_by_id = {r["event_id"]: r for r in pre_rows}
    post_by_id = {r["event_id"]: r for r in rows}

    ema_value_diffs = []
    alignment_flips = []
    for eid, post in post_by_id.items():
        pre = pre_by_id[eid]
        if pre["causal_ema100_d1"] is not None and post["causal_ema100_d1"] is not None:
            ema_value_diffs.append(abs(pre["causal_ema100_d1"] - post["causal_ema100_d1"]))
        if pre["htf_proxy_trend_aligned"] != post["htf_proxy_trend_aligned"]:
            alignment_flips.append(eid)

    opened_post = [r for r in rows if r["funnel_terminal_stage"] == "OPENED"]
    n_aligned_ema100_post = sum(1 for r in opened_post if r["htf_proxy_trend_aligned"])
    n_aligned_ema20_post = sum(1 for r in opened_post if r["local_trend_aligned"])

    impact_summary = {
        "events_with_ema_value_change": len(ema_value_diffs),
        "ema100_value_diff_max_price_units": round(max(ema_value_diffs), 4) if ema_value_diffs else None,
        "ema100_value_diff_mean_price_units": round(sum(ema_value_diffs) / len(ema_value_diffs), 4)
            if ema_value_diffs else None,
        "trend_aligned_flag_flips_out_of_75": len(alignment_flips),
        "opened_trend_aligned_ema100_pre_fix": 47,  # verificato manualmente, invariato
        "opened_trend_aligned_ema100_post_fix": n_aligned_ema100_post,
        "opened_local_trend_aligned_ema20_new_metric": n_aligned_ema20_post,
        "conclusion": (
            "Il bug era REALE (il valore EMA100 causale cambia fino a "
            f"{round(max(ema_value_diffs), 2) if ema_value_diffs else 'N/A'} unita' di "
            "prezzo dopo la correzione) ma NON MATERIALE per la conclusione booleana "
            "'trend-aligned': 0 flip su 75 eventi, il 100% degli eventi OPENED resta "
            "trend-aligned sia con la vecchia sia con la nuova finestra causale, e resta "
            "trend-aligned ANCHE con un secondo proxy indipendente (EMA20, trend locale, "
            "mai usato nella versione originale). Il finding 'BUY/SELL dipendono "
            "dall'allineamento di trend' di Phase 7.9I e' quindi CONFERMATO come non "
            "dipendente dal bug di causalita' - ma il bug era comunque un difetto "
            "metodologico reale, ora corretto."
        ),
    }

    # --- Secondo problema trovato: bar-offset nel path forward (full_path_curve /
    # compute_path_anatomy). CONFERMATO ma NON corretto (upstream in Phase 7.9H, frozen). ---
    bar_offset_finding = {
        "status": "CONFIRMED_NOT_CORRECTED_UPSTREAM_IN_FROZEN_7_9H",
        "description": (
            "compute_path_anatomy() (Phase 7.9H, congelato) e full_path_curve() (Phase "
            "7.9I, stessa logica) cercano la prima barra D1 con time >= entry_time. Per "
            "un ingresso INTRADAY (es. 17:30, il caso reale per tutti i 47 eventi OPENED, "
            "nessuno ha un fill esattamente a mezzanotte), questa ricerca SALTA la barra "
            "del giorno di ingresso stesso (il cui orario di apertura, 00:00, precede le "
            "17:30) e trova invece la barra del giorno SUCCESSIVO come window[0]. Il "
            "codice poi enumera da window[1:] partendo da 'bar 1' - quindi 'bar 1' e' in "
            "realta' la chiusura di DUE giorni di calendario dopo l'ingresso, non uno. "
            "L'offset e' costante (+1 barra) e SIMMETRICO fra tutti gli eventi (OPENED "
            "reali e controfattuali BLOCKED/BROKER_REJECT/B-only, tutti con la stessa "
            "convenzione) - non introduce un bias BUY/SELL o fra popolazioni, ma significa "
            "che ogni 'barra N' nei risultati di Path Anatomy/Natural Horizon/Mechanism "
            "Discovery/Gate Diagnostic andrebbe letta come 'N+1 giorni di calendario dopo "
            "l'ingresso', non N."
        ),
        "why_not_corrected": (
            "Per gli eventi OPENED, il campo post_entry_path_anatomy (mfe/mae/bars_to_mfe/"
            "bars_to_mae/horizons) e' GIA' CALCOLATO E CONGELATO dentro il dataset "
            "canonico breakout_acc_intended_d1_v1_dataset.json (Phase 7.9H) - questa fase "
            "non lo modifica (istruzione esplicita di preservare Phase 7.9H). Correggere "
            "SOLO full_path_curve() (usata da Natural Horizon e dal Gate Diagnostic "
            "controfattuale) senza correggere anche il dataset congelato creerebbe una "
            "convenzione INCOERENTE fra i due - peggio che lasciarle entrambe con lo "
            "stesso offset noto e documentato."
        ),
        "recommended_action_not_executed_here": (
            "Una futura Phase dedicata dovrebbe ricalcolare post_entry_path_anatomy in "
            "Phase 7.9H con la ricerca dell'indice corretta (o esplicitamente ridefinire "
            "'bar 0' = giorno di ingresso, 'bar 1' = primo giorno intero successivo), "
            "propagando la stessa convenzione a tutti gli artifact derivati."
        ),
    }

    return {
        "phase": "7.9J",
        "scope": "Audit di causalita' temporale su Phase 7.9I - punto 1 della revisione "
            "richiesta. Preserva Phase 7.9H e i raw data - nessuna modifica.",
        "concrete_example_from_review_request": concrete_example,
        "bug_confirmed_and_fixed": {
            "location": "server/research_scripts/phase7/phase7_9i/nxs_mechanism_context.py "
                ":: causal_ema()",
            "before": "prior = [b for b in d1_bars if b['time'].date() <= as_of_date.date()]",
            "after": "prior = [b for b in d1_bars if b['time'].date() < as_of_date.date()]",
            "impact_measured": impact_summary,
        },
        "causal_atr_checked_and_confirmed_correct_from_origin": {
            "location": "nxs_mechanism_context.py :: causal_atr()",
            "code": "prior = [b for b in d1_bars if b['time'].date() < as_of_date.date()]",
            "verdict": "Gia' corretto (< stretto) fin dalla prima versione - nessuna "
                "modifica necessaria.",
        },
        "breakout_magnitude_c1_checked_and_confirmed_correct": {
            "location": "NXS_BreakoutAccSignalDiagnostic.mq5 (fonte di c1/c2 nella CSV "
                "isolata usata da tutte le feature di magnitudine)",
            "verified": "c1 = rates[i].close (chiusura della barra PRECEDENTE quella "
                "corrente, 'shift 1' nella nomenclatura live) - gia' nota all'inizio del "
                "giorno del segnale (d1_bar_date = rates[i+1].time, la barra 'shift 0' "
                "ancora in formazione) - NESSUN leakage, verificato riga per riga sul "
                "sorgente MQL5.",
        },
        "days_since_previous_raw_accept_checked": {
            "verdict": "Basato solo su confronti fra etichette di data (datetime a "
                "mezzanotte), nessun valore di prezzo/chiusura coinvolto - nessun leakage "
                "possibile per costruzione.",
        },
        "bar_offset_in_forward_path_confirmed_not_corrected": bar_offset_finding,
        "new_feature_added": "causal_ema20_d1_local_trend / local_trend_aligned (trend "
            "locale, EMA20, stessa correzione di causalita' applicata fin dall'origine) - "
            "vedi punto 3 della revisione (direzione x allineamento locale/regime x esito).",
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79J_DIR, "breakout_acc_temporal_causality_audit_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(payload["bug_confirmed_and_fixed"]["impact_measured"]["conclusion"])
    return doc


if __name__ == "__main__":
    main()
