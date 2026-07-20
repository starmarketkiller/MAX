# 6. Settings Schema

## Current state

Settings are defined or defaulted in multiple locations:

- `NXS_Inputs.mqh`
- `NXS_RuntimeSettings.mqh`
- backend defaults in `server/app.py`
- frontend fallback values and forms
- locked profiles and preset seed files.

**Confirmed risk:** values, names and defaults can diverge. Backend accepts broad settings blobs without complete type/range validation. Frontend numeric fields can produce invalid values such as `NaN`.

## Canonical setting metadata

Each setting should define:

```json
{
  "key": "MaxConcurrent",
  "type": "integer",
  "default": 3,
  "minimum": 0,
  "maximum": 20,
  "scope": "INSTANCE",
  "hot_reload": true,
  "requires_restart": false,
  "safety_class": "RISK",
  "description": "Maximum simultaneous Nexus positions"
}
```

## Scopes

- `GLOBAL`
- `ACCOUNT`
- `INSTANCE`
- `SYMBOL`
- `STRATEGY`
- `PROFILE`

## Validation requirements

1. Reject unknown keys unless explicitly allowed for forward compatibility.
2. Reject `NaN`, infinity and non-numeric strings.
3. Enforce integer vs decimal semantics.
4. Enforce ranges and cross-field invariants.
5. Return structured validation errors.
6. Store the applied schema version.
7. Never silently convert manual multiplier `0` into `1` in another layer.

## Cross-field examples

- `StartHour < EndHour`, unless overnight sessions are explicitly supported.
- daily drawdown limits must be non-negative and bounded.
- grid/pyramid add-on limits require exposure caps.
- virtual stop requires persistence and close workflow enabled.
- a locked profile cannot be partially overwritten by ordinary settings.

## Versioned profiles

A locked profile should contain:

```json
{
  "profile_id": "uuid",
  "version": 4,
  "schema_version": 2,
  "created_at": "...",
  "created_by": "operator",
  "settings": {},
  "checksum": "...",
  "status": "ACTIVE"
}
```

## Proposed source

```text
contracts/settings.schema.json
contracts/default-settings.json
```

The frontend form should be generated or validated from the same metadata used by FastAPI.
