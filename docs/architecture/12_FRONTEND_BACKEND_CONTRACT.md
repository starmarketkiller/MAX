# 12. Frontend/Backend Contract

## Current frontend architecture

- React Router and AuthProvider;
- Axios client with credentials;
- large polling-oriented Dashboard;
- numerous operational and analytics pages;
- legacy static dashboard also served by backend.

## Confirmed contract risks

### Polling aggregation

Dashboard issues many requests through a single `Promise.all`. One failure can block the entire refresh.

### Endpoint mismatch

Frontend calls `/api/backtest/library_preset`; no corresponding FastAPI endpoint was identified in the audit.

### Command ambiguity

Frontend uses `/api/command` in several workflows while backend command routes are split among dashboard/EA/bridge concepts. This must be contract-tested rather than inferred.

### Settings response shape

Frontend code paths may expect the settings object directly while backend can return an envelope such as `{ok, settings}`.

### LocalBridge mismatch

IDs, status enums, timestamp units and response fields differ between React expectations and backend implementation.

### Analytics provenance

Lifecycle and strategy pages combine multiple datasets and can present reconstructed or inferred events as directly observed facts.

### Legacy dashboard

`server/static` and React use different authentication/storage approaches, including legacy token use in browser storage.

## Required API contract discipline

Use versioned schemas for every public response:

```json
{
  "schema_version": 1,
  "data": {},
  "meta": {
    "generated_at": "...",
    "provenance": "OBSERVED_LIVE"
  }
}
```

## Frontend query classes

Separate refresh policies:

- live status: short interval or push;
- command status: poll while active;
- settings: on navigation/change;
- historical analytics: longer interval/manual;
- static registries: cache by version.

Suspend live polling when the page is hidden.

## Error behavior

- independent queries should fail independently;
- errors must be visible, not only logged to console;
- PDF/download responses must validate HTTP status;
- invalid forms must never send `NaN` or out-of-range values;
- mutations require optimistic state only when rollback is defined.

## Contract-test requirement

Generate or maintain fixtures covering every endpoint used by React. CI should fail when:

- an endpoint is absent;
- field names change;
- enum values diverge;
- timestamps change units;
- required provenance is missing.
