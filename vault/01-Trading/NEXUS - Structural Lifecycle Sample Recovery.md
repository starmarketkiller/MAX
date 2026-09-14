# NEXUS Research Infrastructure — Phase C: Structural Lifecycle Sample Recovery

Segue [[NEXUS - Causal Research Thread 3 True Break Quality]] (verdict `HOLD_INSUFFICIENT_TRUE_BREAK_SAMPLE`, n_risolti=60 < 150). Obiettivo di questa fase: aumentare il campione causale affidabile **senza modificare entry/exit/risk/strategy semantics**.

## 1. Root cause — dimostrata con trace minimo

Ipotesi da verificare: il desync multi-TF-pass di `NXS_CollectAllSignals` produce lifecycle SH_BMS_RTO inconsistenti (`lifecycle_redundant_after_close`, `true_break_after_close`).

**Trace diagnostico temporaneo** (rimosso dopo la verifica, mai committato): contatore `_shbmsDiagCount` con `Print` sui primi 400 casi `newBar=true` in `NXS_SHBMS_UpdateSide`, campi loggati: `realtick`, `dir`, `tf`, `curBar0`, `state_before`, `barsWaited`, `lastBarTime_before`, `levelId`.

**Evidenza raccolta**: confermati **6 timeframe distinti** (H1, D1, M30, M15, H4, M5) che chiamano `NXS_SHBMS_UpdateSide` con `newBar=true` **nello stesso tick reale**. La funzione riceve `tf = NXS_EffTF()` (il TF del pass multi-TF attivo in quel momento), non il TF nominale di SH_BMS_RTO, mentre lo stato (`g_shbmsBuy`/`g_shbmsSell`) è **condiviso** fra tutti i pass. Poiché `curBar0 = iTime(g_sym, tf, 0)` dipende dal tf del pass, e il gate `newBar = (st.lastBarTime != curBar0)` è definito relativamente a questo valore tf-dipendente, più pass nello stesso tick possono soddisfare `newBar=true` e innescare transizioni usando OHLC di **timeframe diversi fra loro**. MQL5 esegue in modo sincrono: il primo pass che arriva "vince" la transizione e muta lo stato; i pass successivi nello stesso tick vedono lo stato già mutato e proseguono usando i propri dati — producendo cascate SWEEP→TRUE_BREAK/INVALIDATE nello stesso tick con dati di TF incoerenti fra loro. Questo è esattamente ciò che il rebuild Python (v1) osservava come `redundant_after_close`/`true_break_after_close`.

**Causa ulteriore identificata** (emersa durante la validazione, non ipotizzata a priori): la v1 del linkage Python (`assign_episodes()`, replay in ordine di `event_id` + euristica "SH_BMS_RTO in `observed_by`" per riconoscere una nuova apertura) poteva agganciare un TRUE_BREAK/RETEST/INVALIDATE all'episodio Python **sbagliato** quando la riga SWEEP reale non veniva riconosciuta come nuova apertura nel preciso momento in cui veniva osservata (es. osservata prima da `DETECTOR`, con `SH_BMS_RTO` aggiunto solo in un evento successivo per persistenza della condizione su bar successive). Questa contaminazione **cross-episodio** — non solo rumore intra-episodio — è la causa principale del 69.3% di esclusione trovato in Thread 3.

## 2. Fix minimo implementato

**Architettura**: separare l'identità di episodio dall'osservazione multi-TF, senza toccare la semantica operativa di SH_BMS_RTO.

Campo additivo `episodeSeq` in `SNXSSHBmsState`, incrementato **una sola volta**, esattamente alla transizione reale IDLE→SWEPT:

```mql5
struct SNXSSHBmsState {
   ...
   int episodeSeq;   // SOLO diagnostico: mai letto da alcuna condizione di trading
};
```

```mql5
if(st.state == SHBMS_IDLE){
   if(newBar && sw.confirmed && sw.dir == wantSweep){
      ...
      st.episodeSeq++;   // unico punto della transizione IDLE->SWEPT
      NXS_Structural_ObserveSweep(sw, tf, "SH_BMS_RTO", st.structLevelId, st.episodeSeq);
   }
}
```

MQL5 esegue in modo sincrono: qualunque pass multi-TF arrivi qui per primo in un dato tick è l'**unico** a incrementare (i pass successivi nello stesso tick trovano già `state != IDLE` e non rientrano in questo ramo). `episodeSeq` non viene mai azzerato da `NXS_SHBMS_Reset()` (persiste/incrementa in modo monotono per l'intera durata del test). Tutti e 6 i punti di hook lifecycle (`OnInvalidate` ×4, `OnTrueBreak` ×1, `OnRetest` ×1) passano `st.episodeSeq` al research log.

Lato `NXS_StructuralResearchLog.mqh`: nuovo campo `sh_bms_episode_seq` in `SNXSStructuralEvent`, propagato attraverso `_NXS_Struct_LogEvent`, `NXS_Structural_ObserveSweep` (parametro opzionale, default 0 — retro-compatibile per i call site DETECTOR/LIQ_SWEEP che non hanno un concetto di episodio), `NXS_Structural_OnTrueBreak/OnRetest/OnInvalidate`, ed esportato come ultima colonna CSV.

**Nessuna condizione, soglia o decisione di trading toccata** — solo campo additivo + parametro aggiuntivo nelle chiamate di hook, cambi puramente di logging/identità di ricerca.

### Alternative valutate e scartate
- **Guard per event_id/tick**: non necessario — la sincronia di MQL5 già garantisce un solo incremento per transizione reale.
- **State transition ownership su singolo pass canonico**: avrebbe richiesto toccare la logica multi-TF-pass di `NXS_CollectAllSignals`, fuori scope dichiarato (rischio trading).
- **Shadow state per-TF**: avrebbe cambiato la semantica di SH_BMS_RTO (uno stato per TF invece di uno condiviso), esplicitamente escluso.
- **Dedup lifecycle lato Python**: già tentato in v1 (euristica `observed_by`), è la causa stessa del problema — sostituito dall'identità reale.

La soluzione minima scelta (contatore monotono sulla state machine esistente) è l'unica che non tocca alcun ramo decisionale e non richiede assunzioni: l'identità è quella reale della macchina a stati, non una ricostruzione.

## 3. Parità di trading — verificata più volte

Metodologia: config `InpResearchMode=false`, `InpStrategySelector=0` (tutte le strategie attive, incluso SH_BMS_RTO), GOLD H4, Model=1, `2026.06.01→2026.06.15`, confronto OFF (`InpStructuralResearchEventLog=false`) vs ON (`=true`).

| Run | Trade | SHA256 |
|---|---|---|
| Baseline noto (pre-esistente, commit `9b77f83`+Phase A.1) | 104 | `cb25cc93d10a4662ecdb9f800f03f3cc7ab15200681071f486b52e0fd0397094` |
| OFF (fix episodeSeq, codice pulito, terminale LIVE) | 104 | `cb25cc93d10a4662ecdb9f800f03f3cc7ab15200681071f486b52e0fd0397094` |
| ON (fix episodeSeq, codice pulito, terminale LIVE) | 104 | `cb25cc93d10a4662ecdb9f800f03f3cc7ab15200681071f486b52e0fd0397094` |

**Stessi trade, stesso digest, stesso PnL/PF fingerprint.** Nessun impatto sul trading confermato in entrambi gli stati (log ricerca OFF/ON) e ri-verificato una seconda volta dopo la rimozione di codice diagnostico temporaneo introdotto durante il debug infrastrutturale (§5).

## 4. Sample recovery — confronto PRE vs POST

Ricollezionate tutte e 6 le finestre (`2025-05-01 → 2026-08-25`, stesse date esatte di Thread 3) con la nuova strumentazione (Research Mode, selector 21 = SH_BMS_RTO, GOLD H4, Model=1). `assign_episodes()` riscritta per usare `(window_id, direction, sh_bms_episode_seq)` come chiave di episodio reale, al posto del replay euristico per `event_id`+`observed_by` (dettagli in `build_structural_dataset_v1.py`).

| | PRE (Thread 3, v1) | POST (Phase C, v2) |
|---|---|---|
| Episodi con ≥1 TRUE_BREAK | 349 | 270 |
| Esclusi (post-close/redundant) | 242 (69.3%) | 0 (0%) |
| **TRUE_BREAK validi in population** | **107** | **270** |
| AMBIGUOUS_SAME_BAR | 47 (43.9%) | 111 (41.1%) |
| CENSORED | 0 | 0 |
| **RISOLTI totali** | **60** | **159** |
| BUY / SELL | 54 / 53 | 136 / 134 |
| DISCOVERY (wA+w0) / VALIDATION (w1-w4) | — | 69 / 90 |

Il tasso di esclusione post-close crolla da 69.3% a 0% — coerente con la causa dimostrata al §1: la maggior parte delle esclusioni v1 non erano rumore genuino intra-episodio, ma contaminazione cross-episodio dell'euristica di ricostruzione, ora eliminata perché l'identità è quella reale della macchina a stati.

### Nota su un fenomeno collaterale osservato (onesto, non un difetto della fix)
288 TRUE_BREAK (e un numero maggiore di INVALIDATE) restano **orphan** — nessuna riga SWEEP canonica associabile allo stesso `(window_id, direction, episodeSeq)`. Causa identificata con trace mirato: l'evento SWEEP "canonico" (fonte condivisa Fase A.1) è identificato per `(structural_level_id, bar)`, mentre l'identità di SH_BMS_RTO è per transizione reale — quando SH_BMS_RTO si aggancia a un bar il cui evento canonico non viene mai creato (es. sweep scartato dal filtro di coerenza difensiva `sw.level<=0` già documentato in `NXS_Structural_ObserveSweep`, "anomalia osservata... probabile artefatto di dati non ancora sincronizzati"), la sua transizione avviene comunque (episodeSeq incrementato) ma non c'è alcuna riga SWEEP da agganciare. Questi casi sono **correttamente esclusi come orphan** (mai agganciati per timestamp più vicino, mai misattribuiti) — esattamente la policy di sicurezza causale già in vigore. Non impatta la validità del campione di 159 risolti, che sono TUTTI TRUE_BREAK con linkage completo e verificato.

**Target raggiunto: 159 ≥ 150.**

## 5. Nota infrastrutturale (non-causale, per trasparenza)

Durante la raccolta, il terminale TEST (`C:\MT5-Tester`) è diventato instabile dopo ripetute ricompilazioni/kill di processo nella stessa sessione (Research Mode smetteva di raggiungere `OnInit`, confermato con marker diagnostici temporanei e con un test di controllo sul codice originale via `git stash`, che falliva identicamente — provando che la causa non era il fix ma lo stato del terminale). La raccolta delle 6 finestre è stata quindi eseguita sul terminale LIVE (stesso identico fix compilato lì alle 20:38, mai contaminato dal debug del terminale TEST), il cui stato è stato riverificato sano tramite il test di parità del §3. Tutto il codice diagnostico temporaneo è stato rimosso prima del commit finale (verificato via `git diff`).

## 6. Secondo consumer — non necessario

Il target di 150 esiti risolti è stato raggiunto con il solo SH_BMS_RTO instrumentato. Non è stata quindi valutata né implementata alcuna strumentazione aggiuntiva su SILVER_BULLET o SH_BMS_RTO_V2 — non necessaria data la sample recovery già sufficiente.

## 7. Conseguenza naturale — Thread 3 riaperto

Con 159 ≥ 150, lo script `causal_thread3_true_break_quality.py` (invariato, nessuna soglia o metodologia modificata) è proseguito automaticamente oltre il gate di sample-sufficiency fino alla discovery multivariata pre-registrata (54 ipotesi univariate, train/OOS split cronologico DISCOVERY/VALIDATION, soglie di materialità/significatività invariate). Esito: **48 NO_SIGNAL, 6 WEAK_HINT, 0 PROMISING_HYPOTHESIS** → verdict Thread 3: `NO_PROMISING_HYPOTHESIS`. Questo è riportato qui per trasparenza come conseguenza automatica e non pilotata della sample recovery, ma **non è l'oggetto di questa fase** (che riguarda solo l'infrastruttura di campionamento) — un'eventuale analisi dedicata dei 6 WEAK_HINT andrebbe condotta come thread di ricerca separato, con lo stesso rigore anti-data-mining già applicato altrove in questo progetto.

## Verdict

### **SAMPLE_RECOVERY_SUCCESS**

- Root cause: dimostrata con trace minimo (desync multi-TF-pass + contaminazione cross-episodio nell'euristica di linkage v1).
- Fix: additivo, minimale, mai letto da alcuna decisione di trading.
- Parità di trading: **confermata** (104/104 trade, stesso SHA256, OFF e ON, verificata due volte).
- Campione: 60 → **159** risolti (soglia 150 raggiunta).
- Secondo consumer: non necessario.
- Commit: da eseguire subito dopo questo report (fix validato).
