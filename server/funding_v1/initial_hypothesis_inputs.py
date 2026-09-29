#!/usr/bin/env python3
"""NEXUS TASK #0006 punto 11 - dataset iniziale aderente ai casi reali
discussi. Campi STRUTTURATI (dimensions/technical_criteria/capabilities/
next_cheapest_validation_step) dichiarati qui da Claude (giudizio di
design, stessa categoria di lavoro gia' fatta per la tabella di
classificazione in NEXUS TASK #0002 - MAI un'invenzione di dati di
mercato, solo stime esplicite). I campi NARRATIVI (description/
technical_rationale/funding_rationale) sono generati da ministral-3:3b
attraverso l'Orchestrator (vedi run_nexus_task_0006_generate_dataset.py) -
questo modulo fornisce SOLO l'input strutturato per quella generazione.

Tutte marcate INITIAL_HYPOTHESIS - evidence_confidence=LOW uniforme (zero
dati di mercato reali), input_type=ASSUMPTION."""

INITIAL_HYPOTHESES = [
    {"id": "OPP_LOCAL_BUSINESS_STARTER_PACK", "title": "Local Business Starter Pack",
    "category": "SERVICE",
    "dimensions": {"time_to_cash": "SHORT_LT_1M", "capital_required": "LOW",
                 "sales_difficulty": "HIGH", "margin": "MEDIUM", "recurrence": "OCCASIONAL",
                 "automation_level": "PARTIALLY_AUTOMATED", "skills_available": "PARTIAL",
                 "premium_tool_dependency": "LOW_COST", "strategic_reuse": "PARTIAL",
                 "risk": "LOW", "human_time_required": "SIGNIFICANT"},
    "technical_criteria": {"novelty": "LOW", "infrastructure_leverage": "NONE",
                          "complexity_interest": "LOW", "long_term_strategic_value": "LOW"},
    "required_capabilities": ["website_generation", "content", "crm"],
    "next_cheapest_validation_step": {
        "description": "Contattare 10 attivita' locali offrendo il pack gratis a 1 di loro "
                      "in cambio di una recensione/caso studio - misurare interesse dalle "
                      "risposte, non dalle vendite.",
        "estimated_cost": "NONE", "reversibility": "FULLY_REVERSIBLE", "speed": "WEEKS",
        "informational_value": "HIGH"}},
    {"id": "OPP_MINI_SITE_LANDING_PAGE", "title": "Mini-site / Landing Page",
    "category": "PRODUCT",
    "dimensions": {"time_to_cash": "SHORT_LT_1M", "capital_required": "NONE",
                 "sales_difficulty": "MEDIUM", "margin": "MEDIUM", "recurrence": "ONE_OFF",
                 "automation_level": "PARTIALLY_AUTOMATED", "skills_available": "FULLY_AVAILABLE",
                 "premium_tool_dependency": "LOW_COST", "strategic_reuse": "PARTIAL",
                 "risk": "LOW", "human_time_required": "PART_TIME"},
    "technical_criteria": {"novelty": "LOW", "infrastructure_leverage": "NONE",
                          "complexity_interest": "LOW", "long_term_strategic_value": "LOW"},
    "required_capabilities": ["website_generation", "content"],
    "next_cheapest_validation_step": {
        "description": "Costruire 1 landing page demo per un business immaginario e "
                      "mostrarla a 5 conoscenti che gestiscono piccole attivita' - misurare "
                      "se capiscono subito il valore senza spiegazioni.",
        "estimated_cost": "NONE", "reversibility": "FULLY_REVERSIBLE", "speed": "DAYS",
        "informational_value": "MEDIUM"}},
    {"id": "OPP_REVIEW_KIT_QR_NFC", "title": "Review Kit QR/NFC",
    "category": "PRODUCT",
    "dimensions": {"time_to_cash": "SHORT_LT_1M", "capital_required": "LOW",
                 "sales_difficulty": "MEDIUM", "margin": "HIGH", "recurrence": "ONE_OFF",
                 "automation_level": "FULLY_AUTOMATED", "skills_available": "NEEDS_LEARNING",
                 "premium_tool_dependency": "LOW_COST", "strategic_reuse": "NONE",
                 "risk": "LOW", "human_time_required": "PART_TIME"},
    "technical_criteria": {"novelty": "LOW", "infrastructure_leverage": "NONE",
                          "complexity_interest": "LOW", "long_term_strategic_value": "LOW"},
    "required_capabilities": ["physical_fulfillment", "website_generation"],
    "next_cheapest_validation_step": {
        "description": "Verificare il costo REALE di stampa/fornitura di 20 card NFC/QR "
                      "presso 2 fornitori online, prima di assumere qualunque margine.",
        "estimated_cost": "LOW", "reversibility": "FULLY_REVERSIBLE", "speed": "DAYS",
        "informational_value": "HIGH"}},
    {"id": "OPP_SMART_BUSINESS_CARD_NFC_QR", "title": "Smart Business Card NFC/QR",
    "category": "PRODUCT",
    "dimensions": {"time_to_cash": "SHORT_LT_1M", "capital_required": "LOW",
                 "sales_difficulty": "MEDIUM", "margin": "HIGH", "recurrence": "SUBSCRIPTION",
                 "automation_level": "FULLY_AUTOMATED", "skills_available": "NEEDS_LEARNING",
                 "premium_tool_dependency": "LOW_COST", "strategic_reuse": "NONE",
                 "risk": "LOW", "human_time_required": "PART_TIME"},
    "technical_criteria": {"novelty": "LOW", "infrastructure_leverage": "NONE",
                          "complexity_interest": "LOW", "long_term_strategic_value": "LOW"},
    "required_capabilities": ["physical_fulfillment", "website_generation"],
    "next_cheapest_validation_step": {
        "description": "Come Review Kit: verificare costi reali di fornitura prima di "
                      "assumere margini - stesso fornitore, testare entrambi insieme.",
        "estimated_cost": "LOW", "reversibility": "FULLY_REVERSIBLE", "speed": "DAYS",
        "informational_value": "HIGH"}},
    {"id": "OPP_DIGITAL_MENU", "title": "Digital Menu",
    "category": "PRODUCT",
    "dimensions": {"time_to_cash": "SHORT_LT_1M", "capital_required": "NONE",
                 "sales_difficulty": "MEDIUM", "margin": "MEDIUM", "recurrence": "SUBSCRIPTION",
                 "automation_level": "FULLY_AUTOMATED", "skills_available": "FULLY_AVAILABLE",
                 "premium_tool_dependency": "NONE", "strategic_reuse": "PARTIAL",
                 "risk": "LOW", "human_time_required": "MINIMAL"},
    "technical_criteria": {"novelty": "LOW", "infrastructure_leverage": "NONE",
                          "complexity_interest": "LOW", "long_term_strategic_value": "LOW"},
    "required_capabilities": ["website_generation", "content"],
    "next_cheapest_validation_step": {
        "description": "Verificare quanti ristoranti locali usano gia' un menu digitale "
                      "cercando i loro siti/Google Business - misurare saturazione del "
                      "mercato prima di costruire nulla.",
        "estimated_cost": "NONE", "reversibility": "FULLY_REVERSIBLE", "speed": "DAYS",
        "informational_value": "MEDIUM"}},
    {"id": "OPP_BOOKING_PACK", "title": "Booking Pack",
    "category": "SAAS",
    "dimensions": {"time_to_cash": "MEDIUM_1_3M", "capital_required": "LOW",
                 "sales_difficulty": "MEDIUM", "margin": "MEDIUM", "recurrence": "SUBSCRIPTION",
                 "automation_level": "PARTIALLY_AUTOMATED", "skills_available": "PARTIAL",
                 "premium_tool_dependency": "MODERATE_COST", "strategic_reuse": "NONE",
                 "risk": "MEDIUM", "human_time_required": "SIGNIFICANT"},
    "technical_criteria": {"novelty": "LOW", "infrastructure_leverage": "NONE",
                          "complexity_interest": "MEDIUM", "long_term_strategic_value": "LOW"},
    "required_capabilities": ["website_generation", "crm", "messaging", "payments"],
    "next_cheapest_validation_step": {
        "description": "Confrontare 5 tool di booking gia' esistenti sul mercato (prezzo/"
                      "feature) prima di assumere che serva costruirne uno nuovo.",
        "estimated_cost": "NONE", "reversibility": "FULLY_REVERSIBLE", "speed": "DAYS",
        "informational_value": "HIGH"}},
    {"id": "OPP_LEAD_CAPTURE_FOLLOWUP_PACK", "title": "Lead Capture / Follow-up Pack",
    "category": "SAAS",
    "dimensions": {"time_to_cash": "MEDIUM_1_3M", "capital_required": "LOW",
                 "sales_difficulty": "MEDIUM", "margin": "MEDIUM", "recurrence": "SUBSCRIPTION",
                 "automation_level": "FULLY_AUTOMATED", "skills_available": "PARTIAL",
                 "premium_tool_dependency": "MODERATE_COST", "strategic_reuse": "PARTIAL",
                 "risk": "MEDIUM", "human_time_required": "PART_TIME"},
    "technical_criteria": {"novelty": "MEDIUM", "infrastructure_leverage": "PARTIAL",
                          "complexity_interest": "MEDIUM", "long_term_strategic_value": "MEDIUM"},
    "required_capabilities": ["crm", "messaging", "local_llm"],
    "next_cheapest_validation_step": {
        "description": "Costruire 1 form + 1 sequenza di follow-up automatico per un caso "
                      "d'uso finto e testarla end-to-end con la propria email, prima di "
                      "proporla a chiunque.",
        "estimated_cost": "NONE", "reversibility": "FULLY_REVERSIBLE", "speed": "DAYS",
        "informational_value": "MEDIUM"}},
    {"id": "OPP_CONTENT_REPURPOSING_SOCIAL_PACK", "title": "Content Repurposing / Social Pack",
    "category": "SERVICE",
    "dimensions": {"time_to_cash": "SHORT_LT_1M", "capital_required": "NONE",
                 "sales_difficulty": "HIGH", "margin": "MEDIUM", "recurrence": "SUBSCRIPTION",
                 "automation_level": "PARTIALLY_AUTOMATED", "skills_available": "PARTIAL",
                 "premium_tool_dependency": "LOW_COST", "strategic_reuse": "PARTIAL",
                 "risk": "MEDIUM", "human_time_required": "SIGNIFICANT"},
    "technical_criteria": {"novelty": "LOW", "infrastructure_leverage": "PARTIAL",
                          "complexity_interest": "LOW", "long_term_strategic_value": "LOW"},
    "required_capabilities": ["content", "local_llm", "image_video"],
    "next_cheapest_validation_step": {
        "description": "Ripurposare 1 contenuto lungo gia' esistente in 5 post social con "
                      "ministral-3:3b e valutare a mano la qualita' prima di offrirlo come "
                      "servizio.",
        "estimated_cost": "NONE", "reversibility": "FULLY_REVERSIBLE", "speed": "HOURS",
        "informational_value": "MEDIUM"}},
    {"id": "OPP_AI_CUSTOMER_SUPPORT", "title": "AI Customer Support",
    "category": "SAAS",
    "dimensions": {"time_to_cash": "LONG_3_6M", "capital_required": "MEDIUM",
                 "sales_difficulty": "HIGH", "margin": "HIGH", "recurrence": "SUBSCRIPTION",
                 "automation_level": "FULLY_AUTOMATED", "skills_available": "PARTIAL",
                 "premium_tool_dependency": "MODERATE_COST", "strategic_reuse": "HIGH",
                 "risk": "MEDIUM", "human_time_required": "SIGNIFICANT"},
    "technical_criteria": {"novelty": "MEDIUM", "infrastructure_leverage": "HIGH",
                          "complexity_interest": "HIGH", "long_term_strategic_value": "HIGH"},
    "required_capabilities": ["local_llm", "customer_support", "messaging", "crm"],
    "next_cheapest_validation_step": {
        "description": "Costruire un prototipo di supporto clienti con ministral-3:3b su "
                      "10 domande frequenti finte e valutare a mano l'accuratezza, prima di "
                      "proporlo a un cliente reale.",
        "estimated_cost": "NONE", "reversibility": "FULLY_REVERSIBLE", "speed": "WEEKS",
        "informational_value": "HIGH"}},
    {"id": "OPP_AI_RECEPTIONIST", "title": "AI Receptionist",
    "category": "SAAS",
    "dimensions": {"time_to_cash": "LONG_3_6M", "capital_required": "MEDIUM",
                 "sales_difficulty": "HIGH", "margin": "HIGH", "recurrence": "SUBSCRIPTION",
                 "automation_level": "FULLY_AUTOMATED", "skills_available": "NEEDS_LEARNING",
                 "premium_tool_dependency": "MODERATE_COST", "strategic_reuse": "PARTIAL",
                 "risk": "HIGH", "human_time_required": "SIGNIFICANT"},
    "technical_criteria": {"novelty": "HIGH", "infrastructure_leverage": "HIGH",
                          "complexity_interest": "HIGH", "long_term_strategic_value": "HIGH"},
    "required_capabilities": ["voice", "local_llm", "messaging", "crm"],
    "next_cheapest_validation_step": {
        "description": "NON avviare nulla finche' la capacita' 'voice' non esiste in NEXUS - "
                      "il primo passo reale e' valutare un fornitore esterno di sintesi/"
                      "riconoscimento vocale, non costruire nulla in proprio.",
        "estimated_cost": "NONE", "reversibility": "FULLY_REVERSIBLE", "speed": "DAYS",
        "informational_value": "HIGH"}},
    {"id": "OPP_LEAD_RESEARCH_SERVICE", "title": "Lead Research Service",
    "category": "SERVICE",
    "dimensions": {"time_to_cash": "SHORT_LT_1M", "capital_required": "NONE",
                 "sales_difficulty": "HIGH", "margin": "HIGH", "recurrence": "OCCASIONAL",
                 "automation_level": "PARTIALLY_AUTOMATED", "skills_available": "FULLY_AVAILABLE",
                 "premium_tool_dependency": "NONE", "strategic_reuse": "HIGH",
                 "risk": "LOW", "human_time_required": "PART_TIME"},
    "technical_criteria": {"novelty": "LOW", "infrastructure_leverage": "PARTIAL",
                          "complexity_interest": "LOW", "long_term_strategic_value": "LOW"},
    "required_capabilities": ["research", "local_llm", "crm"],
    "next_cheapest_validation_step": {
        "description": "Fare una ricerca di 20 prospect finti per un settore a caso "
                      "riusando la pipeline 'research' gia' esistente e misurare tempo/"
                      "qualita' reali, prima di venderla come servizio.",
        "estimated_cost": "NONE", "reversibility": "FULLY_REVERSIBLE", "speed": "DAYS",
        "informational_value": "HIGH"}},
    {"id": "OPP_MICRO_SAAS", "title": "Micro-SaaS",
    "category": "SAAS",
    "dimensions": {"time_to_cash": "LONG_3_6M", "capital_required": "LOW",
                 "sales_difficulty": "HIGH", "margin": "HIGH", "recurrence": "SUBSCRIPTION",
                 "automation_level": "FULLY_AUTOMATED", "skills_available": "PARTIAL",
                 "premium_tool_dependency": "LOW_COST", "strategic_reuse": "PARTIAL",
                 "risk": "MEDIUM", "human_time_required": "SIGNIFICANT"},
    "technical_criteria": {"novelty": "MEDIUM", "infrastructure_leverage": "PARTIAL",
                          "complexity_interest": "MEDIUM", "long_term_strategic_value": "MEDIUM"},
    "required_capabilities": ["coding", "website_generation", "payments"],
    "next_cheapest_validation_step": {
        "description": "Identificare un problema specifico e ristretto gia' incontrato in "
                      "questo stesso progetto che varrebbe la pena risolvere per altri, "
                      "prima di generalizzare l'idea 'micro-SaaS' in astratto.",
        "estimated_cost": "NONE", "reversibility": "FULLY_REVERSIBLE", "speed": "WEEKS",
        "informational_value": "MEDIUM"}},
    {"id": "OPP_NEXUS_JARVIS_EXTERNAL_PRODUCT", "title": "NEXUS/Jarvis external product",
    "category": "SAAS",
    "dimensions": {"time_to_cash": "VERY_LONG_GT_6M", "capital_required": "HIGH",
                 "sales_difficulty": "VERY_HIGH", "margin": "HIGH", "recurrence": "SUBSCRIPTION",
                 "automation_level": "PARTIALLY_AUTOMATED", "skills_available": "NEEDS_LEARNING",
                 "premium_tool_dependency": "MODERATE_COST", "strategic_reuse": "CORE_REUSE",
                 "risk": "VERY_HIGH", "human_time_required": "FULL_TIME"},
    "technical_criteria": {"novelty": "HIGH", "infrastructure_leverage": "HIGH",
                          "complexity_interest": "HIGH", "long_term_strategic_value": "HIGH"},
    "required_capabilities": ["orchestrator", "local_llm", "voice", "messaging", "coding",
                             "crm", "payments", "customer_support"],
    "next_cheapest_validation_step": {
        "description": "NON procedere - questa e' l'opportunity piu' lontana nel tempo e "
                      "piu' bloccata da capacita' mancanti del framework. Il passo reale e' "
                      "continuare a costruire le capacita' core (voice/crm/payments/"
                      "customer_support) per altre opportunity piu' vicine, non pianificare "
                      "questa direttamente.",
        "estimated_cost": "NONE", "reversibility": "FULLY_REVERSIBLE", "speed": "MONTHS",
        "informational_value": "LOW"}},
]
