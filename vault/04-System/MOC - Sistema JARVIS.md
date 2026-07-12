---
type: moc
domain: system
status: active
tags: [jarvis, sistema, architettura]
created: 2026-07-12
updated: 2026-07-12
---

# ⚙️ Sistema JARVIS — come si parlano i pezzi

## I tre bracci

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

## Collegamenti
[[Home]] · [[RAG - Convenzioni]] · [[Automazioni - Idee n8n]]
