# 07 — Ciclo di vita del dato (Canonical Schema v1)

```
 1. DISCOVERY      il file appare nel repo (push di un agente / sweep runner)
        ↓
 2. IMPORT         checksum SHA256, dedupe, ledger append-only, provenance
        ↓             (import_engine)
 3. PARSING        estrazione del contenuto (oggi: stats CSV; futuro: trade CSV, HTML)
        ↓
 4. VALIDATION     completezza + identity check (selector↔strategia) + regole V01-V12
        ↓             fallimento ⇒ DataQualityIssue, MAI scarto silenzioso
 5. NORMALIZATION  alias (CISD→THREE_BAR_DELIVERY_BREAK), round classification, id canonici
        ↓
 6. KNOWLEDGE      i database: runs / artifacts / issues + vetrina Strategy (campi run-derived)
        ↓
 7. TIMELINE       ricostruzione cronologica per strategia (timeline_engine)
        ↓
 8. FUTURE ANALYSIS  (M4+: Evidence Engine, Query Engine — SOLO sopra dati validati)
```

**Nessuno stadio può essere saltato** (V12). Un dato che non supera la validazione resta visibile (issue aperta) ma non entra mai nella conoscenza come fatto valido. Gli stadi 2-7 sono deterministici e ri-eseguibili: stessa entrata → stessa uscita.

Stato per artefatto lungo il ciclo: `discovered` (1) → `imported` (2, riservato) → `parsed` (3) → `validated` (4). Oggi: stats CSV = validated; manifest/trade CSV/HTML = discovered (parsing futuro).
