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

// Tetto di esposizione EFFETTIVO, scalato sul saldo: cresce col conto, resta
// minuscolo quando il conto e' piccolo (anti-blowup su conti tipo €200).
double _nxs_inst_maxExposure(){
   double cap = InpInstMaxExposureLots;
   if(InpInstExposureRefBalance > 0){
      double bal = AccountInfoDouble(ACCOUNT_BALANCE);
      if(bal > 0) cap = InpInstMaxExposureLots * (bal / InpInstExposureRefBalance);
   }
   double minLot = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);
   return MathMax(minLot, cap);   // almeno il lotto minimo del broker
}

// AUD0-INST-006 / AUD0-RS-003: un cap espresso in lotti non dice nulla sul
// denaro a rischio. Qui si stima la perdita di caso peggiore del gruppo, add
// incluso, usando la distanza fino allo stop del core, e la si confronta col
// budget di drawdown del conto.
bool _nxs_inst_worstCaseOk(ENUM_NXS_DIR dir, SNXSInstGroup &g, double addLots){
   double tickVal  = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_SIZE);
   if(tickVal <= 0 || tickSize <= 0) return true;   // niente metadati: non si stima

   double px = (dir == DIR_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_BID)
                                : SymbolInfoDouble(g_sym, SYMBOL_ASK);
   double slDist = 0.0;
   if(g.coreSL > 0)
      slDist = MathAbs(px - g.coreSL);
   else if(g_atr > 0)
      slDist = g_atr * MathMax(1.0, InpInstGridStepATR) * 2.0;
   if(slDist <= 0) return true;

   double totalLots = g.totalLots + addLots;
   double worstLoss = (slDist / tickSize) * tickVal * totalLots;

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double budget  = balance * MathMax(0.1, g_run_MaxDailyDDPct) / 100.0;
   if(budget <= 0) return true;

   bool ok = (worstLoss <= budget);
   if(!ok)
      PrintFormat("[NEXUS INST] worst-case %.2f su lotti %.2f supera il budget %.2f "
                  "(balance=%.2f ddCap=%.1f%%)",
                  worstLoss, totalLots, budget, balance, g_run_MaxDailyDDPct);
   return ok;
}

// Scansiona le posizioni istituzionali di una direzione e le aggrega.
//
// AUD0-INST-004 / AUD0-INST-005: lo scanner assorbiva OGNI posizione dello
// stesso simbolo e direzione il cui magic cadesse nell'ampio intervallo
// NEXUS. Trade classici, grid ordinari, piramidi e posizioni legacy finivano
// nello stesso "gruppo istituzionale" e venivano gestiti insieme, pur non
// appartenendo alla sequenza. L'appartenenza è ora ristretta ai soli magic
// che il modello istituzionale usa davvero (core + grid), ed escluse le
// piramidi e gli split che hanno il proprio ciclo di vita.
bool _nxs_inst_belongs(long magic){
   return IsCoreMagic(magic) || IsGridMagic(magic);
}

void _nxs_inst_scanDir(ENUM_NXS_DIR dir, SNXSInstGroup &g){
   ZeroMemory(g);
   g.tag = "INST_ADD";
   long want = (dir == DIR_BUY) ? POSITION_TYPE_BUY : POSITION_TYPE_SELL;
   datetime bestT = 0;
   int skippedForeign = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      long mg = (long)PositionGetInteger(POSITION_MAGIC);
      if(!IsNexusMagic(mg)) continue;
      if(PositionGetInteger(POSITION_TYPE) != want) continue;
      if(!_nxs_inst_belongs(mg)){
         skippedForeign++;
         continue;
      }

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
   if(skippedForeign > 0)
      PrintFormat("[NEXUS INST] %s: %d posizioni NEXUS estranee alla sequenza "
                  "istituzionale escluse dal gruppo", NXS_DirName(dir), skippedForeign);
}

// Piazza un add di grid/recovery istituzionale.
//
// AUD0-INST-001 / AUD0-INST-002: questa funzione dichiarava esplicitamente di
// "bypassare i gate di ingresso perché la sequenza è già stata decisa dal
// Core", e chiamava NXS_SafeBuy/SafeSell direttamente. Saltava quindi
// licenza, ruin freeze, protezioni giornaliere, RiskShield, cap direzionale,
// margine proiettato e broker preflight — tutti i controlli che gli altri
// percorsi di esposizione applicano.
//
// Una decisione presa in passato non autorizza esposizione futura illimitata:
// ogni add rivalida lo stato CORRENTE del conto.
bool _nxs_inst_add(ENUM_NXS_DIR dir, double lots, double sl, double tp,
                   string tag, int level, ulong parentTicket = 0){
   double step = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_STEP);
   if(step <= 0) step = 0.01;
   double vmin = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MAX);

   lots = MathFloor(lots / step) * step;
   lots = NormalizeDouble(lots, 8);
   lots = NXS_License_CapLot(lots);
   // AUD0-INST-008: si verificava solo `lots < step`, non il minimo e il
   // massimo di volume dichiarati dal broker.
   if(lots < MathMax(step, vmin)) return false;
   if(vmax > 0 && lots > vmax) lots = MathFloor(vmax / step) * step;

   ENUM_ORDER_TYPE otype = (dir == DIR_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double refPrice = (dir == DIR_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_ASK)
                                      : SymbolInfoDouble(g_sym, SYMBOL_BID);

   // AUD0-INST-007: l'add ereditava coreSL/coreTP, ZERI COMPRESI. Se il core
   // non aveva stop lato broker, nemmeno l'add ne aveva uno. Qui si calcola
   // uno stop valido quando manca, e si rifiuta se non è calcolabile.
   double useSL = sl, useTP = tp;
   if(useSL <= 0.0){
      double atr = (g_atr > 0 ? g_atr : 0.0);
      if(atr <= 0){
         Print("[NEXUS INST] ADD BLOCCATO: nessuno stop ereditabile e ATR non valido");
         return false;
      }
      double slDist = atr * MathMax(1.0, InpInstGridStepATR) * 2.0;
      useSL = (dir == DIR_BUY) ? (refPrice - slDist) : (refPrice + slDist);
      useSL = NormalizeDouble(useSL, (int)SymbolInfoInteger(g_sym, SYMBOL_DIGITS));
      PrintFormat("[NEXUS INST] core senza SL: stop dell'add calcolato a %.5f", useSL);
   }

   // AUD0-INST-009: con esposizione su entrambe le direzioni non si amplia.
   if(g_instHedgedBoth){
      PrintFormat("[NEXUS INST] ADD BLOCCATO: esposizione gia' su entrambe le "
                  "direzioni, il rischio netto non giustifica un ampliamento");
      return false;
   }

   // Invariante unica: licenza, ruin freeze, protezioni, stop obbligatorio,
   // RiskShield, cap direzionale, margine proiettato, broker preflight.
   string gateReason = "";
   if(!NXS_CommonExposurePreflight("INST:" + tag, "INST:" + tag, dir, lots, otype, refPrice,
                                   useSL, useTP, gateReason)){
      PrintFormat("[NEXUS INST] ADD BLOCCATO dal preflight comune: %s", gateReason);
      return false;
   }

   // magic di grid (resta dentro IsNexusMagic / IsGridMagic).
   long magic = InpMagic + MAGIC_GRID + level;
   NXS_TradeSetMagic(magic);
   string cm = StringFormat("%s|%s|%.1f", InpComment, tag, 0.0);
   bool sent = (dir == DIR_BUY) ? NXS_SafeBuy(lots, g_sym, useSL, useTP, cm)
                                : NXS_SafeSell(lots, g_sym, useSL, useTP, cm);
   if(sent)
      // AUD0-LEDGER-010: l'add istituzionale appartiene alla sequenza del
      // gruppo, non e' un trade indipendente. Il gruppo si eredita dalla
      // posizione piu' recente gia' censita; se ignota, l'add apre la propria.
      NXS_Intent_Record(NXS_TradeOrderTicket(), tag, 0.0,
                        NXS_Intent_RiskMoney(g_sym, refPrice, useSL, lots),
                        "institutional", NXS_Intent_GroupOfTicket(parentTicket), g_atr, lots);
   if(!sent)
      PrintFormat("[NEXUS INST] ADD FALLITO lvl=%d lots=%.4f retcode=%d",
                  level, lots, NXS_TradeRetcode());
   return sent;
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
      double profP = (dir == DIR_BUY) ? (px - entry) : (entry - px);
      long   ageS  = (long)(TimeCurrent() - (datetime)PositionGetInteger(POSITION_TIME));

      // #7 TIME-STOP: trade fermo ~0 da troppo tempo -> chiudi, libera margine.
      if(InpInstTimeStopMin > 0 && ageS >= (long)InpInstTimeStopMin * 60 &&
         MathAbs(profP) < atr * InpInstTimeStopATR){
         PrintFormat("[NEXUS INST] TIME-STOP %s ticket=%I64u eta=%dmin prof=%.5f -> chiudo",
                     NXS_DirName(dir), t, (int)(ageS / 60), profP);
         NXS_PM_ProposeClose(t, 80, "INST_TIME_STOP", "institutional stagnation timeout");
         continue;
      }

      // RUNNER: l'ultima op della sequenza (se c'e' piu' di una) tiene un TP
      // esteso cosi' segue il trend; il trailing sotto la protegge.
      if(InpInstRunner && g.count > 1 && t == g.lastTicket){
         // v2.2.9 FIX: se la core NON ha TP (coreTP=0) NON usare |0-entry| (=~prezzo,
         // ~4000 su oro) come distanza: darebbe un rTP negativo sui SELL
         // ("Invalid stops tp:-9233"). Fallback su ATR*BaseTP.
         double tpDist = (g.coreTP > 0) ? MathAbs(g.coreTP - entry) : atr * InpInstBaseTP;
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
      // B) Permanenza minima: finche' non e' passata, NON stringe (lo SL di
      //    tier, largo, resta) -> l'operazione ha spazio per svilupparsi.
      // B) Permanenza minima proporzionale ad ATR/volatilita': quando c'e' piu'
      //    volatilita' (ATR sopra la media) il prezzo ha piu' spazio -> tieni piu'
      //    a lungo; quando e' calmo, meno. Fattore limitato a [0.7x, 2.0x].
      long   posAge     = (long)(TimeCurrent() - (datetime)PositionGetInteger(POSITION_TIME));
      double holdFactor = 1.0;
      if(g_atrAvg > 0) holdFactor = MathMax(0.7, MathMin(2.0, g_atr / g_atrAvg));
      long   minHoldSec = (long)(InpInstMinHoldMin * 60 * holdFactor);
      bool   heldLong   = (InpInstMinHoldMin <= 0) || (posAge >= minHoldSec);
      if(heldLong && profP >= lockDist){
         double tSL = (dir == DIR_BUY) ? px - trailDist : px + trailDist;
         if(dir == DIR_BUY){
            if(tSL > entry && (sl <= 0 || tSL > sl)) newSL = tSL;
         } else {
            if(tSL < entry && (sl <= 0 || tSL < sl)) newSL = tSL;
         }
      }

      // #5 BE+ dopo il primo add di grid: con size extra sul vincente e gruppo
      //    in profitto, nessuna op del cluster puo' piu' chiudere in perdita.
      if(InpInstBEAfterGrid && g.count > 1 && g.aggPL > 0){
         double beSL = (dir == DIR_BUY) ? entry + atr * InpInstBEbufferATR
                                        : entry - atr * InpInstBEbufferATR;
         if(dir == DIR_BUY){ if(beSL > newSL) newSL = beSL; }
         else             { if(beSL < newSL) newSL = beSL; }
      }

      if(MathAbs(newSL - sl) > g_point || MathAbs(newTP - tp) > g_point)
         NXS_PM_ProposeModify(t, NormPrice(newSL), NormPrice(newTP), 50,
                              "INSTITUTIONAL", "institutional trail/runner");
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
         // #6 ma SOLO se il contesto non si e' girato contro: non mediare dentro
         //    un trend confermato opposto (anti-martingala-suicida).
         bool ctxAgainst = (InpInstRecoveryNeedsContext && g_ctx.valid &&
                            g_ctx.htfBias == -(int)dir && g_ctx.structTrend == -(int)dir);
         double adv = (dir == DIR_BUY) ? (g.lastEntry - px) : (px - g.lastEntry);
         if(adv >= step && !ctxAgainst){
            lots  = baseLot * MathPow(MathMax(0.01, InpInstRecoveryMult), depth + 1);
            doAdd = true;
         } else if(adv >= step && ctxAgainst){
            PrintFormat("[NEXUS INST] RECOVERY STOP %s: contesto girato contro (htf+struct) aggPL=%.2f",
                        NXS_DirName(dir), g.aggPL);
         }
      }
      if(doAdd){
         // AUD0-INST-003: la recovery moltiplica il lotto in modo esponenziale
         // dentro una sequenza in perdita (martingala). Il contesto poteva
         // bloccare qualche add, ma non cambiava la struttura di
         // amplificazione. Il tetto monetario qui sotto la vincola: la perdita
         // potenziale aggregata non può superare il budget di rischio.
         double lossBudget = AccountInfoDouble(ACCOUNT_BALANCE)
                             * MathMax(0.1, g_run_MaxDailyDDPct) / 100.0;
         double groupLoss = (g.aggPL < 0) ? -g.aggPL : 0.0;
         if(lossBudget > 0 && groupLoss >= lossBudget){
            PrintFormat("[NEXUS INST] ADD BLOCCATO %s: perdita del gruppo %.2f "
                        "ha esaurito il budget di rischio %.2f",
                        NXS_DirName(dir), groupLoss, lossBudget);
            doAdd = false;
         }
      }
      if(doAdd){
         // AUD0-INST-006: il cap era in LOTTI e scalava linearmente col saldo,
         // senza tener conto di distanza di stop, tick value o volatilità.
         // Si applica anche un tetto sulla perdita monetaria di caso peggiore.
         double maxExp = _nxs_inst_maxExposure();
         if(maxExp > 0 && g.totalLots + lots > maxExp + 1e-9){
            PrintFormat("[NEXUS INST] ADD BLOCCATO cap esposizione %s: %.2f+%.2f>%.2f",
                        NXS_DirName(dir), g.totalLots, lots, maxExp);
         } else if(!_nxs_inst_worstCaseOk(dir, g, lots)){
            PrintFormat("[NEXUS INST] ADD BLOCCATO %s: perdita di caso peggiore "
                        "oltre il budget di conto", NXS_DirName(dir));
         } else if(_nxs_inst_add(dir, lots, g.coreSL, g.coreTP, g.tag, depth + 1,
                                 g.lastTicket)){
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
   // AUD0-INST-009 — GESTIONE SIMULTANEA DELLE DUE DIREZIONI.
   //
   // Il modulo gestisce i gruppi BUY e SELL in modo indipendente a ogni tick.
   // Puo' essere hedging deliberato, ma senza una politica di rischio NETTO di
   // conto due gruppi opposti possono crescere insieme: il margine e il rischio
   // di caso peggiore si sommano, mentre l'esposizione netta — e quindi il
   // "beneficio" della copertura — resta vicina a zero. Si paga spread e swap
   // su entrambi i lati per un'esposizione che non c'e'.
   //
   // Qui il caso viene RILEVATO e limitato: se entrambe le direzioni sono
   // aperte oltre una soglia minima, si smette di ampliare la piu' piccola.
   {
      double blots = 0, slots = 0;
      for(int i = PositionsTotal() - 1; i >= 0; i--){
         ulong pt = PositionGetTicket(i);
         if(pt == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
         if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
         double v = PositionGetDouble(POSITION_VOLUME);
         if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) blots += v;
         else                                                        slots += v;
      }
      double vmin = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);
      if(blots > vmin && slots > vmin){
         g_instHedgedBoth = true;
         static datetime lastHedgeLog = 0;
         if(TimeCurrent() - lastHedgeLog > 300){
            lastHedgeLog = TimeCurrent();
            PrintFormat("[NEXUS INST] esposizione su ENTRAMBE le direzioni "
                        "(BUY %.2f / SELL %.2f): nessun ampliamento del lato "
                        "minore finche' dura", blots, slots);
         }
      } else {
         g_instHedgedBoth = false;
      }
   }

   if(!InpUseInstitutionalCore) return;
   _nxs_inst_manageDir(DIR_BUY);
   _nxs_inst_manageDir(DIR_SELL);
}

#endif
