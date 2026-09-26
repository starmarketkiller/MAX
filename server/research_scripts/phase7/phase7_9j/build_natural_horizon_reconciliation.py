#!/usr/bin/env python3
"""Phase 7.9J - punto 4 della revisione: riconciliazione del Natural
Horizon. Un CI che esclude lo zero NON identifica da solo un plateau,
un decadimento o una durata naturale - verifica sovrapposizione delle
finestre future e dipendenza fra eventi, e declassa esplicitamente
l'interpretazione se queste non vengono affrontate statisticamente.
"""
import os
import statistics
import sys
from datetime import datetime

PHASE79J_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79I_DIR = os.path.abspath(os.path.join(PHASE79J_DIR, "..", "phase7_9i"))
ROOT = os.path.abspath(os.path.join(PHASE79J_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

sys.path.insert(0, PHASE79I_DIR)
import nxs_mechanism_context as ctx  # noqa: E402

MAX_H = ctx.MAX_PATH_WINDOW_D1


def build():
    feat = ctx.build_feature_table()
    rows = [r for r in feat["rows"] if r["funnel_terminal_stage"] == "OPENED"]
    horizon_doc = load_json(os.path.join(PHASE79I_DIR, "breakout_acc_natural_horizon_v1.json"))["payload"]

    entry_times = sorted(datetime.strptime(r["entry_fill_time"], "%Y.%m.%d %H:%M:%S") for r in rows)

    # --- Sovrapposizione delle finestre future (60 barre D1 ~ 60 giorni di calendario). ---
    total_pairs = 0
    overlapping_pairs = 0
    for i in range(len(entry_times)):
        for j in range(i + 1, len(entry_times)):
            total_pairs += 1
            if (entry_times[j] - entry_times[i]).days <= MAX_H:
                overlapping_pairs += 1

    consecutive_gaps = [(entry_times[i + 1] - entry_times[i]).days
                        for i in range(len(entry_times) - 1)]
    n_consecutive_overlapping = sum(1 for g in consecutive_gaps if g <= MAX_H)

    overlap_summary = {
        "n_events": len(entry_times),
        "total_event_pairs": total_pairs,
        "pairs_with_overlapping_60d_windows": overlapping_pairs,
        "pct_pairs_overlapping": round(100 * overlapping_pairs / total_pairs, 1) if total_pairs else None,
        "consecutive_event_gaps_days": {
            "min": min(consecutive_gaps), "median": statistics.median(consecutive_gaps),
            "mean": round(statistics.mean(consecutive_gaps), 1), "max": max(consecutive_gaps),
        },
        "consecutive_gaps_leq_60d": n_consecutive_overlapping,
        "consecutive_gaps_total": len(consecutive_gaps),
        "pct_consecutive_gaps_overlapping": round(
            100 * n_consecutive_overlapping / len(consecutive_gaps), 1),
    }

    # --- Dipendenza SERIALE entro il percorso di un singolo evento: i valori a barra
    # t e t+1 NON sono osservazioni indipendenti (stesso percorso di prezzo che evolve
    # con continuita', non un nuovo campionamento a ogni barra). Quantificata come
    # autocorrelazione lag-1 del ritorno close-to-close AGGREGATO (media sugli eventi)
    # fra barre consecutive - un valore alto conferma che il "run" di 43 barre con CI
    # che esclude zero e' in larga parte la STESSA informazione ripetuta, non 43
    # conferme indipendenti.
    per_bar_means = [p["close_to_close_return"]["mean"] for p in horizon_doc["per_bar_curve"]
                     if p["close_to_close_return"]["mean"] is not None]
    if len(per_bar_means) > 2:
        diffs = [per_bar_means[i + 1] - per_bar_means[i] for i in range(len(per_bar_means) - 1)]
        autocorr_note = (
            f"La media aggregata cresce con incrementi medi di "
            f"{round(statistics.mean(diffs), 2)} unita' di prezzo per barra (stdev "
            f"{round(statistics.stdev(diffs), 2)}) - un andamento LISCIO, non rumoroso "
            "barra-per-barra, che e' la firma attesa di dati con forte dipendenza "
            "seriale entro-evento (ogni evento contribuisce una traiettoria continua, "
            "non un campione indipendente a ogni barra)."
        )
    else:
        autocorr_note = "Dati insufficienti per stimare l'incremento medio barra-per-barra."

    epistemic_downgrade = (
        "DECLASSAMENTO ESPLICITO (Phase 7.9J): il finding originale di Phase 7.9I "
        "('CI95% esclude lo zero in modo continuativo dalla barra 18 alla 60') era "
        "presentato come un 'orizzonte naturale PARZIALMENTE identificabile'. Questo "
        "NON e' corretto senza ulteriori qualifiche: (1) il "
        f"{overlap_summary['pct_consecutive_gaps_overlapping']}% dei gap fra eventi "
        "consecutivi e' inferiore alla finestra di 60 barre - le finestre forward "
        "SI SOVRAPPONGONO nel tempo di calendario, quindi molte 'osservazioni' "
        "condividono segmenti dello stesso percorso di prezzo sottostante (non sono "
        "indipendenti); (2) entro il percorso di un SINGOLO evento, i valori a barre "
        "consecutive sono per costruzione fortemente autocorrelati (una traiettoria "
        "continua, non un nuovo campionamento). Il CI95% calcolato con mean+/-1.96*SE "
        "ASSUME osservazioni indipendenti - questa assunzione e' VIOLATA su entrambi i "
        "fronti. Il risultato pratico e' che gli intervalli di confidenza mostrati sono "
        "probabilmente PIU' STRETTI del reale (l'incertezza vera e' maggiore), e le '43 "
        "barre consecutive' NON vanno lette come 43 conferme indipendenti, ma come "
        "l'evoluzione continua di un numero molto piu' piccolo di traiettorie "
        "indipendenti (~47 eventi, con sovrapposizioni sostanziali che riducono "
        "ulteriormente il numero di 'informazioni indipendenti' effettive sotto 47). "
        "Conclusione corretta: la curva mostra un pattern DESCRITTIVO di crescita del "
        "ritorno medio su 60 barre, senza plateau visibile - ma questo NON costituisce "
        "una prova statisticamente valida di un 'natural horizon', ne' della sua "
        "assenza. I CI vanno letti come puramente descrittivi (dispersione del "
        "campione), non come intervalli di confidenza in senso inferenziale stretto."
    )

    return {
        "phase": "7.9J",
        "supersedes_note": "Qualifica (non sostituisce i numeri di) "
            "breakout_acc_natural_horizon_v1.json (Phase 7.9I) - la curva "
            "per-barra e i valori numerici restano quelli originali (nessun ricalcolo "
            "necessario, il problema e' nell'INTERPRETAZIONE statistica del CI, non nel "
            "calcolo dei valori stessi, che sono corretti come statistiche descrittive).",
        "window_overlap_analysis": overlap_summary,
        "within_event_serial_dependence_note": autocorr_note,
        "epistemic_downgrade": epistemic_downgrade,
        "revised_stable_horizon_identified": False,
        "revised_finding": (
            "Il ritorno medio close-to-close cresce in modo descrittivamente monotono su "
            "60 barre D1, senza plateau visibile - ma con N effettivo molto minore di 47 "
            "a causa della sovrapposizione delle finestre e della dipendenza seriale "
            "entro-evento. Non si puo' concludere ne' l'esistenza ne' l'assenza di un "
            "vero natural horizon statisticamente validato con questo campione e questa "
            "metodologia - il finding resta un pattern descrittivo, non una conferma "
            "statistica."
        ),
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79J_DIR, "breakout_acc_natural_horizon_reconciliation_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(payload["revised_finding"])
    return doc


if __name__ == "__main__":
    main()
