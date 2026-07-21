# PR3 Protection Pipeline Verification

## Scope

- Runtime settings, ruin state and account protections refresh before any add-on exposure.
- Primary, Grid and Pyramid entries share RiskShield, directional exposure and broker preflight gates.
- Every shared gate emits a machine-readable `[NEXUS GATE]` JSON record.
- Grid and Pyramid use the retry-aware SafeOrder route after successful preflight.

## Static acceptance scenarios

1. A blocked RiskShield result returns before an order request.
2. Directional exposure at or above the cap blocks primary, Grid and Pyramid routes.
3. A broker preflight failure blocks all three routes and records its reason.
4. Passing gates preserve broker-adjusted stops and allow the existing order workflow.
5. Web telemetry availability is not required because gate records are written locally.

## Verification commands

```text
python -m pytest server/tests
git diff --check
```

MT5 runtime tests are intentionally excluded at the user's request.
