//+------------------------------------------------------------------+
//| NXS_Strategies_Experimental.mqh                                   |
//| 10/09 - Strategie SPERIMENTALI richieste dall'utente per il nuovo  |
//| protocollo di test (Fast Smoke -> Fast Structural -> Full          |
//| Validation), tenute SEPARATE dalle 51 strategie del nucleo NEXUS   |
//| cosi' da poterle isolare/rimuovere facilmente se non superano i     |
//| primi livelli del protocollo.                                      |
//+------------------------------------------------------------------+
#ifndef __NXS_STRATEGIES_EXPERIMENTAL_MQH__
#define __NXS_STRATEGIES_EXPERIMENTAL_MQH__

// === WICK SWEEP REVERSAL (10/09) ============================================
// Idea dell'utente: su H4, una candela con una wick (sopra, sotto o entrambe)
// lascia un "livello" (l'estremo della wick). Quando una barra successiva
// SUPERA quel livello di almeno InpWickSweep_SweepPips pip, il prezzo tende a
// invertire - si entra SUBITO ("di pancia", al tick, non alla chiusura barra)
// nella direzione opposta allo sweep, con SL/TP fissi in pip.
//
// Convenzione pip ESPLICITA per GOLD (confermata con l'utente 10/09): 1 pip
// = $0.10 = 10 x g_profile.pipSize (che vale 0.01 per XAUUSD) - NON la stessa
// convenzione "1 pip = pipSize" usata altrove nel codice (es. InpFixedBEPips),
// per questo la conversione e' esplicita qui e non riusa g_profile.pipSize
// direttamente.
//
// 10/09 (fase 2 - "audit prima di evolvere"): il primo Fast Smoke dava 0
// trade per un bug di consumo one-shot durante i passaggi multi-TF sbagliati
// (guardia g_activeTF sotto, gia' corretta). Il secondo Fast Smoke dava
// ancora 0 trade per un cancello completamente indipendente a valle
// (NXS_StrategyKnown, vedi commit di registrazione nel contract) - MA nel
// frattempo e' emerso un problema di disegno reale: il livello si marcava
// "consumato" (one-shot per sempre) alla sola RILEVAZIONE dello sweep,
// PRIMA di sapere se il trade si sarebbe davvero aperto. Impossibile cosi'
// distinguere "segnale tradato" da "segnale generato ma rifiutato a valle".
//
// Ora `triggered` (sweep rilevato) e `consumed` (trade REALMENTE aperto,
// confermato da NXS_WickSweep_OnExecuteResult chiamata da NXS_Execution.mqh
// dopo l'esito vero di NXS_TryExecuteRC) sono due stati separati. Un livello
// innescato ma non ancora consumato viene ritentato al massimo una volta per
// barra H4 (throttle su lastAttemptBar - "non un loop infinito sullo stesso
// tick"), finche' non si apre, il prezzo lo invalida tornando sotto/sopra il
// livello originale, o una nuova wick lo sostituisce.
//
// Semplificazioni della prima versione (DA VERIFICARE con i dati, non ancora
// ottimizzate - vedi audit "cosa migliorare" richiesto dall'utente):
//   - un solo livello attivo per lato (alto/basso) alla volta: una nuova
//     candela con wick valida SOSTITUISCE il livello precedente sullo stesso
//     lato, anche se non ancora consumato (conteggiato in
//     levelsReplacedUnused). Se questo scarta troppe opportunita' valide, il
//     prossimo passo naturale e' un registro a piu' zone come
//     NXS_Strat_FVG_Mitigation_Window;
//   - H4 e' hardcoded (non NXS_EffTF()) - la strategia gira SEMPRE sulla
//     candela H4 reale, indipendentemente da InpUseStrategyProfiles/
//     InpProfileMultiTF (che restano necessari per Research Mode ma non
//     condizionano il TF di QUESTA strategia).
struct SNxsWickSide {
   double   level;             // 0 = nessun livello attivo su questo lato
   datetime createdAt;
   bool     triggered;         // sweep >= soglia rilevato almeno una volta
   bool     revisited;         // prezzo ha toccato/superato il livello grezzo (anche senza raggiungere lo sweep) - one-shot per livello
   bool     consumed;          // trade REALMENTE aperto per questo livello (stato terminale)
   datetime lastAttemptBar;    // throttle: barra H4 dell'ultimo tentativo di apertura tentato
   int      attempts;          // quante volte NXS_TryExecuteRC e' stato chiamato per questo livello
   long     id;                // 11/09 - identita' stabile del livello (vedi NXS_WickShadow sotto): SOLO
                                // per instrumentazione/logging, non usata da nessuna decisione di trading -
                                // incrementata a ogni sostituzione in _NXS_WickSweep_UpdateLevel, zero impatto
                                // sul comportamento della strategia canonica.
};
SNxsWickSide g_wickHigh, g_wickLow;
datetime     g_wickLastBar = 0;
long         g_wickLevelIdCounter = 0;

// Funnel completo richiesto dall'utente (10/09) per capire ESATTAMENTE dove
// nella pipeline i segnali si perdono, invece di dedurlo indirettamente dai
// trade aperti. Stampato una volta a fine test da NXS_WickSweep_PrintFunnel
// (chiamata da OnDeinit se InpStrat_WickSweep e' attivo).
struct SNxsWickFunnel {
   long h4Candles;
   long levelsCreated;
   long levelsRevisited;
   long sweepsDetected;
   long duplicateRetrigger;        // sweep gia' innescato/tentato su questa barra, throttle applicato
   long entryAttempts;             // segnale arrivato fino a NXS_TryExecuteRC
   long entryRejected;
   long entryOpened;
   long buyOpened, sellOpened;
   long levelsInvalidatedByPrice;  // il prezzo e' rientrato sotto/sopra il livello originale prima di essere consumato
   long levelsReplacedUnused;      // una nuova wick ha sostituito un livello non ancora consumato
};
SNxsWickFunnel g_wickFunnel;

void _NXS_WickSweep_UpdateLevel(){
   datetime bar0 = iTime(g_sym, PERIOD_H4, 0);
   if(bar0 == g_wickLastBar) return;   // stessa barra H4, gia' aggiornato
   bool firstCall = (g_wickLastBar == 0);
   g_wickLastBar = bar0;
   if(!firstCall) g_wickFunnel.h4Candles++;

   double o1 = iOpen(g_sym, PERIOD_H4, 1), c1 = iClose(g_sym, PERIOD_H4, 1);
   double h1 = iHigh(g_sym, PERIOD_H4, 1), l1 = iLow(g_sym, PERIOD_H4, 1);
   double bodyTop = MathMax(o1, c1), bodyBot = MathMin(o1, c1);
   double upperWick = h1 - bodyTop;
   double lowerWick = bodyBot - l1;
   double pip = 10.0 * g_profile.pipSize;   // 1 pip = $0.10 su GOLD (vedi nota sopra)
   double minWick = InpWickSweep_MinWickPips * pip;

   if(upperWick >= minWick){
      if(g_wickHigh.level > 0 && !g_wickHigh.consumed) g_wickFunnel.levelsReplacedUnused++;
      SNxsWickSide nl; ZeroMemory(nl);
      nl.level = h1; nl.createdAt = iTime(g_sym, PERIOD_H4, 1);
      nl.id = ++g_wickLevelIdCounter;
      g_wickHigh = nl;
      g_wickFunnel.levelsCreated++;
   }
   if(lowerWick >= minWick){
      if(g_wickLow.level > 0 && !g_wickLow.consumed) g_wickFunnel.levelsReplacedUnused++;
      SNxsWickSide nl; ZeroMemory(nl);
      nl.level = l1; nl.createdAt = iTime(g_sym, PERIOD_H4, 1);
      nl.id = ++g_wickLevelIdCounter;
      g_wickLow = nl;
      g_wickFunnel.levelsCreated++;
   }
}

// Chiamata da NEXUS_EA_v2.mq5 subito dopo NXS_TryExecuteRC per QUALUNQUE
// segnale WICK_SWEEP_REV (esito vero: aperto o rifiutato, con motivo -
// EnumToString(rc) copre protections/news/HTF/velocity/score/stops/volume/
// preflight/order-send, cioe' tutti i cancelli possibili, non solo quelli di
// NXS_OpenTrade). Finalizza `consumed` SOLO se opened=true - questo e' il
// fix richiesto: il livello non e' piu' "bruciato" da un tentativo fallito.
void _NXS_WickSweep_FinalizeSide(SNxsWickSide &side, bool opened, string reason){
   g_wickFunnel.entryAttempts++;
   side.attempts++;
   if(opened){
      side.consumed = true;
      g_wickFunnel.entryOpened++;
   } else {
      g_wickFunnel.entryRejected++;
      if(InpDebugLog)
         PrintFormat("[WICKSWEEP][REJECTED] level=%.2f attempts=%d reason=%s",
                     side.level, side.attempts, reason);
   }
}

void NXS_WickSweep_OnExecuteResult(int dir, bool opened, string reason){
   if(dir == DIR_SELL)      _NXS_WickSweep_FinalizeSide(g_wickHigh, opened, reason);
   else if(dir == DIR_BUY)  _NXS_WickSweep_FinalizeSide(g_wickLow,  opened, reason);
   else return;
   if(opened){
      if(dir == DIR_BUY) g_wickFunnel.buyOpened++; else g_wickFunnel.sellOpened++;
   }
}

void NXS_WickSweep_PrintFunnel(){
   PrintFormat("[WICKSWEEP][FUNNEL] h4Candles=%d levelsCreated=%d levelsRevisited=%d "
               "sweepsDetected=%d duplicateRetrigger=%d entryAttempts=%d entryRejected=%d "
               "entryOpened=%d buyOpened=%d sellOpened=%d levelsInvalidatedByPrice=%d "
               "levelsReplacedUnused=%d",
               g_wickFunnel.h4Candles, g_wickFunnel.levelsCreated, g_wickFunnel.levelsRevisited,
               g_wickFunnel.sweepsDetected, g_wickFunnel.duplicateRetrigger, g_wickFunnel.entryAttempts,
               g_wickFunnel.entryRejected, g_wickFunnel.entryOpened, g_wickFunnel.buyOpened,
               g_wickFunnel.sellOpened, g_wickFunnel.levelsInvalidatedByPrice,
               g_wickFunnel.levelsReplacedUnused);
}

// === WICK SWEEP SHADOW/RESEARCH (11/09) =====================================
// Richiesto dall'utente per validare RECLAIM_TRIGGER (emerso dallo studio
// Python offline) a livello tick, PRIMA di introdurlo in qualunque forma nella
// strategia canonica. Puramente osservazionale: NESSUN ordine reale viene
// inviato da questo blocco - legge solo g_wickHigh/g_wickLow (gia' aggiornati
// dalla logica canonica) e simula un trade VIRTUALE con SL/TP identici
// (25/100 pip), nessun BE, nessun trailing, nessun filtro nuovo. Attivo SOLO
// se InpResearchWickShadow=true (default false, zero impatto altrimenti) E
// InpStrat_WickSweep=true (serve la logica canonica viva per avere livelli).
//
// Uno shadow event per lato alla volta (stessa semantica "un livello attivo"
// della strategia reale) - se il livello viene sostituito da una nuova wick
// prima che l'evento si risolva (reclaim + virtual trade chiuso), l'evento
// viene abbandonato e loggato come tale, non forzato a una risoluzione
// artificiale. Input InpResearchWickShadow dichiarato in NXS_Inputs.mqh.

struct SNxsWickShadowEvent {
   bool     active;
   long     sweep_id;
   long     level_id;
   string   side;              // "HIGH" o "LOW"
   int      dir;                // DIR_SELL (side=HIGH) o DIR_BUY (side=LOW) - direzione del fade
   double   level_price;
   double   trigger_price;
   datetime sweep_time;
   double   max_penetration_pips;   // aggiornato tick per tick, SOLO fino al reclaim del trigger (poi congelato)
   bool     reclaimed_trigger;
   datetime reclaim_trigger_time;
   double   price_at_reclaim_trigger;
   bool     reclaimed_level;
   datetime reclaim_level_time;
   bool     virtual_open;
   double   virtual_entry_price;
   datetime virtual_entry_time;
   double   virtual_sl;
   double   virtual_tp;
   double   virtual_mae_pips;
   double   virtual_mfe_pips;
   long     lastSweptLevelId;   // 12/09 - gate one-shot per livello (vedi fix parity FAIL sotto)
};
SNxsWickShadowEvent g_wickShadowHigh, g_wickShadowLow;
long g_wickShadowIdCounter = 0;
long g_wickShadowSweepCount = 0;   // per il controllo di parita' richiesto: deve combaciare con g_wickFunnel.sweepsDetected

void _NXS_WickShadow_ProcessSide(SNxsWickShadowEvent &sh, SNxsWickSide &side, string sideLabel, int fadeDir, bool isNewCohortBar){
   double pip       = 10.0 * g_profile.pipSize;
   double sweepDist = InpWickSweep_SweepPips * pip;
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double ask = SymbolInfoDouble(g_sym, SYMBOL_ASK);
   // stesso riferimento di prezzo usato dalla logica canonica per rilevare lo sweep
   // (bid per il lato alto/SELL, ask per il lato basso/BUY - vedi NXS_Strat_WickSweepReversal)
   double refPrice = (fadeDir == DIR_SELL) ? bid : ask;

   if(!sh.active){
      if(side.level <= 0) return;
      // 12/09 - FIX parity FAIL v1 (shadow_sweeps=1100 vs sweepsDetected=182):
      // gate one-shot per livello, replica `triggered` canonico - un livello
      // genera un evento shadow una sola volta, mai ripetuto finche' l'id non
      // cambia (nuova wick).
      if(side.id == sh.lastSweptLevelId) return;
      // 12/09 - FIX parity FAIL v2 (shadow_sweeps=258 vs sweepsDetected=182,
      // trovato correlando i timestamp reali: le aperture WICK_SWEEP_REV
      // cadono SEMPRE su un boundary InpTFEntry/M15 esatto, mai a meta' barra
      // - scoperta del "New bar gate" globale in OnTick, NEXUS_EA_v2.mq5:
      // `if(iTime(g_sym,InpTFEntry,0) == g_lastBarTime) return;` gia' a monte
      // di NXS_CollectAllSignals - la strategia canonica NON e' davvero
      // valutata a ogni tick nonostante il suo commento dica il contrario,
      // solo una volta per barra InpTFEntry). La COORTE di rilevazione dello
      // sweep deve quindi allinearsi alla stessa cadenza: si crea un nuovo
      // evento shadow SOLO al primo tick di una nuova barra InpTFEntry,
      // esattamente come il canonico - il follow-up (penetrazione/reclaim/
      // virtual trade) resta invece tick-level su ogni tick successivo (vedi
      // sotto, fuori da questo blocco). Vedi nota vault "NEXUS - Global
      // New-Bar Gate / Signal Sampling Audit" (12/09) per l'analisi completa.
      if(!isNewCohortBar) return;
      bool swept = (fadeDir == DIR_SELL) ? (bid >= side.level + sweepDist) : (ask <= side.level - sweepDist);
      if(!swept) return;
      sh.lastSweptLevelId = side.id;
      sh.active = true;
      sh.sweep_id = ++g_wickShadowIdCounter;
      g_wickShadowSweepCount++;
      sh.level_id = side.id;
      sh.side = sideLabel;
      sh.dir = fadeDir;
      sh.level_price = side.level;
      // 12/09 - trigger_price = prezzo REALE osservato al momento della
      // valutazione canonica (refPrice), non piu' il teorico level+sweepDist:
      // il canonico entra a s.entryRef=bid/ask correnti, che puo' gia' aver
      // superato la soglia (gap intrabarra InpTFEntry) - stesso identico
      // riferimento della strategia reale, per un confronto fedele.
      sh.trigger_price = refPrice;
      sh.sweep_time = TimeCurrent();
      sh.max_penetration_pips = MathAbs(refPrice - side.level) / pip;
      sh.reclaimed_trigger = false; sh.reclaimed_level = false; sh.virtual_open = false;
      PrintFormat("[WICKSHADOW][SWEEP] sweep_id=%d level_id=%d side=%s level=%.2f trigger=%.5f time=%s",
                  sh.sweep_id, sh.level_id, sh.side, sh.level_price, sh.trigger_price,
                  TimeToString(sh.sweep_time, TIME_DATE|TIME_SECONDS));
      return;
   }

   // il livello osservato e' stato sostituito prima che l'evento si risolvesse - abbandona, non forzare
   if(side.id != sh.level_id){
      PrintFormat("[WICKSHADOW][ABANDONED] sweep_id=%d reason=level_replaced reclaimed_trigger=%s virtual_open=%s",
                  sh.sweep_id, (sh.reclaimed_trigger?"true":"false"), (sh.virtual_open?"true":"false"));
      sh.active = false;
      return;
   }

   double breachPips = ((fadeDir == DIR_SELL) ? (refPrice - sh.level_price) : (sh.level_price - refPrice)) / pip;
   if(!sh.reclaimed_trigger && breachPips > sh.max_penetration_pips) sh.max_penetration_pips = breachPips;

   if(!sh.reclaimed_trigger){
      bool backToTrigger = (fadeDir == DIR_SELL) ? (refPrice <= sh.trigger_price) : (refPrice >= sh.trigger_price);
      if(backToTrigger){
         sh.reclaimed_trigger = true;
         sh.reclaim_trigger_time = TimeCurrent();
         sh.price_at_reclaim_trigger = refPrice;
         sh.virtual_open = true;
         sh.virtual_entry_price = sh.trigger_price;
         sh.virtual_entry_time = TimeCurrent();
         double slDist = InpWickSweep_SLPips * pip;
         double tpDist = InpWickSweep_TPPips * pip;
         if(fadeDir == DIR_SELL){
            sh.virtual_sl = sh.virtual_entry_price + slDist;
            sh.virtual_tp = sh.virtual_entry_price - tpDist;
         } else {
            sh.virtual_sl = sh.virtual_entry_price - slDist;
            sh.virtual_tp = sh.virtual_entry_price + tpDist;
         }
         sh.virtual_mae_pips = 0; sh.virtual_mfe_pips = 0;
         PrintFormat("[WICKSHADOW][RECLAIM_TRIGGER] sweep_id=%d time=%s price=%.5f "
                     "time_sweep_to_reclaim_sec=%d max_penetration_before_reclaim_pips=%.2f "
                     "virtual_entry=%.5f virtual_sl=%.5f virtual_tp=%.5f",
                     sh.sweep_id, TimeToString(sh.reclaim_trigger_time, TIME_DATE|TIME_SECONDS),
                     sh.price_at_reclaim_trigger, (int)(sh.reclaim_trigger_time - sh.sweep_time),
                     sh.max_penetration_pips, sh.virtual_entry_price, sh.virtual_sl, sh.virtual_tp);
      }
   }
   if(!sh.reclaimed_level){
      bool backToLevel = (fadeDir == DIR_SELL) ? (refPrice <= sh.level_price) : (refPrice >= sh.level_price);
      if(backToLevel){
         sh.reclaimed_level = true;
         sh.reclaim_level_time = TimeCurrent();
         PrintFormat("[WICKSHADOW][RECLAIM_LEVEL] sweep_id=%d time=%s time_sweep_to_reclaim_level_sec=%d",
                     sh.sweep_id, TimeToString(sh.reclaim_level_time, TIME_DATE|TIME_SECONDS),
                     (int)(sh.reclaim_level_time - sh.sweep_time));
      }
   }

   if(sh.virtual_open){
      double favorable = (fadeDir == DIR_SELL) ? (sh.virtual_entry_price - refPrice) : (refPrice - sh.virtual_entry_price);
      double adverse   = (fadeDir == DIR_SELL) ? (refPrice - sh.virtual_entry_price) : (sh.virtual_entry_price - refPrice);
      if(favorable / pip > sh.virtual_mfe_pips) sh.virtual_mfe_pips = favorable / pip;
      if(adverse   / pip > sh.virtual_mae_pips) sh.virtual_mae_pips = adverse / pip;

      bool hitSL = (fadeDir == DIR_SELL) ? (refPrice >= sh.virtual_sl) : (refPrice <= sh.virtual_sl);
      bool hitTP = (fadeDir == DIR_SELL) ? (refPrice <= sh.virtual_tp) : (refPrice >= sh.virtual_tp);
      if(hitSL || hitTP){
         string outcome = hitSL ? "SL" : "TP";
         PrintFormat("[WICKSHADOW][EXIT] sweep_id=%d outcome=%s exit_price=%.5f exit_time=%s "
                     "virtual_MAE_pips=%.2f virtual_MFE_pips=%.2f hold_sec=%d",
                     sh.sweep_id, outcome, refPrice, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
                     sh.virtual_mae_pips, sh.virtual_mfe_pips, (int)(TimeCurrent() - sh.virtual_entry_time));
         sh.virtual_open = false;
         sh.active = false;
      }
   }
}

// Chiamata da OnTick() in NEXUS_EA_v2.mq5, guardata da InpResearchWickShadow.
// Richiama _NXS_WickSweep_UpdateLevel() (idempotente per barra H4, nessun
// effetto collaterale) per garantire che g_wickHigh/g_wickLow siano aggiornati
// anche se questa funzione viene chiamata prima della strategia canonica nello
// stesso tick.
datetime g_wickShadowLastCohortBar = 0;

void NXS_WickShadow_OnTick(){
   if(!InpResearchWickShadow || !InpStrat_WickSweep) return;
   _NXS_WickSweep_UpdateLevel();
   // 12/09 - coorte di rilevazione allineata alla cadenza REALE del canonico
   // (vedi commento dentro _NXS_WickShadow_ProcessSide): NXS_CollectAllSignals,
   // e quindi anche NXS_Strat_WickSweepReversal, gira una sola volta per
   // barra InpTFEntry (il "New bar gate" in OnTick, NEXUS_EA_v2.mq5) - non a
   // ogni tick. Un nuovo evento shadow puo' nascere SOLO al primo tick di una
   // nuova barra InpTFEntry; il follow-up (penetrazione/reclaim/virtual
   // trade) resta tick-level su ogni chiamata successiva.
   datetime cohortBar = iTime(g_sym, InpTFEntry, 0);
   bool isNewCohortBar = (cohortBar != g_wickShadowLastCohortBar);
   if(isNewCohortBar) g_wickShadowLastCohortBar = cohortBar;
   _NXS_WickShadow_ProcessSide(g_wickShadowHigh, g_wickHigh, "HIGH", DIR_SELL, isNewCohortBar);
   _NXS_WickShadow_ProcessSide(g_wickShadowLow,  g_wickLow,  "LOW",  DIR_BUY,  isNewCohortBar);
}

void NXS_WickShadow_PrintSummary(){
   if(!InpResearchWickShadow) return;
   PrintFormat("[WICKSHADOW][SUMMARY] shadow_sweeps=%d canonical_sweepsDetected=%d parity=%s",
               g_wickShadowSweepCount, g_wickFunnel.sweepsDetected,
               (g_wickShadowSweepCount == g_wickFunnel.sweepsDetected ? "PASS" : "FAIL"));
}

// === WICK SWEEP RECLAIM (12/09) ==============================================
// Variante sperimentale SEPARATA (selettore vero 55, NON 54 - non tocca/
// sostituisce WICK_SWEEP_REV), promossa dopo la validazione shadow (vedi vault
// "WICK_SWEEP Entry Timing Study"). STESSA identica sorgente evento di
// WICK_SWEEP_REV: H4 wick, InpWickSweep_MinWickPips/SweepPips/SLPips/TPPips
// (riusati, nessun parametro nuovo), stesso g_wickHigh/g_wickLow (level
// replacement condiviso), stessa semantica one-shot per livello. Unica
// differenza: non entra alla detection canonica, ARMA il setup e attende il
// ritorno del prezzo al trigger_price osservato all'ARM, poi tenta
// un'apertura REALE.
//
// *** CORREZIONE METODOLOGICA (12/09) ***: la nota vault e il primo commento
// di questo blocco descrivevano il follow-up dello shadow come "tick-level".
// Verificato FALSO rileggendo NEXUS_EA_v2.mq5: NXS_WickShadow_OnTick() (unico
// call site) e' chiamata DOPO il "New bar gate" globale
// (`if(iTime(g_sym,InpTFEntry,0)==g_lastBarTime) return;`), quindi anche il
// suo monitoraggio reclaim/uscita gira SOLO una volta per barra InpTFEntry
// (M15), mai piu' spesso - confermato empiricamente (122/123 = 99.2% dei
// reclaim_delay_sec registrati sono multipli esatti di 900 secondi). "FOLLOW-
// UP CADENCE = M15 GATED", non tick-level. Questa variante REPLICA fedelmente
// questa cadenza reale (non quella erroneamente descritta in precedenza): la
// funzione e' chiamata dal .mq5 nello STESSO punto di NXS_WickShadow_OnTick()
// (dopo tutti i gate, incluso il New Bar Gate, che NON viene bypassato ne'
// toccato) - ogni chiamata corrisponde gia' a una nuova barra InpTFEntry, sia
// per l'ARM sia per il monitoraggio del reclaim. Una variante tick-level
// genuina (WICK_SWEEP_RECLAIM_TICK) resta solo un design candidate separato,
// NON implementata (vedi nota vault dedicata).
//
// Sequenza (tutta a cadenza M15/InpTFEntry, nessun bypass del New Bar Gate):
//   barra M15 N   : sweep rilevato -> ARM
//   barra M15 N+k : se il prezzo ha reclaimato il trigger -> tentativo reale
//                   di apertura; altrimenti resta ARMED secondo le stesse
//                   regole shadow (one-shot/replacement/abandonment sotto)
//
// Regole di invalidazione REPLICATE ESATTAMENTE da quelle validate nello
// shadow (_NXS_WickShadow_ProcessSide sopra), NON reinventate:
//   - one-shot per level_id: mirror di sh.lastSweptLevelId
//   - ARM solo al primo tick (=alla chiamata) di una nuova barra InpTFEntry:
//     mirror di isNewCohortBar (qui strutturalmente sempre vero dato il punto
//     di aggancio, mantenuto come guardia esplicita per chiarezza/difesa)
//   - ABANDONED quando side.id cambia (nuova wick sostituisce il livello)
//     PRIMA che il setup sia stato aperto con successo: mirror ESATTO
//     dell'unica condizione di abbandono usata dallo shadow
//     (side.id != sh.level_id), verificata ad OGNI chiamata prima di
//     qualunque altra elaborazione. Un evento gia' OPENED che perde il suo
//     level_id per sostituzione NON viene loggato come abbandonato (mirror:
//     lo shadow non "abbandona" mai un evento gia' risolto, la posizione
//     reale vive di vita propria col suo SL/TP a mercato).
//   - trigger_price = prezzo REALE osservato al momento dell'ARM (bid/ask
//     live), non il teorico level+sweepDist: mirror di sh.trigger_price
//   - SL/TP calcolati dal trigger_price (non dal prezzo di mercato al momento
//     del reclaim, che puo' differire per spread/slippage reale): mirror di
//     sh.virtual_sl/virtual_tp - permette un confronto fedele con lo shadow,
//     lo scostamento fill-reale vs trigger_price va riportato come rumore di
//     esecuzione, non nascosto.
//
// UNICA differenza NON coperta dallo shadow (che apre sempre con successo,
// nessun gate reale sul virtuale): un tentativo di apertura reale puo' essere
// bloccato (posizione strategia gia' aperta, throttle "una decisione per
// barra TF", preflight, protezioni, reject broker). Scelta esplicita (non
// nello shadow, quindi dichiarata qui, non silenziosa): se bloccato, si
// ritenta alla barra InpTFEntry successiva finche' il setup resta RECLAIMED
// (stessa filosofia di retry gia' usata da NXS_Strat_WickSweepReversal per i
// propri tentativi rifiutati - vedi side.attempts/lastAttemptBar sopra -
// stessa cadenza a barra, non inventata).
enum ENUM_NXS_WICKRECLAIM_STATE {
   WR_IDLE = 0,
   WR_ARMED,
   WR_RECLAIMED,
   WR_OPENED
};

struct SNxsWickReclaimState {
   ENUM_NXS_WICKRECLAIM_STATE state;
   long     sweep_id;
   long     level_id;
   string   side;             // "HIGH" o "LOW"
   int      dir;               // DIR_SELL (side=HIGH) o DIR_BUY (side=LOW)
   double   level_price;
   double   trigger_price;
   datetime sweep_time;
   double   max_penetration_pips;   // aggiornato tick per tick, congelato al reclaim (mirror shadow)
   datetime reclaim_time;
   long     lastArmedLevelId;  // one-shot per livello, mirror di sh.lastSweptLevelId
};
SNxsWickReclaimState g_wickReclaimHigh, g_wickReclaimLow;
long g_wickReclaimIdCounter = 0;

struct SNxsWickReclaimFunnel {
   long armed;
   long reclaimAvailable;
   long entryAttempts;
   long entryOpened;
   long blockedOpenPosition;
   long blockedTfThrottle;
   long blockedPreflight;
   long blockedProtection;
   long brokerReject;
   long abandoned;
};
SNxsWickReclaimFunnel g_wickReclaimFunnel;

void _NXS_WickReclaim_ProcessSide(SNxsWickReclaimState &st, SNxsWickSide &side, string sideLabel, int fadeDir, bool isNewCohortBar){
   double pip       = 10.0 * g_profile.pipSize;
   double sweepDist = InpWickSweep_SweepPips * pip;
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double ask = SymbolInfoDouble(g_sym, SYMBOL_ASK);
   double refPrice = (fadeDir == DIR_SELL) ? bid : ask;   // stesso riferimento della logica canonica/shadow

   if(st.state == WR_IDLE){
      if(side.level <= 0) return;
      if(side.id == st.lastArmedLevelId) return;   // one-shot per livello
      if(!isNewCohortBar) return;                  // stessa coorte canonica M15
      bool swept = (fadeDir == DIR_SELL) ? (bid >= side.level + sweepDist) : (ask <= side.level - sweepDist);
      if(!swept) return;
      st.lastArmedLevelId = side.id;
      st.state = WR_ARMED;
      st.sweep_id = ++g_wickReclaimIdCounter;
      g_wickReclaimFunnel.armed++;
      st.level_id = side.id;
      st.side = sideLabel;
      st.dir = fadeDir;
      st.level_price = side.level;
      st.trigger_price = refPrice;   // prezzo reale osservato, non il teorico level+sweepDist
      st.sweep_time = TimeCurrent();
      st.max_penetration_pips = MathAbs(refPrice - side.level) / pip;
      PrintFormat("[WICKRECLAIM][ARMED] sweep_id=%d level_id=%d side=%s level=%.2f trigger=%.5f time=%s",
                  st.sweep_id, st.level_id, st.side, st.level_price, st.trigger_price,
                  TimeToString(st.sweep_time, TIME_DATE|TIME_SECONDS));
      return;
   }

   // il livello osservato e' stato sostituito: libera SEMPRE lo slot (serve
   // perche' un futuro nuovo livello sullo stesso lato possa armarsi), ma
   // logga/conta come ABANDONED solo se il setup non si era ancora aperto con
   // successo - un evento gia' WR_OPENED che perde il suo level_id per
   // sostituzione non e' un abbandono (la posizione reale vive di vita propria
   // col suo SL/TP a mercato, mirror shadow: vedi commento di testa al blocco).
   // 12/09 - BUG TROVATO nella prima Fast Smoke reale: questo controllo
   // logava/contava ABANDONED anche per WR_OPENED (180/181 armed marcati
   // abbandonati, quasi tutti dopo un'apertura riuscita) - telemetria
   // fuorviante, MA nessun impatto sui trade reali (che restano gestiti dal
   // broker indipendentemente da questo stato). Corretto qui.
   if(side.id != st.level_id){
      if(st.state != WR_OPENED){
         PrintFormat("[WICKRECLAIM][ABANDONED] sweep_id=%d reason=level_replaced state=%d",
                     st.sweep_id, (int)st.state);
         g_wickReclaimFunnel.abandoned++;
      }
      st.state = WR_IDLE;
      return;
   }

   if(st.state == WR_ARMED){
      double breachPips = ((fadeDir == DIR_SELL) ? (refPrice - st.level_price) : (st.level_price - refPrice)) / pip;
      if(breachPips > st.max_penetration_pips) st.max_penetration_pips = breachPips;

      bool backToTrigger = (fadeDir == DIR_SELL) ? (refPrice <= st.trigger_price) : (refPrice >= st.trigger_price);
      if(backToTrigger){
         st.state = WR_RECLAIMED;
         st.reclaim_time = TimeCurrent();
         g_wickReclaimFunnel.reclaimAvailable++;
         PrintFormat("[WICKRECLAIM][RECLAIM_AVAILABLE] sweep_id=%d time=%s price=%.5f "
                     "time_sweep_to_reclaim_sec=%d max_penetration_before_reclaim_pips=%.2f",
                     st.sweep_id, TimeToString(st.reclaim_time, TIME_DATE|TIME_SECONDS), refPrice,
                     (int)(st.reclaim_time - st.sweep_time), st.max_penetration_pips);
      }
      return;
   }
   // WR_RECLAIMED: resta cosi' finche' NXS_WickReclaim_OnExecuteResult non lo
   // porta a WR_OPENED (o l'inizio di questa funzione lo abbandona per
   // sostituzione livello) - il tentativo di apertura vero e proprio vive nel
   // .mq5 (serve NXS_StrategyHasOpenPos/NXS_GetLastTfBar/NXS_OpenTrade,
   // dichiarate/incluse DOPO questo file).
}

datetime g_wickReclaimLastCohortBar = 0;

// Chiamata da OnTick() in NEXUS_EA_v2.mq5, stesso punto di NXS_WickShadow_OnTick
// (dopo tutti i gate a monte, prima di NXS_CollectAllSignals). Aggiorna SOLO lo
// stato ARM/RECLAIM - il tentativo di apertura vero e proprio e' fatto dal
// chiamante tramite NXS_WickReclaim_HasPendingEntry/OnExecuteResult sotto.
void NXS_WickReclaim_Detect(){
   if(!InpStrat_WickSweepReclaim || !NXS_SelectorAllows(55)) return;
   _NXS_WickSweep_UpdateLevel();   // idempotente per barra H4, condiviso con REV/shadow
   datetime cohortBar = iTime(g_sym, InpTFEntry, 0);
   bool isNewCohortBar = (cohortBar != g_wickReclaimLastCohortBar);
   if(isNewCohortBar) g_wickReclaimLastCohortBar = cohortBar;
   _NXS_WickReclaim_ProcessSide(g_wickReclaimHigh, g_wickHigh, "HIGH", DIR_SELL, isNewCohortBar);
   _NXS_WickReclaim_ProcessSide(g_wickReclaimLow,  g_wickLow,  "LOW",  DIR_BUY,  isNewCohortBar);
}

// fadeDir: DIR_SELL interroga il lato HIGH, DIR_BUY il lato LOW (stessa
// convenzione di _NXS_WickReclaim_ProcessSide). Ritorna true e riempie outSig
// se quel lato e' in WR_RECLAIMED (pronto per un tentativo di apertura reale,
// eventualmente ripetuto su tick successivi se il precedente e' stato bloccato).
bool NXS_WickReclaim_HasPendingEntry(int fadeDir, SNXSSignal &outSig){
   SNxsWickReclaimState st;
   if(fadeDir == DIR_SELL) st = g_wickReclaimHigh; else st = g_wickReclaimLow;
   if(st.state != WR_RECLAIMED) return false;
   double pip    = 10.0 * g_profile.pipSize;
   double slDist = InpWickSweep_SLPips * pip;
   double tpDist = InpWickSweep_TPPips * pip;
   ZeroMemory(outSig);
   outSig.dir       = (ENUM_NXS_DIR)fadeDir;
   outSig.strat     = STRAT_STRUCT_REACT;
   outSig.stratName = "WICK_SWEEP_RECLAIM";
   outSig.entryRef  = st.trigger_price;   // ancorato al trigger, non al prezzo live al reclaim (mirror shadow)
   outSig.sourceTF  = PERIOD_H4;
   outSig.score     = 70.0;
   if(fadeDir == DIR_SELL){
      outSig.slPrice = NormPrice(st.trigger_price + slDist);
      outSig.tpPrice = NormPrice(st.trigger_price - tpDist);
   } else {
      outSig.slPrice = NormPrice(st.trigger_price - slDist);
      outSig.tpPrice = NormPrice(st.trigger_price + tpDist);
   }
   outSig.reason = StringFormat("WickReclaim %s: sweep_id=%d level=%.2f trigger=%.5f",
                                 (fadeDir == DIR_SELL ? "SELL" : "BUY"), st.sweep_id, st.level_price, st.trigger_price);
   return true;
}

// Chiamata dal chiamante (.mq5) subito dopo aver tentato l'apertura reale per
// il lato indicato. reason (quando opened=false) e' una delle etichette
// richieste: BLOCKED_OPEN_POSITION / BLOCKED_TF_THROTTLE / BLOCKED_PREFLIGHT /
// BLOCKED_PROTECTION / BROKER_REJECT.
void NXS_WickReclaim_OnExecuteResult(int fadeDir, bool opened, string reason){
   SNxsWickReclaimState st;
   if(fadeDir == DIR_SELL) st = g_wickReclaimHigh; else st = g_wickReclaimLow;
   if(st.state != WR_RECLAIMED) return;   // difesa: nulla da finalizzare
   g_wickReclaimFunnel.entryAttempts++;
   PrintFormat("[WICKRECLAIM][ENTRY_ATTEMPT] sweep_id=%d dir=%d time=%s",
               st.sweep_id, fadeDir, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS));
   if(opened){
      st.state = WR_OPENED;
      g_wickReclaimFunnel.entryOpened++;
      PrintFormat("[WICKRECLAIM][OPENED] sweep_id=%d dir=%d time=%s", st.sweep_id, fadeDir,
                  TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS));
   } else {
      if(reason == "BLOCKED_OPEN_POSITION")      g_wickReclaimFunnel.blockedOpenPosition++;
      else if(reason == "BLOCKED_TF_THROTTLE")   g_wickReclaimFunnel.blockedTfThrottle++;
      else if(reason == "BLOCKED_PROTECTION")    g_wickReclaimFunnel.blockedProtection++;
      else if(reason == "BROKER_REJECT")         g_wickReclaimFunnel.brokerReject++;
      else                                        g_wickReclaimFunnel.blockedPreflight++;
      PrintFormat("[WICKRECLAIM][%s] sweep_id=%d dir=%d time=%s", reason, st.sweep_id, fadeDir,
                  TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS));
      // resta WR_RECLAIMED: ritentato al prossimo tick finche' non si apre o
      // il livello viene sostituito (ABANDONED, gestito in _NXS_WickReclaim_ProcessSide)
   }
   if(fadeDir == DIR_SELL) g_wickReclaimHigh = st; else g_wickReclaimLow = st;
}

void NXS_WickReclaim_PrintFunnel(){
   if(!InpStrat_WickSweepReclaim) return;
   PrintFormat("[WICKRECLAIM][FUNNEL] armed=%d reclaimAvailable=%d entryAttempts=%d entryOpened=%d "
               "blockedOpenPosition=%d blockedTfThrottle=%d blockedPreflight=%d blockedProtection=%d "
               "brokerReject=%d abandoned=%d",
               g_wickReclaimFunnel.armed, g_wickReclaimFunnel.reclaimAvailable, g_wickReclaimFunnel.entryAttempts,
               g_wickReclaimFunnel.entryOpened, g_wickReclaimFunnel.blockedOpenPosition,
               g_wickReclaimFunnel.blockedTfThrottle, g_wickReclaimFunnel.blockedPreflight,
               g_wickReclaimFunnel.blockedProtection, g_wickReclaimFunnel.brokerReject,
               g_wickReclaimFunnel.abandoned);
}

SNXSSignal NXS_Strat_WickSweepReversal(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "WICK_SWEEP_REV";
   if(!InpStrat_WickSweep || !NXS_SelectorAllows(54)) return s;
   // 10/09 - vedi nota di testa: valuta/muta lo stato SOLO sul passaggio H4
   // (o multi-TF spento), altrimenti il consumo one-shot si perde su un
   // passaggio sbagliato che il filtro TF scarta comunque dopo.
   if(g_activeTF != PERIOD_CURRENT && g_activeTF != PERIOD_H4) return s;

   _NXS_WickSweep_UpdateLevel();
   double pip       = 10.0 * g_profile.pipSize;
   double sweepDist = InpWickSweep_SweepPips * pip;
   double slDist    = InpWickSweep_SLPips   * pip;
   double tpDist    = InpWickSweep_TPPips   * pip;

   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double ask = SymbolInfoDouble(g_sym, SYMBOL_ASK);

   // --- lato alto: sweep sopra un livello alto -> fade SELL ---
   if(g_wickHigh.level > 0 && !g_wickHigh.consumed){
      if(!g_wickHigh.revisited && bid >= g_wickHigh.level){
         g_wickHigh.revisited = true;
         g_wickFunnel.levelsRevisited++;
      }
      if(bid >= g_wickHigh.level + sweepDist){
         bool firstTrigger = !g_wickHigh.triggered;
         g_wickHigh.triggered = true;
         if(firstTrigger) g_wickFunnel.sweepsDetected++;
         if(g_wickHigh.lastAttemptBar == g_wickLastBar){
            g_wickFunnel.duplicateRetrigger++;   // gia' tentato su questa barra H4, throttle
         } else {
            g_wickHigh.lastAttemptBar = g_wickLastBar;
            s.dir      = DIR_SELL;
            s.entryRef = bid;
            s.slPrice  = NormPrice(bid + slDist);
            s.tpPrice  = NormPrice(bid - tpDist);
            s.score    = 70.0;
            s.reason   = StringFormat("WickSweep SELL: high=%.2f swept+%.1fpip attempt#%d",
                                       g_wickHigh.level, InpWickSweep_SweepPips, g_wickHigh.attempts + 1);
            return s;
         }
      } else if(g_wickHigh.triggered && bid < g_wickHigh.level){
         // il prezzo e' rientrato sotto il livello originale prima di essere consumato: tesi invalidata
         g_wickFunnel.levelsInvalidatedByPrice++;
         g_wickHigh.level = 0;
      }
   }

   // --- lato basso: sweep sotto un livello basso -> fade BUY (simmetrico) ---
   if(g_wickLow.level > 0 && !g_wickLow.consumed){
      if(!g_wickLow.revisited && ask <= g_wickLow.level){
         g_wickLow.revisited = true;
         g_wickFunnel.levelsRevisited++;
      }
      if(ask <= g_wickLow.level - sweepDist){
         bool firstTrigger = !g_wickLow.triggered;
         g_wickLow.triggered = true;
         if(firstTrigger) g_wickFunnel.sweepsDetected++;
         if(g_wickLow.lastAttemptBar == g_wickLastBar){
            g_wickFunnel.duplicateRetrigger++;
         } else {
            g_wickLow.lastAttemptBar = g_wickLastBar;
            s.dir      = DIR_BUY;
            s.entryRef = ask;
            s.slPrice  = NormPrice(ask - slDist);
            s.tpPrice  = NormPrice(ask + tpDist);
            s.score    = 70.0;
            s.reason   = StringFormat("WickSweep BUY: low=%.2f swept-%.1fpip attempt#%d",
                                       g_wickLow.level, InpWickSweep_SweepPips, g_wickLow.attempts + 1);
            return s;
         }
      } else if(g_wickLow.triggered && ask > g_wickLow.level){
         g_wickFunnel.levelsInvalidatedByPrice++;
         g_wickLow.level = 0;
      }
   }
   return s;
}

#endif
