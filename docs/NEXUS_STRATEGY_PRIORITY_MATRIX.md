# NEXUS — MATRICE DI PRIORITÀ E ORDINE DI RICOSTRUZIONE

> Consegna 1 del `NEXUS_CLOUD_STRATEGY_WORK_PACKAGE_v1` (§22.3 / §27.4–§27.7).
> **Documento analitico.** Contiene *proposte*. Nessuna è stata applicata:
> §27 impone che la prima consegna non modifichi il comportamento delle
> strategie, e non l'ha modificato.

| | |
|---|---|
| Data | 2026-07-26 |
| Baseline congelata (STEP 0) | `4465873` |
| Branch | `claude/strategy-work-package-v1` |
| Documenti di riferimento | `docs/NEXUS_STRATEGY_INVENTORY.md`, `docs/NEXUS_STRATEGY_MISMATCH_REPORT.md` |

## Vincolo §21 applicato a tutto ciò che segue

Nessuna azione proposta in questo documento aumenta l'esposizione in LIVE. Le
azioni che *potrebbero* farlo sono marcate **⚠️ tocca l'esposizione** e sono
tutte collocate fra le decisioni che richiedono la tua approvazione (§27.7), mai
fra i lavori eseguibili.

## Cosa questa consegna NON afferma

Richiesto esplicitamente da §26, e vale per ogni riga sotto:

- Non afferma che una strategia sia valida, né che una sia da buttare.
- Non afferma che il sistema sia pronto per la produzione. Non lo è: il vincolo
  precedente resta invariato (nessuna riga di `MQL5/` è mai stata compilata).
- Non afferma che i numeri delle 8 strategie misurate descrivano un edge. Sono
  passate isolate a lotto fisso in `DataCollectionMode`: misurano il
  comportamento del trigger.
- Non usa la permutazione dell'ordine dei trade come prova di edge. §15 ha
  ragione: permutare conserva il totale, serve per il rischio di sequenza e il
  drawdown, non dimostra l'edge. Una mia affermazione precedente in senso
  contrario era sbagliata.
- Non conta "37 strategie" come 37 misure indipendenti. Non lo sono (MM-04).

---

## §27.4 · Priorità dei mismatch

Criterio di gravità, dichiarato invece che assunto:

| | Criterio |
|---|---|
| **P0** | Invalida conclusioni già tratte, oppure agisce oggi sul capitale |
| **P1** | Falsa i confronti fra strategie, o nasconde l'assenza di evidenza |
| **P2** | Igiene: non falsa nulla adesso, costa alla prima modifica |

### P0

| ID | Azione proposta | Cambia comportamento? | Nota |
|---|---|---|---|
| **MM-13** | Portare `1/(n+1)` dietro un input a default `false`, oppure rimuoverla conservando la versione (§3.2) | **sì** ⚠️ tocca l'esposizione | **Decisione D1** — è il primo punto che ti chiedo. Nessuna azione senza risposta |
| **MM-04** | Dichiarare nel registro che 3 coppie condividono la funzione research; escluderle dai conteggi di indipendenza | no (solo dichiarazione) | Eseguibile subito. L'implementazione separata è lavoro successivo |
| **MM-06** | Eseguire le 29 passate isolate mancanti (28 mai fatte + `SAR` sulla baseline corrente) | no (è misura) | Costo: tempo macchina. **Decisione D6** sull'ampiezza |
| **MM-01** | Riempire `selector_index` per le 14 voci in `knowledge/strategy_database.json`, rigenerare il registro | no (solo dato) | Prerequisito tecnico di MM-06: senza indice non si isola |
| **MM-02** | `DISP_REBAL` gira mentre il registro la dichiara spenta, e il control plane non può spegnerla | dipende dall'opzione | **Decisione D3** — tre opzioni, una sola senza cambio di comportamento |

### P1

| ID | Azione proposta | Cambia comportamento? |
|---|---|---|
| **MM-10** | Invertire la direzione della derivazione: l'input MQL5 è il fatto, il registro lo rispecchia; il parsing di prosa smette di decidere `default_enabled` | no — **Decisione D2** |
| **MM-05** | Correggere `PROXY_MAP` sul bersaglio reale, o derivarla dal codice invece che scriverla a mano | no |
| **MM-12** | Unificare le due tassonomie di famiglia, o dichiarare che `_nxs_inst_family()` non è una misura di correlazione | no se solo dichiarativo; **sì** se cambia la pesatura ⚠️ |
| **MM-07** | Dare profilo TF e parametrico alle 8 senza; smettere di scrivere `"*"` dove il dato è assente (usare `null`) | **sì** per i profili ⚠️; no per `null` |
| **MM-08** | Indicizzare `THREE_BAR_DELIVERY_BREAK` anche per id canonico in `STRATEGIES` | no |
| **MM-09** | Esporre nel frontend `research_parity`, `proxy_for` e la presenza di evidenza | no |
| **MM-03** | `ELLIOTT`: riconciliare `status`, assenza di research e input a `false` | no — **Decisione D5** |

### P2

| ID | Azione proposta | Cambia comportamento? |
|---|---|---|
| **MM-11** | Collegare ogni `bug_storici` / `fix_applicati` a un commit verificabile | no |

---

## §27.5 · Ordine di ricostruzione proposto

L'ordine non è una preferenza: ogni fase è **prerequisito** della successiva, e
il work package impone due dei passaggi (§3.10 prima la fedeltà logica poi i
parametri; §3.9 prima le strategie singole poi le combinazioni).

```
FASE A  ripristinare la capacità di MISURARE       nessun cambio di comportamento
   ↓
FASE B  rendere le misure ATTRIBUIBILI             nessun cambio di comportamento
   ↓
FASE C  verificare la FEDELTÀ logica MQL5 ↔ Python  §3.10 — prima dei parametri
   ↓
FASE D  MISURARE le 29 mancanti                    nessun cambio di comportamento
   ↓
FASE E  strategie SINGOLE, poi combinazioni        §3.9 — mai prima
```

### Fase A — ripristinare la capacità di misurare

Tutto eseguibile subito: sono dati e dichiarazioni, non logica.

1. `selector_index` per le 14 voci mancanti nel knowledge base → rigenerare
   registro e `strategyRegistry.js` (MM-01).
2. Chiave canonica per `THREE_BAR_DELIVERY_BREAK` in `STRATEGIES`, mantenendo
   `CISD` come alias (MM-08).
3. `null` al posto di `"*"` in `supported_timeframes` quando il timeframe non è
   dichiarato: un'assenza smette di leggersi come universalità (MM-07, parte
   dichiarativa).
4. `research_parity`, `proxy_for` e presenza di evidenza nel payload del
   frontend (MM-09).

**Gate di uscita:** il registro sa isolare tutte e 37, e la dashboard distingue
misurata / surrogata / ignota.

### Fase B — rendere le misure attribuibili

5. Dichiarare le 3 coppie a funzione condivisa (MM-04) e correggere `PROXY_MAP`
   sul bersaglio reale (MM-05).
6. Invertire la derivazione di `status` / `default_enabled`: dall'input MQL5 al
   registro, non dalla prosa italiana (MM-10, D2).
7. Collegare bug e fix a commit verificabili (MM-11).

**Gate di uscita:** ogni numero prodotto da qui in avanti è attribuibile a una
strategia sola e a una baseline sola.

### Fase C — fedeltà logica, prima di qualsiasi parametro

§3.10 vieta di ottimizzare parametri prima di aver verificato la fedeltà della
logica. §7 chiederebbe il confronto contro la **fonte originale**: oggi
impossibile (`SOURCE_GAP`, vedi D8). Quindi il confronto in questa fase è
`MQL5 ↔ Python`, dichiarato per quello che è.

Ordine interno, con criterio esplicito: **prima le 8 con misura sulla baseline
corrente**, perché sono le uniche dove una correzione di fedeltà ha un prima e
un dopo osservabili. In particolare `TSI` e `ADX_RSI`, i cui bug storici dicono
che il nome non descrive il trigger.

Poi le 29 senza misura, nell'ordine della tabella per strategia qui sotto.

**Gate di uscita:** per ogni strategia, una riga che dice se MQL5 e Python
implementano la stessa regola, e dove no.

### Fase D — misurare le 29 mancanti

Solo dopo C: misurare prima di aver verificato la fedeltà significa misurare una
logica che potrebbe non essere quella dichiarata — è già successo con `TSI`.

### Fase E — singole, poi combinazioni

§3.9. Nessuna combinazione, nessun router di regime, nessun ranking di
portafoglio prima che ogni strategia abbia una misura propria sulla baseline
corrente. E per ogni conclusione, §16: dichiarare **quanti tentativi** sono
stati fatti prima di arrivarci, altrimenti il migliore di 37 non è una strategia
testata.

---

## Priorità per strategia

Conteggio delle **condizioni verificate** su ciascuna strategia live. Le colonne
sono fatti binari letti dalle fonti, non giudizi:

| Sigla | Condizione |
|---|---|
| `dup` | Condivide la funzione research con un'altra strategia (MM-04) |
| `prox` | Dichiarata proxy nel registro (MM-05) |
| `nosw` | Nessuna passata isolata (MM-06) |
| `offb` | Passata isolata su una baseline diversa (MM-06) |
| `bnf` | Bug storici registrati, nessun fix registrato (MM-11) |
| `nopr` | Nessun profilo TF né parametrico (MM-07) |
| `nosel` | `selector_index` assente dal registro (MM-01) |
| `stat` | Stato dichiarato ≠ default dell'input MQL5 (MM-02, MM-03) |
| `nopy` | Nessuna implementazione research (MM-03) |

> **`n` non è un punteggio.** È il numero di condizioni verificate. Non misura
> qualità, non ordina per bontà, e **non deve entrare in nessun calcolo di
> sizing** — sarebbe esattamente l'errore di MM-13.

| Strategia | n | dup | prox | nosw | offb | bnf | nopr | nosel | stat | nopy | trade |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ELLIOTT` | 5 | | | X | | X | X | | X | X | — |
| `SMS_BMS_RTO` | 5 | X | X | X | | X | | X | | | — |
| `AMD_REVERSAL` | 4 | | | X | | X | X | X | | | — |
| `JUDAS_SWING` | 4 | | | X | | X | X | X | | | — |
| `PO3` | 4 | | | X | | X | X | X | | | — |
| `WEEKLY_EXP` | 4 | X | X | X | | | | X | | | — |
| `AMD_CONT` | 3 | | | X | | | X | X | | | — |
| `DISP_REBAL` | 3 | | | X | | | | X | X | | — |
| `LDN_REVERSAL` | 3 | | | X | | | X | X | | | — |
| `LIQ_VOID` | 3 | | X | X | | | | X | | | — |
| `LONDON_BO` | 3 | X | X | X | | | | | | | — |
| `NY_REVERSAL` | 3 | | | X | | | X | X | | | — |
| `RANGE_FADE` | 3 | X | X | X | | | | | | | — |
| `SH_BMS_RTO` | 3 | X | X | X | | | | | | | — |
| `SILVER_BULLET` | 3 | | | X | | | X | X | | | — |
| `MALAYSIAN_SNR` | 2 | | | X | | | | X | | | — |
| `OTE_CONT` | 2 | | | X | | | | X | | | — |
| `RSI_DIV` | 2 | | | X | | X | | | | | — |
| `SAR` | 2 | | | | X | X | | | | | 261 |
| `STRUCT_REACT` | 2 | | | X | | X | | | | | — |
| `THREE_BAR_DELIVERY_BREAK` | 2 | | | X | | | | X | | | — |
| `BB_SQUEEZE` | 1 | | | X | | | | | | | — |
| `BOLLINGER` | 1 | X | | | | | | | | | 144 |
| `EMA_PULLBACK` | 1 | | | X | | | | | | | — |
| `FVG_MIT` | 1 | | | X | | | | | | | — |
| `ICHIMOKU` | 1 | | | X | | | | | | | — |
| `IFVG` | 1 | | | X | | | | | | | — |
| `OB_MIT` | 1 | | | X | | | | | | | — |
| `ORDER_BLOCK` | 1 | | | X | | | | | | | — |
| `TURTLE_SOUP` | 1 | | | X | | | | | | | — |
| `ADX_RSI` | 0 | | | | | | | | | | 915 |
| `BJORGUM` | 0 | | | | | | | | | | 397 |
| `BREAKOUT_ACC` | 0 | | | | | | | | | | 216 |
| `FVG_CONT` | 0 | | | | | | | | | | 251 |
| `LIQ_SWEEP` | 0 | | | | | | | | | | 292 |
| `MACD` | 0 | | | | | | | | | | 1244 |
| `TSI` | 0 | | | | | | | | | | 839 |

**`n = 0` non significa "a posto".** `TSI` ha zero condizioni aperte qui e porta
il bug storico *"CRITICO: non calcolava TSI, era RSI+EMA20 col nome sbagliato"*
— con fix registrato, ma il fix non è collegato a un commit verificabile
(MM-11). Sono esattamente le strategie da verificare per prime in Fase C.

---

## §27.6 · Informazioni mancanti

Marcate `SOURCE_GAP`: non sono opinioni, sono cose che nel repository non ci
sono e che servono per completare il lavoro.

1. **`NEXUS_CORPUS_SEMANTIC_AUDIT_PRELIMINARY_v1.md`** — citato dal work
   package, assente. Blocca il confronto richiesto da §7.
2. **PDF e materiali di corso** — assenti. Per le strategie SMC/ICT non esiste,
   nel repository, la definizione d'origine contro cui verificare la fedeltà
   concettuale. Senza questi, la Fase C può confrontare solo MQL5 con Python:
   può dire se le due implementazioni concordano, **non** se implementano la
   strategia giusta.
3. **29 passate isolate mancanti** — 28 mai eseguite, `SAR` solo su baseline
   precedente.
4. **Nessun risultato out-of-sample congelato.** Non risulta, per nessuna
   strategia, una data di congelamento con esito registrato dopo di essa (§16).
5. **Nessun conteggio dei tentativi.** Non risulta quante varianti, timeframe,
   simboli e combinazioni parametriche siano state provate prima della
   configurazione attuale (§16). Senza questo numero, "la migliore di 37" non è
   una misura interpretabile.
6. **Disponibilità di candele intraday reali** per il motore Python. Il codice
   stesso annota le strategie di sessione con *"richiedono candele intraday
   reali"*: non è verificabile da qui se quei dati esistano. Determina se le 8
   strategie `SESSION`/`AMD` siano misurabili in ricerca (Decisione D7).
7. **Corrispondenza fix ↔ commit** per i 42 bug storici (MM-11).
8. **Motivo per cui `DISP_REBAL` è "disabilitata in produzione reale"** — la
   frase è nel knowledge base senza una ragione registrata. Serve per D3, perché
   §3.3 richiede un report motivato per una disattivazione permanente.

---

## §27.7 · Decisioni che richiedono la tua approvazione

Per ognuna: cosa c'è oggi, le opzioni, la mia raccomandazione, e cosa faccio nel
frattempo. **Nel frattempo non faccio niente su nessuna di queste.**

### D1 · L'euristica `1/(n+1)` sulla conviction correlata ⚠️ tocca l'esposizione

**È mia.** L'ho introdotta nella remediation v18 senza validarla. §3.4 vieta di
modificare il sizing con euristiche inventate, §20 vieta di adottare `1/(n+1)`
come correzione canonica senza validazione, e la famiglia su cui poggia è un
classificatore a sottostringa che mette 12 strategie eterogenee in `OTHER`
(MM-12). Oggi è attiva e non disattivabile.

| Opzione | Cosa fa | Effetto |
|---|---|---|
| **A (raccomandata)** | Input dedicato, default `false` | Comportamento pre-remediation ripristinato; la formula resta nel codice, documentata e testabile, e la versione è conservata (§3.2) |
| B | Rimozione completa | Perde la possibilità di confrontarla; §3.2 impone comunque di conservare la versione altrove |
| C | Lasciarla attiva e validarla dopo | Continua a modificare il sizing con un'euristica non validata mentre la si studia |

Raccomando **A**: è l'unica che rispetta contemporaneamente §3.4 (smette di
agire), §3.2 (conserva la versione) e §20 (diventa disattivabile, confrontabile
con la baseline, testabile). Riduce l'esposizione rispetto a oggi, quindi §21 è
soddisfatto.

### D2 · Chi è la fonte di verità per "questa strategia è accesa?"

Oggi: `default_enabled` deriva dal parsing di una frase in italiano nel knowledge
base (MM-10). Il fatto operativo è l'input MQL5.

Raccomando: **l'input MQL5 è il fatto**, il registro lo rispecchia estraendolo da
`NXS_Inputs.mqh`, e un controllo in CI fallisce se divergono. Nessun cambio di
comportamento: cambia solo chi copia da chi. Rende MM-02 visibile invece che
silenzioso.

### D3 · `DISP_REBAL` ⚠️ tocca l'esposizione nell'opzione C

Gira di default (`InpUseStrat_DispRebal = true`), il registro la dichiara
`DISABLED`, e `auto_disable_eligible: false` impedisce al control plane di
spegnerla. Non ha dati di sweep.

| Opzione | Cosa fa | Effetto |
|---|---|---|
| A | Correggere solo la dichiarazione del registro | Nessun cambio di comportamento; resta accesa |
| **B (raccomandata)** | Come A, più `auto_disable_eligible: true` | Nessun cambio di comportamento di default; **restituisce** alla dashboard la facoltà di spegnerla. Amplia il controllo, non l'esposizione |
| C | `InpUseStrat_DispRebal = false` | Cambio di comportamento. §3.3 richiede un report motivato, e la motivazione oggi **non esiste** nel repository (vedi §27.6 punto 8) |

Raccomando **B**. C resta possibile, ma solo dopo che mi avrai detto *perché* è
"disabilitata in produzione reale": senza quel motivo il report richiesto da
§3.3 sarebbe inventato.

### D4 · Le 6 strategie proxy / a segnale condiviso

`RANGE_FADE`, `LONDON_BO`, `WEEKLY_EXP`, `LIQ_VOID`, `SH_BMS_RTO`,
`SMS_BMS_RTO`. §2 vieta di cancellarle e non lo propongo.

| Opzione | Cosa fa | Effetto |
|---|---|---|
| **A (raccomandata)** | Dichiararle non misurabili in modo indipendente finché condividono la funzione, ed escluderle dai conteggi di indipendenza | Nessun cambio di comportamento. Onesto e immediato |
| B | Scrivere subito 6 implementazioni research distinte | Lavoro sostanziale; §7 chiederebbe la fonte originale, che manca (D8) |

Raccomando **A** adesso, **B** dopo D8.

### D5 · `ELLIOTT`

Dichiarata `ACTIVE` e `default_enabled: true` nel registro, senza implementazione
research, senza profili, con l'input MQL5 a `false` e un rename annunciato
(`FIVE_SWING_IMPULSE`) mai eseguito.

Raccomando: `status: EXPERIMENTAL`, `default_enabled` allineato all'input reale
(`false`), e registrarla come **non testabile** finché manca la controparte
research. Nessun cambio di comportamento: l'input è già `false`. Il rename è una
tua decisione a parte — ha effetti su tutti gli storici che portano il nome
`ELLIOTT`.

### D6 · Ampiezza della campagna di misura

29 passate isolate mancanti. Raccomando **tutte e 29**: finché mancano, qualsiasi
affermazione sul portafoglio riguarda 8 strategie su 37 ed è estesa alle altre 29
per analogia, che non è evidenza. Se il tempo macchina è un vincolo, dimmelo e
propongo un sottoinsieme con il criterio esplicito, invece di sceglierlo io in
silenzio.

### D7 · Le 8 strategie di sessione e AMD

`AMD_CONT`, `AMD_REVERSAL`, `JUDAS_SWING`, `LDN_REVERSAL`, `NY_REVERSAL`, `PO3`,
`SILVER_BULLET` (+ `ELLIOTT`) non hanno profilo TF né parametrico, e il motore
research annota che richiedono candele intraday reali. Prima di lavorarci devo
sapere se quei dati esistono. Se non esistono, sono strategie che girano in LIVE
e che la ricerca **non può misurare**: è una condizione da dichiarare, non da
aggirare.

### D8 · I documenti d'origine

Servono `NEXUS_CORPUS_SEMANTIC_AUDIT_PRELIMINARY_v1.md` e i materiali di corso.
Senza, la Fase C verifica che MQL5 e Python concordino, ma nessuno dei due contro
la definizione della strategia. È il limite più grande di tutto il piano, e non è
risolvibile da dentro il repository.

---

## Cosa posso iniziare senza aspettare risposta

Tutta la **Fase A** e i punti 5 e 7 della Fase B: sono dati e dichiarazioni,
nessuno tocca la logica di una strategia né l'esposizione. Se mi dici di
procedere, parto da lì mentre decidi su D1–D8.

## Collegamenti

`docs/NEXUS_STRATEGY_INVENTORY.md` · `docs/NEXUS_STRATEGY_MISMATCH_REPORT.md` ·
`docs/NORMATIVE_CONFORMANCE.md` · `docs/REMEDIATION_STATUS.md`
