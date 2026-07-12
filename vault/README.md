# Vault JARVIS — memoria del sistema

Questo è un vault [Obsidian](https://obsidian.md) versionato dentro il repo MAX. È il nodo
**🧠 Memoria** dell'architettura JARVIS: le note qui dentro sono ciò che Claude legge (via RAG)
quando JARVIS lo invoca per Trading, Business o Social.

## Come aprirlo
In Obsidian: **File → Apri cartella come vault** → seleziona questa cartella (`MAX/vault`).
Non serve altro: è markdown puro, wiki-link `[[Nota]]` e frontmatter YAML.

## Struttura

| Cartella | Cosa contiene | Stato |
|---|---|---|
| `00-Inbox/` | Cattura rapida, non ancora smistato | vuoto, da usare |
| `01-Trading/` | NEXUS EA: architettura, log versioni, lezioni, screening strategie | **popolato con dati reali** |
| `02-Business/` | Chantilly | scaffold, da compilare |
| `03-Social/` | Instagram / contenuti | scaffold, da compilare |
| `04-System/` | Come funziona JARVIS stesso: prompt Claude, convenzioni RAG, idee automazioni | popolato |

Punto d'ingresso: **[[Home]]**.

## Perché Trading è già pieno e gli altri no
Trading (NEXUS EA) è il progetto su cui abbiamo lavorato per settimane in questa sessione:
la memoria esiste già, l'ho solo trascritta in note durature invece di lasciarla nella
chat. Business e Social partono da zero — li ho scaffoldati con la struttura giusta ma
senza inventare contenuti che non mi hai dato.

## Non è codice dell'EA
Questo vault è documentazione/memoria, separato da `MQL5/`, `server/`, `frontend/`.
Niente qui viene eseguito o deployato.
