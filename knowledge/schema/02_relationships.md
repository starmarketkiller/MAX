# 02 — Relazioni (Canonical Schema v1)

```
Strategy 1 ──── N Run                (Run.strategy → Strategy.nome, alias-aware)
Strategy 1 ──── N TimelineEvent      (event.strategy_id)
Strategy N ──── M Bug                (Bug.strategie_coinvolte - testo libero in v1, vedi P2)
Strategy 0..1 ─ N DataQualityIssue   (issue.strategy)
Run      1 ──── 1 Artifact           (Run.artifact_checksum → Artifact.checksum)
Run      1 ──── 0..1 SignalMetrics   (embedded)
Run      1 ──── 0..1 EquityMetrics   (riservata)
Run      0..1 ─ N TimelineEvent      (event.related_run_id)
Artifact 1 ──── N Import             (stesso checksum: primo import + skip successivi)
Bug      0..1 ─ 1 commit git         (Bug.commit_fix)
Bug      1 ──── N TimelineEvent      (bug_discovered / bug_fixed)
Decision N ──── M Document           (documenti_sorgente - testo libero in v1)
Backtest 1 ──── N Run                (implicito via round_id in v1, vedi P3)
TimelineEvent 0..1 ─ 1 commit git    (related_commit)
```

Regole: nessuna relazione circolare; le FK verso Run/Bug sono validate dal timeline engine (V08); la relazione Backtest→Run è implicita in v1 (il `round` della Run identifica la campagna) — formalizzarla è la proposta P3.
