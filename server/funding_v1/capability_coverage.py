#!/usr/bin/env python3
"""NEXUS TASK #0006 - Capability Coverage V1: confronta le capacita'
DICHIARATE richieste da un'opportunity con le capacita' GIA' dimostrate/
disponibili in NEXUS (tassonomia fissa di 15) - calcolo puramente
deterministico, mai una stima.

NEXUS_CURRENT_CAPABILITIES e' lo stato REALE di questo repository a oggi
(non aspirazionale) - ogni voce e' giustificata da un artifact/fase
concreta gia' esistente in questo progetto, non una dichiarazione vaga."""

ALL_CAPABILITIES = [
    "orchestrator", "deterministic_workers", "local_llm", "research", "coding",
    "website_generation", "content", "image_video", "messaging", "crm", "analytics",
    "payments", "voice", "physical_fulfillment", "customer_support",
]

# Stato REALE dichiarato di ogni capacita' NEXUS oggi - vedi rationale per la fonte.
NEXUS_CURRENT_CAPABILITIES = {
    "orchestrator": ("AVAILABLE_NOW", "Task Queue/Router/Ledger operativi, NEXUS TASK "
                    "#0001-#0005 (server/orchestrator_v1/core/)"),
    "deterministic_workers": ("AVAILABLE_NOW", "deterministic_worker.py, azioni gia' "
                            "dimostrate in 4 NEXUS TASK reali"),
    "local_llm": ("AVAILABLE_NOW", "ministral-3:3b via Ollama, Local Model Bake-Off V1"),
    "research": ("AVAILABLE_NOW", "pipeline Phase 7 (backtest/validazione/provenance) - "
                "gia' usato per 27+ fasi di ricerca reali"),
    "coding": ("AVAILABLE_NOW", "Claude/Codex + worker locale per piccoli fix (dimostrato "
             "in NEXUS TASK #0002/#0003)"),
    "website_generation": ("PARTIAL", "Control Plane React/FastAPI gia' esistente "
                          "(Product-Platform/), ma nessuna pipeline di generazione siti "
                          "PER TERZI"),
    "content": ("PARTIAL", "ministral-3:3b puo' generare testo (narrative gia' dimostrate "
              "in NEXUS TASK #0002), ma nessuna pipeline editoriale/qualita' per contenuto "
              "rivolto a clienti esterni"),
    "image_video": ("MISSING", "nessuna capacita' di generazione immagini/video in questo "
                   "repository - richiederebbe un servizio esterno"),
    "messaging": ("MISSING", "nessuna integrazione email/SMS/chat outbound esistente in "
                 "questo repository (Telegram/PWA menzionati come client futuri, non "
                 "ancora costruiti)"),
    "crm": ("MISSING", "nessun sistema di gestione contatti/lead esistente"),
    "analytics": ("PARTIAL", "forte capacita' di analytics INTERNA (Phase 7, Control "
                "Plane), ma nessuna pipeline di analytics per un prodotto/servizio "
                "rivolto a clienti esterni"),
    "payments": ("EXTERNAL_SERVICE_REQUIRED", "nessuna integrazione di pagamento - "
                "richiederebbe Stripe/simili, mai integrati in questo repository"),
    "voice": ("MISSING", "nessuna sintesi/riconoscimento vocale in questo repository (il "
             "'client voce' e' menzionato come obiettivo futuro di Jarvis, non ancora "
             "costruito)"),
    "physical_fulfillment": ("EXTERNAL_SERVICE_REQUIRED", "NEXUS e' un sistema software - "
                            "qualunque fulfillment fisico (es. stampa NFC/QR) richiede "
                            "SEMPRE un fornitore esterno"),
    "customer_support": ("MISSING", "nessuna pipeline di supporto clienti (chatbot/ticket) "
                        "esistente oggi"),
}


def compute_capability_coverage(required_capabilities):
    """required_capabilities: lista dichiarata di capacita' richieste da
    un'opportunity (sottoinsieme di ALL_CAPABILITIES). Ritorna il dict
    conforme a CAPABILITY_COVERAGE_V1."""
    per_capability = {}
    blockers = []
    required_set = set(required_capabilities)
    covered_count = 0

    for cap in ALL_CAPABILITIES:
        if cap not in required_set:
            per_capability[cap] = "NOT_REQUIRED"
            continue
        status, _rationale = NEXUS_CURRENT_CAPABILITIES[cap]
        per_capability[cap] = status
        if status == "AVAILABLE_NOW":
            covered_count += 1
        elif status in ("MISSING", "EXTERNAL_SERVICE_REQUIRED"):
            blockers.append(f"{cap}: {status}")
        # PARTIAL non e' un blocker (coerente con hard_gates.py: solo MISSING/
        # EXTERNAL_SERVICE_REQUIRED bloccano BLOCKED_BY_CAPABILITY) - contribuisce comunque
        # negativamente a existing_capability_coverage_pct sotto.

    pct = round(covered_count / len(required_set) * 100, 2) if required_set else 100.0
    return {"schema_version": 1, "per_capability": per_capability,
           "existing_capability_coverage_pct": pct, "blockers": blockers}
