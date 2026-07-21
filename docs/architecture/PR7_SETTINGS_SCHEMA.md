# PR7 — Settings schema and profiles

## Canonical sources

- `contracts/settings.schema.json` defines types, ranges, defaults and safety
  metadata for every runtime-hot-reload setting.
- `contracts/default-settings.json` is the only backend default source and is
  aligned with `NXS_Inputs.mqh`.
- `frontend/src/contracts/settingsContract.js` is the frontend adapter used by
  the Settings form.

The previous backend defaults `MaxTradesPerDay=30`, `MaxConcurrent=3` and
`MinEntryScore=70` diverged from the EA values 12, 4 and 50. The backend now
loads the latter from the versioned contract.

## Validation

Backend mutations reject unknown keys, non-finite values, numeric strings,
fractional integers and out-of-range values with HTTP 422 and structured field
errors. Existing stored blobs are read through a compatibility filter so legacy
unknown fields do not leak back into the active runtime contract.

The frontend form uses numeric metadata for input `min`, `max` and `step`, keeps
an empty input as empty instead of producing `NaN`, and blocks save until local
validation succeeds.

## Locked profiles

Every profile written by the dashboard, library lock or results importer now
contains:

- stable `profile_id`;
- monotonically increasing `version`;
- settings `schema_version`;
- creation timestamp and actor;
- `ACTIVE` status;
- deterministic SHA-256 checksum over canonicalized profile parameters.

Ordinary runtime settings and locked profiles remain separate stores, so a
settings patch cannot partially overwrite an active locked profile.
