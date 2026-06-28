//+------------------------------------------------------------------+
//|  NXS_EdgeAdaptive.mqh — Sprint 3 (edge / adaptive layer)         |
//|  #5 Reaction cache · #7 SL virtualizzato · #8 OnTradeTransaction |
//|  #9 Slippage per sessione · #12 Volatility regime · #13 Learner  |
//|  v2.0.9 — completes the 15-point performance roadmap             |
//+------------------------------------------------------------------+
#ifndef __NXS_EDGEADAPTIVE_MQH__
#define __NXS_EDGEADAPTIVE_MQH__

// =====================================================================
// #5 — REACTION ENGINE CACHE  (compute once per new M5 bar)
// =====================================================================
struct SNXSReactionCache {
   datetime barTime;
   bool     detected;
   int      direction;
   double   quality;
   double   priceLo;
   double   priceHi;
   string   tag;
};
SNXSReactionCache g_NXSeaReact;

bool NXS_EA_ReactionShouldRecompute(){
   datetime cur = iTime(_Symbol, PERIOD_M5, 0);
   if(cur == 0) return false;
   if(cur == g_NXSeaReact.barTime) return false;
   g_NXSeaReact.barTime = cur;
   return true;
}

// =====================================================================
// #7 — VIRTUALIZED STOP LOSS  (broker SL wide, real SL internal)
// =====================================================================
input bool   InpVirtSL_Enable         = true;
input double InpVirtSL_HardSL_ATRMult = 4.0;

struct SNXSVirtSL {
   ulong  ticket; int direction;
   double virtPrice; double brokerSL;
   bool   active;
};
SNXSVirtSL g_NXSeaVSL[];
int        g_NXSeaVSL_N = 0;

void NXS_EA_VirtSL_Register(ulong ticket, int dir, double virtSL, double brokerSL){
   if(!InpVirtSL_Enable) return;
   ArrayResize(g_NXSeaVSL, g_NXSeaVSL_N + 1);
   g_NXSeaVSL[g_NXSeaVSL_N].ticket    = ticket;
   g_NXSeaVSL[g_NXSeaVSL_N].direction = dir;
   g_NXSeaVSL[g_NXSeaVSL_N].virtPrice = virtSL;
   g_NXSeaVSL[g_NXSeaVSL_N].brokerSL  = brokerSL;
   g_NXSeaVSL[g_NXSeaVSL_N].active    = true;
   g_NXSeaVSL_N++;
}

int NXS_EA_VirtSL_Check(){
   if(!InpVirtSL_Enable) return 0;
   int closed = 0;
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   for(int i = 0; i < g_NXSeaVSL_N; ++i){
      if(!g_NXSeaVSL[i].active) continue;
      bool hit = (g_NXSeaVSL[i].direction == +1)
                  ? (bid <= g_NXSeaVSL[i].virtPrice)
                  : (ask >= g_NXSeaVSL[i].virtPrice);
      if(hit){
         g_NXSeaVSL[i].active = false;
         closed++;
         PrintFormat("[NXS VirtSL] ticket=%I64u hit %.5f dir %d",
                     g_NXSeaVSL[i].ticket, g_NXSeaVSL[i].virtPrice,
                     g_NXSeaVSL[i].direction);
      }
   }
   return closed;
}

// =====================================================================
// #8 — ONTRADETRANSACTION  (event-driven fill capture)
// =====================================================================
ulong g_NXSeaLastDealTicket = 0;
uint  g_NXSeaLastFillMs     = 0;

void NXS_EA_OnTradeTx(const MqlTradeTransaction &tx){
   if(tx.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(tx.deal == 0) return;
   g_NXSeaLastDealTicket = tx.deal;
   g_NXSeaLastFillMs     = GetTickCount();
}

ulong NXS_EA_GetLastDeal(){ return g_NXSeaLastDealTicket; }
uint  NXS_EA_GetFillMs (){ return g_NXSeaLastFillMs;     }

// =====================================================================
// #9 — SESSION-AWARE SLIPPAGE CAP
// =====================================================================
input int InpSlip_Asian   = 8;
input int InpSlip_London  = 15;
input int InpSlip_NewYork = 22;
input int InpSlip_Overlap = 30;
input int InpSlip_Off     = 12;

int NXS_EA_SlippageCap(int sessionCode){
   switch(sessionCode){
      case 1: return InpSlip_Asian;
      case 2: return InpSlip_London;
      case 3: return InpSlip_NewYork;
      case 4: return InpSlip_Overlap;
      default: return InpSlip_Off;
   }
}

// =====================================================================
// #12 — VOLATILITY REGIME ADAPTER  (ATR percentile rolling 100 bars)
// =====================================================================
input bool InpVolAdapt_Enable    = true;
input int  InpVolAdapt_LookbackN = 100;

double g_NXSeaVolWin[];
int    g_NXSeaVolN = 0;

void NXS_EA_VolAdapt_Sample(double atr){
   if(atr <= 0) return;
   if(ArraySize(g_NXSeaVolWin) < InpVolAdapt_LookbackN)
      ArrayResize(g_NXSeaVolWin, InpVolAdapt_LookbackN);
   int idx = g_NXSeaVolN % InpVolAdapt_LookbackN;
   g_NXSeaVolWin[idx] = atr;
   g_NXSeaVolN++;
}

double NXS_EA_VolAdapt_Pct(double curAtr){
   int n = MathMin(g_NXSeaVolN, InpVolAdapt_LookbackN);
   if(n < 20) return 0.5;
   int below = 0;
   for(int i = 0; i < n; ++i)
      if(g_NXSeaVolWin[i] < curAtr) below++;
   return (double)below / (double)n;
}

void NXS_EA_VolAdapt_Multipliers(double atr, double &slMult, double &tpMult){
   slMult = 1.0; tpMult = 1.0;
   if(!InpVolAdapt_Enable) return;
   double pct = NXS_EA_VolAdapt_Pct(atr);
   if(pct < 0.33){ slMult = 0.7; tpMult = 0.9; return; }
   if(pct > 0.75){ slMult = 1.5; tpMult = 1.3; return; }
}

// =====================================================================
// #13 — SESSION×STRATEGY AUTO-LEARNER  (CSV: NEXUS\auto_disable.csv)
// =====================================================================
input bool InpLearner_Enable = true;

struct SNXSAutoDisable { string strat; int session; string reason; };
SNXSAutoDisable g_NXSeaAD[];
int             g_NXSeaAD_N = 0;

int NXS_EA_Learner_Load(){
   if(!InpLearner_Enable) return 0;
   int fh = FileOpen("NEXUS\\auto_disable.csv",
                     FILE_READ | FILE_CSV | FILE_ANSI | FILE_COMMON, ',');
   if(fh == INVALID_HANDLE) return 0;
   ArrayResize(g_NXSeaAD, 0);
   g_NXSeaAD_N = 0;
   while(!FileIsEnding(fh)){
      string c1 = FileReadString(fh);
      if(c1 == "" || c1 == "strategy") continue;
      string c2 = FileReadString(fh);
      string c3 = FileReadString(fh);
      ArrayResize(g_NXSeaAD, g_NXSeaAD_N + 1);
      g_NXSeaAD[g_NXSeaAD_N].strat   = c1;
      g_NXSeaAD[g_NXSeaAD_N].session = (int)StringToInteger(c2);
      g_NXSeaAD[g_NXSeaAD_N].reason  = c3;
      g_NXSeaAD_N++;
   }
   FileClose(fh);
   PrintFormat("[NXS Learner] loaded %d auto-disable rules", g_NXSeaAD_N);
   return g_NXSeaAD_N;
}

bool NXS_EA_Learner_IsDisabled(string strat, int session, string &reason){
   if(!InpLearner_Enable) return false;
   for(int i = 0; i < g_NXSeaAD_N; ++i){
      if(g_NXSeaAD[i].strat == strat && g_NXSeaAD[i].session == session){
         reason = StringFormat("LEARNER %s/%d %s", strat, session, g_NXSeaAD[i].reason);
         return true;
      }
   }
   return false;
}

#endif // __NXS_EDGEADAPTIVE_MQH__
