---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, audit, sicurezza, remediation]
created: 2026-07-25
updated: 2026-07-25
---

# NEXUS EA — remediation dell'audit master v18

Revisione completa di `docs/NEXUS_MASTER_PROJECT.md` (15.489 righe, 310 identificatori
di finding) e implementazione nel codice. **Unita in `main` il 25/07/2026**:
13 commit, avanzamento lineare da `ef807ab` a `3cf2b3b`.

**Sì, il codice è stato modificato davvero** — non è un lavoro di sola
documentazione. Sotto c'è cosa è cambiato, e soprattutto cosa cambia nel
comportamento osservabile.

## Stato

| | |
|---|---|
| Identificatori del master document | 310 |
| Citati nel repository dove vive la correzione | 310 (100%) |
| Test automatici backend | 211 passati, 1 saltato (erano 129) |
| Compilazione MetaEditor | **mai eseguita** — vedi sotto |
| Strategy Tester | **mai eseguito** — vedi sotto |
| Stato produzione | **NO-GO** (invariato) |

> **"Citato al 100%" non vuol dire "risolto al 100%".** Un identificatore è citato
> perché la correzione è implementata e testata (la maggioranza), oppure perché il
> difetto è mitigato con il residuo dichiarato, oppure perché non è risolvibile
> qui e la nota lo dice. Il dettaglio per ognuno è in `docs/REMEDIATION_STATUS.md`
> e `docs/NORMATIVE_CONFORMANCE.md`.

## Il limite più importante

**Niente di ciò che riguarda `MQL5/` è stato compilato né fatto girare.** In questo
ambiente non ci sono MetaEditor né Strategy Tester. La verifica fatta è statica:

- bilanciamento di graffe/parentesi su tutti i 67 file, confrontato con lo stato
  precedente per escludere regressioni;
- unicità delle definizioni di ogni simbolo nuovo;
- ordine di dichiarazione fra moduli (l'inclusione MQL5 è testuale: l'ordine conta);
- coerenza con il registro canonico delle strategie.

È una rete robusta contro gli errori grossolani. **Non sostituisce la compilazione.**
Il primo passo dell'agente desktop è compilare — vedi
[[TODO - Agente Desktop (consegna remediation)]].

## I difetti più gravi corretti

Non l'elenco completo (è nel repository), ma quelli che avrebbero potuto costare
denaro reale.

### Capitale

- **Protezioni di conto che chiudevano un solo simbolo.** ESL, DPT e lo scudo di
  ruin calcolano le soglie sull'equity del **conto**, ma chiudevano solo le
  posizioni del simbolo del grafico. Su un conto multi-simbolo: l'equity scende
  sotto il limite, l'istanza su XAUUSD appiattisce XAUUSD e si ferma, e le
  posizioni su BTC, EUR e indici **restano aperte** con la stessa equity che
  continua a scendere.
- **Rischio offline del Virtual SL.** Il lotto era dimensionato sullo stop
  *logico*, ma al broker arriva uno stop più largo. Lo stop logico vale solo
  finché l'EA gira: a terminale spento la perdita reale è quella del broker. Ora
  il caso peggiore è calcolato sullo stop realmente inviato e ha un tetto.
- **`TRADE_RETCODE_PLACED` contato come esecuzione.** Aperture, chiusure, parziali
  e modifiche venivano dichiarate riuscite su una risposta che significa
  "accettato", non "eseguito".
- **`NXS_DoModify` non verificava nulla.** Breakeven e trailing credevano di aver
  protetto la posizione mentre il broker poteva aver applicato un valore diverso —
  o nessuno. Ora rilegge la posizione e conferma.
- **Equity breaker mai alimentato.** Difetto **non presente nell'audit**, trovato
  leggendo: `NXS_RS_Breaker_Check()` non era chiamato da nessuna parte del
  progetto. Il gate esisteva in `NXS_RS_BlockEntry`, ma `g_NXSrsBreakerUntil`
  restava a zero per sempre: una protezione documentata e **completamente inerte**.

### Dati e ricerca

- **La R veniva inventata.** Quando il rischio iniziale non era ricostruibile, ogni
  esito positivo diventava +1R e ogni negativo −1R. Una perdita da 5R e una da 0.2R
  finivano entrambe a −1R, e sopra ci giravano expectancy, win rate in R e ranking
  delle strategie. Ora un trade senza rischio noto è **escluso** dalle statistiche
  in R, non convertito in un numero comodo.
- **Chiave primaria dei trade collidibile fra conti.** `trades.ticket` era la
  chiave: due conti sullo stesso backend con lo stesso numero di posizione **si
  sovrascrivevano a vicenda**, senza errore. Ora la chiave è `(account_id, ticket)`.
- **Ledger append-only solo a parole.** Era una convenzione scritta nei commenti.
  Ora ci sono trigger che abortiscono `UPDATE` e `DELETE`, più una catena di hash
  che rileva una manomissione fatta aggirando i trigger. Si verifica con
  `python -m app --verify-ledger`.
- **Identità dal commento della posizione.** MT5 tronca i commenti a 31 caratteri e
  alcuni broker li riscrivono. Strategia, rischio, timeframe e gruppo venivano tutti
  dedotti da lì. Nuovo modulo `NXS_Intent.mqh`: registra strategia, budget di
  rischio, ATR e sequenza **al momento dell'invio**, quando sono fatti e non
  deduzioni.

### Sicurezza

- **Credenziali di default** rimosse ovunque; il backend rifiuta di avviarsi in
  DEMO/PAPER/LIVE se ne trova. ⚠️ Ma il bundle distribuito le contiene ancora —
  vedi [[NEXUS EA - Igiene Repository e Duplicati]] §5.
- **Esecuzione shell arbitraria rimossa** dal worker LocalBridge.
- **Step-up per disarmare le protezioni.** Azzerare ESL/DPT era autorizzato dallo
  stesso cookie valido 12 ore: provava che qualcuno si era autenticato stamattina,
  non che fosse la stessa persona adesso. Ora serve reinserire la password.
- **Ambiente nella busta del comando.** Un backend condiviso serve istanze DEMO e
  LIVE: senza quel campo, un comando prodotto guardando una dashboard DEMO poteva
  essere eseguito da un'istanza LIVE con lo stesso conto e simbolo.

### Comportamento dell'EA

- **Nessuna rete sul percorso del tick.** `NXS_PullSettings()` faceva una
  `WebRequest` con timeout 3 s dentro `OnTick`: in quella finestra non giravano
  Virtual SL, protezioni e `OnTradeTransaction`.
- **`OnInit` non attende più la rete.** Push iniziale e riconciliazione di 7 giorni
  partivano bloccanti all'aggancio dell'EA al grafico.
- **Nuovo `NXS_Outbox.mqh`**: le consegne HTTP fallite finiscono in una coda su
  file drenata dal timer, invece dei ritentativi con `Sleep()` che bloccavano il
  thread fino a ~63 secondi **subito dopo una chiusura di protezione**.

## Cosa resta dichiaratamente aperto

Tre requisiti sono **parziali** e sono scritti come tali in
`docs/NORMATIVE_CONFORMANCE.md`:

1. **Credenziale per istanza** (`NEXUS-ID-004`) — tutte le istanze EA condividono
   un token. Chi lo possiede può impersonare qualunque EA. Serve un registro di
   enrollment per EA: è un cambio di protocollo.
2. **Firma degli artefatti** (`NEXUS-SEC-003`) — l'integrità è verificata (SHA-256
   per file), l'autenticità dell'origine no.
3. **Gate di approvazione delle strategie** (`NEXUS-STRAT-001/003`) — i dati per
   decidere esistono, manca un blocco che *impedisca* di abilitare una strategia
   priva di evidenza. È una decisione di prodotto.

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Igiene Repository e Duplicati]] ·
[[DEC - Cambi di comportamento post-remediation]] ·
[[TODO - Agente Desktop (consegna remediation)]] · [[NEXUS EA - Principi]] ·
[[NEXUS EA - Log Versioni]]
