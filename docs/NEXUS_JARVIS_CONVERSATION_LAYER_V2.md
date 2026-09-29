# NEXUS Jarvis Conversation Layer V2

## Scope

Conversation Layer V2 makes Telegram/Web requests readable and durable without
changing Router, Queue, Dispatcher, Approval Gate or provider selection.
Conversation context is an index only; TaskQueue and EventLedger remain the
canonical sources for task state.

## TASK_7035F5E80552 diagnosis

The production Queue/Ledger record was not available to this checkout and the
protected production endpoint could not be queried without an authenticated
session. Render stdout has no event for this task because Queue/Ledger events
are persisted to JSON files, not emitted as application logs. Therefore this
report does not invent which of the two fail-closed BLOCKED paths occurred.

The identical `fd7997ff` code path was reproduced locally. A generic Jarvis
`business_analysis` task:

1. is created as `action=jarvis_task`, `task_type=RESEARCH`;
2. is claimed and moved to `RUNNING` by the dispatcher;
3. is routed directly to `MANUAL_REVIEW` because all local agents reject the
   `RESEARCH` task type;
4. becomes `ESCALATION_REQUIRED` with classification
   `ROUTER_DIRECT_ESCALATION`.

It never reaches `_run_local`, so a missing `LocalTaskHandler` is **not** the
cause of this generic path. On this baseline a task can become `BLOCKED` after
`RUNNING` only when the dispatcher catches an execution exception
(`DISPATCH_EXECUTION_AMBIGUOUS`) or when startup recovers an orphaned RUNNING
task (`ORPHANED_RUNNING_AFTER_RESTART`). The exact distinction for
`TASK_7035F5E80552` is stored in `dispatch_last_error`, `recovery` and its
ledger lifecycle. V2 exposes those fields through authenticated diagnostics
and natural-language task details so the next inspection is exact.

No capability or scientific gate was weakened to make the task appear to run.

## Durable conversation context

`ConversationStore` atomically persists this non-canonical context:

- `conversation_id -> last_task_id`
- pending destructive confirmation
- last update timestamp

Production uses `${JARVIS_STATE_DIR}/conversation_context_v2.json`, which is
under `/data` with the current Render configuration. After a restart Jarvis
first reads this index. If it is absent or damaged, it searches the canonical
Queue for the newest task created by the same Jarvis user/conversation.

## Supported conversation operations

- create task;
- status and continuation of the latest task;
- human and optional technical task details;
- two-step cancellation for non-running tasks;
- approve/reject through the existing approval path;
- `/start`, `/help`, `/status`, `/tasks`, `/approvals`, `/agents`;
- useful conversational fallback for unknown requests.

Technical states are retained verbatim and accompanied by a human explanation.
Technical details include action, dispatcher attempts/error, recovery
classification, escalation, result decision and ordered ledger events.

## Cancellation boundary

Cancellation is a new terminal `CANCELLED` Queue state. It requires explicit
confirmation and is allowed only from states where no worker is actively
executing. A `RUNNING` task is never marked cancelled because V2 has no safe
worker-interrupt/checkpoint protocol. `TASK_CANCEL_REQUESTED` and
`TASK_CANCELLED` are append-only Ledger events.

## Known limitations

- The historical production record must be read after this version is deployed
  (or via an authenticated current-production request) to name its precise
  BLOCKED subtype.
- Generic research/business tasks correctly escalate because no local agent is
  authorized for `RESEARCH`; provider connectors remain out of scope.
- Conversation persistence is single-instance JSON storage. It is safe for the
  current single Render instance, not for horizontal multi-process operation.
- `RUNNING` cancellation requires a future cooperative worker cancellation
  protocol.

Decision: `JARVIS_CONVERSATION_LAYER_V2_READY_WITH_LIMITATIONS`.
