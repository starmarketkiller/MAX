#!/usr/bin/env python3
"""NEXUS Orchestrator V1 Core - Retry ed escalation (Fase 7 del task).

    attempt -> verifier
    PASS -> COMPLETED
    FAIL -> bounded retry MASSIMO 1 (stesso agente, stesso task, nessuna
            modifica di scope - §7 dell'architettura)
    FAIL -> classify:
        ENVIRONMENT, TOOLING, LOCAL_MODEL_CAPABILITY, SCIENTIFIC_AMBIGUITY,
        COMPLEX_CODE_CHANGE, PERMISSION, UNKNOWN
    routing:
        SCIENTIFIC_AMBIGUITY -> TIER3_CLAUDE
        COMPLEX_CODE_CHANGE  -> TIER4_CODEX
        ENVIRONMENT/TOOLING  -> rimedio deterministico (TIER0), poi ri-tenta
        PERMISSION           -> APPROVAL_REQUIRED
        UNKNOWN               -> MANUAL_REVIEW

Niente loop infiniti per costruzione: RETRY_MAX_ATTEMPTS=1 e' una costante,
non un parametro che un chiamante puo' alzare a piacere."""

RETRY_MAX_ATTEMPTS = 1

CLASSIFICATIONS = ["ENVIRONMENT", "TOOLING", "LOCAL_MODEL_CAPABILITY", "SCIENTIFIC_AMBIGUITY",
                  "COMPLEX_CODE_CHANGE", "PERMISSION", "UNKNOWN", "STRATEGIC_AMBIGUITY"]
# STRATEGIC_AMBIGUITY aggiunta in NEXUS TASK #0008 (Multi-Agent Review &
# Finalization Pipeline V1) per il work_type "business analysis"/strategico -
# estensione additiva, nessuna classificazione esistente rimossa o rinominata.

ROUTING_FOR_CLASSIFICATION = {
    "SCIENTIFIC_AMBIGUITY": "TIER3_CLAUDE",
    "COMPLEX_CODE_CHANGE": "TIER4_CODEX",
    "ENVIRONMENT": "TIER0_DETERMINISTIC_REMEDIATION",
    "TOOLING": "TIER0_DETERMINISTIC_REMEDIATION",
    "PERMISSION": "APPROVAL_REQUIRED",
    "UNKNOWN": "MANUAL_REVIEW",
    # Default a TIER3_CLAUDE (unico "second opinion" oggi realmente
    # raggiungibile in automatico) - server/review_pipeline_v1/specialist_registry.py
    # puo' rimappare su STRATEGIC_GENERALIST quando un provider come ChatGPT
    # risulta CONFIGURED+AVAILABLE, senza toccare questo default.
    "STRATEGIC_AMBIGUITY": "TIER3_CLAUDE",
    # LOCAL_MODEL_CAPABILITY non ha una riga fissa: dipende se esiste un tier
    # locale piu' forte non ancora provato (escalation TIER1->TIER2) o se
    # anche il piu' forte ha gia' fallito (allora sale a Claude/Codex in base
    # al code_risk del task - decisione presa dal chiamante, non hardcoded
    # qui, perche' dipende dal manifest).
}

_ENV_PATTERNS = ["read timed out", "readtimeout", "connectionerror", "connection refused",
                "out of memory", "oom", "killed", "low-memory", "low memory"]
_TOOLING_PATTERNS = ["modulenotfounderror", "importerror", "nameerror", "no such file or "
                    "directory", "filenotfounderror", "harness_error"]
_PERMISSION_PATTERNS = ["files_forbidden", "permission denied", "vietato", "non consentito"]


def classify_failure(error_texts, *, task_touched_forbidden_file=False,
                    is_logic_error_not_crash=False, requires_scientific_judgment=False,
                    requires_multi_file_refactor=False):
    """Classificazione EURISTICA basata su pattern (trasparente, non una
    black-box) + segnali strutturati espliciti passati dal chiamante (che
    conosce il contesto del task meglio di quanto un semplice grep possa
    dedurre). I segnali strutturati hanno PRIORITA' sui pattern testuali."""
    if task_touched_forbidden_file:
        return "PERMISSION"
    if requires_scientific_judgment:
        return "SCIENTIFIC_AMBIGUITY"
    if requires_multi_file_refactor:
        return "COMPLEX_CODE_CHANGE"

    combined = " ".join(str(e).lower() for e in error_texts)
    if any(p in combined for p in _ENV_PATTERNS):
        return "ENVIRONMENT"
    if any(p in combined for p in _TOOLING_PATTERNS):
        return "TOOLING"
    if is_logic_error_not_crash:
        return "LOCAL_MODEL_CAPABILITY"
    if not combined.strip():
        # returncode!=0 senza messaggio d'errore chiaro, o un mismatch di
        # verifica senza eccezione - trattato come capacita' del modello,
        # non come ambiente (nessun segnale di crash/ambiente rilevato).
        return "LOCAL_MODEL_CAPABILITY"
    return "UNKNOWN"


def decide_escalation_target(classification, manifest, already_tried_stronger_local=False):
    """Per LOCAL_MODEL_CAPABILITY: se esiste un tier locale piu' forte non
    ancora provato, ri-prova li' PRIMA di salire a premium (stessa gerarchia
    empiricamente validata nel bake-off: 3B/FAST -> STRONG -> premium, mai
    saltare direttamente a Claude/Codex per un compito che il tier locale
    superiore potrebbe gestire)."""
    if classification == "LOCAL_MODEL_CAPABILITY" and not already_tried_stronger_local:
        return "TIER2_LOCAL_STRONG_RETRY"
    if classification == "LOCAL_MODEL_CAPABILITY" and already_tried_stronger_local:
        # entrambi i tier locali hanno fallito - sale in base al code_risk
        return "TIER4_CODEX" if manifest["code_risk"] in ("MEDIUM", "HIGH") else "TIER3_CLAUDE"
    return ROUTING_FOR_CLASSIFICATION.get(classification, "MANUAL_REVIEW")
