# JV-01 — Local Chat Spine · Preparation Plan

**Gate:** JV-01 PREPARATION (no implementation in this document)  
**Date:** 2026-11-11 (Europe/Rome)  
**Parent:** JV-00 READY_TO_PLAN (92%) · PR [#80](https://github.com/starmarketkiller/MAX/pull/80)  
**Directive:** `AGENT_OPERATING_DIRECTIVE_V1.md`

---

## 1. PR #80 verification (no merge)

| Check | Result |
|---|---|
| State | OPEN, `MERGEABLE` |
| Base / head | `main` ← `cursor/jv00-jarvis-discovery-5198` |
| Files | **Only** `NEXUS_JV00_DISCOVERY/*` (7 docs) — zero Trading/CC/server code |
| Commits | `1675290` inventory/plan · `14af07b` directive |
| Reviews / issue comments / review comments | **None** |
| CI (`gh pr checks` / statusCheckRollup) | **No checks reported** on branch |
| Merge / deploy | **Not performed** (forbidden) |

Human edits to PR description (if any in UI) do not change file scope: still docs-only recon.

---

## 2. Reuse confirmation (esistente)

| Component | Reusable for JV-01? | Evidence |
|---|---|---|
| `server/jarvis_v1/` | **Yes** — chat/command paths, response shaping | `service.py` `/mistral`, gateway clients |
| `ministral_chat.py` | **Yes** for Render→tunnel path | Fail-closed errors + `gateway_status()` diagnostics |
| `LocalBridge/nexus_local_inference_gateway.py` | **Yes** — canonical local HTTP boundary | `GET /v1/jarvis/health`, `POST /v1/jarvis/chat` |
| `orchestrator_v1/core/ollama_worker.py` | **Yes** — localhost Ollama only | `DEFAULT_MODEL=ministral-3:3b`, no cloud fallback |
| Telegram adapter | **Reuse later (JV-04)** — **out of JV-01 scope** | Exists; not required for local spine |
| Task queue / approvals / ledger | **Do not duplicate** — **not used by JV-01** | Delegation/missions = post JV-01 |
| Orchestrator dispatcher | **Do not create a second one** | JV-01 is chat I/O only |

**JV-01 principle:** thin local entrypoint that calls **existing** gateway or `call_local_model`, with diagnostic logging. No new brain, no new queue.

---

## 3. Confini con Codex CC-01

| Concern | Jarvis (JV-01) | Control Center (Codex) |
|---|---|---|
| Conversation text in/out | **Owns** | Does **not** implement chat |
| Ledger / mission manager / approvals | **Does not create** | May **display** existing queue/approvals (already RI/CC patterns) |
| Local chat health | Emits **read-only status** (latency, last_error codes, model name) | May **project** that status in UI later |
| MT5 / `nexus_local_worker.py` | **No access** | CC owns |
| Research Control Center | Untouched | Remains read-only research projection (`docs/RESEARCH_CONTROL_CENTER_V1.md`) |

**Non-duplication rule:** JV-01 must not invent `mission_manager`, parallel ledger, or a second approval store. Those stay Orchestrator/`jarvis_v1` approvals for later JV-02+.

---

## 4. Model availability

### Live check this session
- Self-hosted worker: **offline** (0 connected)  
- Cloud VM: no `ollama` binary  
→ **Live `ollama list` not executed here.** Documented PC state from bake-off + `LOCAL_INFERENCE_CONNECTIVITY_V1` still points to **`ministral-3:3b`**.

### Preflight obbligatorio (umano/PC) prima del codice
```powershell
ollama list
curl http://127.0.0.1:11434/api/version
# if gateway used:
curl http://127.0.0.1:8765/v1/jarvis/health
```
Pass: `ministral-3:3b` present + Ollama reachable.

### Alternatives (evidence-only — do **not** swap by default)

| Model | Evidence | JV-01 stance |
|---|---|---|
| **ministral-3:3b** | NEXUS bake-off winner 0.9764; DEFAULT_MODEL; pilot 4/4 | **Required default** |
| qwen2.5:3b-instruct | Bake-off #2 (0.911); keep as offline fallback **only if** ministral missing | Optional fallback, same prompt path |
| qwen3:4b | Bake-off disqualified (timeouts) | **Forbidden** for spine |
| External paid APIs | — | **Forbidden** |

External 2026 tool-calling blogs (cited in JV-00 research) do **not** override the PC bake-off without a new local rematch.

---

## 5. Piano minimo JV-01 (testo → Ollama → risposta)

### Goal
Operator types text on PC → local Ministral replies → structured diagnostic log on success/failure. No Telegram, no Render, no delegation, no MT5.

### Preferred call path
1. **Primary:** `POST http://127.0.0.1:8765/v1/jarvis/chat` (existing gateway; auth token from LocalBridge `.env`, never logged)  
2. **Fallback (dev only):** `ollama_worker.call_local_model` if gateway down but Ollama up — still localhost-only  

### Error handling (reuse codes where possible)
Map/emit stable codes, never secrets:
- `OLLAMA_UNREACHABLE` / `GATEWAY_CONNECT_ERROR` / `GATEWAY_TIMEOUT` / `GATEWAY_NOT_CONFIGURED`
- `MODEL_CALL_FAILED` / `EMPTY_MODEL_RESPONSE`
- `UNAUTHORIZED` / `RATE_LIMITED` (gateway)
- Timeout budget: **60s** client (aligned with connectivity fix for cold ~49s)

### Diagnostic logging
JSONL line per turn (local file under gitignored path or `$JARVIS_STATE_DIR`):
`ts, latency_ms, model, path(gateway|direct), ok, error_code, prompt_chars, reply_chars`  
No raw secrets, no full prompt dump by default (optional `--verbose` flag).

### Acceptance (PASS only with evidence)
| ID | Proof |
|---|---|
| A1 | Script exit 0 + non-empty reply from ministral |
| A2 | Stop Ollama → exit ≠0 + `OLLAMA_UNREACHABLE` or gateway connect error in log |
| A3 | Unit tests with mocked HTTP (no live model required in CI) ≥ existing style |
| A4 | `git diff` contains **zero** `MQL5/`, `frontend/` CC pages, `nexus_local_worker.py`, phase7 research |

### Out of scope (explicit)
Mission draft, approvals, agent routing, Telegram, voice, auto-delegation, second Orchestrator, paid APIs, MT5, merge, deploy.

---

## 6. File previsti in implementazione (dopo approvazione piano)

| Path | Action |
|---|---|
| `scripts/jv01_local_chat.py` (or `server/jarvis_jv/local_chat_cli.py`) | **NEW** — CLI stdin/arg → gateway/ollama → stdout + JSONL diag |
| `server/tests/test_jv01_local_chat_spine.py` | **NEW** — mocked gateway/ollama cases |
| `NEXUS_JV00_DISCOVERY/JV01_*.md` or `NEXUS_JV01_*/RESULT.md` | **NEW** — run evidence after live PC test |
| `LocalBridge/nexus_local_inference_gateway.py` | **Touch only if** bugfix needed for spine (prefer zero edits) |
| `server/orchestrator_v1/core/ollama_worker.py` | **Prefer import-only** — no behavior change |
| `server/jarvis_v1/**` | **Prefer zero edits** in JV-01 (reuse via HTTP/import) |
| `MQL5/**`, CC frontend, `nexus_local_worker.py`, phase7 | **Forbidden** |

Branch when authorized: `cursor/jv01-local-chat-spine-5198` off `main` (docs-only #80 stays separate unless Direction merges it first).

---

## 7. Contratti di integrazione che richiedono coordinamento con Codex

| Contract | Need | Coordination |
|---|---|---|
| **None blocking for JV-01 code** | Spine runs headless CLI | Codex not required to ship A1–A4 |
| `JV_LOCAL_CHAT_STATUS_V1` (optional, additive) | `{ok, model, last_latency_ms, last_error, ollama_reachable, gateway_reachable}` | **If** CC-01 wants a dashboard chip: agree schema + **read-only** GET; Codex implements UI, Jarvis emits status. No shared writes. |
| Existing `/api/jarvis/executive-state` | Unchanged | CC may already show executive projections — **do not** overload with chat turns |
| Approvals / ledger schemas | Unchanged in JV-01 | Codex must not expect JV-01 to feed missions |

**Coordination message for Codex (one paragraph):**  
*JV-01 is an offline CLI chat spine to local Ollama/gateway only. It will not create missions, ledger events, or approval records. If CC-01 needs visibility, consume an optional read-only `JV_LOCAL_CHAT_STATUS_V1` later; until then, ignore JV-01.*

---

## 8. Directive-style summary

| Campo | Contenuto |
|---|---|
| Stato esistente | Stack chat locale già presente (gateway + ollama_worker + ministral default); PR #80 docs-only |
| Opportunità | CLI spine unifica path di diagnosi senza Telegram/Render |
| Soluzione consigliata | New thin CLI + mocks; reuse gateway; keep ministral-3:3b |
| Motivazione | Free/local-first; bake-off evidence; zero Orchestrator fork |
| Rischi | PC worker offline → live model unconfirmed; cold-start latency; accidental scope creep into JV-02 |
| Evidenze | PR #80 file list; `ollama_worker.DEFAULT_MODEL`; gateway routes; bake-off vault |
| Prossima azione | Human approves this plan + PC preflight `ollama list` → then authorize implementation |

**Missione preparazione JV-01:** **100%** (piano consegnato)  
**Implementazione JV-01:** **0%** (non autorizzata)

### Prossimi 3 passi (dopo approvazione)
1. PC preflight: Ollama + `ministral-3:3b` (+ gateway opzionale)  
2. Branch `cursor/jv01-local-chat-spine-5198` + CLI + mock tests  
3. Live evidence run on PC; optional status contract note to Codex  

---

## 9. Verdetto

# READY_FOR_ISOLATED_IMPLEMENTATION

Piano circoscritto, riuso confermato, nessun blocco di design su Codex.  
**Preflight PC** (modello presente) è condizione di *start coding*, non di validità del piano.  
Nessuna implementazione fino ad approvazione esplicita di questo documento.
