# NEXUS MASTERPLAN V4.1 — Independent Review (4 livelli)

**Stato: PROPOSTA, non implementata.** Formalizza e numera i 4 livelli richiesti dalla task (sez.11), riusando componenti già reali invece di inventarne di nuovi. Contratto: [`contracts/nexus-independent-review-v1.schema.json`](../contracts/nexus-independent-review-v1.schema.json). Estende [NEXUS_MASTERPLAN_V4_INDEPENDENT_REVIEWER_MODEL.md](NEXUS_MASTERPLAN_V4_INDEPENDENT_REVIEWER_MODEL.md) (già proposto in V4 per il ciclo di self-improvement) ai workflow in generale, non solo agli esperimenti di miglioramento.

## I 4 livelli, cosa sono davvero e cosa li implementa già oggi

| Livello | Nome | Chi/cosa verifica | Componente reale già esistente |
|---|---|---|---|
| **L0** | Schema/invariant | Un validatore deterministico, nessuna logica di dominio | `contracts/validate_registry.py`, qualunque validazione JSON Schema contro `contracts/*.schema.json` (64 file già reali) |
| **L1** | Verifica di dominio | Il verificatore del task stesso (regole specifiche al tipo di lavoro) | `core/result_packet.py`'s `verifier:{ran,passed,errors}`, `FreeCodingWorkerHandler.verify()`, `BoundedLocalTaskHandler.verify()`, `compliance_check()` dell'Agency |
| **L2** | Revisione indipendente | Produttore e verificatore sono processi distinti, mai lo stesso agente che valuta se stesso | `finalization_gate.py` (scansione segreti pre-FINALIZED, già reale e non bypassabile) — da generalizzare al confronto baseline-vs-variante per il self-improvement |
| **L3** | Approvazione umana | Per azioni ad alto rischio — spesa, pubblicazione, trading live, modifiche a `HIGH_PATHS` | `classify_deploy_risk.py`+`evaluate_auto_approval.py` (deploy), gate di approvazione crediti dell'Agency, `unified_approvals()` di Jarvis |

**La scoperta chiave**: NEXUS **ha già tutti e 4 i livelli**, ma sparsi per sistema specifico (deploy, agency, task generico) senza un contratto comune che li renda interoperabili e visualizzabili in un unico posto (il Visual Operations Center). Questo documento non inventa una nuova capacità — la rende un'interfaccia comune.

## Regola non negoziabile

**Nessun agente può modificare i propri permessi o il proprio sistema di validazione e dichiararsi autonomamente sicuro.** Già vero oggi per il deploy (`evaluate_auto_approval.py` valuta sempre la versione pre-commit del file, mai quella che il commit stesso propone) — questo principio va esteso esplicitamente a ogni L2/L3 futuro, non solo al deploy.

## Verdetti (già usati nel contratto)

`PASS | REVISION_REQUIRED | REJECTED | BLOCKED` — stessa semantica già implicita in `finalization_gate.py` (passa/blocca) e nei gate a `ValueError` dell'Agency (equivalenti a REJECTED), ora esplicitata in un vocabolario comune.

## Come un workflow dichiara il livello richiesto

`NEXUS_WORKFLOW_DEFINITION_V1.verifier_policy.required_level` (contratto già proposto in questa sessione) — un reparto può dichiarare "questo nodo richiede almeno L2" senza dover reinventare come L2 funziona.

## Cosa NON fa questo documento

Non sostituisce `finalization_gate.py`, `classify_deploy_risk.py`, o nessun verificatore di dominio esistente. Non implementa un nuovo motore di revisione. Propone solo il vocabolario comune (`NEXUS_INDEPENDENT_REVIEW_V1` come forma di output) che li rende leggibili in modo uniforme da Jarvis e dal Visual Operations Center.

## Checklist prima di implementare
- [ ] Conferma utente sul design.
- [ ] Nessuna modifica a `finalization_gate.py`/`classify_deploy_risk.py`/`evaluate_auto_approval.py` — solo un adattatore che ne proietta l'esito nella forma comune.
- [ ] Il reparto pilota del self-improvement ([NEXUS_DISTRIBUTED_SELF_IMPROVEMENT_V1.md](NEXUS_DISTRIBUTED_SELF_IMPROVEMENT_V1.md)) è anche il primo a usare L2 in questa forma comune.
