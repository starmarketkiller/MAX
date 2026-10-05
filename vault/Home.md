---
type: moc
domain: system
status: active
tags: [jarvis, home]
created: 2026-07-12
updated: 2026-10-05
---

# 🤖 JARVIS — punto d'ingresso

> **Per lo stato operativo reale (cosa è chiuso/attivo/bloccato, prossimo P0), vai
> direttamente a [[CURRENT_STATE]]** — questa pagina resta la mappa dei domini,
> non lo stato del giorno.

JARVIS oggi non è più l'idea n8n/Midjourney del 12 luglio 2026 (vedi in fondo):
è l'**Orchestrator V1 / Jarvis V1** reale, live su Render, con bot Telegram,
Task Queue/Router/Ledger, Dynamic Specialist Review e un router cognitivo
locale opzionale (Ministral). Architettura corrente: **[[MOC - Sistema JARVIS]]**.

## Domini
- **[[MOC - Trading]]** — NEXUS EA, backtest, MT5. Live; VOLBRK Serious 3Y
  preregistrato ma `PARTIALLY_BLOCKED` su 3 soglie decisionali umane.
- **[[MOC - Business]]** — Funding Priority & Opportunity Framework
  ([[MOC - Opportunity and Funding]]) + primo esperimento reale di revenue
  (`OPP_LEAD_RESEARCH_SERVICE`, outreach manuale in corso).
- **[[MOC - Social]]** — Instagram / contenuti. Ancora da compilare.
- `00-Inbox/` — cattura rapida, non ha una MOC apposta perché è zona di passaggio
  (vedi la sua `README.md`), non memoria definitiva.

## Il sistema stesso
- **[[CURRENT_STATE]]** — stato operativo del progetto, aggiornato ad ogni
  milestone chiusa (fonte di verità per "dove siamo", non questa pagina).
- **[[MOC - Sistema JARVIS]]** — architettura Jarvis V1/Orchestrator V1: come i
  pezzi si parlano oggi.
- **[[CHAT_MIGRATION_LEDGER_V1]]** — tracciamento delle sessioni Claude Code
  pesanti distillate nel vault, nessuna cancellazione fatta.
- **[[RAG - Convenzioni]]** — schema frontmatter e regole di tagging usate in tutto il vault.
- Prompt Claude per verticale: **[[Prompt - Claude Trading]]** · **[[Prompt - Claude Business]]**
  · **[[Prompt - Claude Social]]**
- **[[Automazioni - Idee n8n]]** — backlog, non più l'unico piano per JARVIS (superato
  dall'Orchestrator V1 reale).

## Nota storica (stato onesto del 12 luglio 2026, superato)
A luglio 2026 JARVIS era ancora un'idea (Obsidian + n8n/Zapier + Midjourney,
niente di automatizzato), e il trading era in fase di validazione EA v2.5.0
dopo l'overfitting scoperto su v2.4.8 (**[[NEXUS EA - Lezione Overfitting 3Y]]**).
Quella fase è conclusa; lo stato reale di oggi è in **[[CURRENT_STATE]]**.
