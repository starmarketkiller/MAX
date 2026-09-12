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

void _NXS_WickShadow_ProcessSide(SNxsWickShadowEvent &sh, SNxsWickSide &side, string sideLabel, int fadeDir){
   double pip       = 10.0 * g_profile.pipSize;
   double sweepDist = InpWickSweep_SweepPips * pip;
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double ask = SymbolInfoDouble(g_sym, SYMBOL_ASK);
   // stesso riferimento di prezzo usato dalla logica canonica per rilevare lo sweep
   // (bid per il lato alto/SELL, ask per il lato basso/BUY - vedi NXS_Strat_WickSweepReversal)
   double refPrice = (fadeDir == DIR_SELL) ? bid : ask;

   if(!sh.active){
      if(side.level <= 0) return;
      // 12/09 - FIX parity FAIL (prima corsa: shadow_sweeps=1100 vs
      // sweepsDetected=182): senza questo gate, un evento risolto (virtual
      // trade chiuso, sh.active=false) ripartiva IMMEDIATAMENTE se il prezzo
      // era ancora oltre la soglia di sweep - garantito subito dopo un
      // virtual SL (che sta 25 pip PIU' oltre il trigger, quindi ancora ben
      // oltre i 35 pip di sweep) - creando una cascata di "nuovi" sweep sullo
      // stesso livello a ogni tick. La logica canonica non ha questo bug
      // perche' `triggered` e' one-shot per livello (mai resettato finche'
      // il livello non cambia id) - replicato qui identico.
      if(side.id == sh.lastSweptLevelId) return;
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
      sh.trigger_price = (fadeDir == DIR_SELL) ? side.level + sweepDist : side.level - sweepDist;
      sh.sweep_time = TimeCurrent();
      sh.max_penetration_pips = InpWickSweep_SweepPips;
      sh.reclaimed_trigger = false; sh.reclaimed_level = false; sh.virtual_open = false;
      PrintFormat("[WICKSHADOW][SWEEP] sweep_id=%d level_id=%d side=%s level=%.2f trigger=%.2f time=%s",
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
void NXS_WickShadow_OnTick(){
   if(!InpResearchWickShadow || !InpStrat_WickSweep) return;
   _NXS_WickSweep_UpdateLevel();
   _NXS_WickShadow_ProcessSide(g_wickShadowHigh, g_wickHigh, "HIGH", DIR_SELL);
   _NXS_WickShadow_ProcessSide(g_wickShadowLow,  g_wickLow,  "LOW",  DIR_BUY);
}

void NXS_WickShadow_PrintSummary(){
   if(!InpResearchWickShadow) return;
   PrintFormat("[WICKSHADOW][SUMMARY] shadow_sweeps=%d canonical_sweepsDetected=%d parity=%s",
               g_wickShadowSweepCount, g_wickFunnel.sweepsDetected,
               (g_wickShadowSweepCount == g_wickFunnel.sweepsDetected ? "PASS" : "FAIL"));
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
