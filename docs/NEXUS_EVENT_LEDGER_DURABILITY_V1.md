# NEXUS Event Ledger durability V1

`EventLedger` remains the single append-only Activity Ledger. Each JSONL append
is flushed and `fsync`ed before success is returned. On restart, readers may
ignore only a malformed final record that has no line terminator, which is the
bounded signature of a write interrupted by a process or host crash. The next
append removes that incomplete fragment first. Malformed intermediate records,
blank complete records, and malformed final records with a terminator are
reported as corruption and are never skipped.

## Atomicity boundary

This change provides durability for each individual ledger append. It does not
make a Task Queue state replacement and its corresponding ledger append one
atomic transaction. A crash between those two operations can therefore leave a
durable queue transition without its event, or an event before the related
queue transition. Existing recovery/reconciliation code must continue to treat
the queue as current state and the ledger as append-only history, detect that
gap, and fail closed. F-03 does not add a second registry or a distributed
transaction mechanism.
