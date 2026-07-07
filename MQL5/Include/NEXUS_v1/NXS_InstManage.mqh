//+------------------------------------------------------------------+
//|  NXS_InstManage.mqh - Gestione della posizione istituzionale      |
//|  (Fase 3 del modello istituzionale, dietro InpUseInstitutionalCore)|
//|                                                                    |
//|  Una volta che il Core ha aperto 1 posizione per direzione, qui la |
//|  gestiamo come un'unica sequenza:                                  |
//|   - PROFITTO -> GRID/pyramiding: add a favore, do' forza al        |
//|                 vincente (moltiplicatore InpInstGridMult).         |
//|   - PERDITA  -> RECOVERY: add con moltiplicatore InpInstRecoveryMult|
//|                 per recuperare a un prezzo migliore (martingala).  |
//|   - TETTO DI SICUREZZA: max profondita' (InpInstMaxRecoveryDepth) e |
//|     max esposizione per direzione (InpInstMaxExposureLots).        |
//|   - TRAILING (training stop): appena c'e' un po' di profitto        |
//|     (InpInstLockATR) blocca il profitto inseguendo a InpInstTrailATR|
//|     -> protegge sempre un po' di guadagno, anche prima del TP.     |
//|   - RUNNER: l'ultima op della sequenza tiene un TP esteso           |
//|     (InpInstRunnerTPmult) per seguire il trend mentre il trailing   |
//|     la protegge.                                                    |
//+------------------------------------------------------------------+
#ifndef __NXS_INST_MANAGE_MQH__
#define __NXS_INST_MANAGE_MQH__

struct SNXSInstGroup {
   int      count;        // posizioni aperte in questa direzione (core + add)
   double   totalLots;    // esposizione totale
   double   coreLot;      // lotto della posizione core (base per gli add)
   double   coreSL;       // SL/TP della core: ereditati dagli add
   double   coreTP;
   double   lastEntry;    // prezzo di apertura della op piu' recente
   datetime lastTime;
   ulong    lastTicket;   // ticket della op piu' recente (= runner)
   double   aggPL;        // P/L flottante aggregato del gruppo (soldi)
   string   tag;          // firma della collaborazione (dal comment della core)
};

// Scansiona tutte le posizioni NEXUS in una direzione e le aggrega.
void _nxs_inst_scanDir(ENUM_NXS_DIR dir, SNXSInstGroup &g){
   ZeroMemory(g);
   g.tag = "INST_ADD";
   long want = (dir == DIR_BUY) ? POSITION_TYPE_BUY : POSITION_TYPE_SELL;
   datetime bestT = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      long mg = (long)PositionGetInteger(POSITION_MAGIC);
      if(!IsNexusMagic(mg)) continue;
      if(PositionGetInteger(POSITION_TYPE) != want) continue;

      g.count++;
      double vol = PositionGetDouble(POSITION_VOLUME);
      g.totalLots += vol;
      g.aggPL += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);

      datetime pt = (datetime)PositionGetInteger(POSITION_TIME);
      if(pt >= bestT){
         bestT       = pt;
         g.lastEntry = PositionGetDouble(POSITION_PRICE_OPEN);
         g.lastTicket= t;
         g.lastTime  = pt;
      }
      if(IsCoreMagic(mg)){
         g.coreLot = vol;
         g.coreSL  = PositionGetDouble(POSITION_SL);
         g.coreTP  = PositionGetDouble(POSITION_TP);
         string cm = PositionGetString(POSITION_COMMENT);
         string parts[]; int np = StringSplit(cm, '|', parts);
         if(np >= 2 && StringLen(parts[1]) > 0) g.tag = parts[1];
      }
   }
}

// Piazza un add di grid/recovery (bypassa i gate di ingresso: la sequenza e'
// gia' stata decisa dal Core, qui la gestiamo). Volume normalizzato allo step.
bool _nxs_inst_add(ENUM_NXS_DIR dir, double lots, double sl, double tp,
                   string tag, int level){
   double step = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_STEP);
   if(step <= 0) step = 0.01;
   lots = MathFloor(lots / step) * step;
   lots = NormalizeDouble(lots, 8);
   lots = NXS_License_CapLot(lots);
   if(lots < step) return false;

   // magic di grid (resta dentro IsNexusMagic / IsGridMagic).
   long magic = InpMagic + MAGIC_GRID + level;
   NXS_TradeSetMagic(magic);
   string cm = StringFormat("%s|%s|%.1f", InpComment, tag, 0.0);
   if(dir == DIR_BUY)  return NXS_SafeBuy(lots, g_sym, sl, tp, cm);
   return NXS_SafeSell(lots, g_sym, sl, tp, cm);
}

// Trailing (training stop) su ogni op del gruppo + runner sull'ultima.
void _nxs_inst_trail(ENUM_NXS_DIR dir, SNXSInstGroup &g, double atr){
   double lockDist  = atr * InpInstLockATR;
   double trailDist = atr * InpInstTrailATR;
   long   want      = (dir == DIR_BUY) ? POSITION_TYPE_BUY : POSITION_TYPE_SELL;
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double ask = SymbolInfoDouble(g_sym, SYMBOL_ASK);
   double px  = (dir == DIR_BUY) ? bid : ask;

   for(int i = PositionsTotal() - 1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      if(PositionGetInteger(POSITION_TYPE) != want) continue;

      double entry = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl    = PositionGetDouble(POSITION_SL);
      double tp    = PositionGetDouble(POSITION_TP);
      double newSL = sl, newTP = tp;

      // RUNNER: l'ultima op della sequenza (se c'e' piu' di una) tiene un TP
      // esteso cosi' segue il trend; il trailing sotto la protegge.
      if(InpInstRunner && g.count > 1 && t == g.lastTicket){
         double tpDist = MathAbs(g.coreTP - entry);
         if(tpDist <= 0) tpDist = atr * InpInstBaseTP;
         double rTP = (dir == DIR_BUY) ? entry + tpDist * InpInstRunnerTPmult
                                       : entry - tpDist * InpInstRunnerTPmult;
         if((dir == DIR_BUY  && (tp <= 0 || rTP > tp)) ||
            (dir == DIR_SELL && (tp <= 0 || rTP < tp)))
            newTP = rTP;
      }

      // TRAILING: appena il profitto supera lockDist, blocca inseguendo a
      // trailDist. Sposta lo SL solo verso il profitto e solo oltre l'entry
      // (cosi' non chiude mai in perdita una volta protetto).
      double prof = (dir == DIR_BUY) ? (px - entry) : (entry - px);
      if(prof >= lockDist){
         double tSL = (dir == DIR_BUY) ? px - trailDist : px + trailDist;
         if(dir == DIR_BUY){
            if(tSL > entry && (sl <= 0 || tSL > sl)) newSL = tSL;
         } else {
            if(tSL < entry && (sl <= 0 || tSL < sl)) newSL = tSL;
         }
      }

      if(MathAbs(newSL - sl) > g_point || MathAbs(newTP - tp) > g_point)
         NXS_DoModify(t, NormPrice(newSL), NormPrice(newTP));
   }
}

// Gestione di una direzione: prima gli add (grid/recovery), poi il trailing.
void _nxs_inst_manageDir(ENUM_NXS_DIR dir){
   SNXSInstGroup g; _nxs_inst_scanDir(dir, g);
   if(g.count == 0) return;

   double atr  = (g_atr > 0 ? g_atr : g_point * 100.0);
   double step = atr * InpInstGridStepATR;
   int    depth   = g.count - 1;   // add gia' piazzati
   double baseLot = (InpInstAddLot > 0) ? InpInstAddLot
                                        : (g.coreLot > 0 ? g.coreLot : 0.01);
   double px = (dir == DIR_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_BID)
                                : SymbolInfoDouble(g_sym, SYMBOL_ASK);

   bool depthOk = (InpInstMaxRecoveryDepth <= 0) || (depth < InpInstMaxRecoveryDepth);
   if(depthOk && step > 0){
      bool   doAdd = false;
      double lots  = 0;
      bool   isGrid = false;
      if(g.aggPL > 0){
         // GRID: prezzo avanzato a favore -> add sul vincente.
         double adv = (dir == DIR_BUY) ? (px - g.lastEntry) : (g.lastEntry - px);
         if(adv >= step){
            lots   = baseLot * MathPow(MathMax(0.01, InpInstGridMult), depth + 1);
            isGrid = true; doAdd = true;
         }
      } else if(g.aggPL < 0){
         // RECOVERY: prezzo andato contro -> add a prezzo migliore (martingala).
         double adv = (dir == DIR_BUY) ? (g.lastEntry - px) : (px - g.lastEntry);
         if(adv >= step){
            lots  = baseLot * MathPow(MathMax(0.01, InpInstRecoveryMult), depth + 1);
            doAdd = true;
         }
      }
      if(doAdd){
         // TETTO DI ESPOSIZIONE: hard cap, l'add che sforerebbe non parte.
         if(InpInstMaxExposureLots > 0 && g.totalLots + lots > InpInstMaxExposureLots + 1e-9){
            PrintFormat("[NEXUS INST] ADD BLOCCATO cap esposizione %s: %.2f+%.2f>%.2f",
                        NXS_DirName(dir), g.totalLots, lots, InpInstMaxExposureLots);
         } else if(_nxs_inst_add(dir, lots, g.coreSL, g.coreTP, g.tag, depth + 1)){
            PrintFormat("[NEXUS INST] %s ADD lvl=%d lots=%.2f (%s) aggPL=%.2f tot=%.2f",
                        (isGrid ? "GRID" : "RECOVERY"), depth + 1, lots, g.tag,
                        g.aggPL, g.totalLots + lots);
         }
      }
   }

   _nxs_inst_trail(dir, g, atr);
}

// Punto d'ingresso: chiamato a ogni tick quando il modello istituzionale e'
// attivo (la gestione classica BE/trail/grid/pyramid resta per il modello
// best-per-bar).
void NXS_InstManage_OnTick(){
   if(!InpUseInstitutionalCore) return;
   _nxs_inst_manageDir(DIR_BUY);
   _nxs_inst_manageDir(DIR_SELL);
}

#endif
