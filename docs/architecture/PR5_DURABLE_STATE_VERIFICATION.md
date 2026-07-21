# PR5 Durable Operational State Verification

## Scope

- Schema 2 snapshots are written to a temporary file, reopened and validated before replacement.
- The previous known-good snapshot is retained and used as restore fallback.
- Shutdown forces a final snapshot regardless of the periodic throttle.
- Restore reconciles snapshot records against broker-owned Nexus positions.
- Each position retains logical ID, group, strategy, entry ATR, profile version, phase, last event, residual volume and split markers.
- Corrupt primary and fallback snapshots block new exposure while existing-position management remains active.
- Split targets use the restored entry ATR and cannot repeat after restart.

## Static acceptance scenarios

1. Invalid schema, record count or trailer rejects the snapshot.
2. A valid temporary snapshot replaces the primary only after verification.
3. A damaged primary restores from the previous snapshot.
4. Closed broker positions are removed during reconciliation.
5. Broker positions missing from the snapshot are reconstructed deterministically.
6. A failed restore blocks entry gates but does not disable management or emergency exits.
7. `OnDeinit` invokes the forced-save path.

MT5 runtime/Strategy Tester tests are intentionally excluded at the user's request.
