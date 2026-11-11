# LOCAL_AI_AND_SKILLS_RESEARCH — NEXUS JV-00

**Mission:** JV-00 discovery  
**Research date:** 2026-11-11  
**Constraint:** free / no paid API required  
**Note:** `parallel-cli` unavailable in this environment; research via Cursor WebSearch. Claims below cite those results. PC bake-off remains the **authoritative local measurement**.

---

## 1. Hardware reality (PC NEXUS)

From `server/orchestrator_v1/environment_inventory_v1.json` + bake-off vault:

- Windows 11, **Intel i5-7200U** (2C/4T), ~20 GB RAM, Intel HD 620  
- **CPU-only** inference is the only realistic path  
- Context-hungry agent shells (OpenCode / Hermes needing ~64K) already deferred in bake-off Extra phase  

Implication: prefer ≤4B–8B quantized models, short prompts, tool shortlists, and deterministic verifiers — not “one big local Claude”.

---

## 2. Local models (free) — external 2026 signal vs NEXUS bake-off

### Already validated on this PC
| Model | Role | Evidence |
|---|---|---|
| **ministral-3:3b** | LOCAL_FAST + LOCAL_STRONG | Bake-off winner 0.9764; tool-calling; pilot 4/4 |
| qwen2.5:3b-instruct | Cheap baseline | Keep |
| gemma3:4b | Optional | Hallucination found in bake-off; no native tools on Ollama then |
| qwen3:4b | Rejected on PC | 88% timeout / non-disableable thinking |

### External benchmarks (do **not** override PC bake-off without remeasure)
- Small models can beat much larger ones on MCP tool calling: e.g. qwen3-4b-thinking ~89%, ministral-3-3b ~85% in one 21-model MCP study ([Alyx.pink MCP benchmark](https://alyx.pink/posts/2026-02-26-local-llm-mcp-benchmark/)).  
- Another local agent bench ranks phi4-mini / qwen3 small / ministral-3:3b competitively but shows **qwen3:4b ~64s avg** ([Mike Veerman Local Agent Bench](https://mikeveerman.be/blog/github-2026-02-06-tool-calling-benchmark/)) — consistent with NEXUS timeout lesson.  
- Ollama publishes a large tool-calling model catalog including `ministral-3`, `phi4-mini`, `qwen3`, `gemma4` ([localaimaster Ollama tool-calling list](https://localaimaster.com/blog/best-ollama-models-tool-calling)).  

**JV recommendation:** keep `ministral-3:3b` as default. Optional **PC-only** bake-off delta candidates (install only after authorization): `phi4-mini:3.8b`, newer `gemma4:e2b`/`e4b` if RAM allows — never on cloud credits.

---

## 3. Runtimes compatible with free local use

| Layer | Tool | Fit for NEXUS PC |
|---|---|---|
| Packaging | **Ollama** (MIT) | **Keep** — already integrated (`ollama_worker`, gateway) ([CTAIO comparison](https://ctaio.dev/en/local-ai/ollama-vs-lm-studio/)) |
| Engine | llama.cpp | Optional escape hatch for CPU tuning; not needed for MVP |
| GUI | LM Studio | Optional human playground; app proprietary/free — do not make it a hard dependency |
| Serving | vLLM | Poor fit (GPU / Linux production) |
| UI | Open WebUI | Optional chat UI in front of Ollama; not required if Telegram + Command Floor exist |

Stack model: engine ≠ packaging ≠ UI ([Local AI Frontier layering](https://localaifrontier.com/blog/local-ai-tooling-stack-2026/)).

**Decision for JV:** stay on **Ollama + existing gateway**; no second runtime in MVP.

---

## 4. Open-source coding / agent shells

| Agent | License | Local LLM | Fit |
|---|---|---|---|
| **Aider** | Apache 2.0 | Ollama yes; warn on small `num_ctx` | Good **optional** git-native executor behind approval ([critique.sh survey](https://www.critique.sh/comparisons/best-open-source-coding-agents-2026)) |
| **Goose** | Apache 2.0 | Ollama + MCP | Strong local-first general agent; evaluate as **delegate target**, not core Jarvis rewrite |
| **OpenHands** | MIT | Local possible; wants large context / capable models | Likely **too heavy** for 3B CPU ([OpenHands local LLMs](https://docs.openhands.dev/openhands/usage/llms/local-llms)) |
| OpenCode | MIT | Local | Already **deferred** (64K context) in NEXUS bake-off |
| Cline / Continue | Apache 2.0 | Local | IDE-centric; Continue upstream read-only — low priority |
| NEXUS Local Agent Bridge | in-repo | Ollama | **Prefer** for bounded coding before adopting external agents |

MVP: Jarvis proposes → human approves → existing queue / local bridge. External agents only as later optional executors.

---

## 5. Offline voice

| Piece | Candidate | Notes |
|---|---|---|
| STT light | **Vosk** | Fast on weak CPU ([Linux Bash guide](https://linuxbash.sh/post/artificial-intelligence-voice-assistants-on-linux)) |
| STT accurate | **whisper.cpp** (`tiny.en`/`base.en`) | Better quality, heavier on i5-7200U |
| TTS | **Piper** | Local neural TTS; HA/Wyoming ecosystem ([HA local assistant](https://www.home-assistant.io/voice_control/voice_remote_local_assistant/)) |
| Wake word | openWakeWord / Rhasspy legacy | Post-MVP |
| Loop pattern | mic → STT → text Jarvis → Piper | Same as whispa-style stacks ([whispa-pi](https://github.com/marcelogdomingues/whispa-pi)) |

**Voice is out of JV MVP** (text-first). When authorized: STT→existing `/api/jarvis/message`, never a parallel brain.

---

## 6. Making 3B models effective (skills, tools, memory)

Evidence that small models need **orchestration**, not just “bigger weights”:

1. **Tool retrieval / shortlists** — Llama 3.2 3B tool-name accuracy 2.5% → **84.5%** with k=10 retrieved tools ([Thinking Inside the Box](https://thinkinginsidethebox.ai/aaif/engineering/2026/09/17/tool-retrieval-for-slm-agents.html)).  
2. **Schema / guided decoding + validators** — SLM-default, LLM-fallback agent pattern ([arXiv SLM survey PDF](https://arxiv.org/pdf/2510.03847)).  
3. **Role split (Planner / Caller / Generator)** — separate planning from tool call from answer ([P-C-G paper](https://arxiv.org/pdf/2509.19369v1.pdf)).  
4. **Skills alone are weak below ~12B** for reliable skill selection ([Agent Skill Framework study](https://arxiv.org/html/2602.16653v3)) → for 3B, prefer **deterministic routers + few tools** over open skill catalogs.  
5. **Agent distillation with retrieval/code tools** helps 0.5B–3B ([NeurIPS 2025 agent distillation](https://proceedings.neurips.cc/paper_files/paper/2025/file/99263f9bf46874e2b8b7f104b5063864-Paper-Conference.pdf)).  

Maps cleanly onto NEXUS already:

- Deterministic `programming.py` / task compiler  
- Fail-closed `task_authorization`  
- Separate review / finalization pipeline  
- Capability registry with forbidden paths  

---

## 7. Concrete PC benchmarks to run (after authorization — not now)

Do **not** install during JV-00. Proposed suite on research PC:

| ID | Goal | Method | Pass bar |
|---|---|---|---|
| B1 | Chat latency warm/cold | 20× `/v1/jarvis/chat` ministral-3:3b | p50 warm &lt; 10s; document cold |
| B2 | JSON schema compliance | 30× forced JSON mission card | ≥95% valid against new JV schema |
| B3 | Mission classify | 40 Italian intents (chat vs mission vs refuse trading) | ≥90% correct class |
| B4 | Tool shortlist | Same prompts with 3 vs 30 tools | Measure parse + correct tool rate |
| B5 | Voice (later) | Vosk small-it / whisper tiny on 20 Italian clips | WER + wall time |
| B6 | Optional model delta | phi4-mini vs ministral on B2–B4 | Only keep if beats ministral on reliability |

Hardware protocol: unload other models (`keep_alive:0`) before each run — lesson from bake-off OOM.

---

## 8. Local automations / memory

| Need | Free approach | Avoid |
|---|---|---|
| Task memory | Existing queue + ledger | Second SQLite “missions” without sync |
| Conversational memory | Bounded `conversation_store` + optional vault RAG upgrade | Cloud vector SaaS |
| Reminders | Local scheduler / Telegram delayed messages (later) | Paid push SaaS |
| Desktop automation | Optional later (AutoHotkey / computer-use) | Giving 3B shell root |

Vault RAG today is keyword (`vault_context.py`). Upgrade path: local embeddings via Ollama embed model + sqlite-vss / chroma **local only**, post-MVP.

---

## 9. Research conclusion for Jarvis

1. **Do not replace Ollama or ministral-3:3b** without a new PC bake-off.  
2. **Architecture beats parameters** on this hardware: short tools, schemas, verifiers, human approval.  
3. External coding agents are **delegates**, not the product.  
4. Voice stack exists as free building blocks; wire after text MVP.  
5. Never assume 3B can safely do unconstrained coding or trading judgment.

---

## Sources

- [I benchmarked 21 local LLMs on real MCP tool calling](https://alyx.pink/posts/2026-02-26-local-llm-mcp-benchmark/)  
- [Local Agent Bench (Mike Veerman)](https://mikeveerman.be/blog/github-2026-02-06-tool-calling-benchmark/)  
- [Ollama Tool-Calling Models list](https://localaimaster.com/blog/best-ollama-models-tool-calling)  
- [Best Small Language Models 2026](https://vdf.ai/blog/best-small-language-models/)  
- [Ollama vs LM Studio vs llama.cpp vs vLLM (CTAIO)](https://ctaio.dev/en/local-ai/ollama-vs-lm-studio/)  
- [Local AI tooling stack 2026](https://localaifrontier.com/blog/local-ai-tooling-stack-2026/)  
- [Best Open Source Coding Agents 2026](https://www.critique.sh/comparisons/best-open-source-coding-agents-2026)  
- [OpenHands local LLMs](https://docs.openhands.dev/openhands/usage/llms/local-llms)  
- [Open-source coding agents (OpenHands blog)](https://www.openhands.dev/blog/open-source-ai-coding-agents)  
- [HA fully local voice assistant](https://www.home-assistant.io/voice_control/voice_remote_local_assistant/)  
- [Linux Bash offline voice assistants](https://linuxbash.sh/post/artificial-intelligence-voice-assistants-on-linux)  
- [Tool retrieval for SLM agents](https://thinkinginsidethebox.ai/aaif/engineering/2026/09/17/tool-retrieval-for-slm-agents.html)  
- [Agent Skill Framework (arXiv HTML)](https://arxiv.org/html/2602.16653v3)  
- [SLM agentic survey (arXiv PDF)](https://arxiv.org/pdf/2510.03847)  
- [P-C-G SLM tool use (arXiv PDF)](https://arxiv.org/pdf/2509.19369v1.pdf)  
- [Agent distillation NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/file/99263f9bf46874e2b8b7f104b5063864-Paper-Conference.pdf)  
- In-repo: `vault/01-Trading/NEXUS - Local Model Bake-Off V1.md`, `docs/LOCAL_INFERENCE_CONNECTIVITY_V1.md`
