# LOCAL_CODING_APPROVAL_CONTINUATION_01

SHA di partenza: `8eae2c6ebf25814fdfab8136045e681e4393a22d`.

`WAITING_APPROVAL` prima di un'approvazione valida non è un errore.

## Comportamento attuale

Per `conversational_programming`, `verify` scrive la proposta solo nella copia di workspace. `apply` restituisce `files_changed` vuoto e `proposal_only`. Il record va in `WAITING_APPROVAL` con `approval_effect` `REQUEUE` e `proposed_patch`.

`JarvisService.approval`, se l'effetto non è `ACCEPT_ONLY`, esegue `transition(task_id, "QUEUED")`. Non controlla tentativo, hash della proposta o hash della baseline e non scrive il progetto.

Un `process_task` successivo entra in `_run_local` e chiama di nuovo il modello. Nessun percorso legge `proposed_patch` per applicarlo ai file autorizzati. I task deterministici e il bridge usano lo stesso `REQUEUE`, ma questo contratto non cambia il loro comportamento.

`Path.write_text` sul verifier di workspace traduce `\n` in `\r\n` su Windows. Quei byte non sono la proposta persistita.

## Policy LF/CRLF

`preserve_proposal_bytes`: i byte applicati sono l'UTF-8 del contenuto della proposta, senza traduzione `os.linesep`.

`proposal_sha256` è SHA-256 dei contenuti della proposta, in ordine di percorso e uniti da un byte NUL quando i file sono più di uno. `applied_sha256` usa la stessa costruzione sui byte riletti dal progetto. I due valori restano campi distinti e sono uguali solo se quelle sequenze di byte sono uguali. Una somiglianza dopo normalizzazione non è identità.

`baseline_sha256` riassume i digest dei file di destinazione prima della scrittura. Non è il digest della proposta.

## Contratto atteso

1. Senza approvazione valida, il progetto destinatario non cambia.
2. L'approvazione è legata a task, tentativo, hash della proposta e hash della baseline.
3. La ripresa usa la proposta verificata e non chiama un modello.
4. Baseline o proposta diverse: rifiuto prima di qualunque scrittura.
5. Si scrivono solo percorsi autorizzati, dentro il progetto isolato.
6. Una seconda richiesta non ha un secondo effetto.
7. `COMPLETED` arriva solo dopo scrittura e pytest consentito, con ricevuta persistita. Un errore non è un completamento.

La continuazione vale solo per `conversational_programming` quando `proposed_patch` contiene già il legame (`proposal_sha256`, `baseline_sha256`, `newline_policy`, `attempt`, `baselines`). Gli altri tipi di task, e le proposte di coding persistite prima di questo legame, restano sul `REQUEUE` esistente. Un legame parziale viene rifiutato prima della scrittura.

Il binding che autorizza la scrittura è `approval-continuation-binding-v2`: schema, percorso e contenuto di ogni file, con lunghezze esplicite. `proposal_sha256` resta il digest del solo contenuto. Un'approvazione che porta solo quel digest non scrive; serve un messaggio nuovo con lo schema v2.

Nello stesso processo un lock copre controllo, scrittura, verifica, rollback e finalizzazione del task. Due processi distinti non condividono quel lock. Il recupero dopo un riavvio usa `application_intent` sulla coda, non una seconda coda, e non chiama un modello.
