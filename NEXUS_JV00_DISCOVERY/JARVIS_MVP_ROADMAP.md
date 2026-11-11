# JARVIS_MVP_ROADMAP — NEXUS JV-00

**Mission completion status below.**  
**Implementation:** blocked until explicit human authorization after this report.

---

## 1. MVP definition (minimum that still feels like Jarvis)

A local-first loop that can:

1. Accept a text message  
2. Answer with **local** Ministral via existing gateway/Ollama  
3. Detect when the message is a **mission** (not only chat)  
4. Propose **which agent** should handle it  
5. Emit a **structured task draft**  
6. **Wait for human authorization** before any enqueue/execute  
7. Record progress and outcomes on the existing ledger/queue views  

No automatic external delegation. No voice. No trading execution. No CC/Trading file ownership.

---

## 2. Build sequence (when authorized)

### JV-01 — Local chat spine (thin facade)
- Local CLI or small script: stdin → gateway `/v1/jarvis/chat` → stdout  
- Optional: wrap as `POST` to existing gateway without Render  
- Reuse timeouts/warmup already in LocalBridge  
- Tests: offline mock Ollama OR skip-if-no-ollama markers  

**Exit:** user can chat with Ministral on PC without Telegram/Render.

### JV-02 — Mission draft + approval gate
- Schema `JV_MISSION_DRAFT_V1` (new file under `contracts/` only if approved)  
- Deterministic rules + optional Ministral JSON (schema-validated)  
- Map to proposed agent per NON_INTERFERENCE_PLAN  
- Emit draft card; **stop** until approval recorded  
- Wire approval to existing `/api/jarvis/approvals` **or** local approval file if offline-only mode  

**Exit:** “scrivi un task per Codex” produces draft, not execution.

### JV-03 — Progress narration (read-only)
- Poll task status / ledger projection  
- Summarize with local model (no authority)  
- Refuse to invent success  

**Exit:** user asks “a che punto siamo?” and gets ledger-backed answer.

### JV-04 — Optional Telegram parity
- Only after local spine works  
- Same draft/approval semantics on existing webhook  
- No new bot required  

### JV-05 — Voice spike (optional later)
- Vosk or whisper.cpp tiny → text → same MVP path → Piper  
- Benchmark B5 from research doc first  

### Explicit backlog (not MVP)
- Auto-spawn Cursor cloud agents  
- n8n resurrect  
- Vector vault RAG  
- Multi-model router ACTIVE on phone latency budget  
- Computer-use desktop control  

---

## 3. Effort shape (technical, not calendar)

| Workstream | Invasiveness | Dependencies |
|---|---|---|
| JV-01 local chat | Low — new scripts/package only | Ollama + gateway running on PC |
| JV-02 mission draft | Medium — schema + classifier + tests | JV-01; careful not to fork queue |
| JV-03 narration | Low–medium | Queue/ledger access |
| JV-04 Telegram | Medium | Render secrets (human) |
| Voice | Medium–high | Audio devices; CPU budget |

Risks: dual LocalBridge confusion; weakening approvals; qwen3-style latency regressions if model swapped without bake-off.

---

## 4. Acceptance tests for MVP

| ID | Test |
|---|---|
| A1 | Local chat returns non-empty Ministral reply |
| A2 | “compra 0.1 lot GOLD” → mission_class REFUSE, no task enqueue |
| A3 | “prepara task per rivedere il dashboard LocalBridge” → DELEGATE_CONTROL_CENTER draft, awaits approval |
| A4 | Approval false → zero Orchestrator side effects |
| A5 | Approval true → exactly one task with files_forbidden including `MQL5/` |
| A6 | Progress query cites task id from queue, not hallucinated |

---

## 5. What already accelerates MVP

Do **not** rebuild:

- `JarvisGateway` / `JarvisService`  
- Ministral gateway + Ollama worker  
- Approvals + task handoff  
- Capability / skill registry patterns  
- Command Floor (can host UI later)  

MVP is a **facade + mission policy**, not a second Orchestrator.

---

## 6. JV-00 mission scorecard

| Deliverable | Status |
|---|---|
| EXISTING_JARVIS_INVENTORY.md | Done |
| LOCAL_AI_AND_SKILLS_RESEARCH.md | Done (WebSearch; parallel-cli N/A) |
| ARCHITECTURE_AND_INTEGRATIONS.md | Done |
| NON_INTERFERENCE_PLAN.md | Done |
| JARVIS_MVP_ROADMAP.md | Done |
| No Trading/CC code edits | Honored |
| No installs / deploy / trading | Honored |
| Adapter memory | Skipped (declined) |
| Live PC Ollama verify this session | Not possible from cloud VM |

**JV-00 completion: 92%**

Remaining 8%: live confirmation on `pc-mt5` that Ollama+gateway still match docs; optional Adapter recall if later enabled.

---

## 7. Final verdict

# READY_TO_PLAN

Enough real code and research exists to plan JV-01/JV-02 without greenfield risk.  
**Do not implement** until you authorize the next mission (suggested: **JV-01 Local chat spine**).

Clarifications that would raise confidence but are **not blocking**:

- Confirm Ollama still lists `ministral-3:3b` on the PC today  
- Whether MVP must be offline-only or may assume Render Telegram  

Neither blocks READY_TO_PLAN.
