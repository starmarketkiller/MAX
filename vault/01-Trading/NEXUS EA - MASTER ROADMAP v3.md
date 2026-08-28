---
type: master-roadmap
domain: trading
status: active
version: 3.0
tags: [nexus-ea, roadmap, engineering, validation, agents, mt5, mql5, backtest]
created: 2026-07-17
updated: 2026-07-17
recommended_path: vault/01-Trading/NEXUS EA - MASTER ROADMAP v3.md
---

# NEXUS EA — MASTER ROADMAP v3

> Documento principale per programmatori e agenti AI che devono analizzare, modificare, testare o validare NEXUS EA.
>
> Questo file definisce l'ordine corretto del lavoro. Non è una raccolta di idee: contiene priorità, dipendenze, criteri di completamento, test obbligatori e regole per evitare di produrre risultati non affidabili.

---

# 0. Mandato operativo

L'obiettivo è trasformare NEXUS EA da sistema complesso, ricco di strategie e automazioni, in un motore:

- verificabile;
- riproducibile;
- modulare;
- osservabile;
- testabile strategia per strategia;
- robusto fuori campione;
- gestibile da più agenti senza perdita di contesto;
- pronto per forward test e, solo dopo, per uso live controllato.

La priorità immediata **non è aumentare il profitto**.

La priorità è poter dimostrare la catena completa:

```text
commit sorgente
→ build compilata
→ parametri realmente caricati
→ strategia realmente selezionata
→ timeframe e profilo realmente risolti
→ segnale realmente generato
→ filtri realmente applicati
→ ordine realmente inviato
→ posizione realmente gestita
→ trade realmente chiuso
→ log e report riconciliati
→ conclusione scientificamente valida
```

Se anche un solo passaggio non è verificabile, il risultato non deve essere usato per:

- promuovere una strategia;
- bocciare una strategia;
- modificare il portafoglio;
- cambiare sizing;
- concludere che un filtro funziona;
- concludere che un'uscita è migliore;
- dichiarare una versione pronta per produzione.

---

# 1. Stato del progetto da assumere come punto di partenza

Il programmatore deve verificare nel repository ogni punto seguente, senza assumere che una nota precedente sia ancora corretta.

## 1.1 Architettura esistente

Il sistema comprende almeno:

- Expert Advisor MQL5 principale;
- include modulari;
- router delle strategie;
- circa 37 strategie;
- motore di scoring e filtri globali;
- profili di rischio e uscita;
- modalità Data Collection;
- runner e automazioni per backtest MT5;
- Backtest Lab Python/sito;
- backend FastAPI;
- LocalBridge;
- dashboard e strumenti diagnostici;
- vault Obsidian con audit, risultati, fonti e decisioni.

## 1.2 Problemi storici già emersi

Sono stati trovati, in fasi diverse, problemi capaci di invalidare interi batch di test:

- file `.set` contenenti parametri che non erano veri `input` MQL5;
- centinaia di variabili concettualmente configurabili ma non esposte al Tester;
- riuso della configurazione o strategia precedente durante sweep automatici;
- controllo duplicati limitato ai report adiacenti;
- report attribuiti alla strategia sbagliata;
- assenza del gate "una posizione per strategia" in Data Collection Mode;
- segnali persistenti capaci di riaprire posizioni a ogni tick;
- due sistemi indipendenti di durata massima;
- tabella strategia → timeframe vecchia e incompleta;
- fallback silenzioso a una durata generica di 12 ore;
- log CSV di chiusura vuoto o non riconciliabile;
- proxy Python non fedeli alla logica MQL5 reale;
- strategie diverse rappresentate da proxy quasi identici;
- overfitting su periodi corti;
- conclusioni corrette successivamente da altri agenti.

Questi problemi impongono una regola: **i risultati precedenti devono essere classificati, non semplicemente riutilizzati**.

## 1.3 Evidenze strategiche preliminari

Le evidenze raccolte finora suggeriscono, ma non dimostrano definitivamente, che:

- uno score globale più alto non separa necessariamente trade vincenti e perdenti;
- setup BUY e SELL possono avere comportamenti differenti;
- struttura interna ed esterna funzionano meglio come varianti indipendenti che come doppio gate obbligatorio;
- alcune strategie possono avere una direzione corretta ma uscite inadatte;
- break-even e trailing non devono essere trattati come equivalenti;
- ottimizzare il proxy Python non garantisce un miglioramento del comportamento MT5;
- alcune strategie considerate forti su pochi trade sono poi crollate su campioni più estesi;
- un portafoglio non va giudicato solo dalla somma dei risultati individuali, ma anche da correlazione, concentrazione delle perdite e sovrapposizione temporale.

Tutte queste indicazioni vanno rivalidate dopo la bonifica P0.

---

# 2. Regole vincolanti per ogni programmatore o agente

1. **Non modificare strategie prima di chiudere i blocchi P0.**
2. **Una sola ipotesi principale per esperimento.** Non cambiare contemporaneamente trigger, filtro, uscita, sizing e sessione.
3. **Mai lavorare direttamente su `main` per esperimenti.** Usare un branch dedicato.
4. **Ogni test deve dichiarare commit, build, configurazione e dataset.**
5. **Separare sempre risultati MT5, risultati Python e teoria.**
6. **Non usare il nome della strategia come prova che il codice implementi davvero quella logica.**
7. **Buy e Sell sono setup distinti.** Analizzarli separatamente prima di disattivarne uno.
8. **Uno score maggiore non implica automaticamente maggiore edge.**
9. **Struttura interna ed esterna sono varianti, salvo prova contraria.**
10. **Nessun default silenzioso per strategia sconosciuta o parametro mancante.** Fallire in modo visibile.
11. **Ogni bug corretto deve avere un test di regressione.**
12. **Ogni risultato senza manifest è esplorativo, non validato.**
13. **Ogni nota deve distinguere fatti, ipotesi, decisioni e attività aperte.**
14. **Nessun merge senza prova che la compilazione e i test minimi passino.**
15. **Nessuna release live sulla base del solo backtest.**

---

# 3. Modello delle priorità

- **P0 — Bloccante:** integrità di esecuzione, configurazione e dati.
- **P1 — Fondazione:** osservabilità, test automatici, collaborazione e qualità del software.
- **P2 — Nuova baseline:** riesecuzione affidabile delle strategie e classificazione dell'edge.
- **P3 — Architettura decisionale:** separazione delle responsabilità, score, filtri, conflitti e regimi.
- **P4 — Miglioramento dell'edge:** trigger, uscite, rischio e costruzione del portafoglio.
- **P5 — Produzione:** forward test, monitoraggio, resilienza e processo di release.

Le priorità sono sequenziali. P3 e P4 non devono partire seriamente prima della chiusura di P0 e P1.

---

# 4. P0 — Integrità assoluta di esecuzione e backtest

## P0.1 — Congelare una baseline tecnica

### Attività

- Identificare il commit iniziale da cui partire.
- Creare tag o branch `baseline-post-infra-audit`.
- Registrare:
  - commit SHA;
  - versione EA;
  - versione MetaTrader 5;
  - versione compilatore MQL5;
  - broker o specifica simbolo usata;
  - timezone;
  - qualità e origine dati;
  - periodo;
  - spread e commissioni;
  - modalità tick;
  - deposito, valuta e leva.
- Calcolare checksum della build `.ex5`.

### Output

- `results/manifests/baseline_manifest.json`
- `vault/01-Trading/Decisions/DEC - Baseline tecnica corrente.md`

### Done quando

Un secondo programmatore può ricreare la stessa build e ottenere lo stesso identificatore.

---

## P0.2 — Audit completo degli input MQL5

### Obiettivo

Garantire che ogni parametro configurato da `.set`, runner o profilo venga realmente letto e applicato.

### Attività

- Estrarre automaticamente tutti gli `input` dalla build.
- Confrontarli con tutte le chiavi presenti nei `.set`.
- Classificare ogni parametro come:
  - vero input;
  - parametro derivato;
  - costante interna intenzionale;
  - variabile erroneamente non esposta;
  - parametro deprecato.
- Eliminare o migrare chiavi morte.
- Definire precedenza tra:
  - input globale;
  - profilo strategia;
  - override runtime;
  - fallback.
- Stampare all'avvio i valori effettivi, non solo quelli richiesti.

### Test obbligatori

- `.set` con chiave sconosciuta: il test deve fallire.
- Modifica di un input sentinella: il valore runtime deve cambiare nel log.
- Override concorrenti: il log deve mostrare quale livello ha vinto.

### Done quando

Nessun parametro può essere ignorato silenziosamente.

---

## P0.3 — Identità univoca di ogni passata

### Obiettivo

Impedire che una passata venga archiviata con il nome, i parametri o la strategia sbagliati.

### Campi minimi all'avvio

- `experiment_id`;
- `run_id`;
- `requested_strategy`;
- `resolved_strategy`;
- elenco strategie abilitate;
- `strategy_selector`;
- simbolo;
- timeframe richiesto e risolto;
- data collection mode;
- build hash;
- config hash;
- commit SHA;
- periodo;
- parametri critici;
- timestamp di inizio.

### Vincoli

- Se `requested_strategy != resolved_strategy`, abortire.
- Se più strategie sono abilitate in un test isolato, abortire.
- Se il report è identico a uno storico incompatibile, abortire.
- Se il timestamp del file non è successivo all'inizio della passata, abortire.
- Se il report non contiene l'identità prevista, non archiviarlo.

### Done quando

Non è possibile etichettare un test LIQ_SWEEP come ADX_RSI o viceversa.

---

## P0.4 — Idempotenza dei segnali e gate di posizione

### Obiettivo

Evitare che frequenza tick, riavvio EA o segnali persistenti alterino artificialmente il numero di trade.

### Attività

- Applicare il gate "una posizione per strategia" in tutti i path.
- Verificare Data Collection Mode separatamente.
- Distinguere:
  - segnali evento;
  - segnali stato;
  - segnali validi solo a chiusura barra.
- Inserire edge detection per segnali persistenti.
- Rendere esplicita la policy multi-entry per le sole strategie che la richiedono.
- Verificare comportamento al riavvio dell'EA.
- Rendere coerenti cooldown, nuova barra e posizione esistente.

### Test obbligatori

- Segnale vero per 20 barre: numero aperture conforme alla policy.
- Doppio tick sulla stessa barra: nessuna duplicazione.
- Riavvio EA con posizione aperta: nessun nuovo ordine duplicato.
- Data Collection ON/OFF: stessa logica di gate, salvo differenze dichiarate.

### Done quando

Il numero di trade non dipende dalla densità dei tick per strategie bar-based.

---

## P0.5 — Unica source of truth strategia → configurazione

### Obiettivo

Eliminare mappe duplicate e fallback temporali errati.

### Creare un registro centralizzato per ogni strategia

- id;
- nome canonico;
- stato attivo/disattivo;
- source timeframe;
- execution timeframe;
- sessione;
- min hold;
- max hold;
- cooldown;
- profilo SL/TP;
- policy multi-entry;
- policy BUY/SELL;
- dipendenze indicatori;
- modalità trigger;
- versione logica.

### Vincoli

Tutti i componenti devono leggere lo stesso registro:

- SignalRouter;
- protezioni;
- duration manager;
- logger;
- StrategySelector;
- runner;
- dashboard;
- Backtest Lab, quando applicabile.

### Done quando

Nessuna strategia può finire su un default generico senza errore esplicito.

---

## P0.6 — Riconciliazione completa dei trade

### Log minimo per ogni trade

- run id;
- build id;
- config hash;
- strategy id/name/version;
- direction;
- setup timestamp;
- signal timestamp;
- entry timestamp/prezzo;
- SL/TP iniziali;
- lotto;
- rischio monetario;
- ticket e position id;
- timeframe risolto;
- sessione;
- regime;
- score locale;
- modificatori globali separati;
- filtri passati/bloccanti;
- spread, slippage, commissioni;
- MFE e MAE;
- exit timestamp/prezzo/reason;
- durata;
- P&L monetario;
- R multiple.

### Riconciliazioni

- ogni OPEN ha un CLOSE;
- ogni CLOSE ha un OPEN;
- history MT5 = trade log;
- somma trade = report Tester;
- contatore strategia = righe CSV;
- P&L lordo/netto coerente;
- nessun ticket duplicato.

### Done quando

Le differenze sono zero o documentate da una regola verificabile.

---

## P0.7 — Validazione del runner automatico

### Attività

- Verificare che ogni processo precedente sia concluso.
- Pulire o versionare output temporanei.
- Confermare caricamento del `.set` corretto.
- Inserire timeout controllati.
- Gestire crash e test incompleti.
- Non considerare concluso un test solo perché esiste un file.
- Generare un `run_status.json` con:
  - started;
  - completed;
  - failed;
  - aborted;
  - reason.

### Done quando

Un batch non può proseguire silenziosamente dopo una passata fallita o contaminata.

---

# 5. P1 — Fondazione software, osservabilità e collaborazione

## P1.1 — Manifest standard per gli esperimenti

Ogni esperimento deve produrre un file machine-readable:

```yaml
experiment_id:
owner:
agent:
branch:
base_commit:
head_commit:
build_hash:
objective:
hypothesis:
strategy:
strategy_version:
direction:
symbol:
timeframe:
period:
data_source:
data_quality:
config_hash:
controlled_variables:
changed_variables:
expected_effect:
result_files:
metrics:
verdict:
limitations:
next_action:
```

Senza manifest, il risultato è solo esplorativo.

---

## P1.2 — Protocollo multi-agente

### Branch

```text
agent/<nome>/<ticket>
```

### Handoff obbligatorio

Ogni agente deve creare:

```text
vault/01-Trading/Agent-Handoffs/HANDOFF - <ticket> - <agente>.md
```

Contenuto minimo:

- obiettivo;
- contesto letto;
- file analizzati;
- file modificati;
- decisioni prese;
- test eseguiti;
- risultati;
- assunzioni;
- rischi;
- elementi non verificati;
- commit;
- prossima azione consigliata.

### Regole anti-conflitto

- un owner per ticket;
- nessun agente modifica la stessa area senza coordinamento;
- rebase/fetch prima del lavoro;
- nessuna riscrittura della storia condivisa;
- le decisioni approvate non si mescolano alle note di ricerca;
- ogni agente deve indicare cosa **non** ha verificato.

---

## P1.3 — Separare Research, Decisions, Handoffs e Status

Struttura consigliata:

```text
vault/01-Trading/
├── Research/
├── Decisions/
├── Agent-Handoffs/
├── Status/
├── Strategies/
├── Tests/
├── Incidents/
└── Archive/
```

### Regola

- **Research:** ipotesi e analisi, anche smentibili.
- **Decisions:** scelta approvata con evidenze e commit.
- **Handoffs:** passaggio operativo tra agenti.
- **Status:** fotografia aggiornata del progetto.
- **Incidents:** bug che hanno invalidato dati o test.
- **Archive:** documenti superati, mai cancellati senza traccia.

---

## P1.4 — Test automatici minimi

### MQL5

- compilazione senza errori;
- warning trattati e classificati;
- test del registry strategie;
- test del selector;
- test dei gate;
- test duration/timeframe;
- test config hash;
- test logger;
- smoke test di ogni strategia.

### Python

- unit test dei proxy;
- test input/output del Backtest Lab;
- test di coerenza timeframe;
- test metriche;
- test parser report MT5;
- test duplicati;
- test manifest;
- test determinismo.

### Done quando

Una pull request non può essere considerata pronta se i test minimi non passano.

---

## P1.5 — CI e controlli pre-merge

Pipeline raccomandata:

1. lint e formattazione;
2. compilazione;
3. unit test;
4. test registry;
5. test config;
6. smoke test;
7. validazione manifest;
8. confronto snapshot;
9. report finale.

Ogni modifica al router, registry, input o protezioni deve attivare test più severi.

---

## P1.6 — Telemetria e dashboard tecnica

La dashboard deve mostrare almeno:

- build e commit attivi;
- strategie abilitate;
- posizioni per strategia;
- trade giornalieri;
- errori di configurazione;
- fallback usati;
- segnali generati e bloccati;
- motivi di blocco;
- rischio corrente;
- drawdown giornaliero e dal picco;
- heartbeat LocalBridge;
- stato logger;
- divergenze tra runtime e configurazione attesa.

---

# 6. P2 — Ricostruire una baseline affidabile delle 37 strategie

## P2.1 — Inventario canonico

Per ogni strategia creare una scheda con:

- nome e id;
- stato connessione;
- file sorgente;
- trigger reale;
- indicatori;
- timeframe;
- sessione;
- direzioni supportate;
- parametri;
- uscita;
- rischio;
- proxy Python equivalente;
- livello di fedeltà;
- ultimo test affidabile;
- campione;
- verdict.

Nessuna strategia deve esistere solo nel router senza scheda o viceversa.

---

## P2.2 — Smoke test isolato di tutte le strategie

Per ciascuna strategia:

- abilitarla da sola;
- verificare che generi il tipo di segnale previsto;
- controllare BUY/SELL;
- verificare TF e sessione;
- controllare gate e durata;
- produrre log completo;
- controllare che nessun'altra strategia operi;
- verificare assenza di errori runtime.

Output: matrice `PASS / FAIL / NO_SIGNAL / NOT_CONNECTED`.

---

## P2.3 — Classificare i risultati storici

Ogni dataset o report esistente deve essere marcato come:

- **VALIDATED:** pipeline e configurazione dimostrate corrette;
- **USABLE_WITH_LIMITS:** utile ma con limitazioni note;
- **EXPLORATORY:** genera ipotesi, non decisioni;
- **INVALID:** contaminato, errato o non attribuibile;
- **UNKNOWN:** non ancora verificato.

Non cancellare i dati invalidi: archiviarli con spiegazione.

---

## P2.4 — Nuovo test diagnostico standard

Ordine consigliato per ogni strategia:

1. trigger base senza filtri globali non essenziali;
2. BUY e SELL separati;
3. timeframe nativo;
4. uscita base fissa;
5. rischio costante in R;
6. nessun compounding;
7. spread e costi realistici;
8. campione multi-regime;
9. out-of-sample separato;
10. stabilità per anno e trimestre.

### Metriche minime

- numero trade;
- expectancy in R;
- profit factor;
- win rate;
- payoff medio;
- max drawdown;
- longest losing streak;
- dispersione annuale;
- percentuale anni positivi;
- MFE/MAE;
- durata;
- sensibilità ai costi;
- concentrazione del profitto.

---

## P2.5 — Walk-forward e robustezza

Per ogni strategia candidata:

- sviluppo;
- validazione;
- out-of-sample;
- rolling walk-forward;
- test su regimi differenti;
- perturbazione parametri;
- Monte Carlo dell'ordine trade;
- sensibilità spread/slippage;
- test con ritardo ingresso;
- test su dati non usati nel tuning.

### Promozione minima

Una strategia non è valida perché ha il miglior parametro. È candidata se mostra un **plateau robusto**, non un picco isolato.

---

## P2.6 — Classificazione finale delle strategie

Categorie suggerite:

- **Core:** robusta, campione sufficiente, utile al portafoglio.
- **Satellite:** edge valido ma dipendente da regime o sessione.
- **Experimental:** promettente, ancora non validata.
- **Research-only:** utile per studio, non per trading.
- **Disabled:** non connessa, duplicata o priva di edge.
- **Rejected:** fallisce criteri minimi dopo test affidabili.

---

# 7. P3 — Rifattorizzare l'architettura decisionale

## P3.1 — Separare le responsabilità

Il motore deve distinguere chiaramente:

1. **Setup validity:** il pattern esiste?
2. **Timing:** è il momento corretto per entrare?
3. **Context:** regime, sessione e direzione sono compatibili?
4. **Execution:** spread, liquidità e distanza ordine sono accettabili?
5. **Risk:** il trade può essere aperto in sicurezza?
6. **Portfolio priority:** esistono conflitti o concentrazioni?
7. **Position management:** come si gestisce dopo l'ingresso?

Uno score unico non deve nascondere queste dimensioni.

---

## P3.2 — Ridisegnare lo score

### Problema

Un EntryScore globale può ricreare dipendenza tra strategie teoricamente indipendenti.

### Direzione consigliata

- score locale specifico della strategia;
- componenti leggibili e registrate separatamente;
- nessuna somma arbitraria di conferme eterogenee;
- blocker duri distinti da preferenze morbide;
- calibrazione empirica dello score;
- verifica monotonicità: score più alto deve mostrare edge maggiore, altrimenti lo score non va usato come soglia.

### Possibile output

```text
setup_quality
signal_freshness
market_context
execution_quality
risk_permission
portfolio_priority
```

---

## P3.3 — Regime engine

Definire regimi osservabili e non ridondanti:

- trend;
- range;
- transizione;
- volatilità alta/bassa;
- compressione/espansione;
- sessione liquida/illiquida;
- rischio evento.

Ogni strategia deve dichiarare:

- regimi consentiti;
- regimi vietati;
- regimi neutrali;
- evidenza empirica del comportamento.

Evitare un regime engine che blocca tutto senza dimostrare beneficio.

---

## P3.4 — Multi-timeframe e struttura

- separare TF di rilevazione, contesto ed esecuzione;
- evitare tabelle duplicate;
- trattare struttura interna ed esterna come varianti testabili;
- non imporre conferme cumulative senza A/B test;
- registrare quale variante ha generato il trade;
- evitare look-ahead e repaint negli swing.

---

## P3.5 — State machine delle strategie

Le strategie complesse devono esporre stati espliciti:

```text
IDLE
SETUP_DETECTED
ARMED
TRIGGERED
ORDER_SENT
POSITION_OPEN
MANAGING
COOLDOWN
INVALIDATED
```

Questo riduce:

- riaperture duplicate;
- segnali persistenti;
- conflitti tra barre;
- log ambigui;
- differenze tra test e live.

---

## P3.6 — Gestione dei conflitti

Quando più strategie segnalano contemporaneamente:

- non fondere automaticamente i segnali;
- registrare correlazione e direzione;
- definire limite rischio per cluster;
- evitare esposizione multipla equivalente;
- distinguere consenso da duplicazione;
- decidere se usare ranking, quota rischio o priorità di portafoglio.

---

# 8. P4 — Migliorare edge, uscite, rischio e portafoglio

## P4.1 — Ottimizzazione strategia per strategia

Ordine corretto:

1. fedeltà del trigger;
2. qualità del setup;
3. BUY/SELL;
4. timing;
5. contesto;
6. uscita;
7. rischio;
8. interazione portafoglio.

Non ottimizzare tutto insieme.

---

## P4.2 — Uscite basate su MFE/MAE

Per ogni strategia analizzare:

- MFE dei vincenti e perdenti;
- MAE dei vincenti;
- tempo al MFE;
- tempo all'invalidazione;
- percentuale trade fermati prima del movimento favorevole;
- efficienza dell'uscita;
- distribuzione per direzione e regime.

Testare separatamente:

- SL fisso;
- SL ATR;
- target fisso;
- target strutturale;
- break-even;
- partial close;
- trailing;
- time stop;
- uscita per invalidazione;
- combinazioni limitate e motivate.

Break-even e trailing devono essere esperimenti distinti.

---

## P4.3 — Risk engine

Priorità:

- rischio per trade espresso in R o percentuale equity;
- limite rischio per strategia;
- limite rischio per cluster correlato;
- limite esposizione totale;
- daily stop;
- weekly stop;
- drawdown dal picco;
- perdita consecutiva;
- margin guard;
- equity floor;
- spread/slippage guard;
- kill switch.

### Divieti iniziali

- martingala non validata;
- aumento lotto per recupero emotivo;
- compounding aggressivo;
- hedge automatico trattato come garanzia di sicurezza.

---

## P4.4 — Portfolio construction

Per le strategie validate misurare:

- correlazione dei rendimenti;
- sovrapposizione temporale;
- concentrazione delle perdite;
- contributo al drawdown;
- marginal contribution to risk;
- stabilità per regime;
- dipendenza dallo stesso fattore di mercato;
- beneficio reale di diversificazione.

Una strategia profittevole può peggiorare il portafoglio se amplifica il drawdown nello stesso momento.

---

## P4.5 — Allineamento Python ↔ MQL5

Per ogni strategia creare test golden-case:

- stesso dataset;
- stessi indicatori;
- stessi timestamp;
- stessi parametri;
- stessi segnali attesi.

Classificare il proxy Python come:

- 1:1 fedele;
- approssimazione controllata;
- diagnostico soltanto;
- non disponibile.

Il sito non deve essere chiamato "source of truth" per strategie che non replica fedelmente.

---

## P4.6 — Ottimizzazione robusta

- usare range plausibili;
- limitare gradi di libertà;
- cercare plateau;
- penalizzare complessità;
- conservare holdout intatto;
- evitare selezione su una sola metrica;
- riportare anche configurazioni vicine;
- applicare correzione per multiple testing quando necessario.

---

# 9. P5 — Forward test e produzione

## P5.1 — Shadow mode

Prima del trading reale:

- generare segnali live senza ordini;
- confrontare con attese del backtest;
- misurare spread, ritardo e slippage potenziale;
- verificare sessioni e timezone;
- controllare riavvii e riconnessioni;
- confrontare log locale e dashboard.

---

## P5.2 — Demo e micro-live

Sequenza:

1. shadow;
2. demo;
3. micro-live a rischio minimo;
4. aumento graduale solo con criteri predefiniti.

Non saltare direttamente dal backtest al conto reale significativo.

---

## P5.3 — Resilienza operativa

Testare:

- perdita connessione;
- restart terminale;
- cambio spread improvviso;
- mercato chiuso;
- ordine rifiutato;
- partial fill;
- requote;
- simbolo con specifiche diverse;
- dati mancanti;
- LocalBridge offline;
- dashboard offline;
- file bloccato;
- disco pieno;
- clock/timezone errato.

---

## P5.4 — Release process

Ogni release deve avere:

- versione semantica;
- changelog;
- commit/tag;
- build hash;
- manifest;
- test passati;
- strategie abilitate;
- parametri approvati;
- rischi noti;
- rollback plan;
- approvazione esplicita.

---

# 10. Criteri di promozione di una strategia

Una strategia entra nel portafoglio solo se:

- trigger verificato nel codice;
- smoke test passato;
- log riconciliato;
- campione sufficiente;
- expectancy positiva fuori campione;
- costi realistici inclusi;
- parametri non dipendenti da un singolo picco;
- comportamento BUY/SELL conosciuto;
- drawdown compatibile;
- nessuna dipendenza da bug o fallback;
- contributo al portafoglio positivo;
- forward test coerente.

Una strategia può essere valida anche con win rate basso, se expectancy e rischio sono solidi.

---

# 11. Metriche obbligatorie per sistema e strategia

## Strategia

- trade count;
- expectancy R;
- PF;
- win rate;
- average win/loss;
- max DD;
- recovery factor;
- longest losing streak;
- MFE/MAE;
- tempo medio in posizione;
- distribuzione annuale;
- BUY vs SELL;
- regime;
- sessione;
- cost sensitivity;
- parameter stability.

## Portafoglio

- rendimento netto;
- max DD;
- DD dal picco;
- tempo di recupero;
- correlazione;
- contributo per strategia;
- concentrazione del rischio;
- esposizione simultanea;
- perdita peggiore giornaliera/settimanale;
- tail risk;
- rischio di rovina;
- stabilità per regime.

## Infrastruttura

- test falliti;
- run abortiti;
- mismatch config;
- mismatch report;
- trade non riconciliati;
- fallback;
- errori runtime;
- heartbeat;
- build attiva.

---

# 12. Errori da non ripetere

- fidarsi del nome di un file `.set`;
- fidarsi dell'etichetta del report;
- confrontare report senza build/config hash;
- ottimizzare su tre mesi e dichiarare validazione;
- usare pochi trade come prova;
- modificare cinque componenti nello stesso test;
- trattare il sito come equivalente MT5 senza test 1:1;
- usare uno score aggregato non calibrato;
- aggiungere filtri solo perché suonano professionali;
- confondere meno trade con maggiore qualità;
- disattivare BUY o SELL senza analisi separata;
- considerare il trailing sempre migliore;
- usare hedge come sostituto del controllo rischio;
- lasciare default silenziosi;
- cancellare risultati invalidi senza spiegazione;
- modificare `main` senza branch e handoff;
- fare release senza rollback.

---

# 13. Ordine consigliato dei ticket

## Sprint 1 — Integrità

1. `INFRA-001` — Experiment identity e manifest.
2. `INFRA-002` — Audit input e validazione `.set`.
3. `INFRA-003` — Strategy registry unico.
4. `INFRA-004` — Gate posizione e idempotenza segnali.
5. `INFRA-005` — Riconciliazione trade e report.
6. `INFRA-006` — Runner fail-fast e duplicate detection.

## Sprint 2 — Testabilità

7. `QA-001` — Test automatici registry/selector/config.
8. `QA-002` — Smoke test delle 37 strategie.
9. `QA-003` — Classificazione dataset storici.
10. `QA-004` — Golden test Python ↔ MQL5.

## Sprint 3 — Baseline

11. `VAL-001` — Baseline trigger puro.
12. `VAL-002` — BUY/SELL separati.
13. `VAL-003` — Walk-forward e perturbazione.
14. `VAL-004` — Classificazione Core/Satellite/Experimental/Rejected.

## Sprint 4 — Architettura

15. `ARCH-001` — Separazione setup/context/execution/risk.
16. `ARCH-002` — Score locale e calibrazione.
17. `ARCH-003` — Regime engine.
18. `ARCH-004` — State machine strategie.
19. `ARCH-005` — Conflict e portfolio allocator.

## Sprint 5 — Edge e rischio

20. `EDGE-001` — Studio uscite MFE/MAE.
21. `EDGE-002` — Risk engine.
22. `EDGE-003` — Portfolio construction.
23. `EDGE-004` — Ottimizzazione robusta.

## Sprint 6 — Produzione

24. `LIVE-001` — Shadow mode.
25. `LIVE-002` — Demo controlled rollout.
26. `LIVE-003` — Resilience tests.
27. `LIVE-004` — Release pipeline e rollback.

---

# 14. Primo incarico da assegnare al programmatore

## Ticket: INFRA-001 — Test Integrity and Experiment Identity

### Obiettivo

Rendere ogni passata MT5 identificabile, verificabile e non confondibile con altre.

### Scope autorizzato

- manifest;
- run id;
- build id;
- config hash;
- requested/resolved strategy;
- validazione del report;
- abort su mismatch;
- log di avvio;
- test di regressione.

### Fuori scope

- modifiche ai trigger;
- modifiche allo score;
- nuovi filtri;
- SL/TP;
- sizing;
- martingala;
- hedge;
- ottimizzazione parametri.

### Acceptance criteria

- ogni run produce manifest completo;
- strategia richiesta e risolta coincidono;
- build e config sono tracciate;
- un report vecchio o duplicato non viene accettato;
- un `.set` incompatibile genera errore;
- esiste almeno un test che riproduce il vecchio bug e ora fallisce correttamente;
- documentazione e handoff aggiornati.

### Deliverable richiesti

- branch dedicato;
- codice;
- test;
- esempio manifest;
- esempio log;
- nota handoff;
- elenco rischi residui;
- pull request senza modifiche strategiche.

---

# 15. Checklist prima di ogni commit

- [ ] Il ticket ha uno scope preciso.
- [ ] Il branch è aggiornato.
- [ ] Non sto modificando aree fuori scope.
- [ ] Ho separato fatti e ipotesi.
- [ ] Ho aggiunto o aggiornato i test.
- [ ] La compilazione passa.
- [ ] Non ho introdotto default silenziosi.
- [ ] Log e manifest sono aggiornati.
- [ ] Ho indicato i file modificati.
- [ ] Ho scritto cosa non ho verificato.

---

# 16. Checklist prima del merge

- [ ] Acceptance criteria soddisfatti.
- [ ] Test automatici passati.
- [ ] Smoke test eseguito.
- [ ] Nessun cambiamento strategico nascosto.
- [ ] Configurazione retrocompatibile o migrazione documentata.
- [ ] Handoff presente.
- [ ] Vault aggiornata.
- [ ] Changelog aggiornato.
- [ ] Piano rollback disponibile.
- [ ] Review di almeno un altro agente/programmatore.

---

# 17. Checklist prima di dichiarare una versione pronta al live

- [ ] P0 completamente chiusa.
- [ ] P1 completamente chiusa.
- [ ] Strategie abilitate validate fuori campione.
- [ ] Costi realistici inclusi.
- [ ] Risk engine testato.
- [ ] Drawdown dal picco protetto.
- [ ] Shadow mode completata.
- [ ] Demo completata.
- [ ] Recovery e restart testati.
- [ ] Telemetria attiva.
- [ ] Kill switch verificato.
- [ ] Rollback disponibile.
- [ ] Rischio iniziale minimo.

---

# 18. Formato obbligatorio del responso di un agente

Ogni agente che analizza questo documento deve rispondere con:

```markdown
## Comprensione
Cosa ritiene essere il problema principale.

## Evidenze verificate
File e funzioni realmente controllati.

## Evidenze non verificate
Cosa sta assumendo.

## Rischi critici
Bug o debiti tecnici che possono invalidare i risultati.

## Piano proposto
Ticket ordinati con dipendenze.

## Primo intervento
Modifica più piccola ad alto impatto.

## Test
Come dimostrare che la modifica funziona.

## File coinvolti
Elenco preciso.

## Fuori scope
Cosa non verrà modificato.
```

Questo formato impedisce risposte generiche e rende confrontabili più agenti.

---

# 19. Definizione di successo del progetto

NEXUS EA può essere considerato maturo quando:

- ogni trade è attribuibile e riconciliabile;
- ogni configurazione è verificabile;
- ogni strategia ha una scheda e uno stato reale;
- Python e MQL5 dichiarano chiaramente il livello di equivalenza;
- i risultati sono riproducibili;
- gli esperimenti hanno manifest;
- i bug infrastrutturali hanno test di regressione;
- lo score è empiricamente calibrato oppure rimosso come gate;
- il rischio protegge sia il giorno sia il drawdown dal picco;
- il portafoglio è costruito su contributo marginale e non su intuizione;
- il forward test conferma comportamento, frequenza e costi;
- più agenti possono lavorare senza perdere la storia decisionale.

---

# 20. Istruzione finale per il programmatore

Non iniziare ottimizzando le strategie.

Prima:

1. leggi questa roadmap;
2. confrontala con il codice reale;
3. segnala ciò che è già stato implementato;
4. segnala ciò che è solo documentato;
5. identifica contraddizioni tra vault e repository;
6. proponi il piano minimo per chiudere P0;
7. esegui per primo `INFRA-001`;
8. non modificare trigger, score o rischio finché l'integrità dei test non è dimostrata.

La qualità del sistema dipende prima dalla qualità delle prove, poi dalla qualità delle strategie.

## Collegamenti
[[MOC - Trading]]
