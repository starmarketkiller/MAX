# NEXUS Structural Research — Detector Integrity Fix: SNXSSweepExt Initialization

Segue [[NEXUS - Causal Research Thread 2 Phase A1 Shared Sweep Instrumentation]] (commit `597e9b5`). Root-cause audit richiesto sull'anomalia "confirmed=true con dir/level/levelTag ai default" osservata in ~65% delle osservazioni grezze.

**STATO: fix implementato e verificato, ma la trading parity contro la baseline Fase A.1 NON regge — commit/push NON eseguiti, in attesa di decisione.**

## 1. Root-cause audit

### 1.1 Ispezione statica

`SNXSSweepExt` (`NXS_MarketAnalysis.mqh`) contiene, oltre a `dir`, dieci campi bool/double/string (`level`, `refHigh`, `refLow`, `confirmed`, otto `sweptXXX`, `levelTag`). Prima del fix, `NXS_DetectSweepExt()` inizializzava esplicitamente **solo** `s.dir = DIR_NONE;` alla dichiarazione, confidando in un commento che affermava: *"I campi di SNXSSweepExt sono già inizializzati puliti alla dichiarazione (numerici/bool a 0/false, string a "")"*.

Indizio decisivo trovato per confronto diretto: la funzione gemella più semplice `NXS_DetectSweep()` (poche righe sopra, stesso file) inizializza esplicitamente **tutti e tre** i suoi campi: `SNXSSweep s; s.dir = DIR_NONE; s.level = 0; s.confirmed = false;`. Se l'inizializzazione automatica fosse davvero affidabile, questa riga sarebbe ridondante — la sua presenza suggerisce che l'autore avesse già incontrato il problema in passato e lo avesse corretto solo lì, non nella versione estesa.

Storia del file: un commento datato 17/07 conferma che `ZeroMemory(s)` era usato in origine ed è stato **rimosso** perché, per uno struct con un campo `string` (`levelTag`), sovrascrive l'handle stringa con zeri grezzi senza rilasciarlo correttamente — comportamento non sicuro, motivo valido e non in discussione. Il problema è che la rimozione di `ZeroMemory` non è stata sostituita da un'inizializzazione esplicita di tutti i campi, lasciando lo struct esposto al comportamento reale (non a quello assunto) dell'inizializzazione di default in MQL5 per una variabile struct locale in questo contesto.

### 1.2 Test minimo riproducibile (non assunto — verificato)

Aggiunto temporaneamente un `PrintFormat` subito dopo `SNXSSweepExt s; s.dir = DIR_NONE;`, **prima** di qualunque ramo di sweep, per le prime 40 chiamate di un run breve (GOLD H4, 2026.06.01→2026.06.03, selettore=0). Risultato conclusivo:

```
call=1  confirmed=true  level=26756450673826113772853914993040737166894155887045287940138256189228655707432449015722079141583415693672418305656042679087128995644024556390414390330503578460328070382475992001044210660642385806366435497335891876789616640.00000  tag='(null)'
call=2  confirmed=false level=17506827037938100427081291025765183996257778580341081584070808938721770665529358908937087641845236971336479467649511249747343205784658794251704149772041449040317973456554527908980599169282120677128820507558994939526419867285896089603565549704031526671319395918617377643138383872.00000  tag='(null)'
call=8  confirmed=true  level=(stesso valore astronomico di call=1)  tag='(null)'
```

- `level` non è mai `0.00000` alla dichiarazione: sono valori a doppia precisione astronomici, tipici di byte di stack riletti come double — non zero, non NaN semplice, memoria residua vera e propria.
- `tag='(null)'`: non una stringa vuota `""` (che PrintFormat renderizzerebbe come nulla), ma un handle stringa nullo/non valido.
- `confirmed=true` compare con **periodicità 1 su 7 chiamate esatta** (call 1, 8, 15, 22, 29, 36) nel campione — coerente con un pattern di riuso dello stesso frame di stack ogni N chiamate del loop multi-TF-pass, non con un evento casuale isolato.
- Il pattern persiste per tutta la durata del run (osservato anche a fine finestra nel test Fase A.1, non solo a freddo).

**Conclusione**: una variabile struct locale (`SNXSSweepExt s;`) in questo contesto **non è affidabilmente zero-inizializzata** in MQL5/questa build — la premessa del commento originale era sbagliata. `confirmed`/`level`/`refHigh`/`refLow`/`levelTag`/tutti gli otto `sweptXXX` partivano da stato di stack residuo, non da valori puliti.

### 1.3 Possono esistere return path che non inizializzano completamente lo struct?

No — verificato: `NXS_DetectSweepExt()` ha un **solo** punto di uscita (`return s;` in fondo alla funzione, riga 210 originale). Il problema non è un return path incompleto, è lo stato INIZIALE della dichiarazione stessa, prima ancora che qualunque ramo venga valutato.

## 2. Fix minimale applicato

In `NXS_MarketAnalysis.mqh`, `NXS_DetectSweepExt()`: sostituita la singola riga `SNXSSweepExt s; s.dir = DIR_NONE;` con l'inizializzazione esplicita di **tutti** i 16 campi (`dir`, `level`, `refHigh`, `refLow`, `confirmed`, gli otto `sweptXXX`, `levelTag`), ciascuno al suo valore neutro (`0`/`false`/`""`). **Nessun `ZeroMemory`** (il motivo del 17/07 resta valido e non viene reintrodotto). **Nessuna riga dei dieci rami di rilevamento sweep è stata toccata** — tutte le condizioni (`h1>pdh && c1<pdh`, ecc.) e le soglie sono identiche bit per bit a prima.

Rimosso il diagnostico temporaneo dopo la verifica (non resta nel codice).

## 3. Invariante semantico

Verificato per lettura esaustiva di tutti e dieci i rami: **ogni** ramo che imposta `s.confirmed = true` lo fa nella stessa riga/blocco in cui imposta anche `s.dir` (BUY o SELL, mai NONE), `s.level` (un prezzo reale, sempre >0 per l'oro) e `s.levelTag` (una stringa non vuota). Non esiste un ramo che imposti `confirmed` da solo. Dopo il fix, con lo stato iniziale garantito pulito, vale quindi sempre:

```
confirmed == true  ⇒  dir ∈ {DIR_BUY, DIR_SELL}  ∧  level > 0  ∧  levelTag != ""
```

Nessun caso legittimo di eccezione esiste o è stato trovato — l'invariante è totale, non parziale.

## 4. Re-run finestra di integrità Fase A.1

Stessa identica configurazione cross-consumer (GOLD H4, 2026.06.01→2026.06.15, Model=1, `InpResearchMode=false`, `InpStrategySelector=0`).

| Metrica | Prima del fix | Dopo il fix |
|---|---|---|
| Osservazioni con `confirmed=true` (totale grezzo) | 7644 | **2652** |
| Osservazioni valide (`raw_observations`, post-filtro difensivo) | 2652 | 2652 |
| Eventi canonici unici | 165 | 165 |
| `MULTIPASS_DUPLICATE` | 2225 | 2225 |
| `CROSS_CONSUMER_DUPLICATE` | 262 | 262 |
| **`malformed_skipped`** | **4992** | **0** |

**Acceptance del punto 4 soddisfatta**: `malformed_skipped=0`, nessuna eccezione da documentare. Da notare che i contatori "validi" (raw_observations/unique/multipass/cross-consumer) **non cambiano affatto**: il filtro difensivo della Fase A.1 stava già escludendo correttamente le osservazioni incoerenti dal dataset di ricerca — il fix elimina la CAUSA (quindi `malformed_skipped` scende a zero) ma il dataset "pulito" prodotto dal logger era già identico prima e dopo. Questo conferma che la Fase A.1 non necessita revisione dei propri numeri pubblicati.

## 5. Trading parity — FALLITA rispetto alla baseline Fase A.1

Baseline Fase A.1 (commit `597e9b5`): **102 trade**, SHA256 `e36cc12e9863d941cfc511d47bf26ab9debcd6a7b2164c1d978cd173bf00b92b`.

| | Pre-fix (baseline) | Post-fix |
|---|---|---|
| Righe `NEXUS_trades.csv` (OFF) | 102 | **104** |
| SHA256 (OFF) | `e36cc12e...` | `cb25cc93d10a4662ecdb9f800f03f3cc7ab15200681071f486b52e0fd0397094` (**diverso**) |
| OFF vs ON post-fix (parità interna del gate di logging) | — | **identiche** (stesso SHA256 `cb25cc93...`, 104 righe in entrambe) |

**La parità OFF/ON del gate di ricerca resta intatta** (il logging non introduce differenze) — è il **fix del detector stesso**, rispetto al comportamento pre-fix, a cambiare l'esito.

### Analisi della differenza (per istruzione esplicita: non considerato automaticamente sicuro)

Diff riga per riga tra pre-fix e post-fix: la differenza netta è un trade **AMD_REVERSAL** (`OPEN 2026.06.10 16:45:00` → `CLOSE 17:21:40, sl, -14.2`) presente **solo nel run post-fix**, più uno spostamento di un ticket in avanti per RSI_DIV nello stesso bar (stesso segnale, `score` 78.0→88.0) e conseguente rinumerazione dei ticket di tutti i trade successivi nella finestra (nessun trade successivo cambia prezzo/esito, solo il numero di ticket, per via dell'inserimento del trade AMD_REVERSAL in mezzo alla sequenza).

**Causa identificata**: `AMD_REVERSAL` (`NXS_Strategies_SMC.mqh`) — così come **TURTLE_SOUP** (`NXS_Strategies_SMC.mqh`), **JUDAS_SWING**, **LDN_REVERSAL** e **PO3** (`NXS_Strategies_Institutional.mqh`) — leggono direttamente i campi `sw.sweptPDH/sweptPDL/sweptAsiaHigh/sweptAsiaLow/sweptEQH/sweptEQL` e/o `sw.refHigh/sw.refLow` **senza mai controllare `sw.confirmed` né `sw.dir`**. Esempio (`AMD_REVERSAL`):

```mql5
if(sw.sweptAsiaHigh && g_struct.chochDown){ ... }
if(sw.sweptAsiaLow  && g_struct.chochUp){ ... }
```

Queste **cinque strategie preesistenti** erano quindi anch'esse esposte allo stesso bug di inizializzazione — indipendentemente dall'anomalia "confirmed=true+dir=NONE" già documentata in Fase A.1, che riguardava solo il canale di ricerca. Prima del fix, `sweptAsiaHigh`/`sweptAsiaLow`/ecc. potevano leggersi come `true` per puro stato di stack residuo, **su qualunque bar**, non solo su quelli con uno sweep reale.

Il meccanismo esatto della differenza osservata (un trade AMD_REVERSAL che appare, non uno che scompare) è coerente con l'architettura di selezione "miglior segnale" di `NXS_CollectAllSignals`/router: ad ogni bar vengono valutate decine di strategie che condividono lo stesso `SNXSSweepExt` per quel pass; se una qualsiasi di esse riceveva un flag spurio da stato residuo (non necessariamente AMD_REVERSAL stesso — potenzialmente TURTLE_SOUP, JUDAS_SWING, LDN_REVERSAL o PO3 su quello stesso bar/pass), poteva competere nella selezione del segnale con una priorità diversa da quella corretta. Rimuovendo il rumore da stato residuo in tutti i consumer contemporaneamente, l'esito della selezione per almeno un bar cambia, e AMD_REVERSAL (la cui condizione era realmente vera quel bar) vince la selezione dove prima probabilmente non la vinceva. Non è stato isolato oltre questo livello (richiederebbe strumentare anche le altre quattro strategie, fuori scope per un fix "minimale" di sola inizializzazione).

**Conclusione della sezione 5**: il fix è corretto e necessario come intervento di data integrity, ma **non è comportamentalmente invisibile al trading** come inizialmente atteso — perché il bug ha una superficie più ampia di quella toccata dalla sola istrumentazione di ricerca. Questo NON è stato ignorato né minimizzato: viene riportato esplicitamente, senza procedere a commit/push, come richiesto.

## 6. Filtro difensivo nel research logger

Mantenuto invariato in `NXS_StructuralResearchLog.mqh` (`NXS_Structural_ObserveSweep()`), ora agisce come **guardia di sicurezza ridondante** (assertion), non più come unica fonte di pulizia: con il detector corretto, il filtro conta correttamente **zero** scarti (§4). Nessuna modifica al filtro in questa fase.

## 7. Regressione sui consumer

- **Compilazione**: `MetaEditor64.exe /compile`, entrambi i terminali. **0 errori**, 2 warning preesistenti invariati.
- **WICK_SWEEP_REV**: verificato per ispezione del codice (non richiede run dedicato) — `NXS_Strat_WickSweepReversal()` **non riceve `SNXSSweepExt` come parametro** (usa un rilevamento wick interamente proprio, indipendente dal detector). **Strutturalmente non può essere affetto** da questo fix.
- **LIQ_SWEEP**: gate corretto preesistente (`if(!sw.confirmed) return s;` prima di ogni uso di `sw.dir`/`sw.level`) — non dovrebbe MAI aver potuto leggere uno stato incoerente da solo; non isolato con un run dedicato separato dal test cross-consumer (che lo includeva già, vedi §5 — nessuna variazione di trade LIQ_SWEEP osservata nel diff).
- **SH_BMS_RTO**: stesso discorso — gate `sw.confirmed && sw.dir==wantSweep` preesistente, coerente per costruzione con l'invariante del §3 sia prima sia dopo (nessuna variazione osservata nel diff di trade riconducibile a SH_BMS_RTO).
- **AMD_REVERSAL / TURTLE_SOUP / JUDAS_SWING / LDN_REVERSAL / PO3**: **cambiano comportamento** per i motivi del §5 — non una regressione introdotta da questo fix, ma l'eliminazione di un comportamento preesistente basato su memoria non inizializzata.

## 8. Blockers

Il fix di data-integrity è tecnicamente corretto e minimale (nessuna riga di semantica dello sweep toccata), ma **la sua applicazione cambia il trade count reale** in almeno 5 strategie preesistenti che non erano nello scope dichiarato di questo task ("non cambiare consumer"). Serve una decisione esplicita su come procedere:

1. Applicare comunque il fix (accettando che corregge un bug reale, anche se il suo raggio d'azione supera l'istrumentazione di ricerca), eventualmente accompagnandolo da un secondo intervento (fuori scope qui) che aggiunga il check `confirmed && dir!=DIR_NONE` anche a TURTLE_SOUP/AMD_REVERSAL/JUDAS_SWING/LDN_REVERSAL/PO3, per allinearle allo stesso standard di LIQ_SWEEP/SH_BMS_RTO.
2. Non applicare il fix nel detector e continuare ad affidarsi **solo** al filtro difensivo del research logger (che già produce un dataset pulito, vedi §4) — lasciando il bug di inizializzazione presente ma non corretto nel detector condiviso, documentato per una fase futura dedicata.

## Verdict

### **HOLD_DETECTOR_SEMANTICS_CHANGED**

Non perché la semantica dello SWEEP sia stata ridefinita (le condizioni sono bit-identiche), ma perché il fix di data-integrity, applicato al detector condiviso, cambia il comportamento di trading osservabile (102→104 trade, SHA256 diverso) attraverso cinque consumer preesistenti che non erano gated correttamente. Il fix resta nel codice (non revertito) ma **non è stato committato né pushato**, in attesa di decisione esplicita su come trattare l'impatto sui cinque consumer non in scope.
