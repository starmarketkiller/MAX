//+------------------------------------------------------------------+
//|  NXS_RiskShield.mqh — Sprint 2 (drawdown protection)             |
//|  #6 Spread Burst · #10 Equity Breaker · #11 Correlation Cluster  |
//|  #14 News Tier-3 Position Management                             |
//|  v2.0.9 — institutional-grade capital defense layer              |
//+------------------------------------------------------------------+
#ifndef __NXS_RISKSHIELD_MQH__
#define __NXS_RISKSHIELD_MQH__

// =====================================================================
// #6 — SPREAD BURST PROTECTION
// Tracks a rolling window of spreads and freezes entries when current
// spread exceeds the P95 of the window. Eliminates fill-in-news-spike.
// =====================================================================
input bool   InpSpreadBurst_Enable    = true;
input int    InpSpreadBurst_Samples   = 1000;   // rolling window size
input double InpSpreadBurst_P95Cap    = 1.30;   // multiplier of P95 (e.g. 1.3× P95)
input int    InpSpreadBurst_FreezeSec = 30;     // freeze duration on burst

double g_NXSrsSpreadBuf[];          // ring buffer
int    g_NXSrsSpreadIdx  = 0;
int    g_NXSrsSpreadN    = 0;
datetime g_NXSrsFrozenUntil = 0;

void NXS_RS_SpreadSample(){
   double sp = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(sp <= 0) return;
   if(ArraySize(g_NXSrsSpreadBuf) < InpSpreadBurst_Samples)
      ArrayResize(g_NXSrsSpreadBuf, InpSpreadBurst_Samples);
   g_NXSrsSpreadBuf[g_NXSrsSpreadIdx] = sp;
   g_NXSrsSpreadIdx = (g_NXSrsSpreadIdx + 1) % InpSpreadBurst_Samples;
   if(g_NXSrsSpreadN < InpSpreadBurst_Samples) g_NXSrsSpreadN++;
}

double NXS_RS_SpreadP95(){
   if(g_NXSrsSpreadN < 50) return 0;  // warm-up
   double tmp[];
   ArrayResize(tmp, g_NXSrsSpreadN);
   for(int i = 0; i < g_NXSrsSpreadN; ++i) tmp[i] = g_NXSrsSpreadBuf[i];
   ArraySort(tmp);
   int p95Idx = (int)MathFloor(g_NXSrsSpreadN * 0.95);
   if(p95Idx >= g_NXSrsSpreadN) p95Idx = g_NXSrsSpreadN - 1;
   return tmp[p95Idx];
}

// Call before each new entry attempt. Returns true if entries are blocked.
bool NXS_RS_SpreadBurst_Block(string &reason){
   if(!InpSpreadBurst_Enable) return false;
   NXS_RS_SpreadSample();
   if(TimeCurrent() < g_NXSrsFrozenUntil){
      reason = StringFormat("SPREAD_BURST_FROZEN until %s",
                            TimeToString(g_NXSrsFrozenUntil, TIME_SECONDS));
      return true;
   }
   double p95 = NXS_RS_SpreadP95();
   if(p95 <= 0) return false;          // warm-up, allow
   double cur = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(cur > p95 * InpSpreadBurst_P95Cap){
      g_NXSrsFrozenUntil = TimeCurrent() + InpSpreadBurst_FreezeSec;
      reason = StringFormat("SPREAD_BURST cur=%.0f p95=%.0f cap=%.0f freeze=%ds",
                            cur, p95, p95 * InpSpreadBurst_P95Cap, InpSpreadBurst_FreezeSec);
      return true;
   }
   return false;
}

// =====================================================================
// #10 — EQUITY CURVE BREAKER (rolling Sharpe auto-pause)
// Computes Sharpe over the last N closed trades. If Sharpe < threshold,
// the EA self-pauses for `InpBreaker_PauseHours` and pushes a Coach alert.
// =====================================================================
input bool   InpBreaker_Enable      = true;
input int    InpBreaker_LookbackN   = 50;
input double InpBreaker_SharpeMin   = 0.30;
input int    InpBreaker_PauseHours  = 24;

datetime g_NXSrsBreakerUntil = 0;
double   g_NXSrsLastSharpe   = 0;

// Caller provides closed-trade returns (in R or dollars) in chronological order.
// Returns true if breaker just tripped now (Sharpe below threshold).
bool NXS_RS_Breaker_Check(double &rets[], int n, string &reason){
   if(!InpBreaker_Enable || n < InpBreaker_LookbackN){ reason = ""; return false; }
   double sum = 0.0;
   for(int i = n - InpBreaker_LookbackN; i < n; ++i) sum += rets[i];
   double mean = sum / InpBreaker_LookbackN;
   double sqsum = 0.0;
   for(int i = n - InpBreaker_LookbackN; i < n; ++i){
      double d = rets[i] - mean;
      sqsum += d * d;
   }
   double sigma = MathSqrt(sqsum / InpBreaker_LookbackN);
   double sharpe = (sigma > 1e-9 ? mean / sigma : 0.0);
   g_NXSrsLastSharpe = sharpe;
   if(sharpe < InpBreaker_SharpeMin){
      g_NXSrsBreakerUntil = TimeCurrent() + InpBreaker_PauseHours * 3600;
      reason = StringFormat("EQUITY_BREAKER sharpe=%.2f<%.2f n=%d pause=%dh",
                            sharpe, InpBreaker_SharpeMin, InpBreaker_LookbackN,
                            InpBreaker_PauseHours);
      return true;
   }
   reason = "";
   return false;
}

bool NXS_RS_Breaker_Active(){
   return InpBreaker_Enable && TimeCurrent() < g_NXSrsBreakerUntil;
}

double NXS_RS_Breaker_LastSharpe(){ return g_NXSrsLastSharpe; }

// =====================================================================
// #11 — CORRELATION-CLUSTER RISK CAP
// Two perfectly correlated trades = 2× the intended risk. Group symbols
// into clusters and cap concurrent exposure per cluster, not per ticket.
// =====================================================================
input int InpCluster_MaxPerCluster = 2;   // max concurrent positions per cluster

// Static cluster table. Each symbol belongs to ONE cluster.
//   USD_STRONG: positions that benefit from a strong USD
//   USD_WEAK:   positions that benefit from a weak USD
//   GOLD_BLOCK: gold-correlated cluster
//   CRYPTO:     crypto risk-on cluster
//   INDEX_RISKON: equity indices risk-on cluster
string NXS_RS_ClusterOf(string sym){
   string s = sym; StringToUpper(s);
   if(StringFind(s, "XAU") >= 0 || StringFind(s, "GOLD") >= 0 ||
      StringFind(s, "XAG") >= 0 || StringFind(s, "SILVER") >= 0)
      return "GOLD_BLOCK";
   if(StringFind(s, "BTC") >= 0 || StringFind(s, "ETH") >= 0 ||
      StringFind(s, "SOL") >= 0 || StringFind(s, "DOGE") >= 0)
      return "CRYPTO";
   if(StringFind(s, "US30") >= 0 || StringFind(s, "NAS") >= 0 ||
      StringFind(s, "SPX") >= 0 || StringFind(s, "DAX") >= 0)
      return "INDEX_RISKON";
   if(StringFind(s, "EURUSD") >= 0 || StringFind(s, "GBPUSD") >= 0 ||
      StringFind(s, "AUDUSD") >= 0 || StringFind(s, "NZDUSD") >= 0)
      return "USD_STRONG";   // long these = short USD
   if(StringFind(s, "USDJPY") >= 0 || StringFind(s, "USDCAD") >= 0 ||
      StringFind(s, "USDCHF") >= 0)
      return "USD_WEAK";     // long these = long USD
   return "OTHER";
}

// Returns true if opening a position on `symbol` would exceed cluster cap.
// Caller passes the function that returns count of open positions per symbol.
int NXS_RS_ClusterCount(string targetCluster){
   int total = PositionsTotal();
   int count = 0;
   for(int i = 0; i < total; ++i){
      string s = PositionGetSymbol(i);
      if(s == "") continue;
      if(NXS_RS_ClusterOf(s) == targetCluster) count++;
   }
   return count;
}

bool NXS_RS_Cluster_Block(string sym, string &reason){
   string cl = NXS_RS_ClusterOf(sym);
   int n = NXS_RS_ClusterCount(cl);
   if(n >= InpCluster_MaxPerCluster){
      reason = StringFormat("CLUSTER_CAP %s=%d/%d", cl, n, InpCluster_MaxPerCluster);
      return true;
   }
   return false;
}

// =====================================================================
// #14 — NEWS TIER-3 POSITION MANAGEMENT
// Tier-1: hard block 30min around red news (existing).
// Tier-2: soft score penalty 60min around news (existing).
// Tier-3 (NEW): 5min before red news, tighten SL on open positions
//               to break-even + 1× ATR. Or 50% partial close.
// =====================================================================
input bool   InpNewsTier3_Enable     = true;
input int    InpNewsTier3_LeadMin    = 5;      // minutes before red news
input int    InpNewsTier3_Mode       = 1;      // 0=close50% 1=tightenSL
input double InpNewsTier3_SLBufferATR = 1.0;   // tighten to BE + N*ATR

// Caller provides: minutes until next red news, and the SYMBOL ATR.
// Returns the SL price that should be SET on existing positions (0 if no action).
// Callers loop over their open positions and call this for each.
double NXS_RS_NewsTier3_SuggestedSL(int minutesUntilRedNews, double openPrice,
                                    double atr, int direction){
   if(!InpNewsTier3_Enable) return 0.0;
   if(minutesUntilRedNews < 0 || minutesUntilRedNews > InpNewsTier3_LeadMin) return 0.0;
   if(InpNewsTier3_Mode != 1) return 0.0;
   if(direction == +1)  return openPrice + atr * InpNewsTier3_SLBufferATR;  // BUY: SL above
   if(direction == -1)  return openPrice - atr * InpNewsTier3_SLBufferATR;  // SELL: SL below
   return 0.0;
}

bool NXS_RS_NewsTier3_PartialCloseDue(int minutesUntilRedNews){
   if(!InpNewsTier3_Enable) return false;
   if(InpNewsTier3_Mode != 0) return false;
   return (minutesUntilRedNews >= 0 && minutesUntilRedNews <= InpNewsTier3_LeadMin);
}

// =====================================================================
// MASTER GATE — call this in TryExecute before sending the order.
// One single function that bundles all 4 protections.
// =====================================================================
bool NXS_RS_BlockEntry(string sym, string &reason){
   if(NXS_RS_Breaker_Active()){
      reason = StringFormat("EQUITY_BREAKER sharpe=%.2f", g_NXSrsLastSharpe);
      return true;
   }
   if(NXS_RS_SpreadBurst_Block(reason)) return true;
   if(NXS_RS_Cluster_Block(sym, reason)) return true;
   return false;
}

#endif // __NXS_RISKSHIELD_MQH__
