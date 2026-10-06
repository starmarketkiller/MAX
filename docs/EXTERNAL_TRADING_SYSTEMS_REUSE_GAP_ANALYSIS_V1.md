# External Trading Systems Reuse — Gap Analysis V1

**Stato:** forensic/gap-analysis completa, non committata. Nessuna modifica a runtime/MQL5/risk/execution, nessuna nuova dipendenza installata, nessun framework importato, nessuna decisione live, nessun refactor, nessun commit di codice.

**Nota preliminare:** al momento di questa analisi, `docs/NEXUS_EXTERNAL_TRADING_AUDIT_WAVE1.md`/`WAVE2.md`/`WAVE3.md` non esistevano ancora come file nel repo (i link condivisi non si erano resi leggibili) — l'analisi è stata fatta sul testo completo incollato in conversazione. Sono stati poi salvati come file canonici subito dopo, stesso contenuto, nessuna modifica — ora leggibili da qualunque sessione futura senza dipendere dalla conversazione.

**Metodo:** 3 ricognizioni parallele sul codice reale di NEXUS (core/orchestrazione+research, MT5/MQL5, memoria/governance), poi verifica diretta delle 2 affermazioni più rilevanti/sorprendenti prima di consolidare: (a) il gate RiskShield non osservato nel path principale — **confermato come finding già auto-documentato nel repo** (`docs/architecture/07_RISK_AND_PROTECTION_PIPELINE.md`, righe 24-28, non una scoperta di questo audit); (b) la postura CI supply-chain — **confermata**: `.github/workflows/ci.yml` pinna le Actions a tag mobili (`@v4`/`@v5`), nessun CodeQL/SBOM nel file, nessun `dependabot.yml` nel repo.

---

## Matrice completa

### Cluster 1 — Core / Orchestrazione

| Capability | External source | NEXUS current implementation (file) | Gap | Decision | Priority | Dependency | Security/live impact | Tests | Rollback |
|---|---|---|---|---|---|---|---|---|---|
| checkpoint/resume/durable task state | TradingAgents, psyb0t | `server/orchestrator_v1/core/dispatcher.py`, `task_queue.py` — coda persistita su disco, lease/owner/expiry, orfani post-restart → `BLOCKED`, mai ri-eseguiti auto | Nessuno (limite noto: single-process, dichiarato) | **REUSE_EXISTING** | — | Nessuna | Nessuno | — | N/A |
| Work Graph / task state (grafo generico) | TradingAgents (LangGraph) | `task_queue.py`/`orchestrator.py`/`router.py` — state machine a stati fissi | Nessun grafo riconfigurabile — **non un gap, un confine deliberato** | **REJECT** | REJECT | Introdurrebbe un secondo orchestratore | Alto se ignorato | — | N/A |
| provider abstraction | TradingAgents | `docs/NEXUS_PROVIDER_CONNECTOR_LAYER_V1.md`, `core/provider_connector.py`/`provider_policy.py` | Nessuno | **REUSE_EXISTING** | — | Nessuna | Nessuno | — | N/A |
| MCP façade | TradeOS MCP, vincentwongso, Vibe-Trading | **Nessun file** — `docs/NEXUS_JARVIS_ACCESS_LAYER_V1.md` usa protocollo custom `JARVIS_MESSAGE_V1`, non MCP | **GAP TOTALE** confermato | **IMPORT_COMPONENT** (sopra Jarvis Access Layer + Capability Registry esistenti) | P1 | MCP SDK (nuova dipendenza) | Alto per definizione (esposizione esterna) — da costruire SOPRA i gate esistenti, mai a lato | Conformance test per ogni tool | Rimuovere il server MCP, Jarvis custom resta invariato |
| scoped tool permissions | vincentwongso | `agent_capability_registry_v1.json` — 8 dimensioni di scope per agente | Nessuno — già più granulare di molti esempi esterni | **REUSE_EXISTING** | — | Nessuna | Nessuno | — | N/A |
| skill/tool catalog | nawfdev, Vibe-Trading | `agent_capability_registry_v1.json` + `router.py::find_capable_agents()` | Parziale — manca strato schema+eval+contract per singola skill | **EXTEND_EXISTING** | P2 | Nessuna | Basso | Eval cases per skill | Rimuovere i nuovi campi additivi |
| agent gateway | vincentwongso | `docs/NEXUS_LOCAL_AGENT_BRIDGE_V1.md`, `core/local_agent_bridge.py` — HMAC, zero listener inbound, 1 capability type | Nessuno come pattern; gap solo se generalizzato ad altri domini | **REUSE_EXISTING** (pattern) | — | Nessuna | Nessuno | — | N/A |
| point-in-time integrity | TradingAgents | `leakage_guard_v1.md`, `missing_data_policy_v1.md`, `market_ontology.md` (observation_point dichiarato ovunque) | Nessuno — disciplina matura e già testata (1 defect reale trovato e corretto in passato) | **REUSE_EXISTING** | — | Nessuna | Nessuno | — | N/A |
| supply-chain/dependency controls | NautilusTrader | `.github/workflows/ci.yml` — CSRF/JWT/rate-limit/audit CHIUSI; **CONFERMATO**: Actions a tag non SHA, no CodeQL, no SBOM, no Dependabot | **GAP REALE verificato** | **ADAPT_PATTERN** | P1 | Nessuna (solo config CI) | Medio (supply-chain, non trading) | CI verde post-change | Revert del workflow file |
| R→D autonomous research loop | RD-Agent | Discovery Engine v2 (`preregistration_provenance_guard.py`, `candidate_lifecycle.py`), `funding_v1/` | Nessuno — già maturo, testato su RECLAIM e MACD Phase 1 | **REUSE_EXISTING** | — | Nessuna | Nessuno | — | N/A |
| experiment registry | RD-Agent | Decision cards + evidence grading E0-E6, ma **frammentato** tra `docs/`/`vault/`/`server/research_scripts/phase7/*/` | Parziale — manca indice unico machine-readable | **EXTEND_EXISTING** | P2 | Nessuna | Nessuno | Validazione indice | Rimuovere l'indice |
| factor/model candidate registry | RD-Agent/Qlib | `contracts/edge-validation-registry.json` (`3a0906a`) | Nessuno — già più maturo del necessario | **REUSE_EXISTING** | — | Nessuna | Nessuno | — | N/A |
| canonical decision contract pipeline | FinRL-X | `market_ontology.md` + `CANONICAL_COMPONENT_CONTEXT_MODEL_V1.md` (`c971e33`) | Nessuno — stesso pattern, già costruito in questa stessa sessione | **REUSE_EXISTING** | — | Nessuna | Nessuno | — | N/A |
| market/event/component contracts | FinRL-X | `edge-validation-registry.schema.json` (`role_vocabulary`), `event_registry_schema.md` | Nessuno | **REUSE_EXISTING** | — | Nessuna | Nessuno | — | N/A |
| cross-engine validation | LEAN | **Nessun file** | **GAP TOTALE confermato** | **BENCHMARK_ONLY** (non ora) | P2 | LEAN/Nautilus runtime se mai costruito | Nessuno (research-only) | — | N/A |
| research/live parity | RegimeForgeEA | `independent_validation_integrity_v1.md` + saga `CROSS_TIMEFRAME_STATE_CONTAMINATION` (Phase 7.9-7.14) | Nessuno — rigore probabilmente superiore ai riferimenti esterni citati | **REUSE_EXISTING** | — | Nessuna | Nessuno | — | N/A |
| negative-evidence retention | RegimeForgeEA | `failure_memory.md` (26 pattern), `cross_timeframe_state_contamination_failure_memory_v1.json` | Nessuno | **REUSE_EXISTING** | — | Nessuna | Nessuno | — | N/A |
| cost-aware validation | TensorTrade | Cost-calibrated re-evaluation (`ff9f0e5`, 24.1M tick) | Nessuno — NEXUS ha già il meccanismo che TensorTrade raccomanda come warning | **REUSE_EXISTING** | — | Nessuna | Nessuno | — | N/A |
| proxy-data vs broker-native validation | RegimeForgeEA | `independent_validation_integrity_v1.md`, `sar_dukascopy_independent_validation.md` | Nessuno | **REUSE_EXISTING** | — | Nessuna | Nessuno | — | N/A |

### Cluster 2 — MT5 / MQL5

| Capability | External source | NEXUS current implementation (file) | Gap | Decision | Priority | Dependency | Security/live impact | Tests | Rollback |
|---|---|---|---|---|---|---|---|---|---|
| compile automation | psyb0t | `LocalBridge/nexus_local_worker.py::handle_compile_ea` — `metaeditor.exe /compile`, path-containment, timeout | Minore — nessuna verifica digest del binario MetaEditor, nessun job-id | **REUSE_EXISTING** | P2 (hardening) | Nessuna | Medio (esecuzione binario locale, già confinata) | Idempotenza doppia compile | Nessuna azione (nessun cambio) |
| Strategy Tester automation | psyb0t | **Nessun handler** — lancio manuale via `/config` (confermato da memoria utente) | **GAP REALE** | **ADAPT_PATTERN** (riuso scheletro comando/journal esistente) | **P1** | Nessuna obbligatoria | Alto se mal fatto (condivisione data-folder live/tester) | Tester non deve toccare cartella live | Disabilitare il nuovo comando worker |
| .set / .ini generation | psyb0t | File statici creati a mano (`MQL5/Presets/Research/*.set`) | **GAP REALE** | **ADAPT_PATTERN** | P2 | Nessuna | Basso | Round-trip JSON→.set | Tornare ai file statici |
| test queue / job state / restart recovery | psyb0t | Journal/idempotenza GIÀ esistenti (`nexus_worker.journal.json`, `PermanentCommandError`/`RetryableCommandError`) ma non applicati al Tester | Parziale | **EXTEND_EXISTING** | P1 | Nessuna | Medio | Restart a metà run | Rimuovere il comando tester dal journal |
| report/log/artifact collection | psyb0t | `server/research_scripts/parse_mt5_tester_report.py` — già usato per backtest 2014-2026 | Parziale — manca aggancio automatico post-job | **REUSE_EXISTING** (parsing) + **EXTEND_EXISTING** (aggancio) | P1 | Nessuna | Basso | — | Disabilitare l'aggancio |
| MT5_CAPABILITY_GATEWAY_HARDENING_V1 | vincentwongso | `nexus_policy.build_command()`, `operator_audit`/`audit_log()`, journal LocalBridge, `bridge_token` HTTPS-only | Gap di *esposizione* (non pensato per client MCP esterno), non di sicurezza sottostante | **EXTEND_EXISTING** | **P0 verificare prima di costruire altro** | Dipende dal MCP façade (cluster 1) | Alto per definizione, mitigato da gate esistenti | Ogni nuovo tool deve passare dagli stessi gate | N/A finché non costruito |
| MT5_RUN_ARTIFACT_CONTRACT_V1 | psyb0t | Nessuno schema formale (ad hoc per fase) | **GAP REALE** | **ADAPT_PATTERN** | P2 | Nessuna | Basso | Schema validation | Tornare ad ad hoc |
| MT5_TERMINAL_ISOLATION_POLICY_V1 | psyb0t | Config worker con un solo `mt5_path` — isolamento oggi **operativo/manuale** (junction, già un incidente reale vissuto in questo progetto) | **GAP REALE, già vissuto come bug concreto** | **ADAPT_PATTERN** | **P1** | Nessuna | **Alto — stessa classe di bug già verificatosi** | Azione su ruolo sbagliato deve fallire | Rimuovere il campo `terminal_role` |
| MQL5_COMMON_PRIMITIVES_DUPLICATION_AUDIT_V1 | EA31337 | `NXS_SafeOrder.mqh`, `NXS_SymbolProfile.mqh`, `NXS_Globals.mqh` (indicatori cache-once già centralizzati) | Minore — gap più piccolo di quanto ipotizzato nel Wave 3 | **BENCHMARK_ONLY** | P2/REJECT import diretto | Nessuna | Basso | N/A | N/A |
| MQL5_ENGINEERING_SKILL_V1 | nawfdev | **Nessuno** (`.claude/skills/` vuoto per questo) | **GAP TOTALE** | **IMPORT_COMPONENT** (pattern) + contenuto NEXUS-specifico da scrivere | **P0/P1** | Nessuna | Nessuno diretto, alto valore preventivo (previene bug già costati tempo reale in questa sessione) | Eval contro bug reali già noti (BREAKOUT_ACC/ORDER_BLOCK pre-fix) | Rimuovere il file skill |
| read-only vs mutating tool separation | vincentwongso | Implicita per funzione, non dichiarata formalmente | Gap di formalizzazione, non di sostanza | **EXTEND_EXISTING** | P2 | Nessuna | Basso | — | Rimuovere l'attributo |
| preflight | vincentwongso | `NXS_CommonExposurePreflight()` — robusto | Nessuno | **REUSE_EXISTING** | — | Nessuna | Nessuno | — | N/A |
| approval fingerprint | tradememory-protocol | `nexus_policy.build_command()` — conferma testuale, non verificato se fingerprint crittografico del payload esatto | Possibile gap sottile (cross-cluster con audit hash-chain) | **NEEDS_DEEP_AUDIT** | P1 | — | — | — | — |
| idempotency | psyb0t | Journal LocalBridge + idempotency key backend — 2 livelli coerenti | Nessuno | **REUSE_EXISTING** | — | Nessuna | Nessuno | — | N/A |
| append-only audit | mnemox-ai | `operator_audit` + `audit_log()` — reale, append-only per disciplina applicativa, non crittografica | Gap minore (hash-chain, vedi cluster 3) | **EXTEND_EXISTING** (competenza cluster 3) | P1 | — | — | — | — |
| role-scoped tool exposure | vincentwongso | Non trovato oltre all'autenticazione singola | **GAP REALE** | **ADAPT_PATTERN** | P1 (rilevante solo con MCP façade) | Nessuna | Alto se multi-agente futuro | Test per-ruolo | Rimuovere i ruoli |

### Cluster 3 — Memoria / Governance

| Capability | External source | NEXUS current implementation (file) | Gap | Decision | Priority | Dependency | Security/live impact | Tests | Rollback |
|---|---|---|---|---|---|---|---|---|---|
| TRADE_DECISION_RECORD_V1 | mnemox-ai, ai-hedge-fund | `NXS_Trace.mqh` (Decision/Gate/Execution Trace v1) + `NXS_GateTelemetry()` — struttura/enum già buoni, **ma solo log locale MT5, non sincronizzato al server** | Parziale — manca solo persistenza durevole fuori MT5 | **EXTEND_EXISTING** (via canale `NXS_WebBridge.mqh` già esistente) | **P1** | Nessuna se si riusa WebBridge | Nessuno diretto (telemetria, non gate) | Non-regressione formato esistente, verifica non rallenti execution | Disattivare la sincronizzazione, trace locale resta |
| TRADE_EPISODIC_MEMORY_V1 | tradememory-protocol | Nessuno oltre note vault testuali (non query-abili) | **GAP REALE confermato** | **IMPORT_COMPONENT** (pattern, non codice) | P2 | DB locale (SQLite, pattern già usato altrove) | Nessuno se solo informativo — **rischio se trattato come evidenza statistica** (già segnalato dall'utente) | Verifica che il recall non diventi evidenza | Rimuovere il DB |
| PRE_TRADE_BRAKE_V1 | mnemox-ai | `NXS_RuinFrozen()`, `NXS_Prot_EntryBlocked()`, `NXS_CommonExposurePreflight()`, principio NEXUS-RISK-002 esplicito | Nessun gap sul freno deterministico stesso — gap solo sulla componente memoria-based (dipende dal gap sopra) | **REUSE_EXISTING** (freno) / **EXTEND_EXISTING** (se si aggiunge memoria) | P0 verificare, P2 estendere | Nessuna | **Massimo** — path critico di apertura ordine | Suite esistente + nuovi test per gate aggiunti | N/A per il freno esistente |
| HASH_CHAIN_AUDIT_V1 | mnemox-ai | `contracts/nexus-event.schema.json`, `operator_audit` — append-only per convenzione, **nessun campo hash/hash_prev** | **GAP REALE confermato** | **EXTEND_EXISTING** (campo additivo allo schema esistente) | P2 | Nessuna (hashing stdlib) | Nessuno su live trading — solo integrità audit | Verifica estensione additiva non rompe consumer | Rimuovere il campo |
| POST_TRADE_OUTCOME_LINKER_V1 | mnemox-ai | Tabella `trades` esiste, ma con problema noto non chiuso (`AUD0-DB-004`, chiave primaria, PR-12 già pianificato) | Parziale, **bloccato da PR-12 preesistente** | **EXTEND_EXISTING** (dipendente da PR-12) | P1, bloccato | Nessuna | Nessuno se fatto come join server-side | Stessi test già pianificati per PR-12 | N/A |
| Mandate model | ai-hedge-fund | `server/funding_v1/opportunity_lifecycle.py` — pattern fail-closed già maturo, ma per opportunity di business non trading | Gap nel dominio trading specifico, non nel pattern | **ADAPT_PATTERN** | P1 | Nessuna (stesso approccio Python) | Reale solo se il mandato arriva a governare flag live — da tenere come livello di policy sopra, non dentro MQL5 | Stessi test property-based già usati per `opportunity_lifecycle.py` | Rimuovere il modulo mandate |
| Kill switch | ai-hedge-fund | `NXS_RuinFrozen()` — **solo automatico**, nessun endpoint `/api/halt` manuale trovato | **GAP REALE confermato** | **IMPORT_COMPONENT** (pattern semplice) | **P1** | Nessuna | **Alto se mal progettato** — l'endpoint stesso deve essere autenticato/auditato | Funziona anche a sistema degradato | Rimuovere l'endpoint, freeze automatico resta |
| Fail-closed behavior | ai-hedge-fund, tradememory-protocol | Principio già maturo in 3 domini (risk MQL5, ricerca Phase 4, Discovery Engine v2) — **ma** `docs/architecture/07_RISK_AND_PROTECTION_PIPELINE.md` documenta già che `NXS_RS_BlockEntry()` non è osservato nel path di entry principale | **Non un gap concettuale — un gap di wiring GIÀ CONOSCIUTO E PIANIFICATO, confermato da questo audit, non scoperto da esso** | **REUSE_EXISTING** (principio) con fix di wiring già pianificato altrove | **P0 — già pianificato, non nuovo** | Nessuna | **Alto** — è il "Repair priority #1" di quel documento | Test già pianificati in quel documento | N/A |

---

## Conclusioni obbligatorie

### ⚠️ Priorità sopra tutte le altre (pre-esistente, solo riconfermata qui)

`NXS_RS_BlockEntry()` (RiskShield master gate — Equity Breaker, Spread Burst, Correlation Cluster) **non risulta osservato nel path di entry principale**, secondo `docs/architecture/07_RISK_AND_PROTECTION_PIPELINE.md` (righe 24-28) — **non una scoperta di questo audit, un gap già auto-documentato nel repo e già pianificato come "Repair priority #1"**. Questo audit lo riconferma e lo segnala con la massima priorità: nessuna delle 5 capability sotto dovrebbe precederlo se non è già stato risolto altrove.

### Top 5 capability da implementare davvero

1. **MQL5_ENGINEERING_SKILL_V1** — gap totale, valore alto, rischio di duplicazione nullo (puramente additivo), nessuna dipendenza nuova. Previene esattamente la classe di bug (`CROSS_TIMEFRAME_STATE_CONTAMINATION`) che ha già costato tempo reale di debug in questa sessione (ORDER_BLOCK/BREAKOUT_ACC).
   **File da toccare:** nuovo `.claude/skills/mql5-engineering/SKILL.md` (o percorso equivalente già in uso dal progetto per skill) — nessun file NEXUS esistente modificato. **Motivo:** additivo puro, zero rischio.
2. **Kill switch manuale** — gap reale confermato, il freeze automatico (`NXS_RuinFrozen`) non è un comando manuale indipendente dal calcolo di rischio.
   **File da toccare:** nuovo endpoint in `server/app.py` (pattern simile a `operator_audit`/`audit_log()` già esistenti) + flag letto da `NXS_CommonExposurePreflight()` lato MQL5. **Motivo:** ortogonale al freeze automatico, non lo sostituisce, basso rischio di duplicazione.
3. **MT5_TERMINAL_ISOLATION_POLICY_V1** — gap reale già vissuto come incidente concreto in questo stesso progetto (bug di compilazione dalla cartella sbagliata).
   **File da toccare:** `nexus_worker.config.example.json` (nuovo campo `terminal_role: live|tester`) + guardia in `LocalBridge/nexus_local_worker.py::handle_compile_ea`/`handle_deploy_files`. **Motivo:** stessa classe di bug già costata un incidente reale, fix piccolo e contenuto.
4. **TRADE_DECISION_RECORD_V1 (sync server-side)** — la struttura esiste già (`NXS_Trace.mqh`), manca solo la persistenza fuori da MT5.
   **File da toccare:** `MQL5/Include/NEXUS_v1/NXS_Trace.mqh` (aggiungere invio via canale esistente) + `MQL5/Include/NEXUS_v1/NXS_WebBridge.mqh` (riuso, non nuovo canale) + nuovo endpoint server minimale per la persistenza. **Motivo:** estende una struttura già ben progettata, non la sostituisce.
5. **MT5 Strategy Tester automation (estensione del job/journal esistente)** — gap reale, confermato anche dalla memoria operativa dell'utente ("/config non accoda").
   **File da toccare:** `LocalBridge/nexus_local_worker.py` (nuovo `handle_run_tester`, riusando lo stesso schema `PermanentCommandError`/`RetryableCommandError`/journal già usato da `handle_compile_ea`/`handle_deploy_files`) + `server/research_scripts/parse_mt5_tester_report.py` (aggancio automatico post-job, riuso diretto). **Motivo:** riusa interamente l'infrastruttura di journaling già esistente, nessun secondo sistema di coda.

### Top 5 capability già esistenti da non duplicare

1. **Durable task queue / checkpoint-resume** (`server/orchestrator_v1/core/`) — non costruire un secondo Work Graph/LangGraph-style.
2. **Provider abstraction** (`NEXUS_PROVIDER_CONNECTOR_LAYER_V1`/`PROVIDER_POLICY_REGISTRY`) — non costruire un secondo router di provider.
3. **Scoped agent capability registry** (`agent_capability_registry_v1.json`) — non costruire un secondo sistema di permessi.
4. **Ontologia canonica decisione/evento/componente** (`market_ontology.md` + `CANONICAL_COMPONENT_CONTEXT_MODEL_V1.md` + `edge-validation-registry.schema.json`) — non ricostruire da zero una pipeline "FinRL-X-style".
5. **Disciplina di ricerca fail-closed** (`leakage_guard_v1.md`, `missing_data_policy_v1.md`, `independent_validation_integrity_v1.md`, `preregistration_provenance_guard.py`) — non costruire un secondo framework di integrità scientifica.

### Top 5 idee esterne da rifiutare

1. **LLM/agente con autorità diretta di trading live** (TradingAgents trader agent, tool mutante MCP senza consenso di default, voting di persona come controllo di rischio in ai-hedge-fund) — viola l'invariante #1.
2. **Work Graph generico stile LangGraph** in sostituzione dell'orchestratore NEXUS — `DUPLICATE_ORCHESTRATION_STACK`, esplicitamente proibito.
3. **RL (TensorTrade/FinRL) come core a breve termine** — l'esperimento BTC pubblicato da TensorTrade stesso mostra che una commissione realistica ribalta un risultato positivo in perdita; nessuna fondazione di edge ancora dimostrata su cui costruire RL.
4. **Migrazione del motore a LEAN/Nautilus** — MT5 è l'ambiente di esecuzione reale, il rischio di migrazione è sproporzionato; restano solo benchmark/parità.
5. **Kronos (o qualunque foundation model) da previsione diretta a trade** — deve restare `RESEARCH_ONLY`, in attesa della chiusura di `UNIFIED_MARKET_INTELLIGENCE_SHADOW_PHASE1`, mai un segnale di trading diretto.

### Ordine di implementazione consigliato

1. **Verificare lo stato reale del gate RiskShield** (già pianificato altrove, non parte di questo audit — ma logicamente precede tutto il resto).
2. MQL5_ENGINEERING_SKILL_V1 (nessuna dipendenza, nessun rischio).
3. MT5_TERMINAL_ISOLATION_POLICY_V1 (piccolo, previene un incidente già noto).
4. Kill switch manuale.
5. TRADE_DECISION_RECORD_V1 sync server-side.
6. MT5 Strategy Tester automation (estensione journal).
7. Solo dopo: MCP façade (più grande, foundazionale, dipende da decisioni su esposizione esterna non ancora prese) e supply-chain CI hardening (igiene, non urgente per il trading).

Nessuno di questi è autorizzato per l'implementazione da questo documento — è una gap analysis, non un'autorizzazione. Codex resta sul goal revenue finché non libero; questi candidati restano in coda.

---

EXTERNAL_TRADING_SYSTEMS_REUSE_GAP_ANALYSIS_V1_READY_FOR_DECISION
