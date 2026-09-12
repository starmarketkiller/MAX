# NEXUS — Test Validity Certificate v2

Roadmap 95/99, QUANTITATIVE INTEGRITY. Obiettivo: ogni run di Research Mode produce automaticamente un certificato che dichiara se il test è affidabile o no.

## Stato: implementato e testato — 2 PASS reali (ADX_RSI, MACD) + 1 FAIL sintetico dimostrato

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

`MQL5/Include/NEXUS_v1/NXS_TestValidityCertificate.mqh` (nuovo), `NXS_Trace.mqh` (+contatori certificato, `NXS_Trace_TouchPeriod`), `NXS_ResearchMode.mqh` (+`g_certInvariantFailCount++` nel ramo INVARIANT_FAIL esistente), `NXS_Inputs.mqh` (+`InpCertRunSyntheticTest`), `NEXUS_EA_v2.mq5` (include, `NXS_Trace_TouchPeriod()` in testa a `OnTick`, `NXS_Cert_Generate()`+`NXS_Cert_RunSyntheticTest()` in `OnDeinit`, fix run_id con selector).

## Non coperto (dichiarato esplicitamente)

- **Institutional/Legacy pre-check tracing**: esplicitamente fuori scope per questo task (come da istruzione), certificato copre solo ciò che Trace v1 copre.
- **POSSIBLE_TEST_TRUNCATION** è un WARNING euristico (BLK_PAUSED), non una prova diretta di troncamento reale della passata — MQL5 non espone un segnale affidabile per questo caso specifico.
- Il certificato usa `AccountInfoInteger(ACCOUNT_LEVERAGE)` per il campo leverage, non il valore dichiarato nell'ini del Tester — può divergere se il broker/conto applica una leva diversa da quella richiesta (vedi nota PASS reali sopra).
