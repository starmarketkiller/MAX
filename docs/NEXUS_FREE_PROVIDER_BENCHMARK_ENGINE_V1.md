# NEXUS Free Provider Benchmark Engine V1

## Decision

`FREE_PROVIDER_BENCHMARK_ENGINE_V1_READY_WITH_LIMITATIONS`

The engine turns a registry entry into repeatable evaluation evidence. It never edits the
production policy and never promotes a model automatically.

## Modes and safety gates

- `MOCK`: deterministic adapter only; no network. Evidence level is `MOCK_ONLY`.
- `DRY_RUN`: returns the ten-test plan; no adapter invocation and `network_calls=0`.
- `LIVE_EVALUATION`: requires `live_evaluation_confirmed=true`, a configured provider in an
  executable health state, and an explicitly injected adapter. Missing any gate blocks execution.

The engine uses a stable idempotency key per benchmark/test, one retry at most, bounded timeout,
quota-unit budget and immediate stop on rate limiting. Reports contain no credentials. History is
append-only by benchmark ID and stored under the configured Jarvis state directory.

## Standard suite

Structured output, reasoning, coding, debugging, synthesis, classification, long context,
tool use, instruction following and ambiguous-input robustness. Each result retains pass/fail,
schema compliance, verifier score, latency/timeout/retry, token/quota/cost fields when supplied,
determinism, error/hallucination flags, tool-call correctness and output length.

## Scorecard and roles

The scorecard keeps `QUALITY`, `RELIABILITY`, `SPEED`, `STRUCTURED_OUTPUT`, `CODING`, `REASONING`,
`LONG_CONTEXT`, `TOOL_USE`, `DETERMINISM` and `FREE_QUOTA_EFFICIENCY` separate. Roles are recommended
or forbidden from their relevant dimension; the overall average never decides routing alone.

Example MOCK scorecard for `GROQ / QWEN_UNSPECIFIED` with the perfect deterministic test adapter:

```json
{
  "evidence_level": "MOCK_ONLY",
  "scorecard": {
    "QUALITY": 100.0, "RELIABILITY": 100.0, "SPEED": 98.0,
    "STRUCTURED_OUTPUT": 100.0, "CODING": 100.0, "REASONING": 100.0,
    "LONG_CONTEXT": 100.0, "TOOL_USE": 100.0, "DETERMINISM": 100.0,
    "FREE_QUOTA_EFFICIENCY": 100.0
  },
  "production_candidate": false,
  "promotion_recommendation": "EVALUATION_ONLY",
  "human_approval_required": true
}
```

This is test evidence, not a claim about Groq or Qwen quality.

## API

- `GET /api/jarvis/providers/benchmarks`
- `GET /api/jarvis/providers/benchmarks/{provider_id}/{model_id}`
- `POST /api/jarvis/providers/benchmarks/preview`

All are authenticated; preview also uses the mutation/CSRF boundary. V1 intentionally exposes no
HTTP execution endpoint. A future controlled evaluation runner can inject a real adapter after
secrets and quota limits are configured outside the repository.

## Promotion states

The engine may recommend `EVALUATION_ONLY` or `CANDIDATE`. Even a complete live result always has
`production_candidate=false` and `human_approval_required=true`. `production-approved` remains a
separate human governance action outside this engine.

## Limitations

- No real provider adapter, credential or network call is included.
- Token usage and provider cost remain null unless an adapter reports them.
- One live run can only reach `LIVE_SINGLE_RUN`; repeated-run confidence is reserved for a future
  benchmark campaign controller.
