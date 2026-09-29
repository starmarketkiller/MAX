#!/usr/bin/env python3
"""NEXUS TASK #0008 punto 11 - Finalization Gate: deterministico, controlla
ogni precondizione esplicitamente elencata dall'utente. Nessuno stato
FINALIZED viene mai raggiunto bypassando questo gate."""
import json
import re

# Pattern di secret ragionevolmente specifici (non un filtro generico su
# 'password'/'token' come parola - troppi falsi positivi in un output di
# lavoro legittimo che PARLA di token/secret senza contenerne uno reale).
_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),                 # chiavi stile OpenAI/Anthropic
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),                 # GitHub personal access token
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),   # chiave privata
    re.compile(r"\d{9,10}:[A-Za-z0-9_-]{30,}"),          # forma bot-id:secret di Telegram
]


def _scan_for_secrets(final_output):
    text = json.dumps(final_output, ensure_ascii=False) if not isinstance(final_output, str) \
        else final_output
    found = []
    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            found.append(pattern.pattern)
    return found


def check_finalization_gate(*, work_product, verifier_passed, review_completed_if_required,
                           open_escalation, provenance_complete, output_schema_errors,
                           required_approvals_present, policy_violations, final_output):
    """Ritorna (passed: bool, failures: list[str]). Ogni condizione e'
    controllata ESPLICITAMENTE - nessuna scorciatoia 'se tutto il resto va
    bene assumo anche questo'."""
    failures = []

    if not verifier_passed:
        failures.append("verifier non PASS")
    if work_product.get("review_required") and not review_completed_if_required:
        failures.append("review richiesta dalla Review Matrix ma non completata")
    if open_escalation:
        failures.append(f"escalation ancora aperta: {open_escalation}")
    if not provenance_complete:
        failures.append("provenance incompleta (producer/reviewer/verifier/sources mancanti)")
    if output_schema_errors:
        failures.append(f"output non valido contro lo schema atteso: {output_schema_errors}")
    if not required_approvals_present:
        failures.append("approval richieste dal task non presenti")
    if policy_violations:
        failures.append(f"policy violation rilevate: {policy_violations}")

    secrets_found = _scan_for_secrets(final_output)
    if secrets_found:
        failures.append(f"possibile secret rilevato nell'output finale ({len(secrets_found)} "
                       "pattern) - finalizzazione bloccata")

    unresolved_blocker = work_product.get("blocked_reason")
    if unresolved_blocker:
        failures.append(f"blocker non risolto: {unresolved_blocker}")

    return (len(failures) == 0), failures
