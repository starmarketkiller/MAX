# NEXUS Linux CI Portability Fix

## Root causes

Eight failures shared one portability defect: read-model provenance helpers used
`Path.relative_to(repo_root)` unconditionally. Fault-isolation tests replace canonical sources with
temporary files. Windows verification had placed `--basetemp` inside the checkout, while GitHub Linux
uses `/tmp`, where `relative_to` correctly raises `ValueError`.

`server/path_provenance.py` now centralizes the policy:

- repository sources remain repo-relative POSIX paths;
- external fixtures become `external://<filename>`;
- absolute host paths are never exposed;
- equal external filenames produce deterministic provenance across machines.

Two Orchestrator failures came from the producer emitting
`TIER0_DETERMINISTIC_REMEDIATION`, which was never part of `RESULT_PACKET_V1`. Remediation is an action
performed by the existing `TIER0_DETERMINISTIC` executor, not a distinct tier. The producer now emits
the existing canonical enum; the schema remains unchanged.

## Verification

- External-temp regression set: 51 passed.
- Full Windows backend with temp outside the repository: 486 passed, 1 skipped.
- Safe Deploy, security and production requirement tests: 13 passed.
- Production imports and active-example-secret preflight: passed.
- Frontend production build: passed.

Docker is unavailable on the local Windows host. The previous Canary 001 commit proved the Docker CI
job green, but GitHub Linux and Docker validation for this new commit remain required before Canary
002. No deploy was triggered and the Canary 001 marker was not changed.
