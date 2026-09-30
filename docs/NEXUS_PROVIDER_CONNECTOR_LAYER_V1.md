# NEXUS Provider Connector Layer V1

## Boundary

The connector is an Orchestrator execution layer, not a second router. It only
consumes tasks already classified `ESCALATION_REQUIRED`, preserves the Router's
target, applies `TASK_MANIFEST_V1.premium_allowed`, Review Matrix and Premium
Budget Policy, and sends only the existing compact `CONTEXT_PACKET_V1`.

```text
ESCALATION_REQUIRED
  -> ProviderConnectorV1
  -> ProviderAdapterV1 (Claude | Codex | future OpenAI)
  -> deterministic response verification
  -> RESULT_PACKET_V1
  -> COMPLETED
  -> Jarvis FINALIZED response
```

Production adapters are fail-closed `OFFLINE/UNKNOWN` placeholders until a
real transport is configured. V1 adds no API key reader and performs no live
provider request. Tests inject `MockProviderAdapter`; this is the only adapter
that returns successful provider output in this phase.

## Adapter contract

Every adapter implements:

- `state()` returning `AVAILABLE`, `LOW_QUOTA`, `EXHAUSTED`, `RATE_LIMITED`,
  `OFFLINE` or `UNKNOWN`;
- `invoke(context_packet, idempotency_key, timeout_seconds)`;
- a secret-free `public_status()` projection.

The result reports provider status, structured output, provider request ID,
failure class and optional retry delay. No adapter receives Queue records,
Vault content, repository content or conversation history.

## Safety and durability

- A provider is never called when the manifest or Premium Budget Policy denies
  it.
- `CRITICAL_REVIEW` requiring user approval is not called automatically.
- Requests transition to `WAITING_PROVIDER` before invocation.
- The stable idempotency key is derived from task ID, provider and canonical
  context hash.
- Transient exceptions retry at most once with the same key.
- Offline/exhausted providers leave the task in `ESCALATION_REQUIRED`.
- Rate limits and provider errors return the task to `ESCALATION_REQUIRED`.
- Invalid output fails deterministic verification and is never finalized.
- No file mutation, deploy, spend, outreach, legal action or trading action is
  executed by the connector.
- Provider errors stored in diagnostics are sanitized.

`ProviderConnectorV1` is attached to the existing single-concurrency durable
dispatcher. QUEUED local work remains first priority; provider work is checked
only when no local task is runnable.

## Verification and finalization

V1 accepts a provider output only when it is a structured object with a
non-empty summary and valid details/source references. It then creates a
schema-valid `RESULT_PACKET_V1`, records provider provenance and marks the
provider execution verified/finalized. Jarvis delivers that verified result
without invoking a second implicit provider.

## Known limitations

- Claude, Codex and OpenAI network transports are intentionally not included;
  they remain offline until separately configured and security-reviewed.
- JSON Queue/provider claims assume the current single web-process deployment.
- Provider-side cancellation and streaming are not implemented.
- A canonical Provider Policy Registry should replace the small V1
  target-to-provider mapping before adding more providers or tenants.
