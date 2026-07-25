# Conformità ai requisiti normativi NEXUS-*

Il documento master contiene 38 requisiti espressi come obbligo (`MUST`), non
come difetti. Questa matrice dice, per ognuno, **quale controllo concreto lo
rende vero** e **dove vive nel codice** — oppure dichiara apertamente che il
requisito è soddisfatto solo in parte e perché.

Un requisito senza un controllo verificabile non è soddisfatto: dove è così, è
scritto.

Legenda: **Applicato** = esiste un controllo che lo impone e fallisce se
violato · **Parziale** = il controllo esiste ma non copre tutti i casi ·
**Processo** = dipende da una pratica operativa, non solo dal codice.

---

## Architettura

| ID | Requisito | Stato | Controllo |
|---|---|---|---|
| NEXUS-ARCH-001 | Ogni azione eseguibile passa dal percorso comandi canonico | Applicato | Tutte le rotte (dashboard, alias, Coach) passano da `_create_ea_command_from_request` → `nexus_policy.build_command` → `_enqueue_ea_command`. Lato EA ogni apertura passa da `NXS_CommonExposurePreflight`. |
| NEXUS-ARCH-002 | Lo stato confermato dal broker prevale su aspettative interne, AI e UI | Applicato | `EA_TRADE_EVENTS_AUTHORITATIVE` = solo `close`/`resync` scrivono i campi realizzati; `NXS_DoModify` rilegge la posizione; `NXS_DoClose` verifica la post-condizione su `PLACED`; la dashboard distingue `terminal` da `broker_confirmed`. |
| NEXUS-ARCH-003 | Ambienti separati operativamente | Applicato | `environment` nella busta del comando; l'EA rifiuta un ambiente diverso da `InpEnvironment`; `nexus_security.normalize_environment` tratta un valore ignoto come LIVE. |

## Identità e autorizzazione

| ID | Requisito | Stato | Controllo |
|---|---|---|---|
| NEXUS-ID-001 | Identità umane, di servizio, macchina, terminale, EA e AI distinte | Applicato | `operator_audit.actor_type` distingue `human`, `ai_agent`, `service`; EA e worker usano `X-Nexus-Token`, gli umani una sessione JWT; le bozze del Coach sono marcate `AI_RECOMMENDATION`. |
| NEXUS-ID-002 | Autorizzazione basata su capacità e limitata al target | Applicato | Ogni comando porta la tupla di target obbligatoria; il polling filtra per `account_id`+`symbol`; l'EA rifiuta un target che non è il proprio. |
| NEXUS-ID-003 | Le azioni ad alto rischio richiedono step-up | Applicato | `require_stepup` + `POST /api/auth/stepup`: le azioni di classe `PROTECTION` esigono una ri-autenticazione valida 5 minuti. Lato EA, `_nxs_cmd_isSafetyReset` esige conferma, motivo e raffreddamento. |
| NEXUS-ID-004 | Credenziale unica e revocabile per deployment/istanza | **Parziale** | Le licenze sono hashate, revocabili e tracciate (`license_events`). Il token del bridge resta **condiviso** fra le istanze: `InpWebToken` non ha più un default pubblico e la WebSync si spegne senza un token dedicato, ma una credenziale per istanza richiede un registro di enrollment per EA, non ancora presente. |

## Comandi

| ID | Requisito | Stato | Controllo |
|---|---|---|---|
| NEXUS-CMD-001 | Busta canonica: identità, target, ambiente, scadenza, idempotenza, correlazione | Applicato | `nexus_policy.build_command` produce tutti i campi; migrazione `014_command_envelope` li persiste; il GET li restituisce all'EA. |
| NEXUS-CMD-002 | La riconsegna non deve causare doppia esecuzione | Applicato | Lato backend: `idempotency_key` + lease + ACK. Lato EA: insieme durevole dei comandi già eseguiti (`_nxs_cmd_seenStatus`), che risponde con l'esito precedente senza rieseguire. |
| NEXUS-CMD-003 | I comandi scaduti non devono eseguire | Applicato | `_expire_ea_commands` lato backend; controllo di `expires_at` lato EA prima di agire. |

## Rischio e policy

| ID | Requisito | Stato | Controllo |
|---|---|---|---|
| NEXUS-RISK-001 | Nessun percorso bypassa Risk Engine e Policy Engine | Applicato | `nexus_policy.enforce_cap` su ogni rotta che tocca il rischio; `NXS_CommonExposurePreflight` è l'unico varco verso l'esposizione (primario, grid, piramide, istituzionale). |
| NEXUS-RISK-002 | L'incertezza sullo stato blocca nuova esposizione | Applicato | Gate `STATE_UNCERTAIN` nel preflight: ledger degradato, snapshot non ripristinato o indicatori degradati impediscono di aprire. |
| NEXUS-RISK-003 | Le protezioni dure prevalgono su strategia e operatore | Applicato | `NXS_Prot_EntryBlocked` blocca sempre su `g_flattenPending`, anche nel tester; i reset remoti esigono conferma, motivo e raffreddamento. |
| NEXUS-RISK-004 | Sizing ed esposizione calcolati da servizi deterministici | Applicato | `NXS_CalcLotRisk` è puro rispetto allo stato di mercato e restituisce `0.0` (“non aprire”) invece di un lotto di ripiego; i cap vivono in `nexus_policy`. |

## Ciclo di vita del trade

| ID | Requisito | Stato | Controllo |
|---|---|---|---|
| NEXUS-LIFE-001 | Avvio, riconnessione, riavvio e stati ambigui innescano riconciliazione | Applicato | `NXS_Ledger_Boot`, `NXS_Ledger_SweepPending` (timer), `NXS_SyncRecentClosedTrades` con cursore persistente, `NXS_State_Load` + `NXS_State_ReconcileBroker`. |
| NEXUS-LIFE-002 | Ordini, posizioni, parziali e finalizzazione tracciabili a un trade logico | Applicato | Ledger aggregate-diff su `DEAL_POSITION_ID`; registro degli intenti che lega ordine → posizione → sequenza; `sequence_id` propagato al backend. |
| NEXUS-LIFE-003 | Un trade non è finale prima della conferma broker e della riconciliazione | Applicato | `NXS_Ledger_IsClosed` esige volume esaurito **e** posizione assente (per `POSITION_IDENTIFIER`); solo `close`/`resync` scrivono i campi realizzati. |

## Strategie

| ID | Requisito | Stato | Controllo |
|---|---|---|---|
| NEXUS-STRAT-001 | Una strategia attraversa il ciclo di approvazione prima del LIVE | **Processo** | Il registro canonico ha `status` e `live_implementation`, ma il passaggio di stato non è imposto da un gate automatico: resta una decisione umana registrata nel registro. |
| NEXUS-STRAT-003 | L'approvazione LIVE richiede evidenza da limited-live | **Processo** | Stessa natura: l'evidenza esiste (shadow trading, backtest, statistiche per strategia) ma non c'è un gate che la esiga prima di abilitare. |
| NEXUS-STRAT-004 | Una violazione materiale innesca quarantena | Applicato | Moltiplicatore di rischio a `0.0` dal piano di controllo = strategia disattivata (l'apertura viene rifiutata, non ridotta); `strategies_disabled` applicato a runtime. |

## Eventi

| ID | Requisito | Stato | Controllo |
|---|---|---|---|
| NEXUS-EVT-001 | Ogni transizione materiale emette un evento canonico | Applicato | `trade_events` per il ciclo di vita del trade, `command_events` per i comandi, `operator_audit` per le azioni privilegiate, `license_events` per le licenze. |
| NEXUS-EVT-002 | Gli eventi storici non vengono riscritti per nascondere correzioni | Applicato | Trigger `BEFORE UPDATE`/`BEFORE DELETE` su `trade_events` + catena di hash verificabile con `python -m app --verify-ledger`. Una correzione è un evento NUOVO. |

## AI

| ID | Requisito | Stato | Controllo |
|---|---|---|---|
| NEXUS-AI-001 | L'output AI non è stato broker, stato di rischio o evidenza di esecuzione | Applicato | Il Coach produce solo bozze `AI_RECOMMENDATION` con `executed: false`. |
| NEXUS-AI-002 | L'AI non muta direttamente stato live | Applicato | `/api/coach/apply_action` risponde 403 salvo `NEXUS_COACH_ALLOW_ACTIONS`, disattivato per default. |
| NEXUS-AI-003 | Le raccomandazioni portano provenienza, freschezza dei dati e versione di modello/prompt | Applicato | Blocco `provenance` nella bozza: modello, `COACH_PROMPT_VERSION`, versione app, ambiente, età dello stato EA e dell'ultimo trade. |
| NEXUS-AI-004 | L'approvazione si lega ad azione, target e stato di ingresso esatti | Applicato | `binding` = SHA-256 di azione, tipo, strategia, valore proposto, target e freschezza; `binding_expires_at` a 5 minuti. |
| NEXUS-AI-005 | Risk Engine e Policy Engine mantengono il veto finale | Applicato | La bozza non esegue nulla: l'operatore deve passare dalle rotte canoniche, che applicano `enforce_cap` e il contratto dei comandi. Dichiarato nel campo `veto`. |

## Sicurezza

| ID | Requisito | Stato | Controllo |
|---|---|---|---|
| NEXUS-SEC-001 | Preflight fail-closed della configurazione | Applicato | `nexus_security.run_preflight`: in DEMO/PAPER/LIVE una credenziale di default impedisce l'avvio. |
| NEXUS-SEC-002 | Nessun segreto in sorgenti, bundle frontend, log o token condivisi statici | **Parziale** | Rimossi i default pubblici (login, `InpWebToken`, `.env.example` con segnaposto), la CI ha uno scanner di segreti e gli errori non riportano più le risposte dei provider. Resta il token del bridge **condiviso fra istanze**: vedi NEXUS-ID-004. |
| NEXUS-SEC-003 | Gli artefatti di produzione sono firmati e verificati prima dell'attivazione | **Parziale** | Il manifest di deploy porta SHA-256 per file, il worker verifica i digest prima di attivare e fa rollback; la CI verifica il manifest. Manca una **firma** (chiave asimmetrica): oggi l'integrità è verificata, l'autenticità dell'origine no. |

## Operazioni

| ID | Requisito | Stato | Controllo |
|---|---|---|---|
| NEXUS-OPS-001 | I flussi critici producono log, metriche, tracce ed eventi correlati | Applicato | `correlation_id` nella busta del comando, propagato a `command_events` e all'EA; telemetria di salute nel push (impostazioni stantie, indicatori degradati, outbox, flatten pendente). |
| NEXUS-OPS-002 | Un componente non è pronto finché le dipendenze obbligatorie non passano | Applicato | `/api/ready`: scrittura DB, migrazioni, preflight, contratti, artefatti; 503 in caso di fallimento; healthcheck di Docker e Render puntano lì. |
| NEXUS-OPS-003 | Il deployment non è completo finché la verifica continua non riesce | Applicato | CI con `backend-tests`, `security-preflight`, `docker-smoke`, `frontend-build`; `autoDeploy: false` su Render. |
| NEXUS-OPS-004 | Gli incidenti P0/P1 ricevono postmortem e tracciamento correttivo | **Processo** | Non è imponibile dal codice. L'evidenza necessaria esiste (audit append-only, eventi, catena di hash del ledger); il processo di postmortem è responsabilità operativa. |
| NEXUS-OPS-005 | Un backup non è valido finché il restore non è stato provato | Applicato | `nexus_retention.restore_drill`: `drill_passed` è vero solo se `PRAGMA integrity_check` passa **e** i conteggi di riga corrispondono; esposto da `POST /api/admin/backup/drill`. |

---

## Requisiti non pienamente soddisfatti — sintesi onesta

Tre requisiti restano parziali per ragioni strutturali, non per svista:

1. **NEXUS-ID-004 / NEXUS-SEC-002 — credenziale per istanza.** Oggi tutte le
   istanze EA condividono un token. Chiuderlo richiede un registro di
   enrollment per EA (come quello già esistente per gli host LocalBridge) e la
   distribuzione di una credenziale per terminale. È un cambiamento di
   protocollo, non una correzione puntuale.

2. **NEXUS-SEC-003 — firma degli artefatti.** L'integrità è verificata
   (SHA-256 per file, staging e rollback atomici), l'autenticità no. Serve una
   chiave di firma e un punto di fiducia per la chiave pubblica.

3. **NEXUS-STRAT-001 / 003 — ciclo di approvazione delle strategie.** I dati per
   decidere esistono; manca un gate che *impedisca* di abilitare una strategia
   priva di evidenza. È una decisione di prodotto: renderlo bloccante cambia il
   modo di lavorare, non solo il codice.

Quattro requisiti (**NEXUS-OPS-004** e i due sopra) dipendono da pratiche
operative: il codice fornisce l'evidenza, non può imporre il processo.

---

## Finding correlati chiusi da questi stessi controlli

Alcuni finding dell'audit descrivono lo stesso difetto dei requisiti normativi
qui sopra, da un'angolazione diversa. Sono chiusi dagli stessi controlli:

| Finding | Dove è chiuso |
|---|---|
| `AUD0-WEB-001` — comandi distruttivi autenticati dal solo token condiviso | Mitigato: target obbligatorio, ambiente, scadenza, anti-replay durevole, conferma + motivo + raffreddamento per i reset, step-up lato backend, audit locale append-only. **Resta aperta** la credenziale per istanza (NEXUS-ID-004). |
| `AUD0-WEB-011` — la telemetria espone dati sensibili a un endpoint condiviso | Mitigato: `NXS_WebCredentialPreflight` impone HTTPS e un token dedicato (niente più default pubblico), altrimenti la WebSync si spegne. **Resta** l'endpoint condiviso: vedi NEXUS-ID-004. |
| `NXS-CONFIG-001 … NXS-CONFIG-019` — catena di configurazione parallela (`Inp*` / preset / `g_run_*` / profili bloccati / runtime) | Parzialmente chiuso: l'applicazione runtime è ora atomica e validata (`AUD0-SET-001/002/003`), l'ordine di inizializzazione è dichiarato (`AUD0-MQL-011`) e i profili bloccati sono validati contro registro e policy (`AUD0-PROFILE-001`). L'unificazione dei livelli in una sola configurazione effettiva resta una riscrittura non ancora fatta. |
| `NXS-EXP-005` — grid e piramide ereditano solo l'identità del simbolo del grafico | Per costruzione: entrambi operano sul simbolo dell'istanza (`g_sym`), che è anche l'unico su cui l'EA calcola ATR e regime. Il legame alla sequenza è ora esplicito (`group_id` nel registro degli intenti) invece di essere implicito nel commento. Un'estensione multi-simbolo richiederebbe un contesto per simbolo, non presente. |
| `NXS-EXEC-003` — close-and-reverse non passa dal coordinatore | Scelta deliberata e documentata nel codice: la chiusura deve completarsi *prima* dell'apertura opposta nello stesso tick, mentre il coordinatore applica a fine ciclo. Il conflitto è neutralizzato registrando l'azione (`CLOSE_REVERSE`) subito dopo. |
| `AUD0-DEP-001`, `AUD0-DOC-001` | `DEPLOY.md` indica `main` come unica baseline; il README ha la tabella delle cartelle aggiornata e la sezione di precisazioni dell'audit. |
