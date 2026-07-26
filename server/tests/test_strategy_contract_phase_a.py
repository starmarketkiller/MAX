"""Fase A — controlli automatici sul contratto delle strategie.

Coprono i finding della prima consegna del work package
(`docs/NEXUS_STRATEGY_MISMATCH_REPORT.md`) e servono a impedire che tornino:

- MM-01  selector mancanti, duplicati o fuori sequenza
- MM-04  collisioni di implementazione nel motore research
- MM-05  proxy dichiarati verso un bersaglio che non condivide la funzione
- MM-06  provenienza dell'evidenza (MEASURED / SURROGATE / UNKNOWN)
- MM-07  assenza codificata come "*"
- MM-08  strategia indicizzata solo per alias
- MM-13  euristica 1/(n+1) attiva senza interruttore

Ogni test dichiara COSA dimostra. I test sul codice MQL5 sono statici: qui non
esistono MetaEditor ne' Strategy Tester, quindi verificano la FORMA del
sorgente, non la sua esecuzione. Dove il limite conta, e' scritto nel test.
"""
import json
import os
import re
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import backtest
import strategy_registry as sr

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "contracts"))
import extract_selectors            # noqa: E402
import validate_registry as vr      # noqa: E402

CORE = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_InstitutionalCore.mqh")
INPUTS = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Inputs.mqh")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def reg():
    return vr.load_registry()


@pytest.fixture(scope="module")
def live(reg):
    return [r for r in reg["strategies"] if r["live_implementation"]]


# ------------------------------------------------------- MM-01 selector -----
def test_selector_map_extracted_from_code_is_complete_and_contiguous():
    """Il codice isola tutte e 37 le strategie, con indici 1..37 senza buchi."""
    mapping, _, conflicts = extract_selectors.extract()
    assert conflicts == []
    assert sorted(mapping) == list(range(1, 38))
    assert len({v["strategy_id"] for v in mapping.values()}) == 37


def test_registry_selector_matches_the_code(live):
    """Il registro non trascrive piu' i selector: li deriva. Zero divergenze."""
    code = extract_selectors.selector_map()
    assert {r["strategy_id"]: r["selector_index"] for r in live} == code


def test_knowledge_base_has_every_selector(live):
    """La fonte canonica e' allineata: era la lacuna a monte dei 14 mancanti."""
    kb = json.load(open(os.path.join(ROOT, "knowledge/strategy_database.json"),
                        encoding="utf-8"))["strategie"]
    code = extract_selectors.selector_map()
    missing = [e["nome"] for e in kb if e.get("selector_index") is None]
    assert missing == []
    assert {e["nome"]: e["selector_index"] for e in kb} == code


@pytest.mark.parametrize("mutate,expected", [
    (lambda r: r.update(selector_index=None), "senza selector_index"),
    (lambda r: r.update(selector_index=1), "duplicato"),
    (lambda r: r.update(selector_index=99), "fuori dalla sequenza"),
])
def test_validator_rejects_broken_selectors(reg, mutate, expected):
    """Il controllo e' vivo: rompendo il registro il validatore DEVE fallire.

    Senza questo test i tre controlli potrebbero essere inerti — e' esattamente
    il difetto trovato sull'equity breaker durante la remediation v18.
    """
    broken = json.loads(json.dumps(reg))
    target = next(r for r in broken["strategies"]
                  if r["strategy_id"] == "TURTLE_SOUP")
    mutate(target)
    errors = vr.validate(broken)
    assert any(expected in e for e in errors), errors


# ------------------------------------- MM-04 / MM-05 collisioni e proxy -----
def test_collisions_are_declared_for_every_shared_research_function(live):
    """Chi condivide la funzione di segnale lo dichiara. Nessuno escluso."""
    by_func = {}
    for r in live:
        if r["research_function"]:
            by_func.setdefault(r["research_function"], []).append(r["strategy_id"])
    shared = {fn: sorted(ids) for fn, ids in by_func.items() if len(ids) > 1}
    assert shared == {
        "sig_bollinger": ["BOLLINGER", "RANGE_FADE"],
        "sig_breakout": ["LONDON_BO", "WEEKLY_EXP"],
        "sig_ob_mit": ["SH_BMS_RTO", "SMS_BMS_RTO"],
    }
    for r in live:
        assert bool(r["implementation_collision"]) == bool(r["research_shared_with"])


def test_collision_group_counts_as_one_signal_generator(live):
    """Regola del proprietario: gli id restano, il generatore vale uno."""
    groups = {}
    for r in live:
        coll = r["implementation_collision"]
        if not coll:
            continue
        key = "+".join(sorted([r["strategy_id"]] + coll["partners"]))
        groups.setdefault(key, []).append(coll["counts_as_independent_signal_generator"])
    assert len(groups) == 3
    for key, flags in groups.items():
        assert sum(1 for f in flags if f) == 1, key
    # gli id NON vengono fusi: restano tutti e 37
    assert len(live) == 37


def test_collisions_stay_unresolved_until_the_owner_classifies_them(live):
    """Fase A non decide la natura di una collisione: la registra."""
    for r in live:
        coll = r["implementation_collision"]
        if coll:
            assert coll["status"] == "UNRESOLVED"
            assert coll["classification"] == "PENDING_OWNER_REVIEW"
            assert len(coll["candidate_classifications"]) == 4


def test_declared_proxy_targets_are_marked_when_they_do_not_match(live):
    """MM-05: 5 proxy su 6 puntano a una funzione diversa. Reso leggibile."""
    mismatched = sorted(r["strategy_id"] for r in live
                        if r["proxy_for"] and not r["proxy_target_shares_function"])
    assert mismatched == ["LIQ_VOID", "LONDON_BO", "SH_BMS_RTO",
                          "SMS_BMS_RTO", "WEEKLY_EXP"]


# ------------------------------------------------- MM-06 provenienza --------
def test_evidence_status_split(reg, live):
    """8 misurate sul round corrente, 1 surrogata, 28 mai misurate."""
    counts = {}
    for r in live:
        counts[r["evidence"]["historical_status"]] = counts.get(
            r["evidence"]["historical_status"], 0) + 1
    assert counts == {"MEASURED": 8, "SURROGATE": 1, "UNKNOWN": 28}
    assert reg["counts"]["evidence_measured"] == 8


def test_sar_is_surrogate_and_says_so():
    """I numeri di SAR sono di un altro round: non vanno letti come attuali."""
    ev = sr.resolve("SAR")["evidence"]
    assert ev["historical_status"] == "SURROGATE"
    assert ev["current_isolated_run"] == "MISSING"
    assert ev["source_round"] != sr.registry_artifact()["current_sweep_round"]
    assert ev["trades"] == 261          # i numeri restano leggibili...
    assert "round precedente" in ev["note"]   # ...ma etichettati


def test_measured_strategies_all_cite_the_current_round(reg, live):
    for r in live:
        if r["evidence"]["historical_status"] == "MEASURED":
            assert r["evidence"]["source_round"] == reg["current_sweep_round"]
            assert r["evidence"]["run_id"]


def test_validator_rejects_evidence_that_contradicts_itself(reg):
    broken = json.loads(json.dumps(reg))
    target = next(r for r in broken["strategies"] if r["strategy_id"] == "SAR")
    target["evidence"]["historical_status"] = "MEASURED"
    assert any("MEASURED" in e for e in vr.validate(broken))


# ------------------------------------------------------ MM-07 null vs "*" ---
def test_absence_is_null_never_a_star(reg):
    """`"*"` diceva 'tutti'; il fatto era 'non dichiarato'."""
    for r in reg["strategies"]:
        for field in ("supported_symbols", "supported_timeframes"):
            val = r[field]
            assert val is None or (isinstance(val, list) and "*" not in val), \
                f"{r['strategy_id']}.{field} = {val!r}"


def test_the_eight_without_a_timeframe_declare_null(live):
    without = sorted(r["strategy_id"] for r in live
                     if r["supported_timeframes"] is None)
    assert without == ["AMD_CONT", "AMD_REVERSAL", "ELLIOTT", "JUDAS_SWING",
                       "LDN_REVERSAL", "NY_REVERSAL", "PO3", "SILVER_BULLET"]


def test_validator_rejects_a_star(reg):
    broken = json.loads(json.dumps(reg))
    broken["strategies"][0]["supported_symbols"] = ["*"]
    assert any("mai \"*\"" in e for e in vr.validate(broken))


# ------------------------------------------------------ MM-08 alias ---------
def test_three_bar_is_keyed_canonically_in_the_research_engine():
    """La chiave e' l'id canonico; iterare STRATEGIES non mente piu'."""
    assert "THREE_BAR_DELIVERY_BREAK" in backtest.STRATEGIES
    assert "CISD" not in backtest.STRATEGIES


def test_the_historical_alias_still_resolves():
    """Retrocompatibilita': chi passa 'CISD' continua a funzionare."""
    assert backtest.resolve_research_key("CISD") == "THREE_BAR_DELIVERY_BREAK"
    assert backtest.resolve_research_key("MACD") == "MACD"
    assert sr.require_strategy("CISD", research=True) == "THREE_BAR_DELIVERY_BREAK"


def test_every_live_except_elliott_has_a_research_function(live):
    """Il conteggio corretto: 36 su 37, non 35."""
    without = sorted(r["strategy_id"] for r in live if not r["research_function"])
    assert without == ["ELLIOTT"]


def test_passing_both_alias_and_canonical_id_does_not_run_it_twice():
    """Deduplicazione: due nomi della stessa strategia, una sola passata."""
    both = backtest.run_backtest(
        strategies=["CISD", "THREE_BAR_DELIVERY_BREAK"], bars=60)
    once = backtest.run_backtest(
        strategies=["THREE_BAR_DELIVERY_BREAK"], bars=60)
    assert both["strategies"] == ["THREE_BAR_DELIVERY_BREAK"]
    # senza deduplicazione la strategia girerebbe due volte e i trade
    # raddoppierebbero: e' il conteggio a dimostrarlo, non il solo elenco
    assert both["trades"] == once["trades"]
    assert both["net_pnl"] == once["net_pnl"]


# ---------------------------------------------- MM-02 conflitti dichiarati --
def test_disp_rebal_conflict_is_recorded_not_resolved():
    """Il proprietario ha chiesto di REGISTRARE il conflitto, non di deciderlo."""
    r = sr.resolve("DISP_REBAL")
    assert r["declaration_conflict"] == {
        "code_default": "ENABLED",
        "registry_status": "DISABLED",
        "dashboard_auto_disable": "BLOCKED",
        "resolution": "PENDING_OWNER_DECISION",
    }
    # comportamento invariato: il default del codice non e' stato toccato
    assert r["code_default_enabled"] is True
    assert r["auto_disable_eligible"] is False


def test_elliott_conflict_is_recorded_too():
    r = sr.resolve("ELLIOTT")
    assert r["declaration_conflict"]["code_default"] == "DISABLED"
    assert r["declaration_conflict"]["registry_status"] == "ACTIVE"
    assert r["code_default_enabled"] is False


def test_code_defaults_come_from_the_mql_inputs(live):
    """Il fatto operativo e' letto dal codice, non dichiarato a mano."""
    toggles = extract_selectors.toggle_map()
    for r in live:
        assert r["code_toggle"] == toggles[r["strategy_id"]]["toggle"]
        assert r["code_default_enabled"] == toggles[r["strategy_id"]]["default"]


def test_only_two_declaration_conflicts_exist(reg):
    conflicting = sorted(r["strategy_id"] for r in reg["strategies"]
                         if r["declaration_conflict"])
    assert conflicting == ["DISP_REBAL", "ELLIOTT"]


# -------------------------------------- MM-13 euristica dietro interruttore --
def test_correlation_weighting_input_exists_and_defaults_to_false():
    src = _read(INPUTS)
    m = re.search(r"input\s+bool\s+InpInstCorrelationWeighting\s*=\s*(\w+)\s*;", src)
    assert m, "l'euristica deve essere controllabile da input"
    assert m.group(1) == "false", "il default deve essere false"


def test_canonical_conviction_is_the_plain_sum():
    """Con l'interruttore spento la conviction e' la somma, come in baseline."""
    src = _read(CORE)
    body = src.split("SNXSDecision NXS_Institutional_Decide", 1)[1]
    assert re.search(r"double net\s*=\s*MathAbs\(buySum - sellSum\);", body)


def test_the_heuristic_runs_only_behind_the_switch():
    """Nessun percorso raggiunge la pesatura senza l'input acceso."""
    src = _read(CORE)
    body = src.split("SNXSDecision NXS_Institutional_Decide", 1)[1]
    code = re.sub(r"//[^\n]*", "", body)
    assigns = re.findall(r"\bnet\s*=", code)
    assert len(assigns) == 2, "net assegnato piu' volte del previsto"
    guarded = re.search(
        r"if\(InpInstCorrelationWeighting\)\{\s*net\s*=\s*"
        r"_nxs_inst_correlationAdjustedNet\(all, n\);\s*\}", code)
    assert guarded, "la pesatura non e' dietro l'interruttore"


def test_the_unreliable_taxonomy_is_never_consulted_when_the_switch_is_off():
    """`_nxs_inst_family()` e' chiamata SOLO dal ramo sperimentale.

    E' la proprieta' che rende vera l'affermazione 'con false non cambia nulla':
    se la tassonomia a sottostringhe fosse usata anche altrove, spegnere
    l'interruttore non basterebbe.
    """
    src = re.sub(r"//[^\n]*", "", _read(CORE))
    exp = src.split("double _nxs_inst_correlationAdjustedNet", 1)
    assert len(exp) == 2
    inside = exp[1].split("\n}", 1)[0]
    assert "_nxs_inst_family(" in inside
    outside = exp[0] + exp[1].split("\n}", 1)[1]
    callers = [m for m in re.findall(r"_nxs_inst_family\(", outside)]
    # l'unica occorrenza fuori dal ramo e' la definizione della funzione stessa
    assert len(callers) == 1, f"{len(callers)} usi fuori dal ramo sperimentale"
    assert re.search(r"string _nxs_inst_family\(string name\)", outside)


def test_canonical_expression_is_byte_identical_to_the_pre_heuristic_baseline():
    """Torna ESATTAMENTE alla baseline, non a qualcosa di simile.

    Confronto contro il sorgente reale del commit precedente all'introduzione
    dell'euristica: se un giorno la riga canonica venisse riscritta, questo test
    lo dice.
    """
    rel = "MQL5/Include/NEXUS_v1/NXS_InstitutionalCore.mqh"
    try:
        old = subprocess.run(["git", "show", f"866a1bc^:{rel}"],
                             cwd=ROOT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):      # pragma: no cover
        pytest.skip("git non disponibile")
    if old.returncode != 0:                            # pragma: no cover
        pytest.skip("commit di baseline non raggiungibile in questo checkout")
    baseline = re.search(r"double net = MathAbs\(buySum - sellSum\);[^\n]*",
                         old.stdout)
    assert baseline, "riga di baseline non trovata nel commit di riferimento"
    assert baseline.group(0) in _read(CORE)


def test_generated_docs_are_not_stale():
    """I documenti di stato sono derivati: non possono restare indietro.

    Erano scritti a mano da un'estrazione una tantum e diventavano falsi alla
    prima rigenerazione del registro, senza che nulla lo segnalasse.
    """
    import gen_strategy_docs as gsd
    reg, kb = gsd._load()
    for path, text in ((gsd.INVENTORY, gsd.inventory(reg, kb)),
                       (gsd.PROVENANCE, gsd.provenance(reg, kb))):
        assert _read(path) == text, (
            f"{os.path.basename(path)} non allineato: rigenerare con "
            "python3 contracts/gen_strategy_docs.py")


def test_registry_regenerates_without_diff(tmp_path):
    """Il registro e' una derivazione: rigenerarlo non deve cambiarlo.

    Se cambia, un campo generato e' stato scritto a mano oppure una fonte e'
    cambiata senza rigenerare — in entrambi i casi il registro non e' piu' la
    fonte di verita' che dichiara di essere.
    """
    import importlib
    before = _read(os.path.join(ROOT, "contracts", "strategy-registry.json"))
    gen = importlib.import_module("generate_registry")
    out = gen.build()
    after = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    assert before == after


def test_the_weighted_branch_really_would_change_the_number():
    """Controprova: se accesa, l'euristica cambia il risultato.

    Se non cambiasse nulla, spegnerla sarebbe irrilevante e questo lavoro
    inutile. Riproduce le due formule su segnali della stessa famiglia.
    """
    scores = [70.0, 60.0, 50.0]          # tre BUY, stessa famiglia
    plain = sum(scores)
    weighted = sum(s / (i + 1) for i, s in enumerate(scores))
    assert plain == 180.0                 # 70 + 60 + 50
    assert round(weighted, 2) == 116.67   # 70 + 60/2 + 50/3
    # con la soglia di default (60) entrambe passerebbero; con 120 no:
    assert plain > 120 > weighted
