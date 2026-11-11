# EXISTING_JARVIS_INVENTORY — NEXUS JV-00

**Mission:** JV-00 discovery only  
**Generated:** 2026-11-11 (UTC)  
**Scope:** read-only recon of repo + documented PC state  
**Not in scope:** installs, deploys, Trading/Control Center edits, Adapter (declined)

---

## 1. Verdict on “what is real”

JARVIS is **not greenfield**. A substantial Access Layer already exists under `server/jarvis_v1/`, wired into `server/app.py`, with Orchestrator queue/ledger, Telegram webhook, LocalBridge inference gateway, and hundreds of unit tests / result packets claiming READY / OPERATIONAL_WITH_LIMITATIONS.

What is **missing for the future “personal local-first assistant”** is mostly: voice, a dedicated local conversational UX loop that does not depend on Render secrets, automatic multi-agent delegation with human approval UX as first-class, and a clean JV* ownership boundary so Trading (Claude) and Control Center (Codex) stay untouched.

---

## 2. Runnable code (implemented)

### Core
| Path | Role |
|---|---|
| `server/jarvis_v1/` | Access Layer: message handle, Telegram, Ministral clients, programming planner, approvals, task views |
| `server/executive_v1/` | Executive state + Italian conversation intents |
| `server/orchestrator_v1/core/` | Task queue, event ledger, dispatcher, Ollama worker, local agent bridge (server) |
| `server/review_pipeline_v1/jarvis_delivery.py` | User-facing finalization summaries |
| `LocalBridge/nexus_local_inference_gateway.py` | Auth’d localhost gateway → Ollama (`/v1/jarvis/interpret`, `/v1/jarvis/chat`) |
| `LocalBridge/nexus_agent_bridge.py` | Workstation coding job poller |
| `LocalBridge/nexus_local_worker.py` | **MT5 / Control Center worker** (shared PC, not Jarvis chat) |
| `frontend/src/pages/CommandFloorPage.jsx` + `frontend/src/command/*` | Command Floor / Jarvis stations UI |
| `contracts/jarvis-*.schema.json` | Message, response, card, Ministral router output, programming plan |

### HTTP surfaces (Jarvis)
Evidence from `server/app.py` wiring (inventory pass):

- `POST /api/jarvis/message`
- `GET /api/jarvis/tasks/{task_id}` (+ diagnostics, resume-orphaned)
- `GET|POST /api/jarvis/floor-workflow`
- `GET /api/jarvis/activity|context|agents|providers…`
- `GET /api/jarvis/telegram/status` · `POST /api/jarvis/telegram/webhook`
- `GET /api/jarvis/executive-state`
- `GET /api/jarvis/dispatcher/status`
- `GET|POST /api/jarvis/local-bridge/{status,heartbeat,claim,renew,result,failure}`
- `GET|POST /api/jarvis/approvals[/{task_id}]`

Distinct Control Center channel: `/api/local_bridge/*` (EA/desktop MT5).

### Contracts
- `contracts/jarvis-message.schema.json`
- `contracts/jarvis-response.schema.json`
- `contracts/jarvis-card.schema.json`
- `contracts/jarvis-ministral-router-output.schema.json`
- `contracts/jarvis-programming-plan.schema.json`

Related shared (not Jarvis-owned): `nexus-executive-state-v1`, `nexus-event`, `agent-capability-registry`, `task-manifest`, `result-packet`, `final-result-packet`.

---

## 3. Local AI / Ollama (documented PC vs this cloud VM)

### This cloud agent VM
- `ollama` binary: **not present**
- No live model list from this environment

### Research PC (from repo artifacts — treat as last measured state)
| Source | Finding |
|---|---|
| `docs/LOCAL_INFERENCE_CONNECTIVITY_V1.md` | Ollama on `127.0.0.1:11434` verified; gateway `:8765`; Cloudflare tunnel path built; cold Ministral ~49s, warm ~6s |
| `vault/01-Trading/NEXUS - Local Model Bake-Off V1.md` | Winner **`ministral-3:3b`** (score 0.9764); keep `qwen2.5:3b-instruct`; `qwen3:4b` disqualified (timeouts / thinking); hardware: i5-7200U, ~20GB RAM, **CPU-only** |
| `server/orchestrator_v1/core/ollama_worker.py` | `DEFAULT_MODEL = "ministral-3:3b"`; known list includes qwen2.5 3b/7b, qwen3:4b, gemma3:4b |
| `server/orchestrator_v1/environment_inventory_v1.json` | Older snapshot (`2026-09-28`) reported Ollama not yet installed — **superseded** by bake-off + connectivity docs |

Env vars (Render ↔ PC): `JARVIS_MINISTRAL_GATEWAY_URL`, `JARVIS_MINISTRAL_GATEWAY_TOKEN`, router flags (`JARVIS_MINISTRAL_ROUTER_ENABLED` default **false**).

**Do not duplicate** a second gateway. Reuse `LocalBridge/nexus_local_inference_gateway.py` + `start_local_inference.ps1`.

---

## 4. Telegram

| Piece | Status |
|---|---|
| `server/jarvis_v1/telegram_adapter.py` | Implemented (allowlist, webhook secret, rich UX) |
| `configure_telegram_webhook.py` | CLI exists |
| Commands | `/start /help /status /tasks /approvals /agents /task /mistral /mistral_status /new /jarvis /reset` (+ business/revenue cmds) |
| Outbound notify | Separate `_send_telegram` / `TELEGRAM_CHAT_ID` path (EA alerts) sharing `TELEGRAM_BOT_TOKEN` |
| Production E2E | **PARTIAL**: code ready; Render secrets / webhook / deploy approval still gate phone path (`docs/JARVIS_TELEGRAM_PRODUCTION_ACTIVATION.md`, CURRENT_STATE notes) |

---

## 5. Memory, skills, automations

| System | Real? | Notes |
|---|---|---|
| `conversation_store.py` | Yes | Bounded context file under `$JARVIS_STATE_DIR` |
| Task queue + event ledger | Yes | Canonical truth for tasks |
| `shared_cognitive_state.py` | Yes | `GET /api/jarvis/context` |
| `vault_context.py` | Yes | Keyword vault snippets for `/mistral` — **not** a vector RAG |
| `SkillRegistry` in `local_operations.py` | Yes | Allowlists `.claude/skills/mql5-engineering`, `ui-ux-pro-max` + capability registry |
| DurableQueueDispatcher | Yes | In-process when enabled |
| n8n / Midjourney “3 arms” | **DOC-ONLY / historical** | MOC marks superseded |
| Voice STT/TTS | **Absent** in code |

---

## 6. Docs vs code scorecard

### Claimed working (result packets + tests)
- Jarvis Access Layer V1 — OPERATIONAL_WITH_LIMITATIONS  
- Conversation Layer V2 — READY_WITH_LIMITATIONS  
- Conversational Programming V1 Core — READY_WITH_LIMITATIONS (planner; **no** autonomous shell/Git writer)  
- Telegram rich response / interactive UX — READY_WITH_LIMITATIONS  
- Local Agent Bridge V1 — READY_WITH_LIMITATIONS  
- Local model bake-off — LOCAL_MODEL_SELECTION_VALIDATED  

### Partial / gated
- Telegram production phone E2E  
- Ministral router ACTIVE (OFF; latency ~45s historically)  
- Render → gateway env residual  
- Executive conversation Mistral real-path caveats (`…_PARTIAL`)

### Doc-only / historical
- Vault n8n automation ideas  
- Pre-Orchestrator “Claude vertical prompts as JARVIS hub” design  
- Product-Platform tree referenced as forbidden but **absent** in this checkout  

---

## 7. `server/jarvis_v1` module map (1 line)

| File | Purpose |
|---|---|
| `gateway.py` | Schema boundary message→response |
| `service.py` | Channel-agnostic core classifier / commands / tasks |
| `telegram_adapter.py` | Telegram updates + send |
| `ministral_chat.py` / `ministral_router.py` | Gateway clients |
| `ministral_task_compiler.py` / `local_bounded_task_handler.py` | Bounded local task templates |
| `programming.py` | Deterministic programming plan |
| `free_coding_worker.py` | Bounded local coding handler |
| `multi_stage_executor.py` | Sequential child tasks |
| `task_authorization.py` / `task_handoff.py` / `task_result_view.py` | Approvals + artifacts |
| `floor_workflow.py` | Agency floor handoff |
| `local_operations.py` | Skills / capabilities projection (no exec authority) |
| `conversation_store.py` / `vault_context.py` | Context helpers |
| `notifications.py` / `delegation_report.py` / `authenticated_scope.py` | Policy / reporting / scope |

---

## 8. Non-duplication rule for JV*

Reuse before inventing:

1. `JarvisGateway` + `JARVIS_MESSAGE_V1` / `JARVIS_RESPONSE_V1`  
2. Existing approvals + task queue (do not invent a parallel mission store)  
3. Local inference gateway (do not expose Ollama publicly)  
4. Command Floor for operator UI; Telegram for mobile  
5. SkillRegistry / capability registry instead of a new skill DB  

New JV* work should live in a **dedicated package/folder** (proposed later in roadmap) that **calls** these contracts, not forks them inside MQL5 or Control Center trees.

---

## 9. Limits of this inventory

- Adapter MCP declined → no cross-session Adapter memory.  
- Cloud VM cannot verify live Ollama/`pc-mt5` worker state in this pass.  
- No production Render secret inspection (forbidden / unavailable).  
- “Works” claims are from repo tests + packets, not a live Telegram send from this agent.
