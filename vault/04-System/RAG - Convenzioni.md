---
type: note
domain: system
status: active
tags: [jarvis, rag, convenzioni]
created: 2026-07-12
updated: 2026-07-12
---

# Convenzioni RAG del vault

Regole che ogni nota di questo vault segue, così un indicizzatore (o Claude a mano)
può recuperare/filtrare in modo affidabile.

## Frontmatter obbligatorio
```yaml
---
type: moc | note | log | template
domain: trading | business | social | system
status: active | draft | archived
tags: [elenco, di, tag, kebab-case]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```
- `type: moc` — nota indice di un dominio (Map of Content), collega le note figlie.
- `type: note` — contenuto normale.
- `type: log` — cronologia/changelog (es. [[NEXUS EA - Log Versioni]]).
- `type: template` — schema da riusare, non contenuto vero.

## Chunking
Un file = un'unità di recupero di base. Dentro il file, gli header `##` sono i
punti naturali per chunk più fini se serve granularità maggiore. Non spezzare una
nota a metà di un concetto solo per "farla più corta".

## Link
Usa sempre `[[Nome Nota Esatto]]` (wiki-link Obsidian) per collegare, mai URL
relativi a file. Ogni nota dovrebbe avere almeno un link verso la sua MOC di
dominio, in fondo, sotto "Collegamenti".

## Nomi file
`Dominio - Argomento.md` quando ha senso raggruppare (es. `NEXUS EA - Log Versioni.md`),
altrimenti nome diretto. Niente numerazione manuale nei nomi file — l'ordine lo dà
la cartella (`00-`, `01-`...) e i link, non il filename.

## Aggiornare `updated`
Ogni volta che una nota viene modificata in modo sostanziale, aggiorna il campo
`updated` nel frontmatter. È il segnale più semplice per capire cosa è ancora fresco.

## Collegamenti
[[MOC - Sistema JARVIS]]
