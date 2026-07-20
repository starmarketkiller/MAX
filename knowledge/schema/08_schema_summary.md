# 08 — Riepilogo + proposte di modifica (NON applicate)

## Fotografia
Canonical Schema v1 **congela ciò che esiste** dopo M0-M2: 13 entità (9 attive, 1 embedded, 1 implicita, 2 riservate), 8 identificatori canonici, 11 enum, 12 regole di validazione, lifecycle a 8 stadi. Contratto formale: [schema_v1.json](schema_v1.json).

## Breaking change rilevati rispetto a uno schema "ideale" — SOLO PROPOSTE
Per istruzione esplicita, nessuna di queste è stata applicata. Vanno approvate in revisione architetturale.

| # | Proposta | Cosa cambierebbe | Rischio compatibilità |
|---|---|---|---|
| P1 | Normalizzare `Bug.stato` in enum `open/fixed` + campo `qualifier` libero | bug_database + timeline_engine | basso (mappatura 1:1 dai valori attuali) |
| P2 | `Bug.strategie_coinvolte` da testo libero ad array di `strategy_id` + scope (`all`, `portfolio`, `runner`, `unattributable`) | bug_database + fan-out eventi timeline | medio (i valori vaghi tipo "~25 strategie" richiedono decisione umana caso per caso) |
| P3 | `backtest_id` esplicito + FK formale `Run.backtest_id` (oggi implicita via round) | backtest_database + runs | basso |
| P4 | `import_id` esplicito nel ledger (oggi chiave naturale checksum+timestamp) | imports_ledger | basso |
| P5 | Unificare la lingua dei nomi campo (oggi mix IT/EN: `nome` vs `strategy_id`, `origine` vs `source_path`) | tutti i DB | **alto** — rimandare a schema v2 con migrazione completa, non pezzo per pezzo |
| P6 | Entità `Document` esplicita con registro path→checksum | nuova | basso (additiva) |

## Rischi di retrocompatibilità (stato attuale, senza applicare nulla)
1. `Backtest` senza id proprio: se una campagna venisse rinominata, i riferimenti si romperebbero (mitigato: nomi mai cambiati finora).
2. `Document` per path: file spostati nel vault = riferimenti orfani (mitigato: git conserva la storia; da risolvere con P6).
3. Il mix linguistico (P5) è il debito più visibile ma anche il più costoso: da affrontare UNA volta sola, non incrementalmente.

## Assunzioni
1. I nomi `stratName` MQL5 sono l'autorità per `strategy_id` (il codice EA è la fonte, non i documenti).
2. La tabella dei round è chiusa e a manutenzione esplicita: round nuovi = riga nuova nella tabella dell'importer.
3. `SignalMetrics` ed `EquityMetrics` restano SEPARATE per design (mai mischiare dati di segnale e di equity nella stessa entità).
4. `Run.confidence` (qualità import) ed EvidenceLink futura (forza dell'evidenza) sono concetti DISTINTI e non vanno mai fusi.
