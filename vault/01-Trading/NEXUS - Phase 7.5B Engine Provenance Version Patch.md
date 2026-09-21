# NEXUS - Phase 7.5B Engine Provenance Version Patch

**Baseline:** `85cc47a` (Cluster Geometry Consistency Patch - verdetto corretto e coerente). Patch di **sola provenance/versioning** - nessun cambio di logica, detector, spec o verdetto.

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.**

---

## Problema

`sequence_structural_feasibility_gate.py` era stato modificato nella Cluster Geometry Consistency Patch (semantica di `compute_cluster_geometry` cambiata, nuovo invariant fail-closed introdotto) ma continuava a dichiarare `ENGINE_VERSION = "...@v4"` - la stessa versione sia prima sia dopo un cambio di comportamento reale, rendendo `engine_version` inaffidabile come prova di provenance.

## Fix

| | Prima | Dopo |
|---|---|---|
| `ENGINE_VERSION` | `sequence_structural_feasibility_gate.py@v4` | `sequence_structural_feasibility_gate.py@v5` |
| `ENGINE_SOURCE_SHA256` | assente | `111ab15bf2587af5a63638fd44a64c4cba7188edcd8feacfa6f7d04706691ae5` |

`ENGINE_SOURCE_SHA256` e' calcolato **a runtime** (`file_sha256(__file__)` all'import) e incluso in **ogni** provenance emessa dal gate, inclusi i rami di ritorno anticipato (`NEEDS_DETECTOR_FORMALIZATION`) - mai un campo opzionale omesso.

## Regressione anti-ricorrenza

Nuovo test `test_engine_version_matches_recorded_source_hash`: fissa la coppia `(ENGINE_VERSION, hash del sorgente)` come costanti attese nel test stesso. Se il file del gate viene modificato senza incrementare `ENGINE_VERSION`, l'hash calcolato a runtime non coincide piu' con quello registrato nel test → **fallisce esplicitamente**. Se `ENGINE_VERSION` viene incrementata senza aggiornare la costante nel test, fallisce ugualmente - impossibile l'uno senza l'altro. **135/135 PASS** (era 132).

## SEQ-0009 - artifact rigenerato, nessun cambio scientifico

```
engine_version:       sequence_structural_feasibility_gate.py@v5   (era @v4)
engine_source_sha256: 111ab15bf2587af5a63638fd44a64c4cba7188edcd8feacfa6f7d04706691ae5   (nuovo campo)

EVENT_VIEW=246, EPISODE_VIEW=169, INDEPENDENT_VIEW=10        (invariati)
raw_event_embargo_geometry.n_clusters=8                       (invariato)
inferential_independent_geometry.n_independent_clusters=10    (invariato)
FINAL VERDICT: NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY        (invariato)
```

`seq0009_frozen_structural_spec_v1.json`: **nessun diff** (verificato con `git diff --stat`), 26/26 check di coerenza interna ancora PASS - detector, `episode_gap_rule=2`, `proposed_natural_horizon=40`, `embargo=39`, `matching_spec` tutti confermati invariati.

## Regressione completa

135/135 PASS su `test_phase7_5_structural_feasibility_gate.py`, 26/26 su `test_seq0009_frozen_spec.py`, **0 FAIL** sulle altre 9 suite Phase 7 (11 suite totali).

## Conferme

- **NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.**
- Nessuna logica del gate modificata, nessun detector/spec/verdict toccato.
- SEQ-0015 resta chiusa, non riesaminata.

---

**SEQ-0009 e' ora archiviata definitivamente:** `NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY` su `development_discovery`, con geometria internamente coerente (Cluster Geometry Consistency Patch) e provenance tracciabile senza ambiguita' (questa patch). In questa fase il nuovo processo ha gia' prodotto valore concreto due volte: ha fermato sia SEQ-0015 sia SEQ-0009 prima di costruire inferenza statistica su un campione indipendente insufficiente a sostenerla - esattamente il problema che il preflight era stato progettato per prevenire. Nessuna nuova family avviata, come da istruzione.
