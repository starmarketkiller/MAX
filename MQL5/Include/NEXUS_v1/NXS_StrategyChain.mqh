//+------------------------------------------------------------------+
//|  NXS_StrategyChain.mqh                                            |
//|  Smart Continuation & Strategy Chaining (NEXUS v2.0.13)           |
//|                                                                   |
//|  Concetti chiave:                                                 |
//|  - Continuation Pattern: dopo chiusura in profitto su trend       |
//|    chiaro, se il prezzo riprende nella stessa direzione (pullback |
//|    + nuovo high/low), apri trade di continuazione con lotto       |
//|    ridotto.                                                       |
//|  - Smart Close & Reverse: se appare segnale opposto con qualità   |
//|    reaction>=75 E HTF concorde, abbassa la soglia di reverse e    |
//|    chiudi+inverti.                                                |
//|  - Strategy Bridges: mappa esplicita di quale strategia "passa il |
//|    testimone" a quale (es. ADX_RSI → EMA_PULLBACK su pullback).   |
//|  - Re-Entry Memory: ricorda massimi/minimi recenti per riconoscere|
//|    breakouts in continuation.                                     |
//+------------------------------------------------------------------+
#ifndef __NXS_STRATEGY_CHAIN_MQH__
#define __NXS_STRATEGY_CHAIN_MQH__

// ----- Stato chain -----
struct SNXSChainState {
   datetime  lastCloseTime;       // tempo ultima chiusura in profitto
   string    lastStrategy;        // ultima strategia chiusa
   int       lastDir;             // +1 buy, -1 sell
   double    lastClosePrice;      // prezzo di chiusura
   double    lastClosePnL;        // P&L
   double    extremumPrice;       // max/min raggiunto durante il trade
   datetime  extremumTime;
   int       continuationCount;   // n. continuazioni dopo questo trade
   datetime  cooldownUntil;       // cooldown chain
};

SNXSChainState g_chain = {0, "", 0, 0.0, 0.0, 0.0, 0, 0, 0};

// Tracking max/min durante posizione aperta (per re-entry intelligente)
double   g_chainMaxPrice = 0.0;
double   g_chainMinPrice = 1e18;
datetime g_chainTrackStart = 0;
// v2.0.13 — moltiplicatore lotto applicato all'apertura del prossimo trade (continuation)
double   g_chainPendingLotMult = 1.0;

// ----- Strategy Bridges -----
// Mappa quale strategia può "continuare" dopo un'altra
// Esempio: dopo ADX_RSI in profitto, EMA_PULLBACK o BREAKOUT_ACC sono buone continuazioni
bool NXS_Chain_IsCompatible(string lastStrat, string newStrat){
   // Trend-following strategies can chain among themselves
   string trendStrats = "ADX_RSI,MACD,SAR,TSI,EMA_PULLBACK,BREAKOUT_ACC,LONDON_BO,ICHIMOKU,FVG_CONT,AMD_CONT,PO3,OTE_CONT";
   // Reversal/mean-revert can chain to trend after exhaustion
   string reversalStrats = "BOLLINGER,RSI_DIV,BB_SQUEEZE,LIQ_SWEEP,TURTLE_SOUP,IFVG,AMD_REVERSAL,JUDAS_SWING,LDN_REVERSAL,NY_REVERSAL,RANGE_FADE,MALAYSIAN_SNR";
   // SMC structural — can chain to anything aligned
   string smcStrats = "BJORGUM,FVG_MIT,OB_MIT,ORDER_BLOCK,SH_BMS_RTO,SMS_BMS_RTO,SILVER_BULLET,CISD,WEEKLY_EXP,LIQ_VOID,DISP_REBAL,STRUCT_REACT";

   bool lastTrend = (StringFind(trendStrats, lastStrat) >= 0);
   bool newTrend  = (StringFind(trendStrats, newStrat) >= 0);
   bool lastRev   = (StringFind(reversalStrats, lastStrat) >= 0);
   bool newRev    = (StringFind(reversalStrats, newStrat) >= 0);
   bool lastSMC   = (StringFind(smcStrats, lastStrat) >= 0);
   bool newSMC    = (StringFind(smcStrats, newStrat) >= 0);

   // Continuazione: trend→trend (best), trend→SMC, SMC→trend
   if(lastTrend && (newTrend || newSMC)) return true;
   // Reversal → Trend (dopo l'esaurimento), buona transizione
   if(lastRev && (newTrend || newSMC))   return true;
   // SMC → qualsiasi cosa allineata
   if(lastSMC && (newTrend || newSMC || newRev)) return true;
   // Reversal → Reversal (raro ma se HTF cambia)
   if(lastRev && newRev) return true;
   return false;
}

// ----- Reset chain stato dopo cooldown -----
void NXS_Chain_Reset(){
   g_chain.lastCloseTime    = 0;
   g_chain.lastStrategy     = "";
   g_chain.lastDir          = 0;
   g_chain.continuationCount = 0;
}

// ----- Update extremum tracker mentre c'è una posizione aperta -----
void NXS_Chain_TrackExtremum(){
   if(PositionsTotal() == 0){
      // Reset solo quando non ci sono posizioni
      g_chainMaxPrice  = 0.0;
      g_chainMinPrice  = 1e18;
      g_chainTrackStart = 0;
      return;
   }
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   if(bid <= 0) return;
   if(g_chainTrackStart == 0) g_chainTrackStart = TimeCurrent();
   if(bid > g_chainMaxPrice) g_chainMaxPrice = bid;
   if(bid < g_chainMinPrice) g_chainMinPrice = bid;
}

// ----- Hook on close: salva contesto per chain -----
void NXS_Chain_OnTradeClose(string strategy, int dir, double closePrice, double pnl){
   g_chain.lastCloseTime  = TimeCurrent();
   g_chain.lastStrategy   = strategy;
   g_chain.lastDir        = dir;
   g_chain.lastClosePrice = closePrice;
   g_chain.lastClosePnL   = pnl;
   // L'estremo durante il trade è l'high se BUY, low se SELL
   g_chain.extremumPrice  = (dir == +1) ? g_chainMaxPrice : g_chainMinPrice;
   g_chain.extremumTime   = TimeCurrent();
   g_chain.continuationCount = 0;
   // Cooldown breve per evitare ri-entry frenetico
   g_chain.cooldownUntil = TimeCurrent() + 60; // 60s

   // Reset tracker (per il prossimo trade)
   g_chainMaxPrice  = 0.0;
   g_chainMinPrice  = 1e18;
   g_chainTrackStart = 0;
}

// ----- Check Continuazione: il segnale corrente è una continuazione del precedente? -----
bool NXS_Chain_IsContinuation(string newStrat, int newDir, double &lotMult, string &chainReason){
   chainReason = "";
   lotMult = 1.0;

   if(!InpChainEnableContinuation) return false;
   if(g_chain.lastCloseTime == 0) return false;
   if(g_chain.lastClosePnL <= 0) return false;     // solo dopo profitto
   if(g_chain.lastDir != newDir) return false;     // stessa direzione
   if(g_chain.continuationCount >= InpChainMaxContinuations) return false;
   if(TimeCurrent() < g_chain.cooldownUntil) return false;

   // Solo entro la finestra di continuazione (es. 30 min)
   if((TimeCurrent() - g_chain.lastCloseTime) > InpChainContinuationWindowSec) return false;

   // Compatibilità tra strategie
   if(!NXS_Chain_IsCompatible(g_chain.lastStrategy, newStrat)) return false;

   // Conferma: prezzo ha fatto un pullback rispetto all'extremum e sta riprendendo
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double atr = (g_atr > 0 ? g_atr : g_point * 100.0);
   if(bid <= 0 || atr <= 0) return false;

   bool pullbackOk = false;
   if(newDir == +1){
      // Pullback se prezzo è sceso almeno 0.3 ATR dall'extremum e ora è sopra closePrice
      double pullback = g_chain.extremumPrice - bid;
      pullbackOk = (pullback >= 0.3 * atr) && (bid >= g_chain.lastClosePrice * 0.999);
   } else {
      double pullback = bid - g_chain.extremumPrice;
      pullbackOk = (pullback >= 0.3 * atr) && (bid <= g_chain.lastClosePrice * 1.001);
   }
   if(!pullbackOk) return false;

   // Risk-managed: lotto ridotto per continuazioni
   lotMult = MathMax(0.3, InpChainContinuationLotMult);
   chainReason = StringFormat("CHAIN:%s→%s_cont#%d",
                              g_chain.lastStrategy, newStrat,
                              g_chain.continuationCount + 1);
   return true;
}

// ----- Smart Close & Reverse: abbassa soglia se segnali multipli concordi -----
bool NXS_Chain_ShouldSmartReverse(int newDir, double newScore, double reactQual,
                                  int htfBias, double &adjustedThreshold){
   adjustedThreshold = InpMinScoreReverse;
   if(!InpChainEnableSmartReverse) return false;
   if(!InpEnableCloseReverse) return false;

   // Conferma forte se: reaction quality > 75 AND HTF non opposto AND newScore alto
   bool reactStrong = (reactQual >= 75.0);
   bool htfAligned  = (newDir == +1 && htfBias >= 0) || (newDir == -1 && htfBias <= 0);

   if(reactStrong && htfAligned){
      // Abbassa soglia di 15 punti
      adjustedThreshold = MathMax(50.0, InpMinScoreReverse - 15.0);
      return (newScore >= adjustedThreshold);
   }
   if(reactStrong || htfAligned){
      // Abbassa di 5 punti
      adjustedThreshold = MathMax(60.0, InpMinScoreReverse - 5.0);
      return (newScore >= adjustedThreshold);
   }
   // Default: usa soglia originale
   return (newScore >= InpMinScoreReverse);
}

// ----- Incrementa contatore continuazione (chiamato dopo open success) -----
void NXS_Chain_OnContinuationOpen(){
   g_chain.continuationCount++;
   g_chain.cooldownUntil = TimeCurrent() + 30; // breve cooldown tra continuazioni
}

// ----- Dashboard helper: stato chain (per log/debug) -----
string NXS_Chain_StateString(){
   if(g_chain.lastCloseTime == 0) return "Chain: idle";
   int ageMin = (int)((TimeCurrent() - g_chain.lastCloseTime) / 60);
   return StringFormat("Chain: last=%s dir=%s pnl=%.2f age=%dm cont=%d",
                       g_chain.lastStrategy,
                       (g_chain.lastDir > 0 ? "BUY" : (g_chain.lastDir < 0 ? "SELL" : "—")),
                       g_chain.lastClosePnL, ageMin, g_chain.continuationCount);
}

#endif
