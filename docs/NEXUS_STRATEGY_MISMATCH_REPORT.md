# NEXUS — REPORT DEI MISMATCH FRA LE FONTI DI VERITÀ

> Consegna 1 del `NEXUS_CLOUD_STRATEGY_WORK_PACKAGE_v1` (§22.2 / §27.3).
> **Documento analitico: nessuna riga di codice è stata modificata da questa
> consegna, nessun comportamento di strategia è cambiato** (§27).

| | |
|---|---|
| Data verifica | 2026-07-26 |
| Baseline congelata (STEP 0) | `4465873` |
| Branch | `claude/strategy-work-package-v1` |
| Inventario di riferimento | `docs/NEXUS_STRATEGY_INVENTORY.md` |
| Mismatch verificati | 13 (5 P0 · 7 P1 · 1 P2) |

---

## Cosa è stato confrontato, e cosa no

Confronto eseguito **fonte contro fonte**, non a memoria: ogni riga qui sotto è
stata riprodotta leggendo i file nella baseline congelata.

| Confronto | Eseguito |
|---|---|
| `contracts/strategy-registry.json` ↔ `knowledge/strategy_database.json` | sì |
| Registro ↔ interruttori e selettori in `MQL5/` | sì |
| Registro ↔ `server/backtest.py` (`STRATEGIES`) | sì |
| Registro ↔ `server/strategy_registry.py` e rotte `app.py` | sì |
| Registro ↔ `frontend/src/contracts/strategyRegistry.js` | sì |
| Logica MQL5 ↔ logica Python, funzione per funzione | **no — vedi sotto** |
| Codice ↔ **definizione d'origine** della strategia | **no — `SOURCE_GAP`** |

Le ultime due righe sono il limite più importante di questa consegna.

- **`SOURCE_GAP`** — `NEXUS_CORPUS_SEMANTIC_AUDIT_PRELIMINARY_v1.md`, i PDF e i
  materiali di corso citati dal work package **non sono presenti nel repository**.
  Per le strategie SMC/ICT non esiste, qui dentro, la definizione contro cui
  verificare la fedeltà concettuale richiesta da §7. Nessuna affermazione di
  fedeltà concettuale è quindi possibile in questa consegna, in nessuna direzione.
- Il confronto riga-per-riga fra il trigger MQL5 e la funzione Python di ogni
  strategia è **STEP successivo** (§27 autorizza le verifiche di fedeltà solo dopo
  l'approvazione di questa consegna). Qui è riportata solo la corrispondenza
  *strutturale* (quale funzione serve quale strategia), che è verificabile senza
  entrare nel merito della logica.

### Legenda di gravità

| | Significato |
|---|---|
| **P0** | Invalida conclusioni già tratte, o mette a rischio capitale reale |
| **P1** | Falsa i confronti fra strategie, o nasconde l'assenza di evidenza |
| **P2** | Igiene e coerenza: non falsa nulla oggi, costa dopo |

---

## MM-01 · P0 · Il registro non sa isolare 14 strategie su 37

**Fatto.** `contracts/strategy-registry.json` ha `selector_index: null` per 14
strategie **live**:

`AMD_CONT`, `AMD_REVERSAL`, `DISP_REBAL`, `JUDAS_SWING`, `LDN_REVERSAL`,
`LIQ_VOID`, `MALAYSIAN_SNR`, `NY_REVERSAL`, `OTE_CONT`, `PO3`, `SILVER_BULLET`,
`SMS_BMS_RTO`, `THREE_BAR_DELIVERY_BREAK`, `WEEKLY_EXP`.

**Il codice invece le sa isolare tutte.** Verificato in `MQL5/`: i 37 indici di
`NXS_SelectorAllows(N)` sono presenti, contigui da 1 a 37, senza buchi e senza
duplicati. Le 14 sopra hanno indici 22–35.

> Nota di verifica: durante l'estrazione ho inizialmente creduto che le 16
> strategie classiche non passassero dal selettore, e che `ORDER_BLOCK` non
> avesse indice. Entrambe le cose sono **false**: le classiche filtrano
> *dentro* la funzione trigger (`if(!InpStrat_X || !NXS_SelectorAllows(N)) return s;`),
> le SMC/ICT al punto di chiamata in `NEXUS_EA_v2.mq5`, e `ORDER_BLOCK` ha
> l'indice 15. Riportato perché §26 chiede evidenza, non impressioni.

**Origine.** `knowledge/strategy_database.json` ha esattamente la stessa lacuna
per le stesse 14 voci. Divergenza registro ↔ knowledge base: **zero**. Il
generatore `contracts/generate_registry.py` copia `selector_index` dal knowledge
(`"selector_index": s.get("selector_index")`), quindi **propaga fedelmente un
buco che nasce a monte**.

**Conseguenza.** Il registro è dichiarato "unica fonte di verità" (docstring di
`server/strategy_registry.py`). Chi pianifica una passata isolata leggendo il
registro non trova, per 14 strategie su 37, il numero da mettere in
`InpStrategySelector`. Nessun automatismo lo ricava dal codice: `selector_index`
è consumato solo da `contracts/validate_registry.py` (che ne controlla l'unicità,
non la presenza) e dai test.

**Cosa NON dimostra.** Non dimostra che quelle 14 non siano isolabili — lo sono.
Dimostra che la fonte di verità dichiarata non contiene l'informazione.

---

## MM-02 · P0 · `DISP_REBAL`: dichiarata disattivata, accesa nel codice

**Fatto.**

| Fonte | Dice |
|---|---|
| `knowledge/strategy_database.json` | `stato: "attiva nel codice, disabilitata in produzione reale"` |
| `contracts/strategy-registry.json` | `status: DISABLED`, `default_enabled: false`, `auto_disable_eligible: false` |
| `MQL5/Include/NEXUS_v1/NXS_Inputs.mqh:566` | `input bool InpUseStrat_DispRebal = true;` |

**Conseguenza.** L'unico posto che determina davvero se la strategia gira è
l'input MQL5, ed è a `true`. Il registro afferma il contrario. Peggio:
`auto_disable_eligible: false` significa che il piano di controllo **non può
disattivarla** con `disable_strategy` (`server/app.py:5305` filtra su
`strategy_registry.AUTO_DISABLE_IDS`). Il risultato netto è una strategia che
gira di default e che la dashboard non è autorizzata a spegnere, mentre il
registro la descrive come già spenta.

**Cosa NON dimostra.** Non dimostra che `DISP_REBAL` sia dannosa: non ha dati di
sweep (vedi MM-06). Dimostra che lo stato dichiarato e lo stato reale divergono
in modo che rende la dichiarazione inutilizzabile per decidere.

---

## MM-03 · P1 · `ELLIOTT`: dichiarata attiva, senza controparte research, spenta nel codice

**Fatto.**

| Fonte | Dice |
|---|---|
| Registro | `status: ACTIVE`, `default_enabled: true`, `research_implementation: false`, `research_parity: NOT_IMPLEMENTED` |
| `server/backtest.py` | nessuna funzione: è l'**unica** delle 37 live assente dal motore research |
| `NXS_Inputs.mqh:577` | `input bool InpUseStrat_Elliott = false;  // OFF di default: nuova strategia, backtesta prima` |
| Frontend | presente nell'elenco, con `research=false` |
| `NXS_StrategyProfiles.mqh` | nessun profilo TF, nessun profilo parametrico |

**Conseguenza.** Il commento nel codice MQL5 dice la cosa giusta ("backtesta
prima"), ma non esiste il modo di backtestarla: manca l'implementazione research.
Nel frattempo il registro la marca `default_enabled: true`, cioè il contrario di
quello che il codice fa. Il `display_name` è
`"Elliott (rename pending: FIVE_SWING_IMPULSE)"`: un rename annunciato e mai
eseguito, che rende ambiguo il nome canonico stesso.

---

## MM-04 · P0 · Tre coppie di strategie producono, in ricerca, lo stesso segnale per costruzione

**Fatto.** In `server/backtest.py` tre funzioni sono associate a due strategie
ciascuna:

| Funzione Python | Strategie servite |
|---|---|
| `sig_bollinger` | `BOLLINGER`, `RANGE_FADE` |
| `sig_breakout` | `LONDON_BO`, `WEEKLY_EXP` |
| `sig_ob_mit` | `SH_BMS_RTO`, `SMS_BMS_RTO` |

Stessa funzione, stessi argomenti, nessun parametro differenziante nel punto di
associazione. **In ricerca queste sei strategie sono tre.**

**Conseguenza — questa è la ragione della P0.** Qualunque conteggio del tipo
"la ricerca copre 37 strategie" è falso: ne copre 34 distinte più tre duplicati.
E ogni analisi di *diversificazione*, *correlazione fra strategie* o
*conferma multi-strategia* costruita sul motore research conta come due voci
indipendenti ciò che è una sola. Il conteggio di conferme correlate è esattamente
la quantità che alimenta la conviction istituzionale (vedi MM-13).

**Cosa NON dimostra.** Non dimostra che le controparti **MQL5** siano identiche:
in MQL5 hanno trigger distinti e selettori distinti. La duplicazione è, allo stato
verificato, del solo motore research.

---

## MM-05 · P1 · I proxy dichiarati non puntano alla funzione realmente condivisa

**Fatto.** `PROXY_MAP` in `contracts/generate_registry.py` è una mappa **scritta a
mano** (`ASSUMPTION`, non derivata dal codice). Confrontata con le associazioni
reali di `server/backtest.py`:

| Strategia | Proxy dichiarato | Funzione che usa davvero | Funzione del target dichiarato | Coincidono? |
|---|---|---|---|---|
| `RANGE_FADE` | `BOLLINGER` | `sig_bollinger` | `sig_bollinger` | **sì** |
| `LONDON_BO` | `BREAKOUT_ACC` | `sig_breakout` | `sig_breakout_acc` | no |
| `WEEKLY_EXP` | `BREAKOUT_ACC` | `sig_breakout` | `sig_breakout_acc` | no |
| `LIQ_VOID` | `FVG_CONT` | `sig_fvg_cont` | `sig_fvg_cont_ext` | no |
| `SH_BMS_RTO` | `OB_MIT` | `sig_ob_mit` | `sig_ob_mit_ext` | no |
| `SMS_BMS_RTO` | `OB_MIT` | `sig_ob_mit` | `sig_ob_mit_ext` | no |

**Conseguenza.** Cinque dichiarazioni di proxy su sei indicano un bersaglio
sbagliato. La relazione vera è diversa e più stretta: `LONDON_BO ≡ WEEKLY_EXP`,
`SH_BMS_RTO ≡ SMS_BMS_RTO` (MM-04), mentre i target dichiarati usano le varianti
`_ext`, che sono funzioni separate. Chi legge il registro per sapere "di quale
strategia questa è un surrogato" riceve una risposta errata.

**Cosa NON dimostra.** Non dimostra che `sig_fvg_cont` e `sig_fvg_cont_ext` siano
scorrelate — condividono il nome e presumibilmente parte della logica. Dimostra
che il registro afferma un'identità che il codice non ha.

---

## MM-06 · P0 · 28 strategie su 37 sono attive senza alcuna misura, e la 29ª non è sulla baseline

**Fatto.** `knowledge/strategy_database.json`, round `sweep37`, baseline
`e6ce816`:

| | Strategie |
|---|---|
| Con passata isolata completata **sul round corrente** | **8** |
| Con passata isolata **di un round precedente** | 1 (`SAR`) |
| Senza alcuna passata isolata (`trade: null`) | **28** |

Le 8 sulla baseline corrente: `ADX_RSI`, `BJORGUM`, `BOLLINGER`, `BREAKOUT_ACC`,
`FVG_CONT`, `LIQ_SWEEP`, `MACD`, `TSI`. Nessuna ha expectancy positiva
significativa; la migliore è `LIQ_SWEEP` (292 trade, PF 1.04, +0.004R).

`SAR` porta la nota, già scritta nel knowledge base:

> `ATTENZIONE: file piu' recente disponibile per S04 datato 17/07 (round precedente): la passata S04 del round corrente non risulta nei report`

I suoi numeri (261 trade, PF 0.60, −0.09R) descrivono **una versione precedente
del codice**, e la sua voce `ultimo_sweep` è l'unica delle nove priva di `run_id`.

**Conseguenza.** Tutte e 37 girano; per 29 di esse non esiste una misura del
comportamento del trigger sulla baseline attuale. `SAR` è particolarmente
rilevante perché è fra le strategie che pesano di più sul risultato negativo
storico, e la sua unica evidenza non è confrontabile con le altre otto.

**Cosa NON dimostra.** Assenza di misura non è misura di assenza: le 28 non sono
"cattive", sono **ignote**. E i numeri delle 8 misurano una strategia isolata a
lotto fisso in `DataCollectionMode`, cioè il comportamento del trigger, non il
P&L di portafoglio — l'avvertenza è scritta nel knowledge base stesso e va
mantenuta in ogni citazione di quei numeri.

---

## MM-07 · P1 · Otto strategie live senza profilo TF e senza profilo parametrico

**Fatto.** In `NXS_StrategyProfiles.mqh` non compaiono né in `NXS_Profile_TF` né
nella tabella dei profili (`slMult`/`tpMult`/`htf`/`beR`/`trailATR`):

`AMD_CONT`, `AMD_REVERSAL`, `ELLIOTT`, `JUDAS_SWING`, `LDN_REVERSAL`,
`NY_REVERSAL`, `PO3`, `SILVER_BULLET`.

Sette delle otto sono `SESSION` o `AMD`, cioè le famiglie che dipendono
dall'orario intraday. Nel registro il campo diventa `supported_timeframes: ["*"]`,
perché il generatore scrive `["*"]` quando `NXS_Profile_TF` non risponde
(`"supported_timeframes": [tf] if tf else ["*"]`).

**Conseguenza doppia.**
1. In esecuzione girano sui default globali di stop/target, non su un profilo
   proprio: i parametri con cui operano non sono stati scelti per loro.
2. Nel registro `"*"` **legge come "supporta ogni timeframe"**, mentre il fatto
   è "nessun timeframe è dichiarato". Un'assenza è stata codificata come
   un'affermazione di universalità. `server/backtest.py` commenta le stesse
   strategie con *"richiedono candele intraday reali"*: il contrario di `"*"`.

---

## MM-08 · P1 · `THREE_BAR_DELIVERY_BREAK` è indicizzata nel motore research solo sotto l'alias `CISD`

**Fatto.** In `server/backtest.py` il dizionario `STRATEGIES` ha 40 chiavi. 39
sono id canonici; una sola è un alias: `"CISD": sig_cisd`. L'id canonico
`THREE_BAR_DELIVERY_BREAK` non compare. L'interruttore MQL5 usa lo stesso nome
storico (`InpUseStrat_CISD`).

**Conseguenza.** Ogni analisi che itera le chiavi di `STRATEGIES` e le confronta
con `strategy_registry.live_ids()` senza risolvere gli alias conclude che
`THREE_BAR_DELIVERY_BREAK` **non ha implementazione research**. È falso — ce
l'ha. Il caso non è teorico: **la prima versione dell'inventario di questa stessa
consegna riportava `—` in quella cella**, ed è stata corretta risolvendo gli
alias. La classe di errore è quella che §26 chiede di non produrre: un'assenza
dichiarata dove c'è presenza.

`server/strategy_registry.py` risolve correttamente gli alias in `_index()`; il
problema è nel codice che legge `STRATEGIES` direttamente.

---

## MM-09 · P1 · Il frontend presenta 37 strategie come equivalenti

**Fatto.** `frontend/src/contracts/strategyRegistry.js` è generato, e ogni voce
porta cinque campi: `[id, display_name, family, live, research]`. Non porta
`status`, `research_parity`, `proxy_for`, `selector_index`, né alcun indicatore
di evidenza. Ricerca su tutto `frontend/src/`: **zero** occorrenze di `proxy`,
`parity`, `research_parity`.

**Conseguenza.** Nella dashboard una strategia con 915 trade misurati e una senza
alcuna misura hanno lo stesso aspetto; un proxy di un'altra strategia ha lo
stesso aspetto di una strategia indipendente. Chi sceglie dall'interfaccia non ha
modo di vedere la differenza fra "misurata", "surrogata" e "ignota". Questo
rende impraticabile il gate di approvazione `NEXUS-STRAT-001/003`, già dichiarato
**parziale** in `docs/NORMATIVE_CONFORMANCE.md`.

---

## MM-10 · P1 · Lo stato canonico deriva dal parsing di prosa italiana libera

**Fatto.** `contracts/generate_registry.py`:

```python
def status_from_stato(stato):
    s = (stato or "").lower()
    if "disabilitata in produzione" in s:
        return "DISABLED"
    if s == "attiva":
        return "ACTIVE"
    return "EXPERIMENTAL"
```

Da `status` discendono poi `default_enabled` e `auto_disable_eligible`
(`status == "ACTIVE"`).

**Conseguenza.** Il campo che controlla se il piano di controllo può disattivare
una strategia (MM-02) è ottenuto cercando una sottostringa in un campo di testo
scritto a mano. Una variazione innocua di formulazione nel knowledge base —
`"disattivata in produzione"`, `"attiva "` con uno spazio — cambia silenziosamente
`status` in `EXPERIMENTAL` e quindi `auto_disable_eligible` in `false`. Nessun
controllo lo intercetta: `validate_registry.py` verifica che `status` sia un
valore ammesso, non che sia quello giusto.

Va anche detto in positivo: la scelta di derivare il registro da fonti reali
invece di scriverlo a mano è corretta. È l'*input* a essere fragile, non il
metodo.

---

## MM-11 · P2 · 34 strategie live su 37 hanno bug storici registrati; 8 di queste non hanno fix registrati

**Fatto.** `knowledge/strategy_database.json`: 34 voci live su 37 hanno
`bug_storici` non vuoto, per **42 bug** complessivi. 26 hanno `fix_applicati`, 24
hanno `redesign_effettuati`. Otto hanno bug registrati e **nessun fix
registrato**: `SAR`, `RSI_DIV`, `STRUCT_REACT`, `SMS_BMS_RTO`, `AMD_REVERSAL`,
`JUDAS_SWING`, `PO3`, `ELLIOTT`.

Tre esempi testuali, riportati alla lettera:

- `TSI` — *"CRITICO: non calcolava TSI, era RSI+EMA20 col nome sbagliato"*
- `SAR` — *"proxy sito falso (era EMA cross)"*
- `ADX_RSI` — *"nome improprio: non usa un vero ADX come trigger (solo filtro g_adx<20), documentato"*

**Conseguenza.** Il primo e il secondo dicono che, per un periodo, i risultati
attribuiti a `TSI` e `SAR` misuravano un'altra logica. Il terzo dice che il nome
`ADX_RSI` non descrive il trigger. Nessuno di questi campi è collegato a un
commit verificabile in modo automatico, quindi **non è verificabile da qui** se
il fix sia effettivamente nella baseline `4465873`: i riferimenti sono in prosa
(`"v2.5.1 profilo TP10x/BE1.5R"`, `"corretto 9db13f9"`) e non uniformi.

**Cosa NON dimostra.** Non dimostra che i bug siano aperti. Dimostra che lo stato
"corretto / non corretto" non è determinabile dalle fonti presenti.

---

## MM-12 · P1 · Esistono due tassonomie di famiglia indipendenti, in disaccordo su 154 coppie di strategie su 666

**Fatto.** Il progetto classifica le strategie per famiglia in **due punti
diversi, che non si parlano**:

1. `FAMILY_MAP` in `contracts/generate_registry.py` → campo `family` del registro
   → frontend. Mappa scritta a mano; il generatore stesso la marca:
   > `# Mappa famiglia — TASSONOMIA PROVVISORIA (domain judgment, revisionabile).`
   > `# Non e' un dato estratto: e' un raggruppamento documentato per la UI.`
   Etichette: `MOMENTUM`, `TREND`, `VOLATILITY`, `SMC`, `LIQUIDITY`, `SESSION`,
   `AMD`, `PATTERN`.
2. `_nxs_inst_family()` in `MQL5/Include/NEXUS_v1/NXS_InstitutionalCore.mqh:96` →
   pesatura della conviction → sizing. Classificatore **a sottostringa sul nome**.
   Etichette: `IMBALANCE`, `STRUCTURE`, `LIQUIDITY`, `MEAN_REVERSION`,
   `MOMENTUM`, `OTHER`.

Le due inducono partizioni diverse delle 37 strategie live. Su tutte le 666
coppie possibili:

| | Coppie |
|---|---|
| Stessa famiglia in **entrambe** le tassonomie | 27 |
| Stessa famiglia **solo** nel registro | 61 |
| Stessa famiglia **solo** in `_nxs_inst_family()` | 93 |
| **In disaccordo** | **154** |

Esempi diretti, tutti verificati:

| Strategia | Registro | `_nxs_inst_family()` | Perché |
|---|---|---|---|
| `ADX_RSI` | `MOMENTUM` | `MEAN_REVERSION` | il nome contiene `RSI` |
| `LDN_REVERSAL` | `SESSION` | `MEAN_REVERSION` | il nome contiene `REVERSAL` |
| `NY_REVERSAL` | `SESSION` | `MEAN_REVERSION` | idem |
| `AMD_REVERSAL` | `AMD` | `MEAN_REVERSION` | idem |
| `TSI` | `MOMENTUM` | `OTHER` | nessuna sottostringa corrisponde |
| `ICHIMOKU` | `TREND` | `OTHER` | idem |

**`OTHER` è il problema più serio.** Dodici strategie live vi ricadono —
`AMD_CONT`, `BB_SQUEEZE`, `BJORGUM`, `ELLIOTT`, `ICHIMOKU`, `MALAYSIAN_SNR`,
`OTE_CONT`, `PO3`, `SILVER_BULLET`, `THREE_BAR_DELIVERY_BREAK`, `TSI`,
`WEEKLY_EXP` — e `OTHER` è trattato come una famiglia vera. Sono **66 coppie di
strategie non imparentate trattate come correlate** ai fini della pesatura
(MM-13): un breakout settimanale e Ichimoku finiscono nello stesso gruppo perché
nessuno dei due contiene una delle sottostringhe cercate.

**Il commento nel codice contraddice il codice.** La riga sopra la funzione dice:

> `//: AUD0-INST-010 — famiglia di appartenenza usata per pesare i contributi`
> `//: correlati. Raggruppa per CONCETTO letto, non per nome.`

L'implementazione raggruppa **per sottostringa del nome**, cioè esattamente per
nome. L'ho scritto io, durante la remediation v18: il commento descrive
l'intenzione, non ciò che il codice fa.

**Ordine di valutazione fragile.** Le regole sono `if` in cascata e la prima che
matcha vince. `BOLLINGER` finisce in `MEAN_REVERSION` solo perché quella regola
precede `MOMENTUM`, che cerca la sottostringa `"BO"` — con cui `BOLLINGER` pure
corrisponde. Non è un difetto oggi; è un difetto latente al primo rename o alla
prima regola aggiunta in mezzo.

`ASSUMPTION` su entrambe le tassonomie. Nessuna modifica in questa consegna.

---

## MM-13 · P0 · L'euristica `1/(n+1)` sulla conviction correlata è mia, non è validata, ed è attiva

**Non è un mismatch fra fonti: è un difetto che ho introdotto io.** Lo riporto
qui perché il work package (§20, §3.4) lo classifica esplicitamente e perché
tacerlo violerebbe §26.

**Fatto.** Nella remediation dell'audit v18 ho aggiunto a
`MQL5/Include/NEXUS_v1/NXS_InstitutionalCore.mqh` la funzione `_nxs_inst_family()`
e, in `NXS_Institutional_Decide()`, un peso **decrescente** sulle conferme
provenienti dalla stessa famiglia — la n-esima conferma correlata pesa
`1/(n+1)`:

```cpp
// 1.0, 0.5, 0.33, 0.25 ... per contributi successivi della stessa famiglia
double w = 1.0 / (double)(famCnt[idx] + 1);
famCnt[idx]++;
if(all[i].dir == DIR_BUY) buyAdj += all[i].score * w;
else                      sellAdj += all[i].score * w;
```

`buyAdj`/`sellAdj` alimentano `net`, che è confrontato con
`InpInstMinConviction`: il peso decide se il setup passa il gate, e con quale
punteggio.

**Perché è un difetto.**

- §3.4 vieta di modificare il sizing sulla base di euristiche inventate. Il
  punteggio di conviction entra nel dimensionamento: questa è, letteralmente,
  un'euristica inventata che modifica il sizing.
- §20 vieta di adottare `1/(n+1)` come correzione canonica senza validazione.
  Non l'ho validata: non l'ho confrontata con la baseline, non l'ho testata, non
  è disattivabile con un input.
- La famiglia su cui si appoggia è quella di `_nxs_inst_family()`, un
  classificatore a sottostringa in disaccordo con il registro su 154 coppie su
  666, con 12 strategie eterogenee ammassate in `OTHER` (MM-12). Il correttivo di
  correlazione poggia su un raggruppamento che non misura correlazione — e in 66
  coppie penalizza conferme che correlate non sono.

**Il ragionamento sottostante non è sbagliato** — contare cinque conferme
correlate come cinque conferme indipendenti sovrastima la convinzione, ed è la
stessa distorsione di MM-04. Sbagliato è **il modo**: una formula scelta a
intuito, non commutabile, non confrontata, già attiva sul percorso del sizing.

**Cosa NON faccio in questa consegna.** Non la tocco. §27 impone che la prima
consegna non modifichi il comportamento delle strategie: rimuoverla *è* un
cambio di comportamento, e andrebbe fatto con lo stesso rigore che è mancato
quando l'ho introdotta. La rimozione — o il gating dietro un input a default
`false`, con confronto contro baseline — è la **prima voce** delle decisioni che
richiedono la tua approvazione, in
`docs/NEXUS_STRATEGY_PRIORITY_MATRIX.md`.

---

## Riepilogo

| ID | Gravità | Mismatch | Fonti coinvolte |
|---|---|---|---|
| MM-01 | P0 | 14 live senza `selector_index` nel registro, presenti nel codice | registry, knowledge, MQL5 |
| MM-02 | P0 | `DISP_REBAL` dichiarata `DISABLED`, input MQL5 a `true`, non disattivabile dal control plane | registry, MQL5, backend |
| MM-03 | P1 | `ELLIOTT` `ACTIVE` e `default_enabled` senza research e con input a `false` | registry, MQL5, Python, frontend |
| MM-04 | P0 | 3 coppie condividono la funzione research: 37 strategie, 34 segnali | Python |
| MM-05 | P1 | 5 proxy su 6 indicano un target diverso dalla funzione condivisa | registry, Python |
| MM-06 | P0 | 28 senza misura, 1 (`SAR`) misurata su un'altra baseline: 8 su 37 misurate | knowledge |
| MM-07 | P1 | 8 live senza profilo TF né parametrico; assenza codificata come `"*"` | MQL5, registry |
| MM-08 | P1 | `THREE_BAR_DELIVERY_BREAK` indicizzata solo per alias `CISD` | Python, registry |
| MM-09 | P1 | Il frontend non distingue misurata / surrogata / ignota | frontend |
| MM-10 | P1 | `status` (e quindi `default_enabled`) da parsing di prosa libera | generatore, knowledge |
| MM-11 | P2 | 34 con bug storici, 8 senza fix registrato, nessun collegamento verificabile a commit | knowledge |
| MM-12 | P1 | Due tassonomie di famiglia indipendenti, in disaccordo su 154 coppie su 666; 12 strategie in `OTHER` | generatore, MQL5 |
| MM-13 | P0 | Euristica `1/(n+1)` sul sizing: mia, non validata, non disattivabile, attiva | MQL5 (remediation v18) |

## Collegamenti

`docs/NEXUS_STRATEGY_INVENTORY.md` · `docs/NEXUS_STRATEGY_PRIORITY_MATRIX.md` ·
`docs/NORMATIVE_CONFORMANCE.md` · `docs/REMEDIATION_STATUS.md`
