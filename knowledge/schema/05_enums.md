# 05 — Enum centralizzati (Canonical Schema v1)

| Enum | Valori | Usato in |
|---|---|---|
| `run_confidence` | `high` · `medium` · `low` | Run (qualità dell'IMPORT — non è l'Evidence Score) |
| `artifact_status` | `discovered` · `imported` · `parsed` · `validated` | Artifact (solo in avanti) |
| `issue_severity` | `low` · `medium` · `high` | DataQualityIssue |
| `issue_status` | `open` · `resolved` | DataQualityIssue |
| `issue_type` | `missing_artifact` · `incomplete_run` · `identity_mismatch` | DataQualityIssue |
| `artifact_type` | `manifest` · `strategy_stats_csv` · `trades_csv_snapshot` · `html_report` | Artifact |
| `event_type` | `implementation` · `redesign` · `bug_discovered` · `bug_fixed` · `logic_modification` · `parameter_change` · `renamed_strategy` · `backtest_executed` · `sweep_executed` · `baseline_reached` · `issue_detected` · `documentation_update` | TimelineEvent |
| `event_confidence` | `high` (cronologia documentata) · `medium` (data approssimata) | TimelineEvent |
| `round_id` | `sweep37-prefix-r1` · `sweep37-prefix-r2` · `sweep37-gate1pos-r3` · `sweep37-postfix12h-killed` · `sweep37-baseline-e6ce816` | Run (round futuri: aggiunta esplicita alla tabella) |
| `identity_ok` | `true` · `false` · `null` (check non applicabile) | Run |
| `import_esito` | `importato` | Import |

**Non normalizzato in v1** (documentato, non corretto — vedi proposta P1): `Bug.stato` è testo libero (`risolto`, `risolto (rename)`, `APERTO`, `APERTO (deliberato)`, …). Idem `Strategy.stato` e `Backtest.affidabilita`.
