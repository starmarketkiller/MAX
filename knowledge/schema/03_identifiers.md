# 03 — Identificatori (Canonical Schema v1)

| ID | Regola di generazione | Unicità | Immutabilità |
|---|---|---|---|
| `strategy_id` | nome canonico = `stratName` MQL5 (es. `MACD`) | globale | immutabile; rename SOLO con Decision + alias registrato (caso `CISD`→`THREE_BAR_DELIVERY_BREAK`) |
| `run_id` | `{round}__S{NN}__{STRATEGY}__{YYYYMMDD}_{HHMMSS}` — interamente derivato dal file sorgente | globale | immutabile |
| `artifact_id` | `art-` + sha256(file)[:16] — derivato dal contenuto | globale | immutabile |
| `event_id` | `evt-` + sha1(strategy\|type\|date\|title)[:12] — stabile tra rigenerazioni | globale | immutabile |
| `bug_id` | `BUG-NNN` progressivo | globale | immutabile |
| `decision_id` | `DEC-NNN` progressivo | globale | immutabile |
| `quality_issue_id` | `dqi-{tipo}-{contesto}` (deterministico dal contesto) | globale | immutabile |
| `document_id` | path repo-relativo (chiave naturale) | repo | file spostato = documento nuovo (limite noto v1) |

Principio comune: **ogni id è o derivato dal contenuto o progressivo registrato — mai casuale**, così le rigenerazioni deterministiche producono gli stessi id.
