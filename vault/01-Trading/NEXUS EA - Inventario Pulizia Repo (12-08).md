---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, repo-hygiene, git]
created: 2026-08-12
updated: 2026-08-12
---

# Inventario pulizia repo (12/08)

Richiesta dell'utente in vista della "v3": eliminare cartelle/branch
obsoleti prima di consolidare. Solo inventario qui — **nessuna
cancellazione ancora fatta**, aspetto conferma per categoria.

## 1. Cartella da eliminare — sicura, alto guadagno

**`results/reports/` — 418 MB, di cui 367 MB solo `sweep37/`.**
Report HTML/CSV del vecchio MT5 Strategy Tester, tutti datati inizio-metà
luglio (formato `YYYYMMDD` nei nomi file: 3-28 luglio), da PRIMA che
questa sessione spostasse tutto sul motore Python/Dukascopy
(`server/backtest.py`) come source of truth. Verificato: **nessun file
in `server/*.py`, `MQL5/`, `docs/` referenzia `results/reports`** — è
morto, non letto da nessun percorso di codice attivo. Include
`sweep37/pre-fix-16-07-round2` e `round3-gate1pos`, letteralmente
snapshot PRE i bugfix del 16/07 già superati. Consigliato: cancellare
tutta la cartella.

`server/protected/downloads/*.set` (5 file, luglio) e alcuni `.set` in
`results/sets/` — profili demo vecchi (pre tier di rischio, pre-CRT,
pre-oggi), superati dal nuovo `MQL5/Demo/NEXUS_Demo_MultiTF_12-08.set`.
Piccoli (pochi KB), non urgenti ma coerente rimuoverli nello stesso giro.

Nessun problema di sicurezza trovato (il sospetto "credenziali di
default nel bundle React" di un audit precedente non si riproduce più —
nessun `frontend/build` presente con credenziali embedded, `frontend/.env`
pulito).

## 2. Branch remoti — 28 totali, categorie diverse

### Sicuri da cancellare subito (già dentro `main`, zero commit unici)
| Branch | Ultimo commit |
|---|---|
| `claude/dukascopy-fetch-resume-fix` | 08/08 |
| `feature/dukascopy-backtest-datasource` | 08/08 |
| `feature/pr2-virtual-sl` | 21/07 |
| `feature/trade-lifecycle-ledger` | 21/07 |
| `nexus-core-v1-foundation` | 20/07 |

Verificato con `git branch -r --merged origin/main` — ogni commit che
contengono è già in `main` attraverso un'altra strada. Cancellarli non
perde nulla.

### Probabili scarti pre-progetto (gennaio-marzo 2026, ambito diverso)
8 varianti quasi-duplicate di `codex/create-mt5-expert-advisor-for-xm-gold*`
(stesso nome base + 7 suffissi random tipo `-cjtb16`/`-dcj10r`), più
`codex/create-node.js-telegram-bot-project` (progetto completamente
diverso), `codex/convert-mql5-ea-to-pine-script`,
`codex/update-code-to-mql5-format`, `codex/identify-and-fix-105-errors-and-12-warnings`
+ il suo duplicato `le0pf0-codex/...`, `patch-1`. Tutti piccoli (4-18
commit unici), tutti datati gennaio-marzo 2026 o luglio 2025 (molto
prima dell'inizio di questa sessione), 194 commit indietro rispetto a
main — sembrano tentativi/agenti automatici di un'altra fase del
progetto mai portata avanti. **Non verificato nel dettaglio cosa
contengono** (solo i messaggi di commit) — consigliato uno sguardo
veloce prima di cancellare, ma sembrano scarti.

### Da NON cancellare senza guardare — storia reale sostanziale
| Branch | Commit unici | Cosa sembra |
|---|---|---|
| `feature/openai-backtest-analyst` | 326 | Un modulo "OpenAI Backtest Analyst" alternativo (diverso dal coach Claude attuale), fix MQL5 reali, porting Pinescript — ramo alternativo mai fuso, non semplice scarto |
| `baseline-post-infra-audit` | 320 | Fix MQL5 "reali" per BOLLINGER/ICHIMOKU/WEEKLY_EXP/OTE_CONT/RANGE_FADE/NY_REVERSAL/MALAYSIAN_SNR — lavoro sostanziale su strategie oggi fuori dal nucleo, potrebbe contenere fix mai portati su `main` |
| `nexus/d8-source-package` (08/05, recente) | 74 | Ingestione fonti esterne (PDF Yanu Emmanuel, Alchemist, Candle Range Theory) + verifica di fedeltà delle strategie SMC contro le fonti originali — potrebbe sovrapporsi a `01-Trading/Fonti/` nel vault, ma non è detto sia già stato tutto recuperato |
| `claude/file-review-complete-rwq562`, `claude/strategy-work-package-v1`, `claude/trend-gate-nucleo9-spec` | 1-3 | Piccoli, ma recenti (fine luglio-inizio agosto) — sessioni Claude precedenti su questo stesso progetto, da controllare cosa contengono prima di scartarli |

## Raccomandazione

1. **Ora**: cancellare `results/reports/` (418 MB, confermato morto) e i
   5 branch a zero commit unici — rischio sostanzialmente nullo.
2. **Con un'occhiata veloce prima**: gli 11 branch pre-progetto
   gennaio-marzo (verosimilmente scarti, ma non controllati riga per
   riga).
3. **Da decidere con calma, non ora**: i 4 branch con storia sostanziale
   (`openai-backtest-analyst`, `baseline-post-infra-audit`,
   `d8-source-package`, e le 3 sessioni Claude recenti) — potrebbero
   contenere lavoro reale mai confluito in `main`. Cancellarli senza
   guardare rischia di perdere qualcosa di utile per la v3.

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - Igiene Repository e Duplicati]]
