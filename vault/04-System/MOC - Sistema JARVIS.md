---
type: moc
domain: system
status: active
tags: [jarvis, sistema, architettura]
created: 2026-07-12
updated: 2026-10-17
---

# ⚙️ Sistema JARVIS — come si parlano i pezzi

> **Aggiornamento 2026-10-05:** il contenuto sotto (3 bracci n8n/Midjourney,
> "non ancora costruiti") descrive il piano del 12 luglio 2026 ed è superato.
> JARVIS oggi è l'**Orchestrator V1 / Jarvis V1** reale: Task Queue/Router/
> Ledger, bot Telegram live su Render, Dynamic Specialist Review, e un router
> cognitivo locale opzionale (Ministral) — vedi
> **[[NEXUS - Jarvis Ministral Router V1]]** e
> **[[NEXUS - Ministral Task Compiler V1]]**. Stato operativo aggiornato:
> **[[CURRENT_STATE]]**. La sezione storica sotto resta per memoria del
> ragionamento originale, non riscritta.

## I tre bracci (piano originale, luglio 2026 — storico)

### 🧠 Obsidian (memoria)
Questo vault. JARVIS lo consulta come RAG prima di rispondere: legge le note
rilevanti per il dominio della richiesta (Trading/Business/Social) e le passa a
Claude come contesto. Regole di indicizzazione: [[RAG - Convenzioni]].

### ⚙️ Automazioni (azioni)
n8n o Zapier — flussi che collegano eventi a conseguenze senza intervento manuale.
**Non ancora costruiti.** Backlog di idee concrete: [[Automazioni - Idee n8n]].

### 🎨 Creazione (contenuti)
Midjourney/Canva per asset visivi. **Nessuna integrazione automatica per ora** —
uso manuale, gli output finiscono nel calendario social ([[Instagram - Calendario Contenuti]]).

## Il nodo centrale: Claude
Ogni braccio converge su Claude, che poi si specializza per verticale con un
**system prompt diverso** a seconda del dominio:
- [[Prompt - Claude Trading]]
- [[Prompt - Claude Business]]
- [[Prompt - Claude Social]]

Principio: Claude non è "uno solo che fa tutto" — JARVIS sceglie quale prompt
attivare in base a cosa gli viene chiesto, e quel prompt determina quali note del
vault sono rilevanti e quali azioni sono permesse.

## Ordine di costruzione consigliato
1. ✅ **Obsidian** (questo vault) — fatto, 12/07/2026.
2. **Prompt Claude per verticale** — bozze già scritte in questo vault, da rifinire
   con l'uso reale.
3. **Una prima automazione semplice** (n8n), es. "risultato backtest EA → nota
   Obsidian → notifica Telegram" — il progetto ha già `TELEGRAM_BOT_TOKEN` /
   `TELEGRAM_CHAT_ID` configurati su Render (`render.yaml`), è il punto di minor
   attrito per partire.
4. **Creazione contenuti** — resta manuale finché 1-3 non sono stabili; automatizzarla
   per ultima evita di costruire un flusso sofisticato su una base ancora instabile.

## Note di implementazione Orchestrator / Jarvis (aggiunto 2026-10-17)
Note esistenti ma prima non collegate da nessuna MOC (audit link 2026-10-17):
- [[NEXUS - First Production NEXUS TASK (0001)]]
- [[NEXUS - Local Model Bake-Off V1]]
- [[NEXUS - Local Runtime Setup and First Pilot V1]]
- [[NEXUS - Orchestrator V1 Architecture and Environment Discovery]]
- [[NEXUS - Orchestrator V1 Core Implementation]]
- [[NEXUS TASK 0002 - Research Safety Net Auto-Backfill]]
- [[NEXUS TASK 0003 - Approve Safety Net Backfill]]
- [[NEXUS TASK 0004 - Merge Escalation Resolution]]
- [[NEXUS - Jarvis Access Layer V1]]
- [[NEXUS TASK 0008 - Multi-Agent Review and Finalization Pipeline V1]]
- [[NEXUS TASK 0009 - Jarvis Multi-Agent Finalization Integration]]

## Collegamenti
[[Home]] · [[RAG - Convenzioni]] · [[Automazioni - Idee n8n]]
