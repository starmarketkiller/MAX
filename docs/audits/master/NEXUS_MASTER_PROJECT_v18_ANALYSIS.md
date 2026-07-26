# ANALISI STRUTTURATA — NEXUS_MASTER_PROJECT_v18.md

> Fase D8, attività C. **Documento di sola analisi.** Nessun file di codice è
> stato letto, interpretato o modificato per produrlo: l'unica fonte è il file
> archiviato in `docs/sources/master/NEXUS_MASTER_PROJECT_v18.md`.

## Identità della fonte

| | |
|---|---|
| File | `docs/sources/master/NEXUS_MASTER_PROJECT_v18.md` |
| SHA-256 | `72c51a725c152f8246ccce26d4b30578a25e80dfc817ecd13e935420bfbd16e2` |
| Dimensione | 460 362 byte |
| Righe | 15 489 |
| Data dell'analisi | 2026-07-26 |
| Data dichiarata nella fonte | `Last consolidated: 2026-07-23` (riga 8) |

**Nota di provenienza:** il file allegato è risultato **byte-identico** al file
già tracciato nel repository come `docs/NEXUS_MASTER_PROJECT.md` (stesso
SHA-256). L'archiviazione in `docs/sources/master/` non introduce quindi
contenuto nuovo: crea una copia con identità crittografica dichiarata, come
richiesto dal processo D8.

## Legenda delle classificazioni

| Sigla | Significato |
|---|---|
| `EXPLICIT` | affermato testualmente nella fonte, con riferimento di riga |
| `INFERRED` | deduzione ragionevole da testo esplicito; **non è un requisito** |
| `AMBIGUOUS` | la fonte dice cose non univoche, o usa un termine in più sensi |
| `MISSING` | la fonte non contiene l'informazione |
| `REQUIRES_SOURCE_VERIFICATION` | serve un documento d'origine non presente nel repository |

---

## ⚠️ RISULTATO PRINCIPALE, PRIMA DI OGNI DETTAGLIO

**`NEXUS_MASTER_PROJECT_v18.md` non è una specifica di strategie di trading.**
È un audit di repository, architettura e sicurezza, più una specifica di
governance. Verifiche eseguite sull'intero file:

| Verifica | Risultato |
|---|---|
| Identificatori di strategia (`ADX_RSI`, `FVG_CONT`, `SILVER_BULLET`, …) | 36 sonde su 38 a **0 occorrenze**. Le 2 che rispondono — `MACD` e `SAR`, una volta ciascuna — sono **sulla stessa riga 1857** e in quanto **nomi di indicatore**, non di strategia |
| Regola di ingresso descritta | **0** (`"entry rule"`: 0 occorrenze) |
| Nomi di indicatori usati come logica | **1 riga sola**, riga 1857, e come osservazione di *prestazioni* su `CopyBuffer`, non come regola |
| `RSI` come parola intera | 1 occorrenza (le altre 371 sono la sottostringa dentro `VERSION`) |
| `killzone`, `fair value gap`, `liquidity sweep`, `break of structure`, `swing high/low`, `premium/discount`, `divergence`, `breakout`, `pullback` | **0 occorrenze ciascuno** |
| `London`, `New York`, `Asian` (sessioni di trading) | **0 occorrenze ciascuno** |
| `session` (136 occorrenze) | quasi tutte nel senso di *sessione HTTP/JWT*, non di sessione di mercato |

L'unica parte della fonte che tocca concetti di trading è il blocco
**`A4.2 — FULL CORPUS AUDIT INTEGRATION`** (righe 15058–15460), che è a sua
volta il *riassunto statistico* di un corpus di PDF **non presenti nel
repository**: elenca "pagine più indicative" per concetto, senza riprodurre
alcuna regola.

**Conseguenza operativa:** l'audit di fedeltà delle strategie **non può essere
avviato con questa fonte sola**. Il documento lo dice di sé stesso alla riga
15085: `Final comparison against NEXUS: NOT YET DECLARED COMPLETE`.

---

## 1. Identità e scopo del progetto

| Elemento | Classificazione | Evidenza |
|---|---|---|
| Repository `starmarketkiller/MAX` | `EXPLICIT` | riga 3 |
| Ruolo del documento: *single source of truth* | `EXPLICIT` | riga 4 |
| Stato: attivo e aggiornato in continuo | `EXPLICIT` | riga 5 |
| Sostituisce Audit-0, Operational Backlog e PR-A come documenti separati | `EXPLICIT` | righe 6, 16–23 |
| **Nessuna modifica al codice eseguita** durante la stesura | `EXPLICIT` | riga 7 |
| Il progetto è un Expert Advisor MetaTrader 5 con backend e dashboard | `INFERRED` | dedotto dall'inventario dei file (righe 187–290); mai enunciato come frase di scopo |
| Scopo di trading (mercati, obiettivo di rendimento, orizzonte) | `MISSING` | la fonte non dichiara alcun obiettivo di trading |

## 2. Obiettivi dichiarati

| Elemento | Classificazione | Evidenza |
|---|---|---|
| Chiudere l'audit del repository | `EXPLICIT` | righe 72–89 |
| Portare la copertura tecnica al 100% prima di dichiarare l'audit chiuso | `EXPLICIT` | riga 74 |
| Stato corrente `AUDIT OPEN — 91% TECHNICAL COVERAGE — NO-GO` | `EXPLICIT` | riga 89 |
| Ritiro formale della precedente dichiarazione "AUDIT-0 100% completo" | `EXPLICIT` | riga 31 |
| Copertura per area: MQL5 88%, Backend 88%, Frontend 90%, Contracts 96%, Deploy 96%, Security 98%, Documentation 90%, Testing 68% | `EXPLICIT` | righe 42–53 |
| Il 91% è indicatore di *copertura di revisione*, non di sicurezza del codice | `EXPLICIT` | riga 57 |
| Obiettivi di performance del sistema di trading | `MISSING` | — |

## 3. Architettura generale

| Elemento | Classificazione | Evidenza |
|---|---|---|
| Cinque parti: governance, audit, backlog, specifiche, evidenze | `EXPLICIT` | righe 93–125 |
| L'entrypoint EA include oltre cinquanta moduli `.mqh` locali | `EXPLICIT` | riga 1702 |
| L'esecuzione evita deliberatamente la libreria standard MT5 e usa helper nativi | `EXPLICIT` | riga 1703 |
| La valutazione delle strategie è orchestrata da un collector *hard-coded* | `EXPLICIT` | riga 1704 |
| Un timer da un secondo guida websync, riconciliazione ledger, licenza, persistenza, dashboard, statistiche | `EXPLICIT` | riga 1705 |
| La gestione posizioni gira a ogni tick fresco, prima del gate di nuova barra | `EXPLICIT` | riga 1706 |
| Nuova esposizione bloccata da pausa, stato persistito, licenza, protezioni, spread e news | `EXPLICIT` | riga 1707 |
| Modalità multi-timeframe: passate fisse D1, H4 e H1 su un solo grafico | `EXPLICIT` | riga 1708 |
| Lo shutdown persiste ledger, virtual stop e stato | `EXPLICIT` | riga 1709 |
| Livelli di include proposti (1 tipi → 6 orchestrazione) | `EXPLICIT` come *azione richiesta*, non come architettura in essere | righe 1745–1751 |
| Architettura *target* separata da quella *corrente* | `AMBIGUOUS` | il documento alterna descrizione dell'esistente e prescrizione del futuro senza marcatura sistematica |

## 4. Moduli e componenti citati

| Elemento | Classificazione | Evidenza |
|---|---|---|
| 59 moduli `NXS_*.mqh` elencati per nome | `EXPLICIT` | righe 191–252 |
| Fra questi, i moduli con nome di strategia: `NXS_Strategies.mqh`, `NXS_Strategies_Institutional.mqh`, `NXS_Strategies_SMC.mqh`, `NXS_StrategyChain.mqh`, `NXS_StrategyRegistry.mqh`, `NXS_SignalRouter.mqh` | `EXPLICIT` | righe 236–240 |
| Moduli di concetto di trading: `NXS_AMDModel`, `NXS_BjorgumZones`, `NXS_Confluence`, `NXS_FibonacciContext`, `NXS_HTFBias`, `NXS_Structure`, `NXS_StructureMultiLayer`, `NXS_Reaction`, `NXS_Pressure`, `NXS_Velocity`, `NXS_Sessions` | `EXPLICIT` (solo i nomi) | righe 192–245 |
| **Cosa fa ciascun modulo** | `MISSING` | la fonte elenca i nomi; non descrive la logica di nessuno |
| File backend (`server/app.py`, `backtest.py`, …) | `EXPLICIT` | righe 253–269 |
| Pagine frontend (Dashboard, Journal, Live Chart, LocalBridge, Backtest, Analytics) | `EXPLICIT` | righe 270–277 |
| File di contratto e deployment | `EXPLICIT` | righe 278–290 |

## 5. Strategie citate

| Elemento | Classificazione | Evidenza |
|---|---|---|
| **Nessuna strategia è citata per nome** | `EXPLICIT` (assenza verificata) | sonda esaustiva su 38 identificatori canonici: 36 a zero occorrenze; `MACD` e `SAR` compaiono una volta ciascuna, entrambe alla riga 1857, come nomi di **indicatore** in un reperto di prestazioni. Il progetto usa quelle due parole anche come nomi di strategia, ma in questa fonte ricorrono solo nel senso di indicatore |
| Il router assegna numeri di selettore fissi "come 17–37" | `EXPLICIT` | riga 1776 |
| Il router usa array a dimensione fissa (`48` nel percorso di ingresso, `64` in un percorso multi-TF temporaneo) | `EXPLICIT` | riga 1790 |
| Numero totale di strategie | `MISSING` | mai dichiarato; la riga 1792 dice solo che "il conteggio corrente appare sotto il limite" |
| Elenco delle strategie | `MISSING` | — |
| Descrizione di una qualunque strategia | `MISSING` | — |

> Il riferimento "17–37" è l'unico indizio numerico e riguarda la **forma del
> routing**, non l'identità delle strategie. Non è sufficiente per dedurre né
> quante siano né quali.

## 6. Identificatori o nomi delle strategie

| Elemento | Classificazione | Evidenza |
|---|---|---|
| Schema di identificatori dei **requisiti** (`NEXUS-STRAT-###`, …) | `EXPLICIT` | righe 14663–14680 |
| Schema di identificatori delle **strategie** | `MISSING` | la fonte non definisce alcuna convenzione di naming per le strategie |
| Identificatori concreti di strategia | `MISSING` | — |
| Alias o rinomine di strategia | `MISSING` | — |

**Conseguenza per l'inventario (attività D):** l'inventario delle strategie
derivato da questa fonte è necessariamente **vuoto**. Popolarlo con nomi presi
dal codice violerebbe il vincolo 1 dell'incarico ("non analizzare altre fonti
non allegate") e trasformerebbe una deduzione in un dato.

## 7. Indicatori e concetti di trading

| Elemento | Classificazione | Evidenza |
|---|---|---|
| Indicatori nominati: ADX, RSI, Bollinger, MACD, SAR, ATR, medie mobili, Ichimoku | `EXPLICIT` ma **solo come elenco di `CopyBuffer`** | riga 1857 |
| Come vengono usati quegli indicatori | `MISSING` | la riga 1857 è un finding di prestazioni: dice che le letture avvengono a ogni tick, non cosa calcolano |
| La valutazione usa valori di barra chiusa (`shift=1`) | `EXPLICIT` | riga 1717 |
| Concetti del corpus: Market Structure, Support/Resistance & SNR, Supply & Demand, Liquidity & Stop Hunts, Order Blocks & FVG, ICT Concepts, Candlesticks, Fibonacci, Chart Patterns, Entries & Confirmation, Stop Loss & Take Profit, Risk & Money Management, Sessions & Timing, Psychology & Discipline, Sequence / Proprietary Models | `EXPLICIT` come **etichette di categoria**, `REQUIRES_SOURCE_VERIFICATION` come contenuto | righe 15107–15118 e successive; sintesi righe 15461–15480 |
| Definizione operativa di uno qualunque di questi concetti | `MISSING` / `REQUIRES_SOURCE_VERIFICATION` | il corpus è indicizzato per *pagina*, non riprodotto |

## 8. Regole di ingresso

| Elemento | Classificazione | Evidenza |
|---|---|---|
| Regole di ingresso di qualunque strategia | `MISSING` | `"entry rule"`: 0 occorrenze |
| Esiste un gate di nuova barra prima della decisione di ingresso | `EXPLICIT` | righe 1706, 1718 |
| Esiste un punteggio minimo di ingresso come *concetto* | `INFERRED` | dedotto dalla presenza di `NXS_EntryScore.mqh` (riga 200); nessuna soglia dichiarata |
| Categoria "Entries & Confirmation" nel corpus, 789 occorrenze indicative | `EXPLICIT` (statistica) / `REQUIRES_SOURCE_VERIFICATION` (contenuto) | riga 15466 |

## 9. Regole di uscita

| Elemento | Classificazione | Evidenza |
|---|---|---|
| Regole di uscita di qualunque strategia | `MISSING` | `"exit rule"`: 1 occorrenza, non nel senso di regola di strategia |
| Un trade non è finale finché la chiusura non è confermata dal broker e riconciliata | `EXPLICIT` (requisito `NEXUS-LIFE-003`) | riga 14785 |
| Chiusura di fine seduta derivata dai dati di sessione del simbolo, con festivi e chiusure anticipate | `EXPLICIT` come **azione richiesta** | riga citata nel finding sulle sessioni |

## 10. Stop loss e take profit

| Elemento | Classificazione | Evidenza |
|---|---|---|
| Valori, moltiplicatori o regole di SL/TP | `MISSING` | 13 occorrenze di "stop loss" e 12 di "take profit", tutte in contesti di integrità dell'esecuzione, mai come parametro di strategia |
| Esiste un Virtual Stop governato da un modulo dedicato (PR-F) | `EXPLICIT` | roadmap, `## PR-F — Virtual Stop Governor` |
| Categoria "Stop Loss & Take Profit" nel corpus, 85 occorrenze indicative | `EXPLICIT` (statistica) / `REQUIRES_SOURCE_VERIFICATION` | riga 15473 |

## 11. Gestione della posizione

| Elemento | Classificazione | Evidenza |
|---|---|---|
| La gestione posizioni precede il routing di nuovi segnali | `EXPLICIT` | riga 1723 |
| Ordini, posizioni, chiusure parziali e finalizzazione devono restare tracciabili a **un solo trade logico** | `EXPLICIT` (`NEXUS-LIFE-002`) | riga 14782 |
| Esistono percorsi grid, pyramiding, split e institutional | `EXPLICIT` | titolo Block 11, riga 2665 |
| Regole operative di grid/pyramiding/split | `MISSING` | i blocchi ne auditano l'integrità, non ne definiscono la logica |
| Gate per strategia sulle posizioni aperte e tracciamento barra per strategia/timeframe | `EXPLICIT` | riga 1724 |

## 12. Gestione del rischio

| Elemento | Classificazione | Evidenza |
|---|---|---|
| `NEXUS-RISK-001` — nessuna azione manuale, automatica o generata da AI può bypassare Risk Engine e Policy Engine | `EXPLICIT` | riga 14765 |
| `NEXUS-RISK-002` — l'incertezza sullo stato live deve bloccare nuova esposizione fino alla riconciliazione | `EXPLICIT` | riga 14768 |
| `NEXUS-RISK-003` — le protezioni hard attive prevalgono su strategia e operatore | `EXPLICIT` | riga 14771 |
| `NEXUS-RISK-004` — il sizing deve essere calcolato da servizi deterministici | `EXPLICIT` | riga 14774 |
| Percentuali, tetti o formule di rischio concrete | `MISSING` | nessun numero di rischio è dichiarato nella fonte |
| Il tester disattiva il gate delle protezioni, creando divario di parità live/backtest | `EXPLICIT` | riga 2597 |
| Ottimizzazione e backtest non modellano i vincoli di esecuzione live | `EXPLICIT` | riga 2187 |

## 13. Gestione del capitale

| Elemento | Classificazione | Evidenza |
|---|---|---|
| Categoria "Risk & Money Management" nel corpus, **15 occorrenze indicative** — la densità **più bassa** di tutte | `EXPLICIT` | riga 15475 |
| Regole di money management | `MISSING` / `REQUIRES_SOURCE_VERIFICATION` | — |
| Un tenant può possedere più conti e più deployment | `EXPLICIT` (assunzione) | riga 14941 |
| Più strategie non devono condividere autorità illimitata | `EXPLICIT` (assunzione) | riga 14942 |

> La densità di 15 occorrenze su 1092 pagine è un fatto rilevante per la Fase B:
> il corpus d'origine tratta il money management molto meno di quanto tratti
> entries (789) o supporti/resistenze (1515).

## 14. Filtri temporali e sessioni

| Elemento | Classificazione | Evidenza |
|---|---|---|
| Esiste un modulo `NXS_Sessions.mqh` | `EXPLICIT` (nome) | riga 229 |
| Serve calendario/sessioni con timezone del broker, DST e validazione temporale | `EXPLICIT` come **inferenza dichiarata tale dalla fonte stessa** | riga 15125 |
| La chiusura di seduta va derivata dai dati di sessione del simbolo, gestendo festivi e chiusure anticipate | `EXPLICIT` (azione richiesta) | finding sulle sessioni |
| Orari, killzone, sessioni di mercato concrete | `MISSING` | `London`, `New York`, `Asian`, `killzone`: 0 occorrenze |
| Categoria "Sessions & Timing" nel corpus, 319 occorrenze indicative | `EXPLICIT` (statistica) / `REQUIRES_SOURCE_VERIFICATION` | riga 15467 |

## 15. Filtri di volatilità, volume, trend e momentum

| Elemento | Classificazione | Evidenza |
|---|---|---|
| Esistono moduli `NXS_MTFSpreadVol.mqh`, `NXS_Velocity.mqh`, `NXS_Pressure.mqh`, `NXS_HTFBias.mqh` | `EXPLICIT` (nomi) | righe 202, 245, 220, 205 |
| Nuova esposizione bloccata anche da gate su spread e news | `EXPLICIT` | riga 1707 |
| Soglie, periodi, formule di questi filtri | `MISSING` | — |
| Filtro di volume | `MISSING` | nessuna menzione di filtro su volume |

## 16. Regole di selezione delle strategie

| Elemento | Classificazione | Evidenza |
|---|---|---|
| Il routing è duplicato: codice hard-coded **più** identificatori numerici di selettore | `EXPLICIT` | riga 1776 |
| Rischio dichiarato: drift fra MQL, backtest Python, backend e frontend; mapping numerico off-by-one; una strategia può risultare live in un sottosistema e non eseguire in un altro | `EXPLICIT` | righe 1780–1783 |
| Severità `P0 strategy-contract integrity` | `EXPLICIT` | riga 1785 |
| Azione richiesta: generare il registro/dispatch MQL da **una sola fonte canonica** e aggiungere test di parità fra MQL, backend e motore di backtest | `EXPLICIT` | riga 1786 |
| Criteri con cui una strategia viene scelta per operare | `MISSING` | — |

## 17. Conviction, scoring o ranking

| Elemento | Classificazione | Evidenza |
|---|---|---|
| Esistono moduli `NXS_EntryScore.mqh`, `NXS_Confluence.mqh`, `NXS_StratStats.mqh` | `EXPLICIT` (nomi) | righe 200, 195, 235 |
| Formula di conviction o di scoring | `MISSING` | la parola "conviction" non compare nella fonte |
| I risultati di backtest sono ordinati con un ordinamento esplicito di verdetto | `EXPLICIT` | riga 1335 |
| `OnTester` ottimizza **solo** per profit factor | `EXPLICIT` | riga 1905 |
| Il profit factor da solo non codifica numero minimo di trade, drawdown, recovery, expectancy, stabilità, performance out-of-sample | `EXPLICIT` | righe 1907–1913 |
| Severità `P0 research validity` | `EXPLICIT` | riga 1915 |

## 18. Configurazioni live e research

| Elemento | Classificazione | Evidenza |
|---|---|---|
| Cinque ambienti canonici: `RESEARCH`, `SHADOW`, `PAPER`, `LIMITED_LIVE`, `LIVE`, con definizione di ciascuno | `EXPLICIT` | righe 14873–14879 |
| `NEXUS-ARCH-003` — gli ambienti devono restare operativamente separati | `EXPLICIT` | riga 14729 |
| "Specification-ready" ≠ "Production-ready", e i due termini non devono essere usati in modo intercambiabile | `EXPLICIT` | righe 14881–14885 |
| PR-A deve produrre **una sola** configurazione effettiva, eliminando la catena parallela `Inp*` / preset / `g_run_*` / `g_NXSlp_*` / runtime dashboard | `EXPLICIT` | riga 6546 |
| Struttura `SNXSEffectiveConfig` con revision, profileId, registryHash, configHash, issuedAt, expiresAt, riskPct, maxLot, maxConcurrent, maxDailyDDPct | `EXPLICIT` | righe 6564–6580 |
| Valori concreti di configurazione | `MISSING` | la struttura è dichiarata, i valori no |

## 19. Requisiti di compilazione e testing

| Elemento | Classificazione | Evidenza |
|---|---|---|
| L'evidenza di compilazione MQL5 è fra i requisiti di chiusura dell'audit | `EXPLICIT` | riga 82 |
| Evidenza di parità backtest/runtime richiesta | `EXPLICIT` | riga 83 |
| Evidenza di build e avvio Docker puliti richiesta | `EXPLICIT` | riga 81 |
| Inventario dei test e dei workflow CI richiesti | `EXPLICIT` | righe 79–80 |
| Evidenza di backup/restore e di replay dei comandi con crash recovery | `EXPLICIT` | righe 84–85 |
| Copertura corrente di "Testing and executable evidence": **68%**, la più bassa | `EXPLICIT` | riga 53 |
| Metodi di verifica ammessi: `INSPECTION`, `STATIC_ANALYSIS`, `UNIT_TEST`, `CONTRACT_TEST`, `INTEGRATION_TEST`, `SCENARIO_TEST`, `SECURITY_TEST` | `EXPLICIT` | righe 14707–14716 |
| PR-J — Runtime Test Harness, priorità P0, dipende da A–I | `EXPLICIT` | roadmap |

## 20. Backtest e criteri di validazione

| Elemento | Classificazione | Evidenza |
|---|---|---|
| Il backtesting controllato è **permesso**; il trading a denaro reale è **bloccato** | `EXPLICIT` | righe 132–147 |
| L'ottimizzazione gira sincrona dentro le richieste API (`AUD0-COMPUTE-001`) | `EXPLICIT` | riga 1263 |
| Le eccezioni di backtest vengono convertite silenziosamente in candidati mancanti (`AUD0-COMPUTE-003`) | `EXPLICIT` | riga 1294 |
| `GET /api/backtest/optimize/{job_id}` ignora l'ID richiesto e restituisce un unico risultato globale | `EXPLICIT` | riga 1624 |
| I CSV di ottimizzazione scritti da agenti paralleli richiedono un contratto di merge esterno; senza run ID e identità dell'agente i risultati possono essere incompleti, duplicati o mescolati (`AUD0-MQL-014`) | `EXPLICIT` | righe 1918–1926 |
| Criteri numerici di validazione (PF minimo, DD massimo, numero minimo di trade, finestre out-of-sample) | `MISSING` | la fonte dice che servono, non quali |
| Nessun dato di backtest, nessun risultato, nessuna metrica di alcuna strategia | `MISSING` | — |

## 21. Vincoli di sicurezza

| Elemento | Classificazione | Evidenza |
|---|---|---|
| `NEXUS-SEC-001` — la produzione deve fallire in chiusura se sono presenti credenziali di default o segreti di firma di ripiego | `EXPLICIT` | riga 14804 |
| `NEXUS-SEC-002` — i segreti non devono stare in sorgente, bundle frontend, log o token statici condivisi | `EXPLICIT` | riga 14807 |
| `NEXUS-SEC-003` — gli artefatti di deployment devono essere firmati e verificati prima dell'attivazione | `EXPLICIT` | riga 14810 |
| `NEXUS-SEC-004` — le sessioni privilegiate devono essere revocabili lato server | `EXPLICIT` | riga 14813 |
| `NEXUS-SEC-005` — i record di audit devono essere append-only e tamper-evident | `EXPLICIT` | riga 14816 |
| `NEXUS-ID-003` — le azioni ad alto rischio richiedono step-up authentication | `EXPLICIT` | riga 14740 |
| `NEXUS-ID-004` — ogni deployment o istanza EA deve usare una credenziale unica e revocabile | `EXPLICIT` | riga 14743 |
| Token bridge in chiaro nella fonte (`NEXUS_BRIDGE_TOKEN_2026`, 6 occorrenze) | `EXPLICIT` | il documento cita il valore come reperto d'audit |
| **Blocchi in vigore:** trading reale, deploy remoto di codice, deploy automatico in produzione, uso multi-account in produzione, mutazioni live dell'AI Coach, "Point 5" | `EXPLICIT` | righe 140–147 |

## 22. Milestone e attività ancora aperte

| Elemento | Classificazione | Evidenza |
|---|---|---|
| Roadmap di 12 pull request, **PR-A → PR-L**, tutte allo stato `TODO` | `EXPLICIT` | righe 6989–7001 |
| Ordine di esecuzione vincolante `A → B → C → D → E → F → G → H → I → J → K → L` | `EXPLICIT` | riga 7005 |
| Undici PR a priorità P0, una (PR-L, cleanup) a P1 | `EXPLICIT` | tabella righe 6989–7001 |
| Primo task operativo: **PR-A — Effective Config Resolver** | `EXPLICIT` | riga 7011 |
| Registro delle decisioni aperte: `OD-001` … `OD-010` (database, trasporto eventi, secret management, identità macchina, observability, CI/CD, provider AI, isolamento broker-adapter, deployment, retention) | `EXPLICIT` | righe 14890–14903 |
| Ogni decisione aperta richiede un ADR prima del lock implementativo | `EXPLICIT` | riga 14905 |
| Cinque fasi di consegna raccomandate (Foundation, Trading integrity, Safety, Production platform, Evidence and AI) | `EXPLICIT` | righe 14470–14510 circa |

## 23. Contraddizioni interne

### Contraddizioni registrate esplicitamente dalla fonte

**Registro cross-file** (righe 533–551), 4 voci — tutte su configurazione, nessuna su strategie:

| # | Contraddizione |
|---|---|
| 1 | Formato utente admin: README si aspetta un valore tipo email; Render e `.env.example` dicono `admin` |
| 2 | Piano Render: la guida DEPLOY dice che il piano free è adatto; `render.yaml` è impostato su Starter |
| 3 | Branch canonico: la guida DEPLOY nomina ancora il branch di migrazione originale; il default del repository è `main` |
| 4 | Self-hosting: il core è dichiarato self-hostable, ma i file di deployment configurano integrazioni esterne Anthropic e Telegram |

**Matrice di revisione delle contraddizioni** (righe 14855–14866), 10 coppie di
dominio con risoluzione canonica dichiarata — fra cui: il Risk Engine mantiene
il veto sull'autorità umana; lo stato confermato dal broker vince sul ledger
interno; una differenza di hash o parametri fra versione della strategia e
deployment comporta rifiuto o quarantena.

La fonte conclude: `No contradiction currently requires architectural redesign`
(riga 14867).

### Contraddizioni interne rilevate da questa analisi

| # | Contraddizione | Classificazione |
|---|---|---|
| C-1 | Il documento si dichiara *single source of truth* (riga 4) ma non contiene alcuna specifica di strategia, mentre le strategie sono il prodotto. Come fonte unica di verità è **incompleto rispetto al proprio dominio**. | `EXPLICIT` (le due affermazioni sono entrambe verificabili nel testo) |
| C-2 | Riga 14867: "nessuna contraddizione richiede riprogettazione architetturale" — ma la riga 1785 classifica il drift del contratto delle strategie come `P0 strategy-contract integrity` e chiede di **generare** il registro da una fonte canonica, che è un cambio strutturale. | `AMBIGUOUS` — dipende da cosa si intende per "riprogettazione architetturale", termine non definito |
| C-3 | La copertura di revisione è dichiarata al 91% (riga 55) con `Contradiction review 100% architectural` (riga 15040), ma la riga 15085 dichiara `Final comparison against NEXUS: NOT YET DECLARED COMPLETE`. Un confronto non completato non può sostenere una revisione al 100%. | `AMBIGUOUS` |
| C-4 | Il blocco A4.2 stabilisce che "nessun concetto entrerà nel Master NEXUS come requisito operativo prima della formalizzazione" (riga 15489), ma il blocco stesso è già integrato **dentro** il Master, che si dichiara autorevole. | `AMBIGUOUS` |

## 24. Ambiguità

| # | Ambiguità | Evidenza |
|---|---|---|
| A-1 | "Strategia" è usato in due sensi non distinti: unità di logica di trading, e voce di un registro/contratto software. La fonte non definisce il termine. | intero documento |
| A-2 | La fonte alterna descrizione dello stato attuale e prescrizione dello stato futuro senza marcatura sistematica. Solo la sezione 3 (righe 14646–14657) introduce `MUST`/`SHOULD`/`MAY`, e vale per i requisiti indicizzati, non per il resto del testo. | righe 14646–14657 |
| A-3 | "Point 5" compare come elemento bloccato (righe 70, 147) senza essere mai definito. | righe 70, 147 |
| A-4 | "Sequence / Proprietary Models" è una categoria del corpus con 22 occorrenze, e la fonte raccomanda di conservare "il modello proprietario" come strategia isolata (riga 15127) — ma non dice quale sia il modello, né a quale strategia corrisponda. | righe 15118, 15127 |
| A-5 | Le percentuali di copertura per area (88%, 90%, 96%…) non hanno metodo di calcolo dichiarato. Non è verificabile come si passi da "MQL5 88%" a un numero riproducibile. | righe 42–55 |
| A-6 | Il documento dichiara `Code changes performed: none` (riga 7) e insieme `Stato documento: READY FOR IMPLEMENTATION` (riga 7025). Non è chiaro se l'implementazione sia autorizzata o attesa. | righe 7, 7025 |

## 25. Informazioni mancanti

Elencate qui in forma sintetica; il dettaglio con impatto e azione è in
`NEXUS_MASTER_GAPS.md`.

| Area | Mancante |
|---|---|
| Strategie | nomi, identificatori, conteggio, descrizioni, regole di ingresso e uscita, SL/TP, filtri |
| Indicatori | parametri, periodi, soglie, uso |
| Rischio | percentuali, tetti, formule di sizing |
| Sessioni | orari, timezone di riferimento, killzone |
| Selezione | criteri con cui una strategia viene attivata o esclusa |
| Scoring | formula di conviction, pesi, soglie |
| Validazione | criteri numerici di accettazione di un backtest |
| Evidenze | nessun risultato di test, backtest o compilazione è allegato alla fonte |
| Corpus | il contenuto dei 13 PDF indicizzati in A4.2 |

## 26. Elementi che richiedono verifica sui corsi originali

Il blocco A4.2 (righe 15058–15460) indicizza **13 PDF**, **1092 pagine totali**,
di cui **912 con testo nativo o OCR**. Nessuno è presente nel repository.

| # | PDF | Pagine | Pagine con testo/OCR | Caratteri estratti |
|---|---|---:|---:|---:|
| 1 | `863955768-MSNR-x-SMC-x-ICT-the-Alchemist-Yanu-Emmanuel.pdf` | 51 | 51/51 | 28.447 |
| 2 | `Malaysian SNR Emperor.pdf` | 67 | 67/67 | 22.562 |
| 3 | `My Rare SNR Course 2.pdf` | 10 | 10/10 | 2.091 |
| 4 | `My Rare SNR Course.pdf` | 29 | 29/29 | 13.111 |
| 5 | `SNR Malaysia.pdf` | 74 | 74/74 | 18.153 |
| 6 | `Secret Of 411(1).pdf` | 16 | 16/16 | 2.698 |
| 7 | `Sequence.pdf` | 76 | **56/76** | 4.588 |
| 8 | `Sequence_1.pdf` | 74 | **46/74** | 55.488 |
| 9 | `Sequence_2_unlocked.pdf` | 119 | **0/119** | **0** |
| 10 | `allyouneedtoknow-230110032117-f4fdcdb0.pdf` | 153 | 153/153 | 19.045 |
| 11 | `candlesticksfibonacciandchartpatterntrading-forexfactorypdfdrive-210313181656.pdf` | 273 | 263/273 | 355.855 |
| 12 | `flippingmarkets1-230503210106-91bd5cfc.pdf` | 59 | 56/59 | 14.658 |
| 13 | `ict-trading-250828073107-caca0de9.pdf` | 91 | 91/91 | 57.806 |
| | **Totale** | **1092** | **912/1092** | |

I totali di riga corrispondono al dato aggregato dichiarato dalla fonte alla
riga 15462 (`1092` pagine, `912/1092` con testo): la somma delle 13 righe è
stata ricalcolata e coincide.

**Due casi meritano attenzione prima di qualunque uso:**

- `Sequence_2_unlocked.pdf` — **119 pagine, 0 estratte, 0 caratteri**. È il
  documento con più pagine completamente illeggibili del corpus, e appartiene
  alla famiglia "Sequence", cioè proprio la categoria che la fonte chiama
  "Sequence / Proprietary Models". Nessun contenuto di questo file è entrato
  nell'audit semantico.
- `Sequence.pdf` (56/76) e `Sequence_1.pdf` (46/74) hanno anch'essi lacune
  rilevanti. Sommando i tre: **180 pagine su 269 della famiglia "Sequence" non
  hanno testo estratto.** Questo spiega perché "Sequence / Proprietary Models"
  abbia solo 22 occorrenze indicative, la penultima densità dell'intero corpus:
  il dato **non** dimostra che il modello proprietario sia poco trattato,
  dimostra che è poco *leggibile* con l'estrazione usata.

### Densità concettuale globale dichiarata (riga 15464 e seguenti)

| Concetto | Occorrenze indicative |
|---|---:|
| Support/Resistance & SNR | 1515 |
| Entries & Confirmation | 789 |
| Candlesticks | 511 |
| Fibonacci | 493 |
| Chart Patterns | 378 |
| Sessions & Timing | 319 |
| ICT Concepts | 316 |
| Market Structure | 315 |
| Liquidity & Stop Hunts | 281 |
| Order Blocks & FVG | 162 |
| Stop Loss & Take Profit | 85 |
| Supply & Demand | 84 |
| Psychology & Discipline | 62 |
| Sequence / Proprietary Models | 22 |
| Risk & Money Management | 15 |

### Regole che la fonte stessa impone al materiale del corpus

Tutte `EXPLICIT`, righe 15070–15075:

- nessun concetto di fonte diventa logica eseguibile senza formalizzazione deterministica;
- nessuna regola di corso può bypassare Policy Engine o Risk Engine;
- le regole derivate visivamente richiedono verifica a livello di pagina prima dell'implementazione;
- la terminologia duplicata fra corsi non va trattata come equivalenza semantica senza riconciliazione;
- le regole ambigue, discrezionali o non testabili restano candidate di ricerca;
- ogni regola promossa richiede identificatori di requisito, test, evidenze e proprietà versionata.

### Limiti dichiarati dalla fonte (righe 15485–15489)

- le pagine grafiche con OCR assente o debole richiedono verifica visiva diretta;
- un'occorrenza non dimostra che una regola sia corretta, completa o traducibile automaticamente in codice;
- corsi diversi possono usare la stessa parola con significati differenti: la normalizzazione va fatta corso per corso;
- nessun concetto entrerà nel Master come requisito operativo prima della formalizzazione e della verifica.

---

## Sintesi per il passo successivo

| | |
|---|---|
| Requisiti normativi estratti | 38 (`NEXUS-*`, righe 14722–14851) |
| Identificatori di finding distinti | 310 (`AUD0-*`, `NXS-*`, `NEXUS-*`) |
| Strategie inventariabili da questa fonte | **0** |
| PDF del corpus da acquisire | 13 |
| Decisioni architetturali aperte | 10 (`OD-001` … `OD-010`) |
| Pull request pianificate, tutte `TODO` | 12 (PR-A … PR-L) |

**L'audit di fedeltà delle strategie non è avviabile con questa sola fonte.**
Servono i 13 PDF e un documento che dichiari l'elenco e la logica delle
strategie. Finché mancano, ogni affermazione su cosa una strategia "dovrebbe"
fare sarebbe una deduzione presentata come requisito — esattamente ciò che
l'incarico vieta.

## Collegamenti

`docs/sources/master/NEXUS_MASTER_PROJECT_v18.md` ·
`docs/audits/master/NEXUS_MASTER_STRATEGY_INVENTORY.json` ·
`docs/audits/master/NEXUS_MASTER_REQUIREMENTS.json` ·
`docs/audits/master/NEXUS_MASTER_GAPS.md` ·
`docs/sources/SOURCE_MANIFEST.json`
