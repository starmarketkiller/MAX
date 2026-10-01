# Safe Deploy LOW_RISK Canary

This file is the prepared non-runtime canary target for NEXUS Safe Auto Deploy V1.

- `canary_run: CANARY_002`
- expected classification: `LOW_RISK`
- expected reason: `NON_RUNTIME_CHANGE`
- production behavior change: none

For the first approved canary, create a dedicated commit changing only `canary_run`. Run the normal CI
and inspect the risk artifact before allowing the deployment environment to use configured secrets.
Do not combine that commit with runtime, workflow, research, security, auth, trading or configuration
changes.
