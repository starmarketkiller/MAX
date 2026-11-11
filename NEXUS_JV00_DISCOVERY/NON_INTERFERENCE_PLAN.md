# NON_INTERFERENCE_PLAN — NEXUS JV-00

**Owners:** Trading → Claude · Control Center → Codex · Jarvis personal assistant → JV agent  
**Rule:** Jarvis may *observe and propose*; it must not *own or silently mutate* sibling domains.

---

## 1. Hard no-write zones

| Zone | Owner | Jarvis rule |
|---|---|---|
| `MQL5/` (Experts, Include/NEXUS_v1, Indicators, Scripts, Presets) | Claude / Trading | **Never modify**. Never compile/deploy from Jarvis without explicit human + Trading agent. |
| `server/research_scripts/phase7/**` | Trading research | **Never modify** frozen science packs. |
| Trading decision / live / prop execution | Trading | **Hard refuse** in classifier + runtime. |
| Control Center mutation APIs that change EA runtime, certificates ingest, host maintenance beyond status | Codex / CC | Jarvis may read status; enqueue only via approved Orchestrator tasks assigned to Codex. |
| `LocalBridge/nexus_local_worker.py` MT5 semantics | CC | Do not redefine; separate from Jarvis inference gateway. |
| Secrets, `.env`, bot tokens, gateway tokens | Human | Read never; print never. |
| Existing `contracts/jarvis-*.schema.json` breaking changes | Shared | Additive only; prefer new `jv-*` schemas. |

Verifier precedent: Orchestrator tasks already use `files_forbidden` including `MQL5/` and (historically) `Product-Platform/`.

---

## 2. Shared surfaces (safe contracts)

| Surface | Shared how | Interference risk | Mitigation |
|---|---|---|---|
| TaskQueue / EventLedger | Jarvis creates/queries; Orchestrator transitions | Duplicate task systems | **Single queue** — Jarvis drafts → approval → one enqueue |
| `/api/jarvis/*` | Jarvis HTTP | Route sprawl | New JV endpoints under `/api/jarvis/jv/*` or local-only CLI first |
| `/api/local_bridge/*` | CC ↔ EA | Accidental use from Jarvis chat | Never call from JV mission executor |
| `/api/jarvis/local-bridge/*` | Coding agent bridge | Confused with MT5 bridge | Keep naming; docs must stress dual meaning |
| Executive state | Read projection of trading/revenue/system | Stale / wrong advice | Label as **projection**, not authority |
| Telegram bot token | Jarvis webhook + notify | Cross-talk | Separate chat policies; no trading buttons that place orders |
| SkillRegistry `mql5-engineering` | Capability metadata | Jarvis “has skill” ≠ may edit EA | Skill = documentation for **Trading agent**, not local write grant |
| Command Floor UI | Operator console | UI regressions | Additive panels; no rewrite of Research Control Center pages |

---

## 3. Dual LocalBridge clarification (critical)

On the same PC two workers may run:

1. **Inference / coding:** `nexus_local_inference_gateway.py`, `nexus_agent_bridge.py`  
2. **MT5 Control Center:** `nexus_local_worker.py`  

Jarvis JV must only drive (1) for AI. Status of (2) is **read-only telemetry** for briefings.

---

## 4. Delegation protocol (no silent cross-agent edits)

```
User → Jarvis draft → Human approval → Orchestrator task
  ├─ preferred_executor = TIER_LOCAL | CLAUDE_TRADING | CODEX_CC | REVIEW
  ├─ files_allowed / files_forbidden explicit
  └─ financial_risk = NONE | READ_ONLY | FORBIDDEN
```

- Jarvis **does not** open a Cursor agent session that writes into Trading trees without the Trading owner’s task format.  
- Jarvis **does not** merge PRs for CC or Trading.  
- Independent review = `review_pipeline_v1` or a second agent — never the same executor marking its own work APPROVE without ledger.

---

## 5. Communication etiquette between owners

| Event | Who notifies whom |
|---|---|
| Jarvis needs Trading science | Mission draft → human → Claude Trading agent with frozen scope |
| Jarvis needs CC change | Mission draft → human → Codex |
| Trading wants user notify | Existing Telegram notify (not Jarvis mission invent) |
| Conflict on shared schema | Dual review; additive version bump |

---

## 6. Runtime isolation checklist (before any JV implementation PR)

- [ ] Diff contains **zero** paths under `MQL5/`  
- [ ] Diff contains **zero** phase7 research result rewrites  
- [ ] No changes to `nexus_local_worker.py` MT5 protocol  
- [ ] No weakening of `task_authorization` / approval requirements  
- [ ] No new auto-dispatch to premium APIs  
- [ ] Classifier unit tests for REFUSE on “buy/sell/close position/prop challenge”  
- [ ] Document dual LocalBridge in operator runbook  

---

## 7. What JV may create without interfering

- `NEXUS_JV*/` documentation and later `server/jarvis_jv/` (or equivalent)  
- New **additive** contracts `contracts/jv-*.schema.json`  
- Local CLI / scripts under `scripts/jv_*` that call existing APIs  
- Benchmark harnesses that only hit Ollama/gateway  

This JV-00 folder itself is the template for non-interference: **docs-only recon**.
