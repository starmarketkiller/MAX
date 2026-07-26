#!/usr/bin/env python3
"""Genera i documenti di stato delle strategie DAL registro canonico.

Prima erano scritti a mano a partire da un'estrazione una tantum: alla prima
rigenerazione del registro diventavano falsi senza che nulla lo segnalasse — la
stessa classe di problema che il registro stesso doveva risolvere.

Produce due file, entrambi deterministici e rigenerabili:

- `docs/NEXUS_STRATEGY_INVENTORY.md`            inventario e matrice (§27.1-2)
- `docs/NEXUS_STRATEGY_EVIDENCE_PROVENANCE.md`  provenienza dei risultati

Uso:
    python3 contracts/gen_strategy_docs.py
    python3 contracts/gen_strategy_docs.py --check   # 1 se i file sono stale

Solo stdlib. La data NON compare nei file: renderebbe la rigenerazione non
riproducibile e ogni run produrrebbe un diff.
"""
from __future__ import annotations
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(ROOT, "contracts", "strategy-registry.json")
KB = os.path.join(ROOT, "knowledge", "strategy_database.json")
INVENTORY = os.path.join(ROOT, "docs", "NEXUS_STRATEGY_INVENTORY.md")
PROVENANCE = os.path.join(ROOT, "docs", "NEXUS_STRATEGY_EVIDENCE_PROVENANCE.md")


def _load():
    with open(REG, encoding="utf-8") as f:
        reg = json.load(f)
    with open(KB, encoding="utf-8") as f:
        kb = json.load(f)
    return reg, kb


def inventory(reg, kb):
    live = sorted((r for r in reg["strategies"] if r["live_implementation"]),
                  key=lambda r: r["strategy_id"])
    ro = sorted((r for r in reg["strategies"] if not r["live_implementation"]),
                key=lambda r: r["strategy_id"])
    c = reg["counts"]
    L = [f"""# NEXUS — INVENTARIO CANONICO DELLE STRATEGIE

> Consegna 1 del `NEXUS_CLOUD_STRATEGY_WORK_PACKAGE_v1` (§27.1, §27.2, §27.6),
> aggiornato dalla Fase A.
> **Documento generato** da `contracts/gen_strategy_docs.py` a partire da
> `contracts/strategy-registry.json`. Non modificarlo a mano: rigeneralo.

| | |
|---|---|
| Strategie nel registro | {c['total']} ({c['live']} live, {c['research_only']} research-only) |
| Round di sweep corrente | `{reg['current_sweep_round']}` |
| Misurate sul round corrente | {c['evidence_measured']} |
| Con dato surrogato | {c['evidence_surrogate']} |
| Mai misurate | {c['evidence_unknown']} |
| Collisioni di implementazione | {c['implementation_collisions']} |
| Conflitti fra stato dichiarato e codice | {c['declaration_conflicts']} |

## Fonti

{chr(10).join('- `' + s + '`' for s in reg['sources'])}

`selector_index` e gli interruttori NON sono piu' trascritti: sono derivati dal
codice MQL5 da `contracts/extract_selectors.py`, e `contracts/validate_registry.py`
fallisce se registro e codice divergono.

### Cosa NON e' verificabile da qui

`SOURCE_GAP` — `NEXUS_CORPUS_SEMANTIC_AUDIT_PRELIMINARY_v1.md`, i PDF e i
materiali di corso non sono presenti nel repository. Per le strategie SMC/ICT
manca quindi la definizione d'origine contro cui verificare la fedelta'
concettuale (§7): il confronto possibile e' solo MQL5 ↔ Python.

---

## Matrice di corrispondenza

Legenda: **Sel** indice di isolamento · **TF** timeframe dichiarato
(`—` = non dichiarato, non "qualunque") · **Py** funzione del motore research ·
**Ev** stato dell'evidenza · **Coll** condivide l'implementazione research.

| # | Strategia | Famiglia | Sel | Interruttore MQL5 | TF | Py | Ev | Coll |
|---|---|---|---|---|---|---|---|---|"""]
    for i, r in enumerate(live, 1):
        tf = (r["supported_timeframes"] or ["—"])[0]
        coll = r["implementation_collision"]
        ev = r["evidence"]["historical_status"]
        evcell = {"MEASURED": f"**{ev}**", "SURROGATE": f"⚠️ {ev}"}.get(ev, ev)
        L.append(
            f"| {i} | `{r['strategy_id']}` | {r['family']} | {r['selector_index']} | "
            f"`{r['code_toggle']}`={'T' if r['code_default_enabled'] else 'F'} | "
            f"{tf} | `{r['research_function'] or '—'}` | {evcell} | "
            f"{'/'.join(coll['partners']) if coll else '—'} |")

    L.append(f"""
### Research-only (non live)

{', '.join('`' + r['strategy_id'] + '`' for r in ro)} — presenti nel motore
Python e nel frontend, assenti dall'EA. Corretto per costruzione.

---

## Conflitti fra stato dichiarato e codice

Il registro descrive uno stato, il codice ne applica un altro. Registrati, non
risolti: la riconciliazione e' una decisione del proprietario.

| Strategia | Default nel codice | Stato nel registro | Disattivabile dalla dashboard |
|---|---|---|---|""")
    for r in live:
        dc = r["declaration_conflict"]
        if dc:
            L.append(f"| `{r['strategy_id']}` | {dc['code_default']} | "
                     f"{dc['registry_status']} | {dc['dashboard_auto_disable']} |")

    L.append("""
## Collisioni di implementazione

Strategie che condividono la stessa funzione del motore research: in ricerca
producono lo stesso segnale per costruzione. Gli id restano distinti; finche' la
collisione e' `UNRESOLVED`, il gruppo vale **un solo generatore di segnali**.

| Gruppo | Funzione condivisa | Rappresentante | Classificazione |
|---|---|---|---|""")
    seen = set()
    for r in live:
        coll = r["implementation_collision"]
        if not coll:
            continue
        key = tuple(sorted([r["strategy_id"]] + coll["partners"]))
        if key in seen:
            continue
        seen.add(key)
        rep = next(x["strategy_id"] for x in live
                   if x["strategy_id"] in key
                   and x["implementation_collision"]["counts_as_independent_signal_generator"])
        L.append(f"| {' ≡ '.join(key)} | `{coll['shared_function']}` | "
                 f"`{rep}` | {coll['classification']} |")

    L.append("""
## Proxy dichiarati

`proxy_for` e' un'asserzione scritta a mano nel generatore. Accanto, il fatto:
la funzione research usata coincide con quella del bersaglio dichiarato?

| Strategia | Proxy dichiarato di | Funzione usata | Coincide col bersaglio |
|---|---|---|---|""")
    for r in live:
        if r["proxy_for"]:
            L.append(f"| `{r['strategy_id']}` | `{r['proxy_for']}` | "
                     f"`{r['research_function']}` | "
                     f"{'sì' if r['proxy_target_shares_function'] else '**no**'} |")

    L.append("""
## Collegamenti

`docs/NEXUS_STRATEGY_MISMATCH_REPORT.md` ·
`docs/NEXUS_STRATEGY_PRIORITY_MATRIX.md` ·
`docs/NEXUS_STRATEGY_EVIDENCE_PROVENANCE.md`
""")
    return "\n".join(L)


def provenance(reg, kb):
    live = [r for r in reg["strategies"] if r["live_implementation"]]
    kbi = {e["nome"]: e for e in kb["strategie"]}
    by = lambda st: [r for r in live if r["evidence"]["historical_status"] == st]
    m = sorted(by("MEASURED"), key=lambda r: -r["evidence"]["trades"])
    s = sorted(by("SURROGATE"), key=lambda r: r["strategy_id"])
    u = sorted(by("UNKNOWN"), key=lambda r: r["strategy_id"])

    L = [f"""# NEXUS — PROVENIENZA DEI RISULTATI STORICI PER STRATEGIA

> Fase A, punto 7. **Documento generato** da `contracts/gen_strategy_docs.py`.
> Non contiene giudizi: solo da dove viene ogni numero.

| | |
|---|---|
| Round corrente | `{reg['current_sweep_round']}` |
| Strategie live | {len(live)} |
| Misurate sul round corrente | **{len(m)}** |
| Con dato surrogato (altro round) | **{len(s)}** |
| Mai misurate | **{len(u)}** |

## I tre stati

| Stato | Significa | Si puo' usare per… |
|---|---|---|
| `MEASURED` | passata isolata completata sul round corrente, con `run_id` | confrontare il comportamento del trigger dentro la stessa campagna |
| `SURROGATE` | esistono numeri, ma di un altro round | **niente che riguardi il codice attuale** |
| `UNKNOWN` | nessuna passata isolata | niente: assenza di misura, non misura di assenza |

Avvertenza che accompagna **tutti** i numeri, presa dal knowledge base e non
riscritta:

> {kb['avvertenza']}

Misurano il **comportamento del trigger** isolato a lotto fisso. Non sono un
edge, e non sono il P&L di portafoglio.

---

## Round corrente — {len(m)} strategie

| Strategia | Trade | WR % | PF | Exp. R | run_id |
|---|---|---|---|---|---|"""]
    for r in m:
        e = r["evidence"]
        L.append(f"| `{r['strategy_id']}` | {e['trades']} | {e['winrate_pct']} | "
                 f"{e['profit_factor']} | {e['expectancy_R']} | `{e['run_id']}` |")

    L.append(f"\n---\n\n## Dato surrogato — {len(s)} strategia\n")
    for r in s:
        e = r["evidence"]
        L.append(f"""```text
strategy:             {r['strategy_id']}
historical_status:    {e['historical_status']}
source_round:         {e['source_round']}
current_isolated_run: {e['current_isolated_run']}
run_id:               {e['run_id'] or 'assente'}
trades:               {e['trades']}   PF {e['profit_factor']}   exp {e['expectancy_R']}R
```

Nota registrata nel knowledge base:

> {e['note']}

`{r['strategy_id']}` va **programmata per una nuova passata isolata**. I numeri
restano leggibili ma non descrivono il codice della baseline corrente, e non
vanno usati per giudicarla.""")

    L.append(f"""
---

## Mai misurate — {len(u)} strategie

Tutte girano. Nessuna ha una passata isolata.

| Strategia | Sel | TF | Funzione research | Collisione | Bug storici | Fix registrati |
|---|---|---|---|---|---|---|""")
    for r in u:
        e = kbi[r["strategy_id"]]
        tf = (r["supported_timeframes"] or ["—"])[0]
        coll = r["implementation_collision"]
        L.append(f"| `{r['strategy_id']}` | {r['selector_index']} | {tf} | "
                 f"`{r['research_function'] or '—'}` | "
                 f"{'/'.join(coll['partners']) if coll else '—'} | "
                 f"{len(e.get('bug_storici') or [])} | "
                 f"{len(e.get('fix_applicati') or [])} |")

    L.append(f"""
---

## Cosa serve per chiudere questa pagina

{len(s) + len(u)} passate isolate: le {len(u)} mai eseguite piu' quella
surrogata, sulla baseline corrente. Finche' mancano, ogni affermazione sul
portafoglio riguarda {len(m)} strategie su {len(live)} ed e' estesa alle altre
per analogia — che non e' evidenza.

## Collegamenti

`docs/NEXUS_STRATEGY_INVENTORY.md` · `docs/NEXUS_STRATEGY_MISMATCH_REPORT.md` ·
`docs/NEXUS_STRATEGY_PRIORITY_MATRIX.md`
""")
    return "\n".join(L)


def main():
    reg, kb = _load()
    outputs = {INVENTORY: inventory(reg, kb), PROVENANCE: provenance(reg, kb)}
    if "--check" in sys.argv:
        stale = []
        for path, text in outputs.items():
            current = open(path, encoding="utf-8").read() if os.path.exists(path) else None
            if current != text:
                stale.append(os.path.relpath(path, ROOT))
        for p in stale:
            print(f"STALE: {p} — rigenerare con contracts/gen_strategy_docs.py")
        print("documenti allineati al registro" if not stale else f"{len(stale)} da rigenerare")
        return 1 if stale else 0
    for path, text in outputs.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"scritto {os.path.relpath(path, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
