#!/usr/bin/env python3
"""PR6 — Validatore + riconciliazione del Canonical Strategy Registry.

Fa due cose, entrambe deterministiche e senza rete:

1. VALIDA `contracts/strategy-registry.json` contro lo schema e le REGOLE del
   contratto (id univoci, alias senza collisioni, selector_index unici tra i
   live, coerenza dei flag, enum). Regola 1 del pack: un id sconosciuto e' un
   ERRORE, mai fallback silenzioso.

2. RICONCILIA il registry con le fonti reali (backend `STRAT_NAMES_36`, backtest
   `STRATEGIES`, EA selector map da knowledge) e stampa la tabella di drift.

Uso:
    python3 contracts/validate_registry.py            # valida + riconcilia
    python3 contracts/validate_registry.py --table    # stampa tabella markdown
Exit 0 = tutto coerente; 1 = errori di validazione o drift non giustificato.

Solo stdlib (niente jsonschema): le regole sono verificate a mano per restare
eseguibile ovunque.
"""
from __future__ import annotations
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATUSES = {"ACTIVE", "EXPERIMENTAL", "SHADOW_ONLY", "RESEARCH_ONLY",
            "DEPRECATED", "DISABLED"}
PARITIES = {"EXACT", "FUNCTIONALLY_EQUIVALENT", "APPROXIMATE", "PROXY", "NOT_IMPLEMENTED"}


def load_registry():
    with open(os.path.join(ROOT, "contracts", "strategy-registry.json"),
              encoding="utf-8") as f:
        return json.load(f)


def _index(reg):
    """id o alias -> record. Regola 1: risoluzione esplicita, mai fallback."""
    idx = {}
    for r in reg["strategies"]:
        idx[r["strategy_id"]] = r
        for a in r["aliases"]:
            idx[a] = r
    return idx


def resolve(reg, name):
    """Risolve un id/alias al record canonico. Solleva KeyError se sconosciuto."""
    idx = _index(reg)
    if name not in idx:
        raise KeyError(f"strategia sconosciuta: '{name}' (nessun fallback silenzioso)")
    return idx[name]


EVIDENCE_STATUSES = {"MEASURED", "SURROGATE", "UNKNOWN"}


def validate_selectors(reg):
    """Fase A — il selector non puo' piu' mancare, duplicarsi o uscire di sequenza.

    Tre controlli, tutti bloccanti, che coprono i tre modi in cui MM-01 potrebbe
    ripresentarsi:

    1. ogni strategia LIVE ha un `selector_index` (era assente per 14 su 37);
    2. gli indici dei live sono esattamente 1..N, senza buchi e senza duplicati;
    3. la mappa del registro coincide con quella REALE letta dal codice MQL5.

    Il terzo e' quello che conta: rende impossibile che il registro affermi un
    isolamento che l'EA non applica, o viceversa.
    """
    errors = []
    live = [r for r in reg["strategies"] if r.get("live_implementation")]
    got = {}
    for r in live:
        sid, si = r["strategy_id"], r.get("selector_index")
        if si is None:
            errors.append(f"{sid}: live senza selector_index")
            continue
        if si in got:
            errors.append(f"selector_index {si} duplicato: {got[si]} e {sid}")
        got[si] = sid

    idxs = sorted(got)
    expected = list(range(1, len(live) + 1))
    if idxs != expected:
        for missing in sorted(set(expected) - set(idxs)):
            errors.append(f"selector_index {missing} mancante nella sequenza 1..{len(live)}")
        for extra in sorted(set(idxs) - set(expected)):
            errors.append(f"selector_index {extra} fuori dalla sequenza 1..{len(live)}")

    try:
        sys.path.insert(0, os.path.join(ROOT, "contracts"))
        from extract_selectors import selector_map
        code = selector_map()
    except Exception as exc:                       # pragma: no cover - diagnostico
        errors.append(f"impossibile leggere i selector dal codice MQL5: {exc}")
        return errors

    for sid, si in sorted((r["strategy_id"], r.get("selector_index")) for r in live):
        actual = code.get(sid)
        if actual is None:
            errors.append(f"{sid}: nel registro come live, ma il codice MQL5 non la isola")
        elif actual != si:
            errors.append(f"{sid}: selector {si} nel registro, {actual} nel codice MQL5")
    for sid in sorted(set(code) - {r["strategy_id"] for r in live}):
        errors.append(f"{sid}: isolata dal codice MQL5 ma non live nel registro")
    return errors


def validate_evidence(reg):
    """Lo stato dell'evidenza deve essere dichiarato e coerente con i dati."""
    errors = []
    for r in reg["strategies"]:
        sid = r["strategy_id"]
        ev = r.get("evidence")
        if not isinstance(ev, dict):
            errors.append(f"{sid}: manca il blocco evidence")
            continue
        st = ev.get("historical_status")
        if st not in EVIDENCE_STATUSES:
            errors.append(f"{sid}: evidence.historical_status non valido {st!r}")
            continue
        if st == "MEASURED":
            if ev.get("current_isolated_run") != "PRESENT":
                errors.append(f"{sid}: MEASURED ma current_isolated_run != PRESENT")
            if ev.get("source_round") != reg.get("current_sweep_round"):
                errors.append(f"{sid}: MEASURED ma non sul round corrente")
            if not ev.get("trades"):
                errors.append(f"{sid}: MEASURED senza trade")
        if st == "SURROGATE" and ev.get("source_round") == reg.get("current_sweep_round"):
            errors.append(f"{sid}: SURROGATE ma dichiarato sul round corrente")
        if st == "UNKNOWN" and ev.get("trades"):
            errors.append(f"{sid}: UNKNOWN ma con {ev['trades']} trade registrati")
    return errors


def validate_collisions(reg):
    """Le collisioni devono essere simmetriche e con UN solo rappresentante.

    Se due strategie condividono la funzione research, entrambe devono saperlo,
    e il gruppo deve contare come UN generatore di segnali: esattamente uno dei
    membri porta `counts_as_independent_signal_generator = true`.
    """
    errors = []
    by_id = {r["strategy_id"]: r for r in reg["strategies"]}
    groups = {}
    for r in reg["strategies"]:
        coll = r.get("implementation_collision")
        if not coll:
            continue
        sid = r["strategy_id"]
        for p in coll.get("partners", []):
            other = by_id.get(p)
            if other is None:
                errors.append(f"{sid}: collisione con {p}, che non esiste nel registro")
                continue
            oc = other.get("implementation_collision") or {}
            if sid not in oc.get("partners", []):
                errors.append(f"collisione non simmetrica: {sid} cita {p}, {p} non cita {sid}")
        key = "+".join(sorted([sid] + list(coll.get("partners", []))))
        groups.setdefault(key, []).append(
            (sid, coll.get("counts_as_independent_signal_generator")))

    for key, members in sorted(groups.items()):
        reps = [sid for sid, flag in members if flag]
        if len(reps) != 1:
            errors.append(
                f"gruppo {key}: {len(reps)} rappresentanti indipendenti, atteso 1")
    return errors


def validate(reg):
    errors = []
    ids = set()
    aliases_seen = {}
    sel = {}
    for r in reg["strategies"]:
        sid = r.get("strategy_id", "?")
        # id univoci
        if sid in ids:
            errors.append(f"id duplicato: {sid}")
        ids.add(sid)
        # enum
        if r.get("status") not in STATUSES:
            errors.append(f"{sid}: status non valido {r.get('status')}")
        if r.get("research_parity") not in PARITIES:
            errors.append(f"{sid}: research_parity non valido {r.get('research_parity')}")
        # alias non collidono con id o con altri alias
        for a in r.get("aliases", []):
            if a in ids and a != sid:
                errors.append(f"{sid}: alias {a} collide con un id")
            if a in aliases_seen and aliases_seen[a] != sid:
                errors.append(f"alias {a} usato da {aliases_seen[a]} e {sid}")
            aliases_seen[a] = sid
        # selector_index unico tra i live
        si = r.get("selector_index")
        if r.get("live_implementation") and si is not None:
            if si in sel:
                errors.append(f"selector_index {si} duplicato: {sel[si]} e {sid}")
            sel[si] = sid
        # coerenza flag
        if r.get("status") == "RESEARCH_ONLY" and r.get("live_implementation"):
            errors.append(f"{sid}: RESEARCH_ONLY ma live_implementation=true")
        if not r.get("research_implementation") and r.get("research_parity") not in ("NOT_IMPLEMENTED",):
            errors.append(f"{sid}: senza research ma parity={r.get('research_parity')}")
        # regola 6: research-only non promuovibile senza live reference
        if r.get("status") == "RESEARCH_ONLY" and r.get("default_enabled"):
            errors.append(f"{sid}: RESEARCH_ONLY non puo' essere default_enabled")
        # Fase A: un'assenza non si dichiara "*". Se il campo esiste, o e' una
        # lista di valori reali o e' null.
        for field in ("supported_symbols", "supported_timeframes"):
            val = r.get(field)
            if val is not None and (not isinstance(val, list) or "*" in val):
                errors.append(
                    f"{sid}: {field}={val!r} — usare null per 'non dichiarato', mai \"*\"")
    errors += validate_selectors(reg)
    errors += validate_evidence(reg)
    errors += validate_collisions(reg)
    return errors


def reconcile(reg):
    """Confronta il registry con le fonti reali. Ritorna (righe, drift_errors)."""
    idx = _index(reg)
    canonical = {r["strategy_id"] for r in reg["strategies"]}

    # backend
    sys.path.insert(0, os.path.join(ROOT, "server"))
    import backtest
    backend36 = set(getattr(backtest, "STRAT_NAMES_36", []))
    bt = set(getattr(backtest, "STRATEGIES", {}).keys())
    kn = {s["nome"] for s in json.load(open(
        os.path.join(ROOT, "knowledge/strategy_database.json"), encoding="utf-8"))["strategie"]}

    rows, drift = [], []
    # ogni nome che appare in una qualsiasi fonte deve risolvere nel registry
    for name in sorted(backend36 | bt | kn):
        known = name in idx
        rows.append((name, known,
                     "backend" if name in backend36 else "",
                     "backtest" if name in bt else "",
                     "knowledge" if name in kn else ""))
        if not known:
            drift.append(f"'{name}' presente in una fonte ma NON risolvibile nel registry")
    # ogni live del registry deve esistere nella knowledge (source EA)
    for r in reg["strategies"]:
        if r["live_implementation"] and r["strategy_id"] not in kn:
            drift.append(f"{r['strategy_id']}: live nel registry ma assente in knowledge")
    return rows, drift


def main():
    reg = load_registry()
    errors = validate(reg)
    rows, drift = reconcile(reg)

    if "--table" in sys.argv:
        print("| strategia | nel registry | backend | backtest | knowledge |")
        print("|---|---|---|---|---|")
        for name, known, b, t, k in rows:
            print(f"| {name} | {'✅' if known else '❌'} | {b} | {t} | {k} |")

    print(f"\nregistry: {reg['counts']}")
    print(f"validazione: {'OK' if not errors else 'ERRORI'}")
    for e in errors:
        print("  -", e)
    print(f"riconciliazione: {'OK' if not drift else 'DRIFT'}")
    for d in drift:
        print("  -", d)
    return 0 if not errors and not drift else 1


if __name__ == "__main__":
    sys.exit(main())
