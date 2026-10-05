---
type: system-ledger
domain: system
status: active
tags: [jarvis, nexus, sessioni, audit]
created: 2026-10-05
updated: 2026-10-05
---

# CHAT_MIGRATION_LEDGER_V1

Tracciamento delle sessioni Claude Code di questo progetto (`C--Users-User`),
per decidere con evidenza — non per paura — quali trascrizioni pesanti sono
sicure da eliminare. **Nessuna sessione è stata cancellata.** Questo file
registra solo lo stato della verifica, mai un'azione di cancellazione.

## Perché esiste

Timbro di origine: il 2026-10-05 l'utente ha espresso il timore che il
lavoro fatto in vecchie sessioni pesanti non fosse mai stato catturato nel
vault prima di un'eventuale pulizia. Risposta: non rassicurazione a vuoto,
ma due verifiche con evidenza reale —
`NEXUS_KNOWLEDGE_CONSOLIDATION_AUDIT_V1` (correlazione temporale commit↔vault)
e `HEAVY_SESSION_SPOT_CHECK_V1` (verifica di contenuto, non solo di titolo).

## Catena di continuazione reale (verificata via timestamp, non assunta)

Le sessioni risultano un'unica catena quasi continua di `--continue`, non
sessioni scollegate — ogni fine coincide quasi al secondo con l'inizio
della successiva:

| Sessione (uuid) | Dimensione | Periodo (timestamp reali, UTC) | Spot-check contenuto |
|---|---|---|---|
| `249dc5ba-cf82-4ca8-a6cf-5da41643ef49` | 24.8 MB | 2026-09-03 14:47 → 2026-09-07 16:19 | **Non ancora fatto** — non incluso nelle 3 sessioni nominate dall'utente per `HEAVY_SESSION_SPOT_CHECK_V1` |
| `bdfad6b1-63be-4962-8fad-e9b7b1cd3a8f` | 30.9 MB | 2026-09-07 16:19 → 2026-09-13 10:10 | ✅ FULLY_CAPTURED (3/3 milestone campionate) |
| `ba190199-8e79-48d7-a5a3-edcfd27929ac` | 52.9 MB | 2026-09-13 10:11 → 2026-09-20 20:42 | ✅ FULLY_CAPTURED (3/3 milestone campionate) |
| `233679d3-2a69-480e-9c2c-4fa40f6f3d49` | 77.6 MB | 2026-09-20 20:42 → 2026-10-02 09:12 | ✅ FULLY_CAPTURED (3/3 milestone campionate) |
| `385240eb-4405-40fa-9552-eeaacd3964c6` | 41.6 MB | 2026-10-02 09:12 → 2026-10-05 19:04 (in corso) | **Sessione corrente/attiva** — non applicabile, non è una candidata di cancellazione |

Più altre sessioni piccole (<350 KB ciascuna, probabilmente test/esplorazioni
brevi) non pesanti e non in scope per questo ledger.

## Metodo di verifica

1. **Correlazione temporale** (`NEXUS_KNOWLEDGE_CONSOLIDATION_AUDIT_V1`):
   per ciascuna delle 3 sessioni nominate, `git log --since --until -- vault/`
   nella finestra esatta della sessione (estratta via
   `grep -o '"timestamp":"[^"]*"'`, non dal primo record JSON che spesso è
   metadata senza quel campo) → 60-79% dei commit in ciascuna finestra
   toccava `vault/`. Nessun segnale di perdita sistemica.
2. **Spot-check di contenuto** (`HEAVY_SESSION_SPOT_CHECK_V1`): 3 milestone
   campionate per sessione (9 totali), verificando che la nota vault
   corrispondente contenga davvero decisione + SHA/evidenza + limiti/rischi +
   prossimo passo (non solo un titolo che corrisponde) — soglia richiesta
   8/9, risultato reale **9/9 FULLY_CAPTURED**.

## Flag `safe_to_delete_candidate`

| Sessione | `safe_to_delete_candidate` | Motivo |
|---|---|---|
| `bdfad6b1...` | `true` | Spot-check 3/3 passato, correlazione commit alta |
| `ba190199...` | `true` | Spot-check 3/3 passato, correlazione commit alta |
| `233679d3...` | `true` | Spot-check 3/3 passato, correlazione commit alta |
| `249dc5ba...` | `false` | **Mai spot-checkato** — solo correlazione temporale indiretta (fa parte della stessa catena continua, ma non è stata verificata a livello di contenuto) |
| `385240eb...` | `false` | Sessione corrente/recente — non ha ancora un ciclo completo di distillazione vault verificato (contiene anche questa stessa consolidazione) |

**`safe_to_delete_candidate=true` non è un permesso di cancellazione.**
Cancellare resta una decisione separata dell'utente, da prendere solo dopo
che questa consolidazione è committata, pushata, verificata su `origin/main`
e Obsidian è stato ripuntato sul vault canonico.

## Path canonico (confermato in questa consolidazione)

`C:\Users\User\ClaudeWork\MAX` è l'unico vault/repo canonico.
`C:\Users\User\Downloads\MAX-main\MAX-main` è una copia ZIP non più
aggiornata — non va più usata, non è stata cancellata.

## Agenti verificati

- **Claude (questa sessione)**: opera su `C:\Users\User\ClaudeWork\MAX`, `origin`
  → `github.com/starmarketkiller/MAX.git`. Allineato.
- **Codex**: ha un remote `origin` separato che punta allo stesso GitHub
  (`starmarketkiller/MAX.git`), quindi può sincronizzarsi — ma la sua working
  copy locale (`C:\Users\User\Documents\Codex\2026-08-05\...\MAX`) è ferma al
  commit `34bbe7f2` del 2026-08-14, **~7 settimane indietro** rispetto a
  `origin/main`. Non vede Funding Framework completo, First Revenue, né i
  milestone Ministral di oggi. **Disallineamento reale, non ipotetico** —
  da segnalare all'utente, non corretto automaticamente qui (non è una
  working copy di questa sessione).
- **Ministral/NEXUS locale**: non ha un proprio concetto di "path canonico
  vault" — riceve solo task bounded via `BoundedLocalTaskHandler`, non
  naviga il filesystem autonomamente. Nessun disallineamento applicabile.
- Nessun `CLAUDE.md`/`AGENTS.md` esiste in questo repository oggi — nessun
  file di configurazione agent-facing da correggere, ma nemmeno uno che
  dichiari esplicitamente il path canonico. Non creato in questa
  consolidazione (fuori dai punti richiesti esplicitamente); se emergesse
  un secondo disallineamento reale, vale la pena introdurne uno minimale.

## Prossimo passo

Nessuna cancellazione. Se in futuro si vuole chiudere il cerchio su
`249dc5ba`, va fatto lo stesso spot-check di contenuto (3 milestone,
soglia 8/9) prima di marcarla `safe_to_delete_candidate=true`.
