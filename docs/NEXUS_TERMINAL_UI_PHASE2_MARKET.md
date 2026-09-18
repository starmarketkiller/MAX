# NEXUS Terminal — UI Phase 2 Market

## Scope

Phase UI-2 introduces a read-only canonical Market State boundary and replaces the `/market` landing page with an analytical workspace. It does not change detectors, trading logic, research calculations, execution, authentication, or MQL5.

## Source-of-truth rules

- **Research Market State** is read only from structured Phase 5/6 CSV artifacts. Markdown is never parsed into canonical state.
- **Operational Market Telemetry** is adapted from the latest `/api/ea/status` record and stays a separate object.
- The two domains are not merged. `source_domain` is `RESEARCH` or `OPERATIONAL` and `semantic_parity` is explicit.
- Missing columns remain `null`; missing artifact files produce an empty result plus `MISSING_ARTIFACT` warnings.
- Categorical Research fields are deterministic read-model interpretations of versioned numeric features and carry `DERIVED` provenance and limitations.

The repository currently versions detector/build scripts and Phase 6 declarations, but not the generated row-level files under `phase5/data` and `phase6/data`. Therefore a production image built from this baseline may truthfully expose no Research snapshots/events until those structured artifacts are supplied. It does not fabricate replacements.

## MarketStateSnapshot v1

Required envelope fields are `id`, `timestamp`, `symbol`, `timeframe`, `source`, `source_mode`, `source_domain`, `semantic_parity`, `schema_version`, `data_quality`, `limitations`, and `provenance`.

State fields are `regime`, `volatility_state`, `trend_state`, `directional_efficiency`, `momentum_state`, `structure_state`, `range_position`, `compression_state`, and `location_state`. Any unavailable field is `null`.

Research IDs are deterministic hashes of repo-safe source plus timestamp. Operational IDs are deterministic for the EA/account/symbol/timestamp tuple.

## MarketEvent v1

Events expose `event_id`, `family`, `timestamp`, `symbol`, `timeframe`, `direction`, `magnitude`, `observation_point`, `detector_version`, `source_dataset`, `state_snapshot_id`, `linked_research_entity_id`, `limitations`, `source_domain`, `semantic_parity`, and `provenance`.

`linked_research_entity_id` remains `null` unless a structured artifact supplies an unambiguous relation. No relationship is inferred from names.

## API

All routes are authenticated and read-only:

- `GET /api/market/state/latest?symbol=&timeframe=` returns separate `research` and `operational` snapshots plus parity.
- `GET /api/market/state?symbol=&timeframe=&from=&to=&limit=` returns Research history.
- `GET /api/market/events?symbol=&timeframe=&from=&to=&event_family=&direction=&limit=` returns Research events.
- `GET /api/market/events/{event_id}` returns one event or 404.

Limits are clamped (`5000` state rows, `1000` response events). CSV reads use a bounded deque and an in-process cache keyed by path, modification time, size, and window. Static history is fetched once by the workspace and only refetched when filters change; there is no historical polling.

## Research/live semantic gaps

The Research schema contains numeric H4 features such as directional efficiency, ATR percentile, range position, compression percentile, and ROC. EA telemetry may expose regime, volatility regime, HTF bias, velocity, and structure, but it does not implement the same definitions or schema version. Accordingly:

- parity is `PARTIAL` only when both snapshots exist;
- parity is `NONE` when either side is absent;
- parity is never `FULL` in v1;
- runtime values are never backfilled into Research fields.

## UI structure

Desktop uses a two-column Chart/Market State region and a full-width Event Timeline. The existing lightweight-charts implementation is embedded rather than duplicated. It supports dark/light theme and preserves trade/visual markers. The current OHLC endpoint is synthetic and remains visibly marked `DEMO`; canonical event overlays are intentionally omitted because the versioned event rows are absent and timestamps alone are insufficient for faithful price placement.

Mobile uses `Chart`, `State`, and `Events` tabs. The event inspector is a bottom sheet on mobile and a side sheet on desktop. Filters cover family, direction, and time range.

## Known limitations

- Generated Market State/Event CSVs are absent from the tracked baseline, so Research history can be empty in production.
- The chart OHLC feed is synthetic/demo; it is not evidence for canonical Market State.
- Operational EA fields lack canonical detector versions and full feature semantics.
- No live Market Event stream exists. History is snapshot-based; no SSE, WebSocket, animation, or simulated activity is present.
- Canonical chart overlays require real indexed events plus a compatible real OHLC series and are deferred.
