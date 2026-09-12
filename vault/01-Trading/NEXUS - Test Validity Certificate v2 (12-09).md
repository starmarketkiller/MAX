# NEXUS — Test Validity Certificate v2

Roadmap 95/99, QUANTITATIVE INTEGRITY. Obiettivo: ogni run di Research Mode produce automaticamente un certificato che dichiara se il test è affidabile o no.

## Stato: implementato, testato, e corretto con patch identità/provenienza (12/09) — 2 PASS reali (ADX_RSI, MACD) + 1 FAIL sintetico + regression 2x ADX_RSI

## Patch 12/09: run identity + code provenance (approvata dopo il primo giro)

Il classificatore/funnel/logica trading **non sono stati toccati** — solo identità del run e provenienza codice, su richiesta esplicita.

**1. `run_id` vs `config_fingerprint` separati.** Prima: `run_id = Symbol_TimeCurrent(OnInit)_selN` poteva ancora collidere fra due esecuzioni della STESSA strategia sullo STESSO periodo (scoperto rilanciando lo stesso test ADX_RSI due volte per la regression di questo stesso fix). Ora:
- `run_id`: univoco per OGNI esecuzione. `NXS_Cert_MakeUniqueRunId(base)` verifica se un certificato per `base` esiste già su disco e, se sì, prova `base_r001`, `base_r002`, ... finché non trova un nome libero (collision avoidance dichiarata — MQL5 non offre una wall-clock affidabile in Tester per distinguere passate ravvicinate).
- `config_fingerprint`: deterministico per CONFIGURAZIONE riproducibile, non per esecuzione. Stringa leggibile (non un hash — "non serve crittografia forte, serve stabilità e leggibilità", richiesta esplicita): `strat|sel|srcTF|entryTF|exit|lot|lev|ESL|DailyDD|TotalDD|DPT|Ruin|RiskShield|period`. Il componente periodo usa `g_certPeriodStart/End` (range osservato dai tick, granularità giorno) perché MQL5 non espone un modo diretto di leggere FromDate/ToDate configurati nel Tester dall'interno dell'EA — dichiarato come tale nel codice.

**Bug scoperto TESTANDO il fix stesso**: la sandbox `MQL5\Files` di un agente Tester viene ripulita ad ogni nuovo avvio di `terminal64.exe` — lanciare due volte la stessa passata (due processi separati) non faceva mai vedere al secondo run i certificati scritti dal primo, quindi `FileIsExist` falliva sempre silenziosamente (nessun suffisso mai aggiunto). Fix: entrambi il controllo di esistenza e la scrittura usano `FILE_COMMON` (`Common\Files`, terminal/agente-indipendente — su questa macchina risolve in `%APPDATA%\MetaQuotes\Terminal\Common\Files`, **non** ridiretto dentro la cartella portable nonostante `/portable`), l'unico posto in cui un run successivo può vedere davvero i certificati di un run precedente.

**2. Code provenance.** Aggiunto `InpBuildGitCommit` (input string, default `"UNKNOWN"`) — nessun processo di build in questo repo stampa automaticamente lo SHA git dentro il `.mq5` a compile-time, quindi niente da leggere a runtime. Approccio scelto fra i due proposti: **campo esplicito UNKNOWN con nota di provenienza** (non un build-constant popolato a mano, che diventerebbe stantio esattamente come il problema che questo task vuole risolvere). Mai confuso con `NEXUS_VERSION`/`code_build` (quello resta un numero di build applicativo). La nota di provenienza è puramente informativa nel testo/JSON del certificato — **non** passa per `NXS_Cert_Classify` e non altera mai PASS/FAIL/WARNINGS (vincolo esplicito "non cambiare classificatore").

**3. Output.** TXT e JSON ora includono `run_id`, `config_fingerprint`, `code_build`, `git_commit` (+ `git_commit_provenance` nel JSON: `"declared_via_InpBuildGitCommit"` o `"unavailable_at_runtime_no_build_stamping"`).

**4. Regression — due run identici ADX_RSI, stesso `.ini`, stesso periodo:**

| run | run_id | config_fingerprint | verdict |
|---|---|---|---|
| 1 | `GOLD_2026.06.01 00:00:00_sel1` | `strat=ADX_RSI\|sel=1\|srcTF=PERIOD_D1\|entryTF=PERIOD_M15\|exit=RAW\|lot=0.0200\|lev=100\|ESL=0\|DailyDD=0\|TotalDD=0\|DPT=0\|Ruin=0\|RiskShield=0\|period=2026.06.01_2026.06.12` | PASS |
| 2 | `GOLD_2026.06.01 00:00:00_sel1_r001` | *identico al run 1* | PASS |

Due `run_id` diversi ✓, `config_fingerprint` identico ✓, entrambi i certificati presenti su disco ✓, nessuna sovrascrittura ✓, entrambi PASS ✓. MACD non ri-testato (nessuna modifica alla classificazione, come da istruzione).

Compilato dopo la patch: **0 errori**, 2 warning preesistenti invariati. Live Mode invariato.

## Stato precedente alla patch (per riferimento storico)

**Fonte primaria: [[NEXUS - Decision-Gate-Execution Trace v1 (12-09)]]** — non ri-analizza il Journal (MQL5 non può farlo in modo affidabile a runtime): `NXS_Trace_Emit` aggiorna i contatori del certificato (`g_cert*`, in `NXS_Trace.mqh`) nello stesso momento causale in cui stampa la riga di trace. Stessa fonte, nessuna seconda verità che possa divergere (vedi CAUSAL_HOOK_MISMATCH, Failure Memory 12/09).

## Architettura

Nuovo file `MQL5/Include/NEXUS_v1/NXS_TestValidityCertificate.mqh`, incluso dopo `NXS_ResearchMode.mqh` e `NXS_BlockerDiagnostics.mqh` (dipende da entrambi).

**Design deliberato: il classificatore è puro.** `NXS_Cert_Classify(const SNxsCertInput &in, string &failReasons, string &warnReasons)` non legge nessuna variabile globale — prende una struct di contatori/metadati e ritorna un verdetto. Questo permette di testarlo con un funnel sintetico e deliberatamente rotto (`NXS_Cert_RunSyntheticTest`, dietro l'input debug `InpCertRunSyntheticTest`, default false) senza eseguire nessuna passata di Tester reale e senza toccare la logica di trading.

`ENUM_NXS_CERT_VERDICT { CERT_PASS, CERT_PASS_WITH_WARNINGS, CERT_FAIL }`.

## Regole di classificazione

FAIL automatico se una qualsiasi di queste è vera:

| Check | Condizione FAIL |
|---|---|
| MISSING_TELEMETRY | trace non attivo o zero righe di trace emesse |
| FUNNEL_NOT_RECONCILED | `generated != blocked + opened + broker_reject` |
| OPENED_MISSING_POSITION_ID | una riga OPENED con `position_id=0` |
| BROKER_REJECT_MISSING_REASON | una riga BROKER_REJECT con `detail` vuoto |
| UNEXPECTED_EXIT_AUTHORITY_IN_RAW | `[RESEARCH][INVARIANT_FAIL]` > 0 in un run RAW (EXPERT_UNKNOWN o autorità di uscita non opt-in — invariante già implementato in `NXS_ResearchMode.mqh`, qui solo contato) |
| SOURCE_TF_MISMATCH | la stessa strategia dichiara `source_tf` diversi tra due GENERATED |
| SELECTOR_MISMATCH | il nome dichiarato (`NXS_ResearchSelectorName(InpStrategySelector)`) diverge da quanto osservato nella prima riga GENERATED — **solo se il nome dichiarato non è un fallback** `selector_N` (quella lookup non è autorevole, vedi commento nel suo stesso file: se il selector non è nella sua switch, è trattato come INDETERMINATO/WARNING, non FAIL) |

PASS_WITH_WARNINGS (non invalidante):

| Check | Condizione |
|---|---|
| REGISTRY_LOOKUP_INDETERMINATO | selector non presente in `NXS_ResearchSelectorName` — nome non verificabile ma non prova nulla di rotto |
| POSSIBLE_TEST_TRUNCATION | `BLK_PAUSED` (`NXS_BlockerDiagnostics.mqh`) > 0 — **proxy euristico dichiarato**, non un meccanismo diretto. MQL5 non espone un modo affidabile per rilevare "la passata di Tester è finita prima del previsto per uno stop-out/margin call reale" — dichiarato come limite noto invece di inventare un FAIL che potrebbe essere falso positivo (principio generale della Failure Memory 12/09: mai inventare quando manca un meccanismo diretto) |

`broker_time_offset` (`InpServerGMTOffset`) è **sempre** dichiarato nel certificato (esiste sempre come input, default 2 = CEST) — per questa implementazione non esiste quindi un caso di "ambiguità di broker-time non dichiarata" che possa far scattare FAIL da solo.

## Campi del certificato

`run_id, strategy, selector, source_tf, entry_tf, period_start, period_end, research_mode, exit_mode(RAW/RECIPE), leverage, lot_mode+fixed_lot, opt_in{risk_shield,esl,daily_dd,total_dd,ruin,dpt}, code_build, broker_time_offset_h`, funnel `{generated,blocked,open_attempt,opened,broker_reject}`, `gate_reason_counts{...}`, anomalie, `verdict`, `fail_reasons`, `warnings`.

`period_start`/`period_end` sono il range dati **effettivamente attraversato dai tick** (`TimeCurrent()` min/max osservato in `OnTick`, via `NXS_Trace_TouchPeriod()`), non l'orario di lancio del run.

Output: `.txt` leggibile + `.json` machine-readable, entrambi in `MQL5/Files/NEXUS/certificates/<run_id_sanitizzato>.txt|.json` (sandbox dell'agente Tester), più un riepilogo compatto `[CERT][SUMMARY]` nel Journal a fine `OnDeinit`.

## Bug scoperto e corretto durante il test: run_id collideva fra run diversi

Prima versione: `run_id = Symbol_TimeCurrent(OnInit)`. In Strategy Tester, `TimeCurrent()` in `OnInit` è il tempo **simulato** di inizio periodo, non wall-clock — due run con stesso `Symbol`/`FromDate` (es. ADX_RSI e MACD, entrambi 2026.06.01-06.15) producevano lo **stesso run_id**, quindi il certificato del secondo sovrascriveva il file del primo sul disco (scoperto lanciando i due test PASS in sequenza: il file del primo run era sparito, sostituito dal secondo). Fix: `InpStrategySelector` (sempre >0 e univoco per run in Research Mode) aggiunto al run_id — niente wall-clock, così il run_id resta riproducibile fra passate identiche dello stesso test, ma univoco fra strategie diverse.

## Compile e test

Compilato: **0 errori**, 2 warning preesistenti invariati.

**PASS reali** (stesso Fast Smoke 2026.06.01-06.15, GOLD H4, leva 500, usato per Trace v1):

| Strategia | GENERATED | BLOCKED | OPENED | Verdict |
|---|---|---|---|---|
| ADX_RSI (sel=1) | 118 | 117 (OPEN_POSITION) | 1 | **PASS** |
| MACD (sel=3) | 483 | 481 (OPEN_POSITION) | 2 | **PASS** |

Entrambi riconciliano esattamente come Trace v1 (stessi numeri). Nota non bloccante: `leverage` nel certificato riporta `1:100` mentre l'`.ini` del Tester dichiarava `Leverage=500` — il certificato legge `AccountInfoInteger(ACCOUNT_LEVERAGE)` **a runtime**, cioè quello che il conto ha *davvero*, non quello che il file di config intendeva impostare. Comportamento corretto per uno strumento di integrità (dichiara la realtà osservata, non l'intenzione) — segnalato qui perché è una discrepanza visibile, non un bug del certificato.

**FAIL sintetico** (`InpCertRunSyntheticTest=true`, funnel costruito a mano, nessun impatto sul certificato reale dello stesso run):

```
[CERT][SYNTHETIC_TEST] verdict=FAIL (atteso=FAIL) fail_reasons=
  FUNNEL_NOT_RECONCILED(generated=10 blocked+opened+broker_reject=6 - segnali spariti o duplicati);
  OPENED_MISSING_POSITION_ID(1 occorrenze);
  UNEXPECTED_EXIT_AUTHORITY_IN_RAW(2 occorrenze INVARIANT_FAIL...);
  SOURCE_TF_MISMATCH(...);
  SELECTOR_MISMATCH(dichiarato=ADX_RSI osservato=MACD);
```

Tutti e 5 i trigger di FAIL innescati correttamente dal funnel deliberatamente rotto.

## File

`MQL5/Include/NEXUS_v1/NXS_TestValidityCertificate.mqh` (nuovo — anche `NXS_Cert_MakeUniqueRunId`, `NXS_Cert_ConfigFingerprint`, output FILE_COMMON), `NXS_Trace.mqh` (+contatori certificato, `NXS_Trace_TouchPeriod`), `NXS_ResearchMode.mqh` (+`g_certInvariantFailCount++` nel ramo INVARIANT_FAIL esistente), `NXS_Inputs.mqh` (+`InpCertRunSyntheticTest`, +`InpBuildGitCommit`), `NEXUS_EA_v2.mq5` (include, `NXS_Trace_TouchPeriod()` in testa a `OnTick`, `NXS_Cert_Generate()`+`NXS_Cert_RunSyntheticTest()` in `OnDeinit`, run_id reso univoco via `NXS_Cert_MakeUniqueRunId` in `OnInit`).

## Nota operativa: dove trovare i certificati adesso

Dalla patch 12/09 i certificati vivono in `Common\Files\NEXUS\certificates\` (FILE_COMMON), **non** più nella sandbox per-agente `MQL5\Files\NEXUS\certificates\` di prima — su questa macchina risolve in `%APPDATA%\MetaQuotes\Terminal\Common\Files\NEXUS\certificates\`, condivisa da tutti i terminal/agenti, sopravvive a un riavvio di `terminal64.exe` e non viene mai ripulita dal Tester. Necessario per far funzionare la collision avoidance del run_id fra esecuzioni separate (vedi sopra).

## Non coperto (dichiarato esplicitamente)

- **Institutional/Legacy pre-check tracing**: esplicitamente fuori scope per questo task (come da istruzione), certificato copre solo ciò che Trace v1 copre.
- **POSSIBLE_TEST_TRUNCATION** è un WARNING euristico (BLK_PAUSED), non una prova diretta di troncamento reale della passata — MQL5 non espone un segnale affidabile per questo caso specifico.
- Il certificato usa `AccountInfoInteger(ACCOUNT_LEVERAGE)` per il campo leverage, non il valore dichiarato nell'ini del Tester — può divergere se il broker/conto applica una leva diversa da quella richiesta (vedi nota PASS reali sopra).
- `git_commit` resta `UNKNOWN` finché nessun processo di build valorizza `InpBuildGitCommit` — nessuna automazione di questo tipo esiste oggi nel repo (compilazione manuale via MetaEditor CLI).
- `Common\Files` è condiviso fra TUTTI gli EA/script che girano su questo terminal, non isolato per NEXUS — collisione di nome con un altro strumento che scrivesse sotto `NEXUS\certificates\` non è protetta (rischio dichiarato, ritenuto trascurabile dato il prefisso `NEXUS\`).
