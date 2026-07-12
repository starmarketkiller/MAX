---
type: note
domain: system
status: draft
tags: [jarvis, automazioni, n8n, backlog]
created: 2026-07-12
updated: 2026-07-12
---

# Automazioni — backlog idee (n8n/Zapier)

Nessun flusso è ancora costruito. Questa nota è il backlog: idee scritte come
**trigger → passi → output**, pronte da tradurre in un workflow quando si passa
alla fase "⚙️ Automazioni" (vedi [[MOC - Sistema JARVIS]]).

## 1. Backtest EA → nota Obsidian → notifica
**Perché prima questa**: il progetto ha già `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`
configurati su Render (`render.yaml`) — minor attrito per un primo flusso reale.

- **Trigger**: nuovo file in `results/reports/*_stats.csv` (push su repo, o webhook
  dal backend quando un test finisce).
- **Passi**: 1) legge il CSV, estrae net/PF/DD/Sharpe · 2) crea/aggiorna una nota in
  `01-Trading/` con i numeri (append a [[NEXUS EA - Log Versioni]] o nota dedicata) ·
  3) invia riassunto su Telegram.
- **Output**: la memoria si aggiorna da sola, niente più trascrizione manuale in chat.

## 2. Riassunto settimanale Business
- **Trigger**: schedulato, ogni lunedì.
- **Passi**: 1) Claude legge `02-Business/*` · 2) genera un riassunto/checklist della
  settimana · 3) invia per email o lo scrive in `00-Inbox/`.
- **Output**: punto di partenza per la revisione settimanale di Chantilly.
- **Blocca su**: [[Chantilly - Scheda]] deve avere contenuti reali prima che questo
  flusso produca qualcosa di utile.

## 3. Idea contenuto → asset → coda social
- **Trigger**: nuova riga con stato "Idea" in [[Instagram - Calendario Contenuti]].
- **Passi**: 1) notifica che c'è un'idea da produrre · 2) (manuale per ora) genera
  asset su Midjourney/Canva · 3) al caricamento dell'asset, aggiorna lo stato a
  "Pronto".
- **Nota**: i passi 2 non sono automatizzabili senza API Midjourney/Canva — per ora
  resta un trigger di notifica, non un flusso end-to-end.

## Come promuovere un'idea a workflow reale
Quando si costruisce uno di questi in n8n: esporta il JSON del workflow e salvalo
in `vault/04-System/n8n-exports/` (cartella da creare al bisogno), linkalo da qui.
