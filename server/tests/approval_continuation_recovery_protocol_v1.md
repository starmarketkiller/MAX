# Protocollo di recupero — LOCAL_CODING_APPROVAL_CONTINUATION_FIX_01

Scritto dopo la riproduzione e prima della correzione. I riproduttori originali sono in `server/tests/review_reproducers/` e restano invariati. Puntano al checkout `C:\Users\User\ClaudeWork\MAX_approval_review_b0a55c6`, commit `b0a55c622dd3730f81def1f8dba2d01b7f229182`.

## Riproduzione

Eseguiti il 8 novembre 2026 sul codice non corretto. `model_calls` 0.

`independent_review_probe.py` ha riportato sei esiti rossi su dodici. I quattro finding sono questi.

1. `proposal_digest` di due associazioni diverse con un NUL nel contenuto è lo stesso hash `53ed652b4592f06630f82d6b58598aa4d93bc479897bf5d85faf43b57d4b6b2b`. L'approvazione scrive l'altra associazione e chiude `COMPLETED` con i due hash della ricevuta uguali.
2. `race_barrier_probe.py`: la prima risposta è `COMPLETED` con ricevuta `feecd4e53946235ac4c35706bd9f28f13419a2425d75fbf057accfcb349a1806`. La seconda solleva `COMPLETED -> FAILED`. Il file riaperto è la baseline `264700c5d857c1edddb95cba17e081e5ab7ada7f1a23a3e41031e3cc7b9f56b4`.
3. Errore di ledger dopo `FILE_CHANGED`, e errore di transizione dopo `TASK_COMPLETED`: il file è la proposta, lo stato riaperto resta `WAITING_APPROVAL`, la ricevuta è assente. Il retry dell'errore di ledger resta `WAITING_APPROVAL` con `baseline changed`.
4. Rollback con `OSError`: l'eccezione esce, lo stato resta `WAITING_APPROVAL`, `dispatch_last_error` è assente, il file è la proposta.

Lo scambio `ONE`/`TWO` senza collisione, il pytest reale su due file, il requeue legacy, l'isolamento fra due task e il fallimento della seconda scrittura con restore verificato erano già verdi.

## Esiti attesi dopo la correzione

1. Nello stesso processo un solo apply occupa controllo, scrittura, verifica, rollback e finalizzazione. La richiesta che arriva dopo trova `COMPLETED` e non ripristina i file. Due processi distinti non condividono questo lock: è un limite dichiarato, non una garanzia.
2. Prima della prima scrittura il record della coda contiene `application_intent` con schema, task, tentativo, percorsi, hash di baseline, hash di contenuto e hash di binding. Dopo la riapertura si osservano i file. Tutti alla proposta: si rieseguono i test e solo allora si scrive la ricevuta e `COMPLETED`. Tutti alla baseline: si completa lo stesso intento. Misti, diversi o illeggibili: nessun write, nessun `COMPLETED`, nessun modello. Nessuna seconda coda.
3. Un rollback fallito non viene dichiarato riuscito. Per ogni file restano esito, hash riletto, oppure `UNKNOWN` se la rilettura fallisce. Lo stato non è `COMPLETED`. Un retry non riapplica da solo un recupero ambiguo.
4. Il binding autorizzativo è `approval-continuation-binding-v2`: per ogni file, lunghezza del percorso, percorso, lunghezza del contenuto, contenuto. I percorsi duplicati sono rifiutati. `proposal_sha256` resta il digest di contenuto già asserito dai test esistenti. Un'approvazione che porta solo quel digest vecchio non applica. Serve un messaggio nuovo con lo schema v2 e il suo hash.

## Recupero operativo

Si riusano `TaskQueue.annotate` e `EventLedger`. L'intento sulla coda è la fonte dopo un riavvio. Un evento `TOOL_USED` con tool `approval_continuation_intent` è solo audit: se il ledger fallisce, l'intento sulla coda basta.

Alla riapertura non si chiama un modello e non si riscrive una proposta già presente sui file senza prima rileggere gli hash e senza un pytest consentito con uscita 0. `COMPLETED` senza ricevuta non è un esito del recupero.
