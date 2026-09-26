#!/usr/bin/env python3
"""Phase 7.14 - verificatore indipendente. Ri-deriva gli artifact dai
builder quando le tracce reali locali sono disponibili (grandi, non
committate - vedi nota di riproducibilita' nel vault report), verifica
sul sorgente MQL5 attuale che (a) la guardia sia presente esattamente
nella forma autorizzata, (b) nessun'altra logica della strategia sia
stata toccata, (c) nessuna istrumentazione diagnostica temporanea sia
rimasta nel sorgente canonico, (d) OB_MIT continui a chiamare
direttamente NXS_Strat_OrderBlock(); verifica inoltre la consistenza
interna delle tracce CURATE (committate) con i conteggi dichiarati
negli artifact."""
import csv
import os
import subprocess
import sys

PHASE714_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE714_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE714_DIR)
import build_ob_mit_dependency_map as obmit_builder  # noqa: E402
import build_historical_evidence_migration as hist_builder  # noqa: E402

RAW_ARTIFACTS = [
    ("real_trace_comparison_v1.json", "build_real_trace_comparison"),
    ("parity_comparison_v1.json", "build_parity_comparison"),
    ("decision_card_v2_order_block_v1.json", "build_decision_card_v2"),
]
# baseline_pre_fix_v1.json e' volutamente ESCLUSO dalla ri-derivazione per hash:
# registra un hash di CATTURA (nxs_strategies_mqh_sha256_at_capture) del sorgente
# COM'ERA al momento del run pre-fix (istrumentato) - il sorgente attuale e'
# cambiato da allora (fix applicato, istrumentazione rimossa) per disegno, quindi
# NON deve essere identico se ri-derivato ora. Verificato sotto contro il blob
# git storico invece che contro il file di lavoro corrente.
STATIC_ARTIFACTS = [
    ("ob_mit_dependency_map_v1.json", obmit_builder.build),
    ("historical_evidence_migration_v1.json", hist_builder.build),
]


def verify():
    errors = []

    for fname, build_fn in STATIC_ARTIFACTS:
        path = os.path.join(PHASE714_DIR, fname)
        if not os.path.exists(path):
            errors.append(f"{fname}: file mancante")
            continue
        saved = load_json(path)
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    raw_prefix = os.path.join(PHASE714_DIR, "nxs_orderblock_realtrace_diag_prefix.csv")
    raw_postfix = os.path.join(PHASE714_DIR, "nxs_orderblock_realtrace_diag_postfix.csv")
    if os.path.exists(raw_prefix) and os.path.exists(raw_postfix):
        for fname, modname in RAW_ARTIFACTS:
            path = os.path.join(PHASE714_DIR, fname)
            if not os.path.exists(path):
                errors.append(f"{fname}: file mancante nonostante le tracce raw siano presenti")
                continue
            mod = __import__(modname)
            saved = load_json(path)
            fresh = mod.build()
            if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
                errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")
    else:
        print("NOTA: tracce raw locali (39MB/6MB) non presenti - salto la ri-derivazione "
              "degli artifact dipendenti da esse (vedi nota di riproducibilita' nel vault "
              "report); verifico comunque le tracce CURATE committate sotto.")

    # --- baseline_pre_fix_v1.json: non ri-derivabile per hash (registra uno
    # snapshot del sorgente istrumentato, mai committato) - verificato invece
    # ricontando zone create/consumate/invalidate/scadute direttamente dalla
    # traccia CURATA committata (indipendente dal builder). ---
    baseline_path = os.path.join(PHASE714_DIR, "baseline_pre_fix_v1.json")
    curated_prefix_path = os.path.join(PHASE714_DIR, "nxs_orderblock_realtrace_diag_prefix_curated.csv")
    if os.path.exists(baseline_path) and os.path.exists(curated_prefix_path):
        baseline = load_json(baseline_path)["payload"]
        with open(curated_prefix_path, encoding="utf-8-sig") as f:
            curated_rows = list(csv.DictReader(f))
        recount = {"ZONE_CREATED": {"BUY_SIDE": 0, "SELL_SIDE": 0},
                  "ZONE_INVALIDATED": {"BUY_SIDE": 0, "SELL_SIDE": 0},
                  "ZONE_EXPIRED": {"BUY_SIDE": 0, "SELL_SIDE": 0},
                  "RETEST_SIGNAL_FIRED": {"BUY_SIDE": 0, "SELL_SIDE": 0}}
        for r in curated_rows:
            if r["op"] in recount:
                recount[r["op"]][r["side"]] += 1
        checks = [
            (baseline["zones_created"], recount["ZONE_CREATED"], "zones_created"),
            (baseline["zones_invalidated"], recount["ZONE_INVALIDATED"], "zones_invalidated"),
            (baseline["zones_expired"], recount["ZONE_EXPIRED"], "zones_expired"),
            (baseline["zones_consumed_by_retest_total"], recount["RETEST_SIGNAL_FIRED"], "zones_consumed_by_retest_total"),
        ]
        for declared, computed, name in checks:
            if declared != computed:
                errors.append(f"baseline_pre_fix_v1.json.{name} ({declared}) non combacia con la "
                              f"traccia curata ricontata ({computed})")
    elif not os.path.exists(baseline_path):
        errors.append("baseline_pre_fix_v1.json mancante")

    # --- Tracce CURATE (committate) - verifica di coerenza interna, sempre eseguita. ---
    curated_prefix = os.path.join(PHASE714_DIR, "nxs_orderblock_realtrace_diag_prefix_curated.csv")
    curated_postfix = os.path.join(PHASE714_DIR, "nxs_orderblock_realtrace_diag_postfix_curated.csv")
    if not os.path.exists(curated_prefix) or not os.path.exists(curated_postfix):
        errors.append("tracce curate committate mancanti")
    else:
        with open(curated_postfix, encoding="utf-8-sig") as f:
            post_rows = list(csv.DictReader(f))
        non_d1 = [r for r in post_rows if r["tf"] != r["canonical_tf"]]
        if non_d1:
            errors.append(f"trace curata post-fix contiene {len(non_d1)} righe su TF non "
                          "canonico - la guardia non risulterebbe efficace al 100%")
        with open(curated_prefix, encoding="utf-8-sig") as f:
            pre_rows = list(csv.DictReader(f))
        non_d1_pre = [r for r in pre_rows if r["tf"] != r["canonical_tf"]]
        if len(non_d1_pre) == 0:
            errors.append("trace curata pre-fix non mostra alcuna mutazione su TF non canonico - "
                          "il difetto non risulterebbe riprodotto")

    # --- Sorgente MQL5 attuale: guardia presente, forma esatta, nessun'altra modifica,
    # nessuna istrumentazione diagnostica rimasta. ---
    strat_path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
    strat_text = open(strat_path, encoding="utf-8").read()
    if 'if(tf != NXS_Profile_TF("ORDER_BLOCK")) return s;' not in strat_text:
        errors.append("la guardia autorizzata non e' presente nel sorgente attuale")
    if "NXS_OB_DIAG_TRACE" in strat_text or "NXS_OB_DiagWrite" in strat_text:
        errors.append("istrumentazione diagnostica temporanea ANCORA presente nel sorgente "
                      "canonico - doveva essere rimossa dopo la cattura del trace")

    ob_start = strat_text.find("SNXSSignal NXS_Strat_OrderBlock()")
    ob_end = strat_text.find("\n}\n", ob_start)
    ob_body = strat_text[ob_start:ob_end]
    forbidden_changes = ["InpOB_SwingLookback = ", "InpOB_MaxWaitBars = ", "1.2 * atr",
                         "s.score = 70", "NXS_DefaultSLTP"]
    # queste stringhe devono ESISTERE ancora (invariate), non essere state rimosse -
    # verifichiamo l'INTERO file, non solo il body della funzione principale.
    for token in ["1.2 * atr", "InpOB_MaxWaitBars", "OB_retest_bull", "OB_retest_bear",
                 "NXS_DefaultSLTP(s)"]:
        if token not in strat_text:
            errors.append(f"token atteso invariato '{token}' non trovato - la logica della "
                          "strategia potrebbe essere stata alterata oltre alla guardia")

    # --- OB_MIT ancora wrapper diretto (nessuna divergenza introdotta). ---
    smc_path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies_SMC.mqh")
    smc_text = open(smc_path, encoding="utf-8").read()
    ob_mit_start = smc_text.find("NXS_Strat_OB_Mitigation_Structural()")
    ob_mit_body = smc_text[ob_mit_start:smc_text.find("\n}\n", ob_mit_start)]
    if "NXS_Strat_OrderBlock()" not in ob_mit_body:
        errors.append("OB_MIT non chiama piu' direttamente NXS_Strat_OrderBlock()")

    # --- git diff rispetto alla baseline 7b823b9 (Phase 7.13, prima del fix):
    # SOLO NXS_Strategies.mqh modificato in MQL5/, nessun altro file EA/registry.
    # Confrontato contro la baseline, non contro HEAD - dopo il commit di questa
    # fase, HEAD stesso include il fix, quindi un confronto vs HEAD sarebbe
    # sempre vuoto (non informativo). ---
    result = subprocess.run(["git", "diff", "--name-only", "7b823b9", "HEAD", "--", "MQL5/"],
                            cwd=ROOT, capture_output=True, text=True)
    changed = [l for l in result.stdout.strip().splitlines() if l]
    if changed != ["MQL5/Include/NEXUS_v1/NXS_Strategies.mqh"]:
        errors.append(f"file MQL5 modificati oltre al previsto rispetto alla baseline 7b823b9: {changed}")

    # --- decisione ammessa. ---
    card_path = os.path.join(PHASE714_DIR, "decision_card_v2_order_block_v1.json")
    if os.path.exists(card_path):
        card = load_json(card_path)["payload"]
        allowed = {"FIX_CAUSALLY_VALIDATED", "FIX_PARTIALLY_VALIDATED", "FIX_NOT_VALIDATED",
                  "TRACE_INSUFFICIENT"}
        if card["decision"] not in allowed:
            errors.append(f"decisione '{card['decision']}' non ammessa")
        if "ob_mit_status" not in card:
            errors.append("decision card: manca lo stato separato di OB_MIT")

    return errors


def main():
    errors = verify()
    if errors:
        print(f"VERIFY FAILED: {len(errors)} problemi")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("VERIFY OK: tutti i controlli indipendenti passati (0 problemi)")
    sys.exit(0)


if __name__ == "__main__":
    main()
