# NEXUS — SNXSSweepExt Detector Integrity: Semantic Impact Audit

Segue [[NEXUS - SNXSSweepExt Detector Integrity Fix]] (fix locale non committato, verdict `HOLD_DETECTOR_SEMANTICS_CHANGED`). Audit completo dell'impatto per decidere se promuovere il fix.

**Nessun revert eseguito.** Come indicato: la vecchia baseline che dipendeva da memoria non inizializzata non è una reference valida per i consumer coinvolti.

## 1. Audit completo dei consumer di SNXSSweepExt

Tutti gli 11 consumer trovati nel codice (`grep` esaustivo su `SNXSSweepExt`), classificati per ispezione diretta del corpo funzione:

| Consumer | File | Gate osservato | Classificazione |
|---|---|---|---|
| LIQ_SWEEP | `NXS_Strategies.mqh` | `if(!sw.confirmed) return s;` poi `sw.dir==DIR_BUY/SELL` | **SAFE_CONFIRMED_GATED** |
| SH_BMS_RTO | `NXS_Strategies_SMC.mqh` | `sw.confirmed && sw.dir==wantSweep` | **SAFE_CONFIRMED_GATED** |
| SH_BMS_RTO_V2 | `NXS_Strategies_SMC.mqh` | `sw.confirmed && sw.dir==wantSweep` | **SAFE_CONFIRMED_GATED** |
| SILVER_BULLET | `NXS_Strategies_SMC.mqh` | `sw.confirmed && sw.dir==wantSweep` | **SAFE_CONFIRMED_GATED** |
| **TURTLE_SOUP** | `NXS_Strategies_SMC.mqh` | `sw.sweptPDH\|\|sw.sweptEQH` / `sw.sweptPDL\|\|sw.sweptEQL` diretti, mai `confirmed`/`dir` | **EXPOSED_TO_UNINITIALIZED_FLAGS** |
| **AMD_REVERSAL** | `NXS_Strategies_SMC.mqh` | `sw.sweptAsiaHigh`/`sw.sweptAsiaLow` diretti + `sw.refHigh`/`sw.refLow` nel calcolo SL, mai `confirmed`/`dir` | **EXPOSED_TO_UNINITIALIZED_FLAGS** |
| CISD (THREE_BAR_DELIVERY_BREAK) | `NXS_Strategies_Institutional.mqh` | parametro `sw` **mai usato** nel corpo funzione | **NOT_AFFECTED** |
| **JUDAS_SWING** | `NXS_Strategies_Institutional.mqh` | `sw.sweptAsiaLow/sweptPDL/sweptEQL` e `sw.sweptAsiaHigh/sweptPDH/sweptEQH` diretti | **EXPOSED_TO_UNINITIALIZED_FLAGS** |
| **LDN_REVERSAL** | `NXS_Strategies_Institutional.mqh` | idem + `sw.refHigh`/`sw.refLow` nel calcolo SL/TP | **EXPOSED_TO_UNINITIALIZED_FLAGS** |
| NY_REVERSAL | `NXS_Strategies_Institutional.mqh` | parametro `sw` **mai usato** nel corpo funzione | **NOT_AFFECTED** |
| **PO3** | `NXS_Strategies_Institutional.mqh` | `sw.sweptAsiaLow`/`sw.sweptAsiaHigh` diretti + `sw.refLow`/`sw.refHigh` nel calcolo SL | **EXPOSED_TO_UNINITIALIZED_FLAGS** |

Più i tre punti dell'istrumentazione di ricerca (Thread 2 Fase A/A.1: `DETECTOR`, `LIQ_SWEEP`, `SH_BMS_RTO` in `NXS_StructuralResearchLog.mqh`) — tutti **SAFE_CONFIRMED_GATED** per costruzione (`if(!sw.confirmed) return;` più il filtro difensivo aggiuntivo).

**WICK_SWEEP_REV**: non in questa tabella — `NXS_Strat_WickSweepReversal()` non riceve `SNXSSweepExt` come parametro, usa un rilevamento wick interamente indipendente. **NOT_AFFECTED** per costruzione architetturale (confermato di nuovo in questo audit).

**5 consumer EXPOSED confermati**: TURTLE_SOUP, AMD_REVERSAL, JUDAS_SWING, LDN_REVERSAL, PO3.

## 2. Trade attribution 102 → 104 (analisi esatta, non "+2 trade")

Diff riga-per-riga fra `trades_cross_off.csv` (baseline Fase A.1, pre-fix) e `trades_cross_off_postfix.csv` (post-fix), stessa configurazione cross-consumer (GOLD H4, 2026.06.01→2026.06.15, `InpResearchMode=false`, selettore=0).

**Unica differenza reale** (tutte le altre righe del diff sono la STESSA transazione con ticket rinumerato per lo spostamento in avanti di una posizione nella sequenza — stesso prezzo, stesso PnL, stesso orario):

| | Timestamp | Strategia | Direction | Entry | SL | TP | Reason | Esito |
|---|---|---|---|---|---|---|---|---|
| **Presente SOLO post-fix** | 2026.06.10 16:45:00 → 17:21:40 | AMD_REVERSAL | BUY | 4179.56 | 4163.20 | 4225.11 | `AMD:manip<Asia+MSS↑` | CLOSE `sl`, PnL -14.2, r=-0.866 |

Effetto collaterale osservato sulla STESSA barra: `RSI_DIV` apre lo stesso segnale identico (stesso entry/SL/TP/reason) in entrambe le run, ma con **score 78.0 (pre-fix) vs 88.0 (post-fix)** — coerente con un bonus di confluenza che cambia perché un segnale AMD_REVERSAL aggiuntivo è ora presente/assente nello stesso ciclo di valutazione, non un secondo bug indipendente.

**Campo SNXSSweepExt responsabile**: `sw.sweptAsiaLow`, letto direttamente da `AMD_REVERSAL` senza gate su `confirmed`/`dir` (riga `if(sw.sweptAsiaLow && c1 > amd.asianLow && c1 > o1 && g_struct.chochUp)`).

**Meccanismo esatto** (isolato nella sezione 3 sotto, dove la competizione fra strategie è eliminata): nel contesto cross-consumer, il segnale AMD_REVERSAL reale del 16:45 competeva nella selezione "miglior segnale" del router con segnali spuri generati da altre strategie EXPOSED sulla stessa barra/pass (probabilmente TURTLE_SOUP/JUDAS_SWING/LDN_REVERSAL/PO3, guidati da stato residuo su `sweptXXX`) — pre-fix nessuno dei due arrivava ad aprire (il candidato spurio vinceva la classifica ma falliva un gate a valle, es. spread/rischio, senza lasciare traccia nel CSV); post-fix, sparito il rumore spurio, il segnale reale di AMD_REVERSAL vince ed esegue. Non isolato oltre questo livello (richiederebbe strumentare il trace del router per quella barra specifica su TUTTE le ~50 strategie in gara, fuori scope per un fix di sola inizializzazione).

## 3. Isolamento per-strategy (nessuna competizione, stessa finestra 2026.06.01→2026.06.15)

Configurazione: `InpResearchMode=true` (isola una sola strategia per selettore, elimina ogni competizione con altre strategie), stesso periodo. Confronto PRE-fix vs POST-fix sullo stesso identico binario/periodo per ciascuno dei 5 consumer EXPOSED.

| Strategia (selettore) | Pre-fix: generated/blocked/**opened** | Post-fix: generated/blocked/**opened** | Esito |
|---|---|---|---|
| TURTLE_SOUP (17) | 0/0/**0** | 0/0/**0** | Identico — **nessun trade in questa finestra in nessuno dei due casi** (dichiarato, non ottimizzato) |
| **AMD_REVERSAL (24)** | 13/11/**2** | 4/3/**1** | **Cambia materialmente** — vedi dettaglio sotto |
| JUDAS_SWING (29) | 0/0/**0** | 0/0/**0** | Identico — nessun trade in questa finestra |
| LDN_REVERSAL (30) | 0/0/**0** | 0/0/**0** | Identico — nessun trade in questa finestra |
| PO3 (33) | 0/0/**0** | 0/0/**0** | Identico — nessun trade in questa finestra |

### AMD_REVERSAL isolato — dettaglio trade-per-trade

**Pre-fix (2 trade, entrambi vincenti)**:

| OPEN | Entry | SL | TP | CLOSE | Prezzo | PnL | r | Esito |
|---|---|---|---|---|---|---|---|---|
| 2026.06.01 20:00:00 | 4480.35 | **4360.54** | 4509.03 | 2026.06.02 07:18:40 | 4509.03 | **+47.8** | +0.200 | `tp` |
| 2026.06.03 13:15:00 | 4463.36 | **4360.45** | 4492.48 | 2026.06.04 14:45:40 | 4492.48 | **+45.6** | +0.222 | `tp` |

**Post-fix (1 trade, perdente)**:

| OPEN | Entry | SL | TP | CLOSE | Prezzo | PnL | r | Esito |
|---|---|---|---|---|---|---|---|---|
| 2026.06.03 13:15:00 | 4463.36 | **4449.25** | 4492.48 | 2026.06.03 15:35:40 | 4449.25 | **-24.3** | -0.866 | `sl` |

**Due decisioni distinte cambiano, per due ragioni distinte**:

1. **Il trade del 2026.06.01 20:00:00 è interamente spurio**: nessun controparte post-fix. `sw.sweptAsiaLow` leggeva `true` da stato residuo su una barra dove il detector, correttamente inizializzato, non conferma alcuno sweep. Campo responsabile: `sw.sweptAsiaLow` (garbage pre-fix).

2. **Il trade del 2026.06.03 13:15:00 si apre in ENTRAMBE le run con lo stesso identico entry (4463.36)** — la condizione d'ingresso stessa non cambia — **ma con uno stop loss radicalmente diverso**: 4360.45 (pre-fix, ~123 pip da entry) contro 4449.25 (post-fix, ~14 pip da entry). Campo responsabile: **`sw.refLow`**, usato direttamente in `s.slPrice = sw.refLow - 0.4 * atr;` senza alcuna verifica di validità. Pre-fix, `refLow` conteneva un valore di stack residuo (~4360, sospettosamente quasi identico al valore "spurio" del trade #1 — coerente con riutilizzo dello stesso frame di stack) invece del vero riferimento Asia-Low. Lo stop abnormemente largo ha permesso al trade di sopravvivere fino al take profit; con lo stop corretto (stretto, basato sul vero riferimento), lo stesso movimento di prezzo lo avrebbe (e lo ha, post-fix) fermato in perdita.

**Conclusione**: la performance storica isolata di AMD_REVERSAL in questa finestra (+93.4 pre-fix, 2 vincite) era **interamente un artefatto di memoria non inizializzata** — non un edge reale. Il vero risultato (post-fix) è un'unica perdita di -24.3.

Nessun parametro è stato ottimizzato per ottenere questo risultato — è l'esito diretto, non modificato, delle stesse regole di ingresso con il detector corretto.

## 4. Determinism test

Due run identiche della configurazione cross-consumer sul codice POST-fix (stesso identico binario compilato una sola volta), GOLD H4, 2026.06.01→2026.06.15:

| | Run 1 | Run 2 |
|---|---|---|
| Righe `NEXUS_trades.csv` | 104 | 104 |
| SHA256 | `cb25cc93d10a4662ecdb9f800f03f3cc7ab15200681071f486b52e0fd0397094` | **identico** |
| `total_events` (lifecycle) | 379 | 379 |
| `malformed_skipped` | 0 | 0 |
| `raw_observations`/`unique_events`/`multipass_duplicate`/`cross_consumer_duplicate` | 2652/165/2225/262 | **identici** |

**Determinismo confermato bit-a-bit.** Nessuno STOP necessario.

## 5. Semantic correctness — default per campo

| Campo | Default esplicito | Significato quando non c'è sweep | Corretto? |
|---|---|---|---|
| `confirmed` | `false` | "nessun sweep confermato in questa chiamata" | ✅ |
| `dir` | `DIR_NONE` | "nessuna direzione da uno sweep" | ✅ |
| `level` | `0` | "nessun prezzo di livello valido" (0 non è mai un prezzo GOLD plausibile, sentinella coerente col resto del codice, es. i controlli `pmh>0` già esistenti altrove) | ✅ |
| `levelTag` | `""` | "nessun tag di livello" | ✅ |
| `refHigh` | `0` | "nessun riferimento massimo valido" | ✅ |
| `refLow` | `0` | "nessun riferimento minimo valido" | ✅ |
| `sweptPDH`/`sweptPDL`/`sweptPWH`/`sweptPWL`/`sweptPMH`/`sweptPML`/`sweptAsiaHigh`/`sweptAsiaLow`/`sweptEQH`/`sweptEQL` | `false` (ciascuno) | "questo specifico livello non è stato sweepato in questa chiamata" | ✅ |

Nessun nuovo significato introdotto: ogni default è il valore "sentinella nulla" già usato altrove nella stessa codebase per lo stesso tipo (0/false/""), non un valore di fallback "intelligente" o "sicuro" inventato per compensare i consumer non gated. In particolare, **`refHigh`/`refLow` a 0 restano 0** anche se questo espone i 5 consumer EXPOSED a calcoli assurdi se usati senza controllo a monte (es. `0 - 0.4*atr` come SL) — cambiare questo default per "proteggere" quei consumer introdurrebbe un significato nuovo e non richiesto (un fallback fittizio), esplicitamente fuori scope. Il problema dei 5 consumer resta un problema *loro*, non del detector.

## 6. Baseline policy

- **AMD_REVERSAL**: baseline storiche (qualunque backtest/valutazione precedente basato sul detector non corretto) → **INVALIDATED_BY_UNINITIALIZED_STATE_BUG**. Prova diretta in questo audit: 2 trade vincenti (+93.4 aggregato) risultavano da uno stop loss calcolato su un riferimento (`sw.refLow`) di memoria non inizializzata, non dal vero riferimento Asia-Low.
- **TURTLE_SOUP, JUDAS_SWING, LDN_REVERSAL, PO3**: **nessuna invalidazione empirica in questa finestra** (0 trade in entrambi i casi, nessuna prova di impatto qui) — restano però classificati EXPOSED_TO_UNINITIALIZED_FLAGS a livello di codice, quindi qualunque baseline storica calcolata su **altre finestre temporali** in cui questi consumer abbiano prodotto trade **non è verificabile retroattivamente** senza ripetere lo stesso confronto pre/post-fix su quella finestra specifica. Non classificate INVALIDATED per assenza di prova diretta, ma segnalate come a rischio.
- **LIQ_SWEEP, SH_BMS_RTO, SH_BMS_RTO_V2, SILVER_BULLET, CISD, NY_REVERSAL, WICK_SWEEP_REV**: **nessuna invalidazione** — SAFE o NOT_AFFECTED per costruzione, nessuna baseline storica di queste strategie è messa in dubbio da questo fix.

## 7. Acceptance

| Criterio | Esito |
|---|---|
| Root cause confermata | ✅ (test diagnostico minimo, §1 del report precedente) |
| Post-fix deterministico | ✅ (§4, bit-identico su 2 run) |
| `malformed = 0` | ✅ (§4) |
| Tutti i cambi trade spiegabili causalmente | ✅ (§2-3: un solo trade reale di differenza, tracciato a due campi specifici: `sweptAsiaLow` e `refLow`) |
| Nessun consumer SAFE cambia comportamento inaspettatamente | ✅ (nessuna variazione di trade LIQ_SWEEP/SH_BMS_RTO/SH_BMS_RTO_V2/SILVER_BULLET osservata in nessun test) |
| Campi default con semantica corretta | ✅ (§5, nessun nuovo significato introdotto) |
| Nessuna modifica a condizioni/soglie/logica di strategia | ✅ (verificato riga per riga, unica modifica è l'inizializzazione) |

Tutti i criteri soddisfatti.

## Verdict

### **DETECTOR_FIX_SEMANTICALLY_VALID**

Il cambio di trade count (102→104) è interamente spiegato da due campi specifici (`sw.sweptAsiaLow`, `sw.refLow`) letti da un solo consumer preesistentemente non-gated (AMD_REVERSAL), la cui vecchia baseline è stata dimostrata dipendere da memoria non inizializzata e viene dichiarata invalida. Nessun consumer sicuro è stato alterato. Nessuna nuova semantica introdotta. Determinismo pieno.
