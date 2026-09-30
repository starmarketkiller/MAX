# NEXUS Groq Live Evaluation Adapter V1

## Decision

`GROQ_LIVE_EVALUATION_ADAPTER_V1_READY_WITH_LIMITATIONS`

Groq is connected only to the benchmark engine. It is not registered in the normal Provider
Connector and cannot receive production tasks.

## Runtime gates

Every network call requires all of:

- benchmark mode `LIVE_EVALUATION`;
- request field `live_evaluation_confirmed=true`;
- `NEXUS_GROQ_LIVE_EVALUATION_ENABLED=true`;
- `GROQ_API_KEY` present;
- one to three model IDs in `NEXUS_GROQ_EVALUATION_MODELS`;
- positive `max_quota_units`.

The configured model list is never treated as availability truth. `GET /models` discovery can
intersect the configured list with active models before a real campaign. Missing configuration is
fail-closed and causes zero network calls.

## Transport and quota

The adapter uses Groq's OpenAI-compatible `/models` and `/chat/completions` endpoints. Rate-limit
metadata is read from the documented request/token limit, remaining and reset headers. HTTP 429
stops the benchmark immediately. Timeout permits exactly one retry with the same idempotency key.
Provider response bodies and secrets are never included in errors or treasury records.

The treasury lives in the configured Jarvis state directory and exposes only:

```json
{
  "provider_id": "GROQ",
  "requests_used": 3,
  "requests_remaining": 997,
  "tokens_used": 100,
  "tokens_remaining": 7900,
  "reset_time": "1h",
  "last_updated": "2026-09-30T00:00:00+00:00",
  "source": "GROQ_RESPONSE_HEADERS",
  "observed_requests": 1
}
```

These are illustrative test headers, not actual account quota.

## API

- `GET /api/jarvis/providers/groq/status`
- `GET /api/jarvis/providers/groq/quota`
- `POST /api/jarvis/providers/benchmarks/execute`

The execution endpoint accepts only `LIVE_EVALUATION`, is authenticated and uses the mutation/CSRF
boundary. It cannot activate production routing. Maximum automatic outcome remains `CANDIDATE` with
`production_candidate=false` and `human_approval_required=true`.

## Sample scorecard

The test transport produced a ten-case LIVE_EVALUATION result with complete schema compliance. It
is adapter test evidence only; it is not a result for any real Groq model and is not stored as
canonical benchmark history.

## Limitations

- No Groq credential was configured and no real Groq request was made.
- No model is selected in source code; the first campaign must configure and discover at most three.
- Category verification in V1 is deterministic schema/output verification, not a human quality jury.
- Promotion to production requires a later explicit human approval and policy update.
