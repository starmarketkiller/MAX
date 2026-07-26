#!/usr/bin/env python3
"""Fase A — estrae dal codice MQL5 la mappa REALE selector_index -> strategy_id.

Perche' esiste: `selector_index` nel registro canonico era una copia manuale,
e per 14 strategie live su 37 la copia era semplicemente assente
(`docs/NEXUS_STRATEGY_MISMATCH_REPORT.md`, MM-01). Il codice invece le isola
tutte. Questo modulo legge il codice e produce la mappa, cosi' il registro
smette di essere una trascrizione e diventa una derivazione.

Come associa un indice a una strategia — due casi, entrambi verificabili:

1. **Guardia interna.** La funzione trigger dichiara la propria identita' e poi
   si autoesclude:

       SNXSSignal NXS_Strat_ADXRSI(){
          SNXSSignal s; ...; s.stratName = "ADX_RSI";
          if(!InpStrat_ADX_RSI || !NXS_SelectorAllows(1)) return s;

   L'indice sta nel corpo della funzione che dichiara `stratName`.

2. **Guardia al punto di chiamata.** Il router in `NEXUS_EA_v2.mq5` filtra
   prima di chiamare:

       if(InpStrat_TurtleSoup && NXS_SelectorAllows(17)) out[n++] = NXS_Strat_TurtleSoup(swExt);

   L'indice sta sulla stessa riga della chiamata; l'identita' si legge nella
   funzione chiamata.

Ogni altra occorrenza (es. `NXS_ReusePerformancePack.mqh`, che riusa indici gia'
definiti altrove) e' classificata come RIFERIMENTO SECONDARIO: non definisce
l'indice, ma non deve contraddirlo.

Uso:
    python3 contracts/extract_selectors.py            # tabella indice -> id
    python3 contracts/extract_selectors.py --json     # mappa JSON

Exit 0 se la mappa e' coerente; 1 se un indice risolve a due strategie diverse.
Solo stdlib, nessuna rete, deterministico.
"""
from __future__ import annotations
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MQL_DIRS = [os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1"),
            os.path.join(ROOT, "MQL5", "Experts")]

_FUNC_RE = re.compile(r"^SNXSSignal\s+(\w+)\s*\(", re.M)
_NAME_RE = re.compile(r'\.stratName\s*=\s*"([A-Z0-9_]+)"')
_SEL_RE = re.compile(r"NXS_SelectorAllows\s*\(\s*(\d+)\s*\)")
_CALL_RE = re.compile(r"(NXS_Strat_\w+)\s*\(")
_ANYCALL_RE = re.compile(r"(\w+)\s*\(")
_TOGGLE_RE = re.compile(r"\b(Inp(?:Strat|UseStrat|Use)\w*)\b")
_INPUT_DEF_RE = re.compile(
    r"^\s*(?:input\s+)?bool\s+(Inp\w+)\s*=\s*(true|false)\s*;", re.M)


def _mql_sources():
    """File MQL5 in ordine deterministico (path relativi, separatore POSIX)."""
    out = []
    for d in MQL_DIRS:
        for name in sorted(os.listdir(d)):
            if name.endswith((".mqh", ".mq5")):
                out.append(os.path.join(d, name))
    return out


def _strip_comments(text: str) -> str:
    """Toglie commenti conservando le posizioni (sostituisce con spazi).

    L'ordine conta: le stringhe vanno protette PRIMA dei commenti, altrimenti
    un letterale come "http://host" viene tagliato a meta'.
    """
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
            i += 1
        elif c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                out[i] = " "
                i += 1
        elif c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if text[k] != "\n":
                    out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


def _bodies(text: str):
    """(nome_funzione, inizio, fine) per ogni funzione che ritorna SNXSSignal."""
    for m in _FUNC_RE.finditer(text):
        open_brace = text.find("{", m.end())
        if open_brace < 0:
            continue
        depth, i, n = 0, open_brace, len(text)
        while i < n:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        yield m.group(1), open_brace, i


def extract():
    """Ritorna (mappa, secondari, conflitti).

    mappa      : {indice: {"strategy_id", "source", "kind"}}
    secondari  : occorrenze che non definiscono l'indice
    conflitti  : lo stesso indice attribuito a strategie diverse
    """
    func_name = {}      # funzione -> stratName dichiarato direttamente
    func_calls = {}     # funzione -> funzioni SNXSSignal chiamate nel corpo
    files = {}
    for path in _mql_sources():
        with open(path, encoding="utf-8", errors="replace") as f:
            raw = f.read()
        txt = _strip_comments(raw)
        files[path] = txt
        for fn, a, b in _bodies(txt):
            body = txt[a:b]
            names = set(_NAME_RE.findall(body))
            if len(names) == 1:
                func_name[fn] = names.pop()
            elif len(names) > 1:
                # una funzione che dichiara due identita' non e' un trigger
                # singolo: la lascio irrisolta invece di sceglierne una.
                func_name[fn] = None
            func_calls[fn] = set(_ANYCALL_RE.findall(body)) - {fn}

    # Alcuni trigger delegano l'identita' a un helper (es. NXS_Strat_SH_BMS_RTO
    # -> NXS_SHBMS_UpdateSide). Risolvo un livello di indirezione, e solo se
    # l'helper produce UNA identita' sola.
    for fn, callees in func_calls.items():
        if func_name.get(fn):
            continue
        found = {func_name[c] for c in callees
                 if c in func_name and func_name.get(c)}
        if len(found) == 1:
            func_name[fn] = found.pop()
    func_name = {k: v for k, v in func_name.items() if v}

    mapping, secondary, conflicts = {}, [], []

    toggle_defaults = {}
    for path, txt in files.items():
        for name, val in _INPUT_DEF_RE.findall(txt):
            toggle_defaults.setdefault(name, val == "true")

    def claim(idx, sid, source, kind, toggle=None):
        prev = mapping.get(idx)
        if prev is None:
            mapping[idx] = {"strategy_id": sid, "source": source, "kind": kind,
                            "toggle": toggle,
                            "toggle_default": toggle_defaults.get(toggle)}
        elif prev["strategy_id"] != sid:
            conflicts.append(
                f"selector {idx}: {prev['strategy_id']} ({prev['source']}) "
                f"vs {sid} ({source})")

    for path, txt in files.items():
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        # indice dentro il corpo di una funzione trigger -> guardia interna
        owners = []
        for fn, a, b in _bodies(txt):
            if fn in func_name:
                owners.append((a, b, fn))
        for m in _SEL_RE.finditer(txt):
            pos = m.start()
            idx = int(m.group(1))
            line_start = txt.rfind("\n", 0, pos) + 1
            line_end = txt.find("\n", pos)
            line = txt[line_start:line_end if line_end > 0 else len(txt)]
            lineno = txt.count("\n", 0, pos) + 1

            # l'interruttore che accompagna la guardia, quando ce n'e' uno solo
            toggles = sorted(set(_TOGGLE_RE.findall(line)))
            toggle = toggles[0] if len(toggles) == 1 else None

            inner = next((fn for a, b, fn in owners if a <= pos <= b), None)
            if inner:
                claim(idx, func_name[inner], f"{rel}:{lineno}", "guardia interna",
                      toggle)
                continue

            called = [c for c in _CALL_RE.findall(line) if c in func_name]
            if len(called) == 1:
                claim(idx, func_name[called[0]], f"{rel}:{lineno}",
                      "guardia al punto di chiamata", toggle)
                continue

            secondary.append({"selector_index": idx, "source": f"{rel}:{lineno}",
                              "line": line.strip()})

    # un riferimento secondario non deve contraddire la mappa: se cita un indice
    # che nessuno definisce, e' un buco da segnalare, non da ignorare.
    for s in secondary:
        if s["selector_index"] not in mapping:
            conflicts.append(
                f"selector {s['selector_index']} citato in {s['source']} "
                f"ma non definito da nessuna strategia")

    return mapping, secondary, conflicts


def _checked():
    mapping, _, conflicts = extract()
    if conflicts:
        raise ValueError("mappa selector incoerente: " + "; ".join(conflicts))
    idxs = sorted(mapping)
    if idxs != list(range(1, len(idxs) + 1)):
        raise ValueError(f"selector non contigui 1..{len(idxs)}: {idxs}")
    return mapping


def selector_map():
    """{strategy_id: selector_index} — la forma usata dal generatore."""
    return {v["strategy_id"]: k for k, v in _checked().items()}


def toggle_map():
    """{strategy_id: {"toggle", "default"}} letto dal codice, non dichiarato.

    `default` e' il valore con cui l'EA parte se nessuno tocca i parametri: e'
    il fatto operativo. Il registro deve rispecchiarlo, non contraddirlo
    (`docs/NEXUS_STRATEGY_MISMATCH_REPORT.md`, MM-02 e MM-10).
    """
    return {v["strategy_id"]: {"toggle": v["toggle"],
                               "default": v["toggle_default"]}
            for v in _checked().values()}


def main():
    mapping, secondary, conflicts = extract()
    if "--json" in sys.argv:
        print(json.dumps({str(k): v for k, v in sorted(mapping.items())},
                         ensure_ascii=False, indent=2))
        return 1 if conflicts else 0

    print(f"selector definiti nel codice MQL5: {len(mapping)}")
    for idx in sorted(mapping):
        e = mapping[idx]
        print(f"  {idx:3d}  {e['strategy_id']:28s} {e['kind']:28s} {e['source']}")
    if secondary:
        print(f"\nriferimenti secondari (non definiscono l'indice): {len(secondary)}")
        for s in secondary:
            print(f"  {s['selector_index']:3d}  {s['source']}")
    idxs = sorted(mapping)
    expected = list(range(1, len(idxs) + 1))
    print(f"\ncontiguita' 1..{len(idxs)}: {'OK' if idxs == expected else 'BUCHI/FUORI SEQUENZA'}")
    if idxs != expected:
        print("  mancanti:", sorted(set(expected) - set(idxs)))
        print("  fuori range:", sorted(set(idxs) - set(expected)))
    print(f"conflitti: {'nessuno' if not conflicts else len(conflicts)}")
    for c in conflicts:
        print("  -", c)
    return 0 if not conflicts and idxs == expected else 1


if __name__ == "__main__":
    sys.exit(main())
