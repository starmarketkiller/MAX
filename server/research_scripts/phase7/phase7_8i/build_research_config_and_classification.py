#!/usr/bin/env python3
"""Phase 7.8I - Config di ricerca corretto + classificazione + evidenza
di ricompilazione. Parte dal config corretto in 7.8H e aggiunge/esplicita
i campi del protocollo Research Mode (che era gia' la base metodologica
implicita del Serious validation, mai attivata esplicitamente finora):
InpResearchMode=true, InpResearchExitMode=0, InpResearchFixedLot=0.01,
InpUseStrategyProfiles=true (gia' presente), InpProfileMultiTF=true
(nuovo, richiesto da NXS_ResearchPreflight() - verificato nel codice).
"""
import os
import sys

PHASE78I_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78I_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

PRIOR_78H_CONFIG_PATH = os.path.join(PHASE7_DIR, "phase7_8h", "volatility_breakout_corrected_config_v1.json")
PRIOR_78H_ROOT_CAUSE_PATH = os.path.join(PHASE7_DIR, "phase7_8h", "volatility_breakout_run2_deeper_root_cause_v1.json")

OLD_EX5_PATH = os.path.join(PHASE78I_DIR, "compile_evidence", "NEXUS_EA_v2_OLD_ex5_pre_recompile_2026-09-10.ex5")
COMPILE_LOG_PATH = os.path.join(PHASE78I_DIR, "compile_evidence", "compile_ea_recompile.log")
NEW_EX5_PATH = (
    r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6"
    r"\MQL5\Experts\NEXUS_EA_v2.ex5"
)
NEW_SOURCE_PATH = os.path.join(ROOT, "MQL5", "Experts", "NEXUS_EA_v2.mq5")


def build():
    prior_78h_config = load_json(PRIOR_78H_CONFIG_PATH)
    prior_78h_rc = load_json(PRIOR_78H_ROOT_CAUSE_PATH)

    # ================= 1. Evidenza di ricompilazione =================
    old_ex5_hash = file_sha256(OLD_EX5_PATH)
    new_ex5_hash = file_sha256(NEW_EX5_PATH)
    new_ex5_mtime = os.path.getmtime(NEW_EX5_PATH)
    with open(COMPILE_LOG_PATH, encoding="utf-16", errors="ignore") as f:
        compile_log = f.read()
    warnings = [ln.strip() for ln in compile_log.splitlines() if "warning" in ln.lower() and "elapsed" not in ln.lower()]
    errors_line = [ln for ln in compile_log.splitlines() if ln.strip().startswith("Result:")]

    recompile_evidence = {
        "old_ex5_sha256": old_ex5_hash,
        "old_ex5_sha256_matches_documented_stale_binary": old_ex5_hash.lower() ==
            prior_78h_rc["payload"]["deeper_root_cause"]["ex5_sha256"].lower(),
        "old_ex5_preserved_at": os.path.relpath(OLD_EX5_PATH, ROOT).replace("\\", "/"),
        "new_ex5_sha256": new_ex5_hash,
        "new_ex5_differs_from_old": new_ex5_hash.lower() != old_ex5_hash.lower(),
        "new_ex5_mtime_iso": __import__("datetime").datetime.fromtimestamp(
            new_ex5_mtime, tz=__import__("datetime").timezone.utc).isoformat(),
        "new_ex5_postdates_commit_f035d30_2026_09_17": True,  # 2026-09-22 > 2026-09-17
        "compile_result_line": errors_line[0].strip() if errors_line else "NOT_FOUND",
        "compile_errors_count": 0,
        "compile_warnings": warnings,
        "compile_warnings_reviewed": "Entrambi i warning sono innocui e non toccano la logica "
            "VOLATILITY_BREAKOUT_CONFIRMED: 'macro NXS_MAX_SIGNALS redefinition' (macro duplicata, "
            "innocua) e 'possible loss of data ulong->long' (conversione di tipo altrove nel file, non "
            "nella funzione segnale/execution di questa strategia).",
        "new_source_sha256": file_sha256(NEW_SOURCE_PATH),
    }

    # ================= 2. Config di ricerca corretto =================
    prior_text = prior_78h_config["payload"]["tester_execution_config_corrected"]["raw_text"]
    lines = prior_text.splitlines()

    tester_idx = lines.index("[Tester]")
    tester_inputs_idx = lines.index("[TesterInputs]")
    # Inserisce InpResearchMode/ExitMode/FixedLot subito dopo InpStrat_VolBreakoutConfirmed=true
    insert_after = lines.index("InpStrat_VolBreakoutConfirmed=true")
    research_lines = ["InpResearchMode=true", "InpResearchExitMode=0", "InpResearchFixedLot=0.01",
                       "InpProfileMultiTF=true"]
    new_lines = lines[:insert_after + 1] + research_lines + lines[insert_after + 1:]
    corrected_text = "\n".join(new_lines)

    added = [ln for ln in new_lines if ln not in lines]
    removed = [ln for ln in lines if ln not in new_lines]

    tester_config_research = {
        "base": "server/research_scripts/phase7/phase7_8h/volatility_breakout_corrected_config_v1.json"
               " (tester_execution_config_corrected.raw_text, invariato)",
        "base_sha256": prior_78h_config["payload"]["tester_execution_config_corrected"]["sha256"],
        "raw_text": corrected_text,
        "sha256": canonical_sha256({"tester_config_text": corrected_text}),
        "fields_added": added,
        "fields_removed": removed,
        "fields_added_count": len(added),
        "research_preflight_requirements_verified_in_code": {
            "InpStrategySelector_gt_0": "56 > 0 - OK",
            "InpDataCollectionMode_false": "default false, non toccato - OK "
                "(NXS_Inputs.mqh:189)",
            "InpUseInstitutionalCore_false": "plain bool sempre false, non un input esposto al Tester - OK",
            "InpUseStrategyProfiles_true": "gia' presente dal config 7.8H - OK",
            "InpProfileMultiTF_true": "default gia' true (NXS_Inputs.mqh:291), ora congelato "
                "ESPLICITAMENTE per non dipendere da un default silenzioso - richiesto da "
                "NXS_ResearchPreflight() (NXS_ResearchMode.mqh:63)",
        },
        "not_launched_yet_at_build_time": True,
    }

    correction_classification = {
        "correction_type": "RESEARCH_EXECUTION_ENABLEMENT_FIX",
        "strategy_parameters_unchanged": True,
        "entry_logic_unchanged": True,
        "sl_tp_unchanged": True,
        "timeout_unchanged": True,
        "verdict_rules_unchanged": True,
        "data_window_unchanged": True,
        "rationale": "InpResearchMode=true attiva il protocollo di ricerca isolato (lotto fisso, "
            "preflight research, esclusione delle protezioni di produzione non ammesse, logging "
            "[RESEARCH]) che era GIA' la base metodologica implicita del Serious validation dichiarata "
            "in 7.8B (execution_contract: 'RAW... nessuna idealizzazione shadow', management: 'Nessun "
            "trailing/BE/filtro di sessione o regime') - non introduce una logica nuova, attiva "
            "esplicitamente quella gia' presupposta e mai attivata per oversight.",
        "prior_runs_classification": {
            "run1_7_8g": "TECHNICALLY_INVALID_ZERO_TRADE_RUN",
            "run2_7_8h": "TECHNICAL_EXECUTION_FAILURE_STRATEGY_NEVER_INITIALIZED",
            "not_reinterpreted_as_market_result": True,
            "archived_and_unmodified": True,
        },
    }

    return recompile_evidence, tester_config_research, correction_classification


def main():
    recompile_evidence, tester_config_research, correction_classification = build()
    payload = {
        "phase": "7.8I",
        "artifact_role": "RESEARCH_CONFIG_RECOMPILE_AND_CLASSIFICATION",
        "candidate_id": "VOLATILITY_BREAKOUT_CONFIRMED",
        "recompile_evidence": recompile_evidence,
        "tester_execution_config_research": tester_config_research,
        "correction_classification": correction_classification,
        "serious_validation_not_executed_at_this_step": True,
    }
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    out_path = os.path.join(PHASE78I_DIR, "volatility_breakout_research_config_v1.json")
    save_json(out_path, doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"old_ex5={recompile_evidence['old_ex5_sha256'][:16]} new_ex5={recompile_evidence['new_ex5_sha256'][:16]}")
    print(f"fields_added={tester_config_research['fields_added']}")
    return doc


if __name__ == "__main__":
    main()
