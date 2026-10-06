# MQL5 Engineering Skill V1

**Stato:** completato, skill canonica creata. Nessuna modifica a trading logic, risk, execution, nessun refactor MQL5. Priorità consigliata (dopo `RISKSHIELD_DOCUMENTATION_RECONCILED`), prima di `MT5_TERMINAL_ISOLATION_POLICY_V1`.

## Dove vive

`.claude/skills/mql5-engineering/` — struttura:

- `SKILL.md` — la skill canonica (frontmatter + 18 sezioni: lifecycle handle, CopyBuffer, closed-bar/new-bar, TF ownership, timezone, symbol specs, order/position identity, magic/attribution, error handling, logging/trace, risk/execution boundary, compile workflow, Strategy Tester workflow, regression tests, pitfall catalogue, forbidden patterns, output contract, verifier checklist).
- `references/forbidden_patterns.md` — ogni pattern proibito con citazione file:riga reale, non ipotetica.
- `references/golden_examples.md` — pattern corretti già applicati nel codebase, da imitare.
- `eval/eval_cases.md` — 7 scenari basati su bug storici reali di questo progetto, con verdetto atteso (fixture per un futuro harness, non ancora wired in CI).
- `verifier.py` — checker statico grep-based, euristico (testato: funziona, 0 falsi positivi su `NXS_Execution.mqh`, 1 finding euristico onesto su `NXS_RiskShield.mqh` — nessuno dei due è un bug, è advisory).

## Perché questa forma (verifica duplicazioni fatta prima di scrivere)

- **`.claude/skills/`** esisteva già con una sola skill di terze parti (`ui-ux-pro-max`) — nessuna skill MQL5/trading preesistente, nessuna duplicazione. Riusata la stessa convenzione di frontmatter (`name`/`description` YAML) e la stessa struttura "When to Apply" per coerenza con l'unica convenzione già stabilita nel repo.
- **`server/orchestrator_v1/agent_capability_registry_v1.json`** è un registro di **agenti** (chi può eseguire quale `task_type`, con `trust_level`/`file_access`/`mt5_access`), non un registro di **contenuto/skill** — scopo diverso, nessuna sovrapposizione da riconciliare. Non toccato.
- Nessun altro file `SKILL.md` o cartella skill-simile trovata altrove nel repo.

## Perché nessuna euristica scientifica rigida

Ogni soglia numerica citata nella skill (PF, Sharpe, risk %, barre di cooldown) è esplicitamente etichettata come **esempio/policy configurabile**, non verità scientifica — coerente con l'istruzione esplicita e con `docs/TRADING_EDGE_STATUS_RECONCILIATION_V1.md`/`contracts/edge-validation-registry.json`, che restano l'unica fonte di verità su "questo componente ha edge o no."

## Riusabilità multi-modello

Il contenuto di `SKILL.md`/`references/`/`eval/` è markdown puro, nessuna dipendenza da meccanismi di invocazione specifici di Claude — leggibile direttamente da Codex, Ministral o qualunque altro worker semplicemente aprendo il file. Solo l'auto-invocazione contestuale (via il campo `description` del frontmatter) è specifica di Claude Code; il contenuto stesso no.

MQL5_ENGINEERING_SKILL_V1_READY_FOR_REVIEW
