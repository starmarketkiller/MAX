# 5. Strategy Registry Specification

## Current state

**Observed:** strategy definitions are duplicated across:

- MQL5 strategy modules and comments;
- backend `STRAT_NAMES_36`;
- frontend strategy registry with 37 strategies;
- analytics hardcoded family counts;
- Python backtest registry;
- seed files and documentation.

**Observed:** the Python simulator contains additional `SCALP_*` strategies and proxies several live strategies to other implementations.

## Defect

No canonical registry identifies whether a strategy is:

- implemented live;
- implemented in research;
- a proxy;
- deprecated;
- eligible for automated disablement;
- compatible with a symbol/timeframe;
- part of a strategy family.

## Canonical record

```json
{
  "strategy_id": "ADX_RSI",
  "display_name": "ADX + RSI",
  "family": "MOMENTUM",
  "status": "ACTIVE",
  "live_implementation": true,
  "research_implementation": true,
  "research_parity": "APPROXIMATE",
  "proxy_for": null,
  "supported_symbols": ["*"],
  "supported_timeframes": ["M15", "M30", "H1"],
  "default_enabled": true,
  "risk_class": "STANDARD",
  "schema_version": 1
}
```

## Required statuses

- `ACTIVE`
- `EXPERIMENTAL`
- `SHADOW_ONLY`
- `RESEARCH_ONLY`
- `DEPRECATED`
- `DISABLED`

## Required parity values

- `EXACT`
- `FUNCTIONALLY_EQUIVALENT`
- `APPROXIMATE`
- `PROXY`
- `NOT_IMPLEMENTED`

## Rules

1. Unknown strategy IDs are errors, never silent fallback to another strategy.
2. Strategy count is derived from the registry, never hardcoded in UI text.
3. Family counts are derived from records.
4. Backend, frontend and backtest validate against the same registry artifact.
5. Live auto-disable operates only on strategies explicitly marked eligible.
6. Research-only strategies cannot be promoted without a live implementation reference and version.

## Proposed location

```text
contracts/strategy-registry.json
contracts/strategy-registry.schema.json
```

Generated adapters may be created for MQL5, Python and JavaScript, but the JSON registry is the canonical source.

## Migration check

Before changing strategy behavior, produce a reconciliation table containing every currently named strategy and its presence in:

- EA;
- frontend;
- backend;
- backtest;
- documentation;
- historical results.
