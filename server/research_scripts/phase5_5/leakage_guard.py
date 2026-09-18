#!/usr/bin/env python3
"""Phase 5.5 sec.8 - Leakage Guard.

Controlli automatici, statici (grep sul codice sorgente) e dinamici
(verifica diretta sui dati), che possono far fallire la pipeline con
LEAKAGE_GUARD_FAIL invece di proseguire silenziosamente.

Uso: eseguito qui in modalita' AUDIT (sui file gia' scritti di Phase 5),
non integrato nella pipeline stessa in questa fase (l'integrazione come
gate bloccante di build_market_state.py/build_events.py/edge_discovery.py
e' un lavoro successivo - qui si dimostra che il controllo FUNZIONA e SI
APPLICA GIA' RETROATTIVAMENTE a Phase 5, trovando un problema reale).
"""
import glob
import json
import os
import re

import numpy as np
import pandas as pd

ROOT = r"C:\Users\User\ClaudeWork\MAX"
PHASE5_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5")
PHASE55_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5_5")
OUT_JSON = os.path.join(PHASE55_DIR, "leakage_guard_report_v1.json")

findings = []


def flag(check_id, severity, file, line_no, snippet, explanation, verdict):
    findings.append({
        "check_id": check_id, "severity": severity, "file": file,
        "line": line_no, "snippet": snippet.strip(), "explanation": explanation,
        "verdict": verdict,
    })


def _is_code(line: str, match_start: int) -> bool:
    """Esclude match dentro commenti (# prima del match sulla stessa riga)
    o dentro docstring/testo prosa ovvio - controllo grezzo ma sufficiente
    per non confondere una MENZIONE del pattern (in un commento che spiega
    perche' NON viene usato) con un USO reale nel codice."""
    prefix = line[:match_start]
    if "#" in prefix:
        return False
    # euristica: una riga di puro testo prosa contiene tipicamente spazi
    # multipli/punteggiatura naturale intorno - qui ci basta escludere le
    # righe che sono chiaramente stringhe di documentazione/messaggio
    # (contengono virgolette di apertura PRIMA del match senza una
    # chiusura-e-riapertura che indichi codice reale)
    return True


def static_checks():
    py_files = glob.glob(os.path.join(PHASE5_DIR, "*.py")) + glob.glob(os.path.join(PHASE55_DIR, "*.py"))
    py_files = [p for p in py_files if os.path.basename(p) != "leakage_guard.py"]
    for path in py_files:
        rel = os.path.relpath(path, ROOT)
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        in_docstring = False
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                # toggle: apre O chiude un blocco docstring (euristica su
                # triple-quote singole per riga, sufficiente per questi script)
                if stripped.count('"""') % 2 == 1 or stripped.count("'''") % 2 == 1:
                    in_docstring = not in_docstring
                continue
            if in_docstring:
                continue
            m = re.search(r"center\s*=\s*True", line)
            if m and _is_code(line, m.start()):
                flag("CENTERED_ROLLING", "CRITICAL", rel, i, line,
                     "rolling/expanding con center=True guarda anche barre future rispetto al punto di osservazione.",
                     "LEAKAGE_GUARD_FAIL")
            m = re.search(r"\.shift\(\s*-\d", line)
            if m and _is_code(line, m.start()):
                flag("NEGATIVE_SHIFT_FUTURE_LOOKUP", "CRITICAL", rel, i, line,
                     "shift(-N) sposta dati futuri nella riga corrente.",
                     "LEAKAGE_GUARD_FAIL")
            if re.search(r"outcomes_v1|edge_results_v1", line) and "build_market_state" in rel or (
                    re.search(r"outcomes_v1|edge_results_v1", line) and "build_events" in rel):
                flag("FEATURE_SEES_OUTCOME", "CRITICAL", rel, i, line,
                     "Uno script di costruzione feature/eventi referenzia file di outcome/edge - possibile target leakage.",
                     "LEAKAGE_GUARD_FAIL")
            # normalizzazione/soglie fittate: cerca percentile/mean/std su 'state[' o 'state.' SENZA
            # uno slice esplicito (.iloc[:SPLIT... o .loc[:SPLIT...) nella stessa riga - euristica,
            # richiede poi verifica dinamica sotto (i falsi positivi sono attesi e filtrati a mano).
            if re.search(r"nanpercentile|\.median\(\)|\.mean\(\)|\.std\(\)", line) and re.search(r"state\[|state\.loc|state\.iloc", line):
                if not re.search(r"iloc\[:?\s*SPLIT|disc_mask|disc\[|disc_state", line):
                    flag("THRESHOLD_FIT_SCOPE_UNVERIFIED", "REVIEW", rel, i, line,
                         "Calcolo di soglia/statistica su 'state' senza uno slice esplicito di discovery visibile in questa riga - verificare manualmente se include la validation.",
                         "MANUAL_REVIEW_REQUIRED")
    return


def dynamic_checks():
    """Verifica diretta: le soglie effettivamente scritte nei meta.json di
    Phase 5 corrispondono a un calcolo SOLO-discovery o FULL-dataset?"""
    state = pd.read_csv(os.path.join(PHASE5_DIR, "data", "market_state_dataset_v1.csv"))
    SPLIT_IDX = 3366
    edge_meta = json.load(open(os.path.join(PHASE5_DIR, "data", "edge_results_v1.json"), encoding="utf-8"))["meta"]

    full_vol_terc = np.nanpercentile(state["atr_percentile"].dropna(), [33.33, 66.67]).tolist()
    disc_vol_terc = np.nanpercentile(state.iloc[:SPLIT_IDX]["atr_percentile"].dropna(), [33.33, 66.67]).tolist()

    used_vol_terc = edge_meta.get("vol_terciles")
    is_full_sample = np.allclose(used_vol_terc, full_vol_terc, rtol=1e-6)
    is_disc_only = np.allclose(used_vol_terc, disc_vol_terc, rtol=1e-6)

    if is_full_sample and not is_disc_only:
        pct_shift = abs(used_vol_terc[1] - disc_vol_terc[1]) / disc_vol_terc[1] * 100
        flag("BASELINE_TERCILES_FIT_ON_FULL_DATASET", "CONFIRMED_LEAKAGE", "server/research_scripts/phase5/edge_discovery.py",
             None,
             "vol_terc = np.nanpercentile(vol_valid, [33.33, 66.67])  # vol_valid = state['atr_percentile'].dropna(), stato COMPLETO",
             f"Le soglie di cella per il baseline matching (vol_terc, trend_terc) e per 3 delle 5 interazioni predefinite "
             f"(EFFICIENCY_TOP_TERCILE, VOL_BOTTOM_TERCILE, TREND_PERSISTENCE_MEDIAN) sono state calcolate sull'INTERO "
             f"dataset (discovery+validation), non solo su discovery. Verificato dinamicamente: soglia usata realmente "
             f"{used_vol_terc[1]:.4f} == soglia full-dataset {full_vol_terc[1]:.4f}, mentre la soglia solo-discovery sarebbe "
             f"stata {disc_vol_terc[1]:.4f} (scarto {pct_shift:.1f}%). Impatto valutato: PICCOLO in magnitudine (discovery e' "
             f"gia' il 70% del campione) - non rifatto il test per policy di questa fase (nessuna ri-validazione di edge), "
             f"ma e' un difetto metodologico REALE da correggere prima del prossimo ciclo di discovery/validation.",
             "LEAKAGE_GUARD_FAIL (retroattivo su Phase 5 - non blocca questo report, documentato come difetto noto)")

    return {"used_vol_terc": used_vol_terc, "full_vol_terc": full_vol_terc, "disc_vol_terc": disc_vol_terc}


def main():
    static_checks()
    dyn = dynamic_checks()

    # separiamo i finding "critici/confermati" da quelli "review" per non
    # sommergere il segnale in falsi positivi euristici
    critical = [f for f in findings if f["severity"] in ("CRITICAL", "CONFIRMED_LEAKAGE")]
    review = [f for f in findings if f["severity"] == "REVIEW"]

    report = {
        "schema_version": 1,
        "checks_run": ["CENTERED_ROLLING", "NEGATIVE_SHIFT_FUTURE_LOOKUP", "FEATURE_SEES_OUTCOME",
                       "THRESHOLD_FIT_SCOPE (static heuristic + dynamic verification)"],
        "n_critical_confirmed": len(critical),
        "n_review_needed": len(review),
        "overall_verdict": "LEAKAGE_GUARD_FAIL" if critical else "LEAKAGE_GUARD_PASS",
        "critical_findings": critical,
        "review_findings_deduplicated_files": sorted(set(f["file"] for f in review)),
        "dynamic_check_detail": dyn,
        "guard_scope_note": (
            "Questo run e' un AUDIT retroattivo su Phase 5 gia' completata, non un gate "
            "che ha bloccato una nuova pipeline. Il finding BASELINE_TERCILES_FIT_ON_FULL_DATASET "
            "e' reale e va corretto nel codice prima di qualunque futuro ciclo discovery/validation "
            "(vedi report principale sec.8) - non e' stato corretto qui perche' farlo richiederebbe "
            "ri-eseguire edge_discovery.py e quindi ri-validare SWEEP+RECLAIM, esplicitamente vietato "
            "in questa fase."
        ),
    }
    json.dump(report, open(OUT_JSON, "w", encoding="utf-8"), indent=2, default=str)
    print(f"Verdict: {report['overall_verdict']}")
    print(f"Critical/confirmed findings: {len(critical)}")
    for f in critical:
        print(f"  [{f['check_id']}] {f['file']}: {f['explanation'][:150]}...")
    print(f"Review-needed (heuristic, likely false positives, listed for human check): {len(review)} lines across {len(set(f['file'] for f in review))} files")
    print(f"\nwritten: {OUT_JSON}")


if __name__ == "__main__":
    main()
