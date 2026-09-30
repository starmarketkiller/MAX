# NEXUS Provider Policy Registry V1

## Decision

`PROVIDER_POLICY_REGISTRY_V1_READY_WITH_LIMITATIONS`

The registry is an artifact-backed policy catalogue and route-preview layer. It does not
activate providers, perform network calls, consume quota, or replace the Router and Premium
Budget Policy.

## Canonical registry

`server/orchestrator_v1/provider_policy_registry_v1.json` separates providers from models and is
validated against `contracts/provider-policy-registry.schema.json` at load time.
Every model records identity/family, state, configuration and production-verification flags,
cost/quota metadata, capability fields, privacy, allowed/forbidden task types, roles, fallback
priority, health/benchmark provenance and notes. Unknown facts are `null`, never guessed.

Initial production truth:

- Ollama / `ministral-3:3b` is the only verified local entry.
- Claude and Codex/OpenAI are premium policy candidates but remain offline/unconfigured.
- Gemini, Groq, OpenRouter and Hugging Face are evaluation-only free-tier candidates. Their
  model identifiers and unverified capabilities remain explicitly unspecified.

## Policy

Routing order is `DETERMINISTIC -> LOCAL -> FREE_ONLINE -> PREMIUM`. This is an ordering rule,
not a cheapest-model shortcut. Task-type allowlists, risk/review policy, production verification,
provider health and manifest premium consent remain gates. A provider is executable only when it
is configured, production-verified and `AVAILABLE`/`LOW_QUOTA`.

Premium eligibility delegates to the existing Review Matrix and Premium Budget Policy. The
preview never satisfies a required approval and never performs the provider call.

## API

- `GET /api/jarvis/providers`: public, secret-free registry plus known connector runtime state.
- `GET /api/jarvis/providers/policy`: routing order and policy provenance.
- `POST /api/jarvis/providers/route-preview`: authenticated/CSRF-protected dry run. Accepts a
  task manifest directly or as `{ "manifest": {...} }`.

The preview returns primary, executable fallbacks, evaluation candidates, premium fallbacks,
excluded candidates with reasons, provenance, `dry_run=true`, `executed=false`,
`provider_calls=0`, and `estimated_premium_calls=0`.

## Limitations

- No online provider has been connected or benchmarked in this phase.
- Free-tier availability is a declared evaluation category, not a runtime quota guarantee.
- Context windows, quota remaining and unverified feature flags remain `null`.
- A subsequent benchmark/health layer must promote entries to production-verified before use.
