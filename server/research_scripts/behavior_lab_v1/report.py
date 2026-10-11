"""BL-01 markdown report. Every number comes from the run summaries."""
from __future__ import annotations

import json


def _f(value, digits=3):
    if value is None:
        return "n/d"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _wilson(w):
    if not w:
        return "n/d"
    return f"{w['p']:.1%} [{w['low']:.1%}, {w['high']:.1%}]"


def _ci(ci):
    if not ci:
        return "n/d"
    return f"[{ci['low']:.3f}, {ci['high']:.3f}] R ({ci['n_blocks']} mesi)"


def _summary_rows(name, s, pf):
    if not s or not s.get("n_closed"):
        return f"| {name} | 0 | n/d | n/d | n/d | n/d | n/d | n/d |"
    return (f"| {name} | {s['n_closed']} | {_wilson(s.get('p_target_first'))} | "
            f"{_f(s.get('expectancy_r_net'))} | {_ci(s.get('expectancy_r_net_ci95_month_blocks'))} | "
            f"{_f(pf)} | {_f(s.get('mean_spread_cost_r'))} | "
            f"{_f((s.get('mfe_r') or {}).get('q50'))} / {_f((s.get('mae_r') or {}).get('q50'))} |")


def _breakdown(title, data):
    lines = [f"**{title}**", "", "| gruppo | n | P(+2R prima) | expectancy netta R |", "|---|---|---|---|"]
    for key, s in (data or {}).items():
        lines.append(f"| {key} | {s.get('n_closed', 0)} | {_wilson(s.get('p_target_first'))} | "
                     f"{_f(s.get('expectancy_r_net'))} |")
    return "\n".join(lines) + "\n"


def next_experiment(decision):
    d = decision.get("decision")
    failed = " ".join(decision.get("reasons", []))
    if d == "GO":
        return ("Una sola lettura di `internal_validation` con i parametri congelati: "
                "`python -m behavior_lab_v1.run_experiment --split internal_validation`. "
                "Non eseguita automaticamente. Prima, integrare il baseline abbinato di "
                "`phase7/engine/baseline_engine_v4.py` e le diagnostiche di dipendenza.")
    if d == "STOP" and decision.get("kind") in ("DATA_OR_DETECTOR",):
        return "Nessun esperimento: diagnosticare il problema dati su discovery, senza leggere altri split."
    if d == "STOP":
        return ("Chiudere BL-H4M15-IPC-001. Un'eventuale nuova domanda (per esempio impulso su piu' barre, "
                "o conferma diversa) va pre-registrata con un nuovo hypothesis_id; non riusare questi risultati "
                "per scegliere i parametri.")
    hints = []
    if "control" in failed or "cells" in failed:
        hints.append("il vantaggio non regge a parita' di direzione/sessione/volatilita': "
                     "pre-registrare una domanda sul solo effetto del contesto H4 contro il controllo abbinato")
    if "quarters" in failed:
        hints.append("risultato instabile nel tempo: domanda di regime (trend/range) pre-registrata separatamente")
    if "direction" in failed:
        hints.append("asimmetria BUY/SELL: verificare la dominanza da regime come in Phase 7.27 prima di tutto")
    if "hour" in failed:
        hints.append("concentrazione oraria: controllo per ora del giorno prima di attribuire l'effetto al pattern")
    if "cost" in failed:
        hints.append("margine assorbito dai costi: nessun seguito operativo")
    return ("INVESTIGATE, senza leggere internal_validation. " + ("; ".join(hints) if hints else
            "i dati non bastano per GO o STOP") + ". Ogni nuova domanda richiede un nuovo hypothesis_id.")


def render(pre, smoke, full, stop):
    out = ["# BL-01: validazione su dati reali di BL-H4M15-IPC-001", ""]
    out += ["Esplorativo: discovery 2023-02-04 → 2024-08-03. Nessun risultato qui e' una prova confermativa.", ""]

    out += ["## 1. HEAD, ambiente e hash dei dati", "",
            f"- HEAD `{pre['git_head']}` su `{pre['git_branch']}` (remoto PR: `{pre['remote_branch_head']}`)",
            f"- modifiche non committate al codice del lab: `{pre['lab_code_uncommitted_changes'] or 'nessuna'}`",
            f"- dipendenze: `{json.dumps(pre['dependencies'])}`",
            f"- manifest tick: {pre['manifest']['verdict']} `{pre['manifest'].get('sha256', '-')}`",
            f"- file discovery: {pre['discovery_files']['present']}/{pre['discovery_files']['days']} giorni, "
            f"feriali mancanti {pre['discovery_files']['n_weekday_missing']}",
            f"- warmup Phase 6: {pre['warmup_files_phase6']['present']}/{pre['warmup_files_phase6']['days']} giorni",
            f"- params_sha256 `{pre['params_sha256']}`"]
    for run, label in ((smoke, "smoke"), (full, "discovery")):
        if run:
            out.append(f"- {label}: run `{run['run_id']}`, codice `{run['git_commit']}`, "
                       f"{run['total_seconds']} s, picco RAM {_f(run['peak_rss_mb'], 0)} MB, "
                       f"ambiente `{run['environment']['platform']}` Python {run['environment']['python']}")
    out.append("")

    out += ["## 2. Qualita' dei dati", ""]
    for run, label in ((smoke, "smoke"), (full, "discovery")):
        if not run:
            continue
        c = run["data_checks"]
        ref = c["reference_h4_mismatches"]
        out += [f"**{label}**", "",
                f"- tick audit: {c['tick_audit']['verdict']} `{json.dumps(c['tick_audit'])}`",
                f"- disallineamenti H4/M15: {len(c['alignment_mismatches'])}",
                f"- parita' con H4 Phase 7.1: {ref if isinstance(ref, str) else str(len(ref)) + ' differenze'}",
                f"- buchi M15: weekend {c['m15_gaps']['weekend_gaps']}, pausa giornaliera "
                f"{c['m15_gaps']['daily_break_gaps']}, altri {c['m15_gaps']['n_other_gaps']}",
                f"- firma DST: `{json.dumps(c['dst_signature'])}`",
                f"- file giornalieri mancanti: {len(c['missing_day_files'])}", ""]
    if stop:
        out += ["**STOP obbligatorio.** Motivi:", ""] + [f"- {s}" for s in stop] + [""]

    if full and full.get("events") is not None:
        ev, ct = full["events"], full["controls"]
        hl = full["detector_health"]
        out += ["## 3. Statistiche reali del detector", "",
                f"- barre H4 nello split: {full['n_h4_bars_in_split']}",
                f"- impulsi: {hl['IMPULSE']['n_events']} (firing {hl['IMPULSE']['firing_rate']:.2%}, {hl['IMPULSE']['status']})",
                f"- pullback: {hl['PULLBACK']['n_events']} (firing {hl['PULLBACK']['firing_rate']:.2%}, {hl['PULLBACK']['status']})",
                f"- funnel eventi: `{json.dumps(full['funnel_events'])}`",
                f"- selezione: `{json.dumps(full['selection'])}`", "",
                _breakdown("Per trimestre", full["stability"]["by_quarter"]),
                _breakdown("Per direzione", full["by_direction"]),
                _breakdown("Per sessione di ingresso", full["by_session"]),
                f"Concentrazione oraria: quota massima in una sola ora UTC {_f(full['hour_profile']['max_hour_share'])}", ""]
        out += ["## 4. Confronto con il baseline M15 senza filtro H4", "",
                "| gruppo | n | P(+2R prima) Wilson | expectancy netta R | CI95 bootstrap mensile | PF | spread R | MFE/MAE mediani R |",
                "|---|---|---|---|---|---|---|---|",
                _summary_rows("eventi H4→M15", ev, full["profit_factor"]["events"]),
                _summary_rows("controllo M15", ct, full["profit_factor"]["controls"]), ""]
        st = full["vs_control_stratified"]
        out += [f"- a parita' di direzione, sessione e volatilita': delta P {_f(st['adjusted_delta_p'])}, "
                f"delta expectancy {_f(st['adjusted_delta_expectancy_r'])} R; eventi migliori in "
                f"{st['cells_event_better']}/{st['cells_used']} celle; eventi senza controllo comparabile "
                f"{st['events_without_comparable_control']}",
                f"- sensibilita' ai costi (eventi): `{json.dumps(full['cost_sensitivity'])}`",
                f"- sensibilita' ai costi (controllo): `{json.dumps(full['cost_sensitivity_controls'])}`",
                f"- trimestri positivi: {full['stability']['quarters_positive']}/{full['stability']['quarters_with_n_ge_5']} "
                f"(controllo {full['stability_controls']['quarters_positive']}/{full['stability_controls']['quarters_with_n_ge_5']})", ""]

    out += ["## 5. Limiti metodologici", "",
            "- Discovery esplorativa: una sola ipotesi, ma nessuna correzione per test multipli applicata qui.",
            "- Prezzi Dukascopy (BID/ASK), non il feed XM: nessuna parita' MT5 verificata.",
            "- Stop eseguito al prezzo di stop, nessuno slippage; nessuna commissione (`commission_r`=0).",
            "- Eventi vicini nel tempo non indipendenti: bootstrap a blocchi mensili descrittivo, diagnostiche di dipendenza Phase 7 non ancora applicate.",
            "- Controllo descrittivo (stessa regola M15 a tutte le altre chiusure H4), non il baseline abbinato v4.",
            "- Le finestre 2025-2026 non sono holdout indipendenti per questa famiglia (exposure_statement).", ""]

    decision = (full or smoke or {}).get("decision") if not stop else {"decision": "STOP", "reasons": stop,
                                                                       "kind": "DATA_OR_DETECTOR"}
    decision = decision or {"decision": "STOP", "reasons": ["nessun run completato"]}
    out += ["## 6. Decisione", "", f"**{decision['decision']}** (regole `{decision.get('rules', 'BL01_DECISION_RULES_V1')}`)", ""]
    for k, v in (decision.get("checks") or {}).items():
        out.append(f"- [{'x' if v else ' '}] {k}")
    if decision.get("reasons") and not decision.get("checks"):
        out += [f"- {r}" for r in decision["reasons"]]
    if decision.get("meaning"):
        out += ["", decision["meaning"]]
    out += ["", "## 7. Prossimo esperimento consigliato (non eseguito)", "", next_experiment(decision), ""]
    return "\n".join(out)
