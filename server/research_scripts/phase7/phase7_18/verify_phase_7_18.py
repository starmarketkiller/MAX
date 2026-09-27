#!/usr/bin/env python3
"""Phase 7.18 - verificatore indipendente. Ri-deriva gli artifact dai
builder (comprese le tracce curate committate), verifica sul sorgente
MQL5 attuale che (a) la guardia sia presente esattamente nella forma
autorizzata, (b) nessun'altra logica della strategia sia stata
toccata, (c) nessuna istrumentazione diagnostica temporanea sia
rimasta nel sorgente canonico, (d) TSI non abbia wrapper/riuso da
altre strategie; verifica inoltre la consistenza interna delle tracce
curate (committate) con i conteggi dichiarati negli artifact.
"""
import csv
import os
import subprocess
import sys

PHASE718_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE718_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE718_DIR)
import build_tsi_parity_comparison as parity_builder  # noqa: E402
import build_tsi_decision_card_v2 as decision_builder  # noqa: E402
import build_tsi_historical_evidence_migration as hist_builder  # noqa: E402

STRAT_PATH = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
CURATED_PREFIX = os.path.join(PHASE718_DIR, "nxs_tsi_realtrace_diag_prefix_curated.csv")
CURATED_POSTFIX = os.path.join(PHASE718_DIR, "nxs_tsi_realtrace_diag_postfix_curated.csv")

BASELINE_COMMIT = "8590f63"

ARTIFACTS = [
    ("tsi_parity_comparison_v1.json", parity_builder.build),
    ("tsi_decision_card_v2.json", decision_builder.build),
    ("tsi_historical_evidence_migration_v1.json", hist_builder.build),
]


def verify():
    errors = []

    # --- Artifact ri-derivati dai builder (curated CSV committate, quindi
    # sempre riproducibili - a differenza di ORDER_BLOCK 7.14 qui non serve
    # distinguere raw/curated per la ri-derivazione). ---
    for fname, build_fn in ARTIFACTS:
        path = os.path.join(PHASE718_DIR, fname)
        if not os.path.exists(path):
            errors.append(f"{fname}: file mancante")
            continue
        saved = load_json(path)
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    # --- Tracce CURATE (committate) - verifica di coerenza interna. ---
    if not os.path.exists(CURATED_PREFIX) or not os.path.exists(CURATED_POSTFIX):
        errors.append("tracce curate committate mancanti")
    else:
        with open(CURATED_POSTFIX, encoding="utf-8-sig") as f:
            post_rows = list(csv.DictReader(f))
        non_canonical_post = [r for r in post_rows if r["tf"] != r["canonical_tf"]]
        if non_canonical_post:
            errors.append(f"traccia curata post-fix contiene {len(non_canonical_post)} righe su "
                          "TF non canonico - la guardia non risulterebbe efficace al 100%")

        with open(CURATED_PREFIX, encoding="utf-8-sig") as f:
            pre_rows = list(csv.DictReader(f))
        non_canonical_pre = [r for r in pre_rows if r["tf"] != r["canonical_tf"]]
        if len(non_canonical_pre) == 0:
            errors.append("traccia curata pre-fix non mostra alcuna riga su TF non canonico - "
                          "il difetto non risulterebbe riprodotto")

        # scoperta chiave della curazione: entro lo STESSO (close_time_srv, tf=D1),
        # il pre-fix deve mostrare piu' di un signal_dir distinto (evidenza diretta
        # del flip-flop da contaminazione) - se questo non risultasse piu' vero, la
        # curazione (o il trace) sarebbe stata alterata in modo da nascondere il difetto.
        from collections import defaultdict
        d1_groups = defaultdict(set)
        for r in pre_rows:
            if r["tf"] == "PERIOD_D1":
                d1_groups[r["close_time_srv"]].add(r["signal_dir"])
        multi_dir_keys = [k for k, v in d1_groups.items() if len(v) > 1]
        if len(multi_dir_keys) == 0:
            errors.append("traccia curata pre-fix non mostra alcun flip-flop di signal_dir entro "
                          "lo stesso close_time_srv D1 - atteso (contaminazione cross-TF), "
                          "possibile perdita di evidenza nella curazione")

    # --- Sorgente MQL5 attuale: guardia presente, forma esatta, nessun'altra
    # modifica, nessuna istrumentazione diagnostica rimasta. ---
    strat_text = open(STRAT_PATH, encoding="utf-8").read()
    if 'if(tf != NXS_Profile_TF("TSI")) return s;' not in strat_text:
        errors.append("la guardia autorizzata non e' presente nel sorgente attuale")
    if "NXS_TSI_DIAG_TRACE" in strat_text or "NXS_TSI_DiagWrite" in strat_text or "NXS_TSI_DiagHandle" in strat_text:
        errors.append("istrumentazione diagnostica temporanea ANCORA presente nel sorgente "
                      "canonico - doveva essere rimossa dopo la cattura del trace")

    tsi_start = strat_text.find("SNXSSignal NXS_Strat_TSI()")
    tsi_end = strat_text.find("\n}\n", tsi_start)
    tsi_body = strat_text[tsi_start:tsi_end]
    guard_pos = tsi_body.find('if(tf != NXS_Profile_TF("TSI")) return s;')
    first_state_mutation = tsi_body.find("g_tsiState.init = true")
    if guard_pos <= 0:
        errors.append("guardia non trovata nel corpo di NXS_Strat_TSI()")
    elif first_state_mutation > 0 and first_state_mutation < guard_pos:
        errors.append("una mutazione di g_tsiState precede la guardia - violazione del vincolo "
                      "'nessuna EMA/state mutation prima della guardia'")

    # queste stringhe devono ESISTERE ancora (invariate) - formula/periodi/soglie/
    # gate/SLTP non toccati oltre alla guardia.
    for token in ("InpTSI_LongPeriod", "InpTSI_ShortPeriod", "InpTSI_SignalPeriod",
                 "TSI_cross_up", "TSI_cross_down", "NXS_DefaultSLTP(s)",
                 "g_tsiState.barsSeen < InpTSI_LongPeriod * 3"):
        if token not in strat_text:
            errors.append(f"token atteso invariato '{token}' non trovato - la logica della "
                          "strategia potrebbe essere stata alterata oltre alla guardia")

    # --- TSI non ha wrapper/riuso da altre strategie (confermato in Phase 7.17) -
    # su TUTTO l'albero MQL5/, deve esistere esattamente 1 punto di CHIAMATA
    # reale a NXS_Strat_TSI() (il router in NEXUS_EA_v2.mq5), oltre alla
    # definizione stessa in NXS_Strategies.mqh. ---
    result_grep = subprocess.run(["git", "grep", "-n", "NXS_Strat_TSI()", "--", "MQL5/"],
                                 cwd=ROOT, capture_output=True, text=True)
    grep_lines = [l for l in result_grep.stdout.strip().splitlines() if l]
    call_sites = [l for l in grep_lines if "SNXSSignal NXS_Strat_TSI()" not in l]
    if len(call_sites) != 1:
        errors.append(f"attesa esattamente 1 chiamata reale a NXS_Strat_TSI() nell'albero MQL5/ "
                      f"(il router), trovate {len(call_sites)}: {call_sites} - possibile "
                      "wrapper/riuso non documentato in Phase 7.17, il fix potrebbe non "
                      "propagarsi correttamente")

    # --- git diff rispetto alla baseline 8590f63 (Phase 7.17, prima del fix):
    # SOLO NXS_Strategies.mqh modificato in MQL5/. ---
    result = subprocess.run(["git", "diff", "--name-only", BASELINE_COMMIT, "HEAD", "--", "MQL5/"],
                            cwd=ROOT, capture_output=True, text=True)
    changed = [l for l in result.stdout.strip().splitlines() if l]
    if changed and changed != ["MQL5/Include/NEXUS_v1/NXS_Strategies.mqh"]:
        errors.append(f"file MQL5 modificati oltre al previsto rispetto alla baseline "
                      f"{BASELINE_COMMIT}: {changed}")

    # --- decisione ammessa. ---
    card_path = os.path.join(PHASE718_DIR, "tsi_decision_card_v2.json")
    if os.path.exists(card_path):
        card = load_json(card_path)["payload"]
        allowed = {"FIX_CAUSALLY_VALIDATED", "FIX_PARTIALLY_VALIDATED", "FIX_NOT_VALIDATED",
                  "INSUFFICIENT_RUNTIME_EVIDENCE"}
        if card["decision"] not in allowed:
            errors.append(f"decisione '{card['decision']}' non ammessa")

    # --- migrazione evidenza storica: nessun artifact cancellato, nessun
    # riutilizzo del vecchio PF/WR come evidenza della nuova implementazione. ---
    hist_path = os.path.join(PHASE718_DIR, "tsi_historical_evidence_migration_v1.json")
    if os.path.exists(hist_path):
        hist = load_json(hist_path)["payload"]
        if hist.get("no_artifact_deleted") is not True:
            errors.append("migrazione evidenza storica: no_artifact_deleted non e' True")
        if hist.get("no_old_mt5_result_reused_as_evidence_of_new_implementation") is not True:
            errors.append("migrazione evidenza storica: riutilizzo di evidenza vecchia non escluso")

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
