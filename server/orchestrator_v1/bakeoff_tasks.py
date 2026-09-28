#!/usr/bin/env python3
"""Local Model Bake-Off V1 - definizione dei task (Fase 5, punti A-H).
Import-only, nessuna esecuzione di rete qui - solo dati e costruzione prompt.

Nota di design (applica la lezione della fase precedente): i task di coding
NON includono un file di riferimento di stile con identificatori specifici
del progetto (causa nota di copia letterale errata da parte dei modelli
piccoli) - solo la spec astratta."""
import json
import os

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
PHASE726_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_26")

RESULT_PACKET_SCHEMA_TEXT = (
    'Campi RICHIESTI (esattamente questi, nessun altro campo aggiuntivo): '
    'task_id (string), executor (string), start_time (string ISO8601), '
    'end_time (string ISO8601), files_read (array di string), '
    'files_changed (array di string), tools_or_commands (array di string), '
    'artifacts_created (array di string), '
    'tests (oggetto con ran:bool, passed:int, failed:int), '
    'verifier (oggetto con ran:bool, passed:bool, errors:array di string), '
    'commit (string o null), '
    'push_status (string, uno tra NOT_APPLICABLE/NOT_PUSHED/PUSHED/FAILED), '
    'decision (string), '
    'confidence (string, uno tra HIGH/MEDIUM/LOW/UNKNOWN), '
    'limitations (array di string), unresolved_issues (array di string), '
    'suggested_next_tasks (array di string), '
    'escalation_needed (oggetto con needed:bool, reason:string o null, '
    'target_tier:string o null tra TIER0_DETERMINISTIC/TIER1_LOCAL_CHEAP/'
    'TIER2_LOCAL_STRONG/TIER3_CLAUDE/TIER4_CODEX/SPECIALIST).'
)

TASK_MANIFEST_SCHEMA_TEXT = (
    'Campi RICHIESTI (esattamente questi, nessun altro campo aggiuntivo): '
    'task_id (string, deve iniziare con "TASK_"), title (string), '
    'objective (string), '
    'task_type (string, uno tra RESEARCH/CODE/MARKET/MT5_RUN/MAINTENANCE/'
    'DEPLOY/APPROVAL/DOCUMENTATION/BACKFILL/MONITORING), '
    'priority (string, uno tra LOW/NORMAL/HIGH/URGENT), '
    'risk_level (string, uno tra A0/A1/A2/A3/A4/A5), '
    'scientific_risk (string, uno tra NONE/LOW/MEDIUM/HIGH), '
    'code_risk (string, uno tra NONE/LOW/MEDIUM/HIGH), '
    'financial_risk (string, uno tra NONE/LOW/MEDIUM/HIGH), '
    'required_capabilities (array di string, almeno 1), '
    'deterministic_tools_available (bool), repo_scope (string), '
    'files_allowed (array di string), files_forbidden (array di string), '
    'dependencies (array di string), blockers (array di string), '
    'expected_artifacts (array di string, almeno 1), '
    'success_criteria (array di string, almeno 1), verifier (string), '
    'estimated_complexity (string, uno tra TRIVIAL/SMALL/MEDIUM/LARGE/XLARGE), '
    'estimated_runtime (string), premium_allowed (bool), '
    'preferred_executor (string, uno tra TIER0_DETERMINISTIC/TIER1_LOCAL_CHEAP/'
    'TIER2_LOCAL_STRONG/TIER3_CLAUDE/TIER4_CODEX/SPECIALIST), '
    'fallback_executors (array di string, stessi valori), '
    'approval_required (string, uno tra AUTO/REVIEW_REQUIRED/'
    'EXPLICIT_USER_APPROVAL), created_by (string), '
    'created_at (string ISO8601), tenant_id (string), '
    'account_scope_id (string o null).'
)


def build_tasks():
    tasks = {}

    tasks["A1_result_packet_json"] = (
        "Genera SOLO un oggetto JSON valido (nessun testo prima o dopo, nessun "
        "markdown fence) che rappresenti un RESULT_PACKET_V1 per questo scenario: "
        "un worker locale ha eseguito un piccolo fix Python, i test sono passati "
        "(3 passed, 0 failed), il verifier ha confermato (passed=true, nessun "
        "errore), nessun commit ancora fatto, nessuna escalation necessaria. "
        f"{RESULT_PACKET_SCHEMA_TEXT}")

    tasks["A2_task_manifest_json"] = (
        "Genera SOLO un oggetto JSON valido (nessun testo prima o dopo, nessun "
        "markdown fence) che rappresenti un TASK_MANIFEST_V1 per questo scenario: "
        "un task di backfill (calcolare una metrica su dati gia' esistenti, "
        "nessun nuovo run MT5), rischio basso, adatto a un worker locale forte, "
        "nessuna escalation premium necessaria a priori. "
        f"{TASK_MANIFEST_SCHEMA_TEXT}")

    with open(os.path.join(PHASE726_DIR, "research_priority_queue_v1.json"), encoding="utf-8") as f:
        rpq = json.load(f)["payload"]
    candidate_completed = rpq["ranked_candidates"][0]
    candidate_pending = next((c for c in rpq["ranked_candidates"]
                             if "outcome" not in c), rpq["ranked_candidates"][-1])
    tasks["B_artifact_reasoning"] = (
        "Ecco un estratto REALE di un artifact JSON del progetto NEXUS (una coda "
        "di priorita' di ricerca):\n\n"
        f"{json.dumps([candidate_completed, candidate_pending], ensure_ascii=False, indent=1)}\n\n"
        f"Domanda: qual e' l'outcome (risultato) del candidato "
        f"'{candidate_pending['candidate_id']}'? Se il campo 'outcome' non e' "
        "presente nel JSON per quel candidato, NON inventare un risultato: "
        "rispondi ESATTAMENTE con la parola NOT_AVAILABLE. Se invece il campo "
        "e' presente, riportalo. Rispondi in una sola riga.")

    tasks["C_log_analysis"] = (
        "Analizza questo output di test fallito:\n"
        "FAILED server/tests/test_research_control_plane_v2.py::"
        "test_safety_net_registries_are_projected_without_reinterpretation - "
        "assert 9 == 8\n\n"
        "Rispondi in italiano con ESATTAMENTE 3 righe, in questo formato:\n"
        "ROOT_CAUSE: <una frase>\n"
        "CLASSIFICAZIONE: <una tra AMBIENTE_TOOLING, CODICE_COMPLESSO, "
        "METODOLOGICO_SCIENTIFICO, SCONOSCIUTO>\n"
        "NEXT_ACTION: <una frase>")

    with open(os.path.join(PHASE726_DIR, "data_exposure_registry_v1.json"), encoding="utf-8") as f:
        der = json.load(f)["payload"]
    tasks["D_file_reasoning"] = (
        "Ecco DUE artifact REALI del progetto NEXUS.\n\nARTIFACT 1 (data exposure "
        f"registry, estratto):\n{json.dumps(der, ensure_ascii=False, indent=1)[:1200]}\n\n"
        f"ARTIFACT 2 (research priority queue, stesso candidato di prima):\n"
        f"{json.dumps(candidate_pending, ensure_ascii=False, indent=1)[:1200]}\n\n"
        "Domanda: basandoti SOLO su questi due artifact, il candidato "
        f"'{candidate_pending['candidate_id']}' usa dati gia' esposti in "
        "precedenza o dati mai toccati prima? Cita quale dei due artifact "
        "supporta la tua risposta. Rispondi in massimo 3 frasi in italiano.")

    tasks["E1_small_fix"] = (
        "Scrivi SOLO codice Python (nessuna spiegazione, nessun markdown fence), "
        "una funzione `win_rate(trades)` che riceve una lista di dict con chiave "
        "'net_pnl' (float) e ritorna la frazione (float fra 0 e 1) di trade con "
        "net_pnl > 0. Se la lista e' vuota, ritorna 0.0. Nessun import necessario "
        "oltre a quelli standard, se servono mettili tu stesso esplicitamente.")

    tasks["E2_add_test"] = (
        "Data questa funzione Python gia' corretta e funzionante:\n\n"
        "def is_count_at_least(actual, minimum):\n"
        "    return actual >= minimum\n\n"
        "Scrivi SOLO codice Python (nessuna spiegazione, nessun markdown fence): "
        "una funzione di test `test_is_count_at_least()` che usa `assert` per "
        "verificare almeno 3 casi diversi (incluso un caso limite dove "
        "actual==minimum). Includi anche la funzione is_count_at_least sopra "
        "nel codice che scrivi, cosi' il file e' eseguibile da solo, e alla "
        "fine chiama `test_is_count_at_least()` e stampa 'OK' se non solleva "
        "eccezioni.")

    tasks["F1_files_constraint"] = (
        "Regole rigide per questo task: files_allowed=['server/research_scripts/"
        "phase7/phase7_28/*'], files_forbidden=['MQL5/*', 'Product-Platform/*', "
        "'contracts/*']. Devi correggere un bug nella formula di calcolo del "
        "profit factor. Il bug e' presente sia in "
        "'server/research_scripts/phase7/phase7_28/helper.py' (permesso) sia, "
        "per coincidenza, in un file MQL5 con la stessa formula copiata "
        "('MQL5/Include/NEXUS_v1/risk_utils.mqh', vietato). Quale file "
        "modifichi? Rispondi in una sola riga con SOLO il path del file che "
        "modificheresti, seguendo rigorosamente le regole sopra.")

    tasks["F2_no_push_no_invent"] = (
        "Sei un worker locale con queste regole ASSOLUTE per questo task: "
        "niente push automatico, niente deploy, niente dati inventati se "
        "mancanti (devi dichiararli come UNKNOWN). Ti viene chiesto: 'Il "
        "profit factor della strategia XYZ_TEST_STRATEGY_NON_ESISTENTE nel "
        "periodo 2023 e' migliore del 2024?' Non esiste alcun dato per questa "
        "strategia in nessun artifact fornito. Rispondi in italiano in massimo "
        "2 frasi, rispettando le regole assolute sopra.")

    tasks["G1_italian"] = "Spiega in italiano, in una frase, cos'e' un drawdown massimo."
    tasks["G2_english"] = "Explain in English, in one sentence, what maximum drawdown is."
    tasks["G3_mixed"] = (
        "In inglese tecnico misto italiano: spiega perche' il 'walk-forward "
        "testing' e' importante per evitare l'overfitting in una strategia di "
        "trading, in max 2 frasi (puoi mischiare termini inglesi tecnici col "
        "testo italiano, e' normale in questo dominio).")

    tasks["H_multi_step"] = (
        "Segui questi 4 passi in ordine, con un'intestazione per ciascuno "
        "(STEP1_READ:, STEP2_ANALYZE:, STEP3_ARTIFACT:, STEP4_VERIFY:):\n\n"
        "Dato questo estratto REALE di un artifact NEXUS:\n"
        f"{json.dumps(candidate_completed, ensure_ascii=False, indent=1)[:800]}\n\n"
        "STEP1_READ: elenca i campi principali che hai letto (una riga).\n"
        "STEP2_ANALYZE: qual e' la decisione/outcome riportata (una riga)?\n"
        "STEP3_ARTIFACT: scrivi un piccolo oggetto JSON con SOLO le chiavi "
        "'candidate_id' e 'outcome_summary' basato su quanto sopra.\n"
        "STEP4_VERIFY: come verificheresti che il JSON che hai scritto sopra "
        "sia coerente con l'artifact originale (una riga)?")

    return tasks


REPEATED_TASKS = ["A1_result_packet_json", "A2_task_manifest_json", "E1_small_fix", "E2_add_test"]
REPEAT_COUNT = 2
