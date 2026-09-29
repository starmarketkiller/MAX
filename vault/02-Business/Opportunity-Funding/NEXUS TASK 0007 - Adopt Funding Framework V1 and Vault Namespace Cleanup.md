# NEXUS TASK #0007 — Adopt Funding Framework V1 + Vault Namespace Cleanup

**Baseline:** `7dafeae`. Dipendenze: #0005, #0006. Task di **governance/housekeeping**, non di design: promuove lo stato del framework e riorganizza il namespace Vault, senza toccare scoring/gate/dataset.

## Obiettivo

Adottare ufficialmente `FUNDING_FRAMEWORK_V1_READY_FOR_ADOPTION` (deciso in #0006) come framework canonico, e correggere un problema strutturale segnalato dall'utente: il Vault report di #0005/#0006 era finito sotto `01-Trading/`, ma il framework non è trading-specifico — riguarda qualunque opportunity di business.

## Azioni eseguite

1. **Promozione di stato**: `WAITING_APPROVAL` → `ADOPTED`, registrato come artifact machine-readable (`server/funding_v1/framework_adoption_decision_v1.json`), non solo come nota Vault — così un verificatore può controllarlo, non solo leggerlo.
2. **Namespace Vault**: creato `vault/02-Business/Opportunity-Funding/` (sotto il dominio Business già esistente, non un nuovo namespace di primo livello — coerente con la numerazione `00-Inbox`/`01-Trading`/`02-Business`/`03-Social`/`04-System` già in uso). Spostati i report #0005 e #0006 con `git mv` (rename vero, storia preservata, nessun duplicato) + nuovo sub-MOC `MOC - Opportunity and Funding.md`, linkato da `MOC - Business.md`.
3. **Bug reale trovato durante l'esecuzione**: `server/knowledge_browser.py` (l'indice read-only consultato da Jarvis/Control Plane) aveva `ALLOWED_ROOTS` **hardcoded solo su `vault/01-Trading/`** — spostare i report li avrebbe resi silenziosamente invisibili all'indice. Aggiunta una seconda root (`vault-business` → `vault/02-Business/`), con test dedicato che verifica sul repo reale che entrambi i titoli restino indicizzabili dopo lo spostamento.
4. **Integrità verificata per hash, non per dichiarazione**: l'artifact di adozione congela lo SHA256 di ogni file di logica (`opportunity_scoring.py`, `hard_gates.py`, `capital_scenarios.py`, `capability_coverage.py`, `opportunity_lifecycle.py`, `self_funding_loop.py`, `opportunity_assembly.py`) e il `canonical_sha256` di ogni artifact dati (opportunities, priority queue, brief, lifecycle, self-funding-loop) al momento dell'adozione. Il verificatore indipendente ricalcola entrambi da zero e fallisce se anche un solo byte è cambiato — rende "nessuna modifica a scoring/gate/dataset" un fatto verificabile, non una promessa in prosa.

## Perché non un nuovo namespace di primo livello

L'utente aveva proposto anche `vault/Businesses/Opportunity/` o `vault/Projects/Funding/`. Scelto invece `vault/02-Business/Opportunity-Funding/` perché il namespace `02-Business` **esiste già** (con la stessa convenzione numerata degli altri 4 domini) — creare un quinto namespace parallelo avrebbe frammentato la futura Global Vault architecture invece di prepararla.

## Deliverables

`server/funding_v1/build_framework_adoption_decision.py` + `framework_adoption_decision_v1.json`, `server/orchestrator_v1/verify_nexus_task_0007.py`, fix a `server/knowledge_browser.py` (ALLOWED_ROOTS), `server/tests/test_knowledge_browser.py` (+1 test), `server/tests/test_funding_v1.py` (+1 test), `vault/02-Business/Opportunity-Funding/` (2 report rinominati + questo report + sub-MOC), `vault/02-Business/MOC - Business.md` (aggiornato).

## Regressione

`verify_nexus_task_0007.py`: **PASSED** (adozione registrata, hash di logica/dataset bit-per-bit invariati, rename senza duplicati, knowledge_browser aggiornato, `test_funding_v1.py` incluso). `test_funding_v1.py`: 22/22. `test_knowledge_browser.py`: 11/11 (10 preesistenti + 1 nuovo).

## Decisione finale

**`FUNDING_FRAMEWORK_V1_ADOPTED`**. Nessuna nuova opportunity, nessuna modifica a score/gate, nessuna azione commerciale, nessuna chiamata premium automatica. Il framework è ora canone per Jarvis/futuri task NEXUS.

## Prossimo passo (non ancora una NEXUS TASK)

Uso reale del framework su un'opportunity concreta, a partire da quelle con miglior rapporto time-to-cash/capitale/capability coverage — sempre partendo dal `next_cheapest_validation_step` dichiarato, mai un'azione commerciale reale senza approval esplicita.
