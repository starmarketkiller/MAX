# 01 — Entità (Canonical Schema v1)

Fonte formale: [schema_v1.json](schema_v1.json). Qui: scopo, esempio e note per ognuna. **13 entità**: 9 attive, 1 embedded, 1 implicita, 2 riservate.

| Entità | File | Stato |
|---|---|---|
| Strategy | strategy_database.json | attiva |
| Run | runs_database.json | attiva |
| SignalMetrics | embedded in Run.metrics | attiva (embedded) |
| EquityMetrics | — | **riservata** (future-ready, separata da SignalMetrics per non mischiare dati di segnale e di equity) |
| Artifact | artifacts_database.json | attiva |
| Import | imports_ledger.json | attiva |
| TimelineEvent | strategy_timelines.json | attiva |
| Bug | bug_database.json | attiva |
| Decision | decision_database.json | attiva |
| DataQualityIssue | data_quality_issues.json | attiva |
| Backtest | backtest_database.json | attiva |
| Document | path repo-relativi | **implicita** (nessun DB proprio; il contenuto è versionato in git) |
| EvidenceLink | — | **riservata** (M4; distinta da Run.confidence: quella è qualità dell'import, questa sarà forza dell'evidenza) |

Per ogni entità, `schema_v1.json` specifica: purpose, required/optional, immutable/mutable, relazioni, ownership dei campi.

## Esempi reali (estratti dai DB correnti)

**Run** (baseline valida): `run_id: sweep37-baseline-e6ce816__S03__MACD__20260718_205653`, `completed: true`, `identity_ok: true`, `confidence: high`, `metrics: {trade_eseguiti: 1244, profit_factor: 0.79, ...}`

**DataQualityIssue**: `id: dqi-missing-S04-sweep37-baseline-e6ce816`, `type: missing_artifact`, `strategy: SAR`, `severity: medium`, `status: open`

**TimelineEvent**: `event_id: evt-…`, `strategy_id: THREE_BAR_DELIVERY_BREAK`, `event_type: renamed_strategy`, `related_commit: 1bb167a`, `confidence: high`

## Regola d'oro dell'ownership
I campi **run-derived** di Strategy (ultimo_sweep, PF, WR…) li scrive SOLO l'import engine. I campi **curati** (decisione_corrente, bug_storici…) SOLO revisione umana/approvata. Nessun modulo scrive nei campi dell'altro (V11).
