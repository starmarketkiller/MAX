# Handoff — LOCAL_CODING_APPROVAL_CONTINUATION_01

Revisione distinta. Questo documento non approva il codice e non applica una proposta al repository operativo.

SHA di partenza: `8eae2c6ebf25814fdfab8136045e681e4393a22d`.
Worktree: `C:\Users\User\ClaudeWork\MAX_approval_continuation_8eae2c6`.
Branch: `cursor/local-coding-approval-continuation-01-b2b8`.

`WAITING_APPROVAL` prima di un'approvazione valida resta lo stato corretto.

## Comportamento letto prima della modifica

`FreeCodingWorkerHandler.verify` scrive la proposta solo nella copia di workspace. `apply` restituisce `files_changed` vuoto. L'orchestratore salva `proposed_patch` e passa a `WAITING_APPROVAL` con `approval_effect` `REQUEUE`.

`JarvisService.approval`, per un effetto diverso da `ACCEPT_ONLY`, esegue `transition(task_id, "QUEUED")`. Non controlla tentativo, hash della proposta o hash della baseline e non scrive il progetto. Un `process_task` successivo entra in `_run_local` e può chiamare di nuovo il modello.

La ricerca su `proposed_patch` trova la scrittura del record, la lettura per la review umana e la scrittura nel workspace di verifica. Non c'è un apply sul progetto destinatario.

`Path.write_text` nel workspace, su Windows, traduce `\n` in `\r\n`. Quei byte restano diversi dalla proposta persistita.

## Contratto e policy

Il contratto è in `server/tests/approval_continuation_contract_v1.md`.

Policy fissata prima delle prove: `preserve_proposal_bytes`. La scrittura usa i byte UTF-8 della proposta, senza `os.linesep`.

`proposal_sha256` e `applied_sha256` sono campi separati. Il test li trova uguali perché i byte riletti sono i byte della proposta, 98 byte e zero `CR`. Il file di baseline della fixture resta `264700c5d857c1edddb95cba17e081e5ab7ada7f1a23a3e41031e3cc7b9f56b4`, 98 byte con CRLF. I due digest non vengono dichiarati identici per normalizzazione.

## Difetto e correzione

La prima esecuzione di `tests/test_approval_continuation_v1.py` si è fermata in raccolta: `NEWLINE_POLICY` non esisteva in `free_coding_worker.py`.

La correzione è limitata a `conversational_programming` quando `proposed_patch` contiene il legame catturato da `verify`: tentativo, baseline, digest della proposta e policy. L'approvazione valida chiama `apply_verified_proposal` sulla proposta già salvata. Non costruisce un nuovo prompt e non chiama `call_local_model`.

Un rifiuto per legame, percorso o baseline avviene prima di `write_bytes`. Dopo la scrittura, lo stesso pytest consentito gira nel progetto isolato. Se fallisce, i byte precedenti vengono ripristinati e lo stato diventa `FAILED`, con decisione `FAILED` e senza `application_receipt`. `COMPLETED` e `APPROVAL_GRANTED` arrivano solo dopo scrittura, pytest e ricevuta.

Una proposta di coding senza quel legame, e ogni altro tipo di task, restano su `APPROVE` → `QUEUED`. È il limite che evita di cambiare `proposal_gate`, i task deterministici e le card già coperte da `test_combined_reconciliation_v1.py`. Un legame parziale viene rifiutato e non torna in coda.

`_run_local`, se trova `approval_grant` insieme alla proposta legata, applica il record invece di usare il bridge o il modello.

## Prove

Fixture copiata, non il task `TASK_7079840BBFEB` e non lo store A2:

- sorgente `264700c5d857c1edddb95cba17e081e5ab7ada7f1a23a3e41031e3cc7b9f56b4`, 98 byte
- test `e98023b76671c81832034ab8dce684ce60f5aadc6766d3b06191e6baa21cb36f`, 600 byte
- proposta delle prove `feecd4e53946235ac4c35706bd9f28f13419a2425d75fbf057accfcb349a1806`, 98 byte, zero `CR`

`PYTHONDONTWRITEBYTECODE=1`. Nessuna chiamata a Ollama o a un provider premium: `call_local_model` nelle prove solleva `AssertionError` se viene raggiunto.

Ultima esecuzione, 83 passed in 19.86s:

- `tests/test_approval_continuation_v1.py`
- `tests/test_proposal_approval_gate_v1.py`
- `tests/test_combined_reconciliation_v1.py`
- `tests/test_natural_conversation_v3.py::test_no_regression_on_existing_button_driven_approval`
- `tests/test_executive_state_and_conversation_v1.py::test_interactive_gate_makes_dispatcher_yield_background_work`
- `tests/test_free_coding_worker_routing_v1.py`
- `tests/test_dynamic_specialist_review_v1.py`
- `tests/test_local_agent_bridge_v1.py`
- `tests/test_jarvis_conversational_programming_v1.py`

Casi del contratto coperti dal nuovo file: nessuna scrittura senza approvazione valida; legame su task, tentativo, proposta e baseline; ripresa senza modello; baseline cambiata e percorso non autorizzato rifiutati prima della scrittura; seconda approvazione senza un secondo `FILE_CHANGED`; pytest rosso dopo la scrittura ripristinato e `FAILED`; grant già in coda applicato senza modello; proposta storica senza legame ancora rimessa in coda e senza scrittura; `yield_predicate` interattivo ancora prima di `claim_next`.

La card tardiva con `expected_state` `WAITING_APPROVAL`, a task già `COMPLETED`, restituisce `response_type` `ERROR` e non riscrive il file. Il campo `status` di quella risposta resta lo stato persistito, perché `_state_matches` è condiviso e non è stato modificato.

## Fuori dal perimetro

Il repository operativo e i file estranei del checkout `MAX` non sono stati modificati. `metatester64` risulta ancora presente con PID 5380 e 15776. Nessun merge, deploy o attivazione remota. I criteri C01–C20 non sono stati modificati. La proposta non è stata applicata al repository di lavoro.
