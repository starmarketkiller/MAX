# ARCHITECTURE_AND_INTEGRATIONS — NEXUS JV-00

**Mission:** JV-00 discovery  
**Rule:** design by composition over existing Jarvis/Orchestrator; no Trading or Control Center file ownership.

---

## 1. Target product (future)

Local-first personal assistant that:

1. Talks (text now; voice later)  
2. Understands requests / projects  
3. Uses free local models  
4. Proposes delegation to the right agent  
5. Tracks progress, gathers results, requests independent review  
6. Uses skills / tools / sub-agents  
7. Handles reminders / notifications  
8. **Interfaces with NEXUS without autonomous financial execution**

---

## 2. Recommended system shape (reuse-first)

```
                    ┌─────────────────────────────┐
  User text/voice → │  JV Conversation Facade     │  (new thin layer)
                    │  - session UX               │
                    │  - mission draft cards      │
                    │  - approval gate            │
                    └──────────────┬──────────────┘
                                   │ JARVIS_MESSAGE_V1
                    ┌──────────────▼──────────────┐
                    │  Existing JarvisGateway     │
                    │  + JarvisService            │
                    └──────────────┬──────────────┘
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
   Local Ollama path        TaskQueue/Ledger         Read-only NEXUS
   (gateway /ministral)     + Approvals              Executive State
           │                       │
           ▼                       ▼
   Deterministic tools      Proposed executors
   (vault search,           (Claude Trading /
    classifiers)             Codex CC / LocalBridge /
                             Review pipeline)
```

**Key idea:** JV owns *conversation + mission drafting + approval UX*. Orchestrator owns *task lifecycle*. Domain agents own *execution* inside their trees.

---

## 3. MVP loop (authorized design only — not implemented in JV-00)

| Step | Behavior | Existing building block |
|---|---|---|
| 1 | Receive text | `POST /api/jarvis/message` or Telegram adapter |
| 2 | Reply via local model | `/mistral` path → gateway → `ministral-3:3b` |
| 3 | Detect possible mission | Deterministic classifier **or** schema-constrained Ministral JSON |
| 4 | Propose agent | Capability registry + hard rules (Trading→Claude, CC→Codex, local coding→bridge) |
| 5 | Structured task | Reuse `task-manifest` / programming plan schemas; new `JV_MISSION_DRAFT_V1` optional |
| 6 | Wait authorization | Existing `/api/jarvis/approvals` + Telegram confirm buttons |
| 7 | Record progress/outcomes | Event ledger + task_handoff artifacts |

**Explicit MVP non-goals:** auto-dispatch to external paid agents; voice; mutating MQL5; Control Center writes; live trading actions.

---

## 4. Integration contracts (proposed — additive)

These are **contracts**, not file edits to Claude/Codex trees.

### 4.1 Inbound (already exist — reuse)
- `JARVIS_MESSAGE_V1` / `JARVIS_RESPONSE_V1`  
- Telegram card schema  

### 4.2 Mission draft (new, JV-owned schema file when authorized)
Suggested fields:

```json
{
  "type": "JV_MISSION_DRAFT_V1",
  "user_intent": "...",
  "mission_class": "CHAT|LOCAL_TASK|DELEGATE_TRADING|DELEGATE_CONTROL_CENTER|DELEGATE_REVIEW|REFUSE",
  "proposed_agent": "local_ministral|local_bridge|claude_trading|codex_control_center|review_pipeline|none",
  "task_manifest_stub": {},
  "risk": {"financial":"NONE|READ_ONLY|FORBIDDEN", "code":"LOW|MED|HIGH"},
  "requires_human_approval": true,
  "rationale": "..."
}
```

### 4.3 Read-only NEXUS surfaces for Jarvis
| Surface | Use |
|---|---|
| `GET /api/jarvis/executive-state` | Brief user on system status |
| Task queue status APIs | Progress narration |
| Research Control Center read models | Status only; no mutation |
| EA / LocalBridge MT5 status | Health narrative only |

### 4.4 Write / execute surfaces (gated)
| Action | Gate |
|---|---|
| Enqueue Orchestrator task | Human approval |
| LocalBridge coding claim | Approval + `files_forbidden` includes `MQL5/`, research freeze paths |
| Notify Telegram | Policy levels already in `notifications.py` |
| Trading order / prop / live | **Hard refuse** forever in Jarvis path |

---

## 5. Agent routing policy (draft)

| Intent class | Proposed agent | Auto-run? |
|---|---|---|
| Small talk / explain | Local Ministral | Yes (chat) |
| Local bounded coding in allowlist | Local Agent Bridge | Approval |
| Trading research / EA science | Claude (Trading owner) | Approval; Jarvis never edits `MQL5/` |
| Control Center / dashboard ops | Codex | Approval |
| Independent review of a result | Review pipeline | Approval |
| Financial execution | — | **REFUSE** |

---

## 6. Local-first topology

```
PC (always):
  Ollama (ministral-3:3b)
  Local Inference Gateway :8765
  Optional: Agent Bridge, MT5 LocalBridge worker (separate process)
  Optional later: STT/TTS

Cloud (optional):
  Render Jarvis webhook / queue (if Telegram phone path desired)
  Must not be the only brain — offline text loop via localhost should work
```

Offline MVP path: `curl localhost gateway/chat` + local CLI or Command Floor pointing at local service. Phone Telegram can remain optional.

---

## 7. Memory architecture

| Layer | Store | Owner |
|---|---|---|
| Turn context | `conversation_store` | Jarvis |
| Canonical tasks | `task_queue_v1.json` | Orchestrator |
| Audit | `event_ledger_v1.jsonl` | Orchestrator |
| Knowledge | Vault (read) + future local embeddings | Shared read |
| Secrets | Env / LocalBridge `.env` (gitignored) | Human |

---

## 8. Interference-aware package layout (when implementation authorized)

Preferred:

```
server/jarvis_jv/          # or NEXUS_JV*/packages — NEW
  mission_draft.py
  local_chat_loop.py
  approval_card.py
NEXUS_JV00_DISCOVERY/      # this recon (docs only)
```

Forbidden to own:

- `MQL5/**`  
- `server/research_scripts/phase7/**` (Trading research)  
- Control Center mutation pages / LocalBridge MT5 worker semantics  
- `contracts/` changes without explicit dual-owner review (prefer new `contracts/jv-*.schema.json`)

---

## 9. Success metrics for architecture (not JV-00 completion)

- Chat roundtrip local without Render  
- Mission draft JSON always validated  
- Zero unsolicited executor launches  
- Zero writes under `MQL5/` from Jarvis paths  
- Clear user-visible approval step before any delegation
