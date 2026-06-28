//+------------------------------------------------------------------+
//|  NXS_Globals.mqh - Globals, indicator handles, raw trade helpers  |
//|  NO dependency on <Trade\Trade.mqh> - uses only native MQL5 API.  |
//+------------------------------------------------------------------+
#ifndef __NXS_GLOBALS_MQH__
#define __NXS_GLOBALS_MQH__

// ----- Trade state (replaces CTrade) -----
long                       g_tradeMagic   = 0;
ENUM_ORDER_TYPE_FILLING    g_tradeFilling = ORDER_FILLING_FOK;
uint                       g_tradeRetcode = 0;

// ----- Symbol / context -----
string  g_sym;
double  g_point;
int     g_digits;

// Indicator handles
int g_hADX = INVALID_HANDLE;
int g_hRSI = INVALID_HANDLE;
int g_hBB  = INVALID_HANDLE;
int g_hMACD= INVALID_HANDLE;
int g_hSAR = INVALID_HANDLE;
int g_hATR = INVALID_HANDLE;
int g_hEMA200 = INVALID_HANDLE;
int g_hEMA9   = INVALID_HANDLE;
int g_hEMA21  = INVALID_HANDLE;
int g_hEMA_HTF= INVALID_HANDLE;
int g_hEMA_MTF= INVALID_HANDLE;
int g_hICHI   = INVALID_HANDLE;

// Cached values (closed bar = 1)
double g_adx, g_adxPlus, g_adxMinus;
double g_rsi;
double g_bbUpper, g_bbLower, g_bbMid;
double g_macd, g_macdSig;
double g_sar;
double g_atr;
double g_atrAvg;  // rolling avg of ATR (for adaptive SL)
double g_ema200, g_ema9, g_ema21;
double g_emaHTF, g_emaMTF;
double g_ichiTenkan, g_ichiKijun, g_ichiSpanA, g_ichiSpanB;

// State
ENUM_NXS_REGIME g_regime  = REGIME_UNKNOWN;
ENUM_NXS_SESSION g_session= SESS_NONE;
bool   g_eaPaused         = false;
int    g_tradesToday      = 0;
int    g_consecLosses     = 0;
datetime g_dayStart       = 0;
double g_balanceDayStart  = 0;
datetime g_lastTradeTime  = 0;
datetime g_antiRevengeUntil = 0;
datetime g_lastPushTime   = 0;
datetime g_lastPollTime   = 0;
datetime g_lastBarTime    = 0;
// Anti-bleed state
int      g_skipNextSignals  = 0;

// Cached analysis state (kept fresh by OnTick, reused by OnTimer push)
struct SNXSCachedState {
   bool   ready;
   ENUM_NXS_HTF htfBias;
   double htfConf;
   bool   htfRev;
   ENUM_NXS_VEL velState;
   ENUM_NXS_AMD amdPhase;
   double amdHi, amdLo;
   ENUM_NXS_DIR sweepDir;
   bool   sweepConf;
};
SNXSCachedState g_cached;

// ----- Magic helpers -----
bool IsNexusMagic(long m){
   return (m >= InpMagic && m <= InpMagic + MAGIC_SPLIT + 100);
}
bool IsCoreMagic(long m){ return m == InpMagic + MAGIC_CORE; }
bool IsGridMagic(long m){ return m >= InpMagic + MAGIC_GRID    && m < InpMagic + MAGIC_PYRAMID; }
bool IsPyrMagic(long m) { return m >= InpMagic + MAGIC_PYRAMID && m < InpMagic + MAGIC_SPLIT;   }

double NormPrice(double p){ return NormalizeDouble(p, g_digits); }

// ----- Raw trade helpers (replace CTrade) -----
void NXS_TradeSetMagic(long m){ g_tradeMagic = m; }

void NXS_TradeSetFillingBySymbol(string sym){
   long mode = (long)SymbolInfoInteger(sym, SYMBOL_FILLING_MODE);
   if((mode & SYMBOL_FILLING_FOK) != 0)      g_tradeFilling = ORDER_FILLING_FOK;
   else if((mode & SYMBOL_FILLING_IOC) != 0) g_tradeFilling = ORDER_FILLING_IOC;
   else                                       g_tradeFilling = ORDER_FILLING_RETURN;
}

bool NXS_DoBuy(double volume, string sym, double sl, double tp, string comment){
   MqlTradeRequest req;  ZeroMemory(req);
   MqlTradeResult  res;  ZeroMemory(res);
   req.action      = TRADE_ACTION_DEAL;
   req.symbol      = sym;
   req.volume      = volume;
   req.type        = ORDER_TYPE_BUY;
   req.price       = SymbolInfoDouble(sym, SYMBOL_ASK);
   req.sl          = sl;
   req.tp          = tp;
   req.deviation   = 30;
   req.magic       = g_tradeMagic;
   req.comment     = comment;
   req.type_filling= g_tradeFilling;
   bool ok = OrderSend(req, res);
   g_tradeRetcode = res.retcode;
   return ok && (res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED);
}

bool NXS_DoSell(double volume, string sym, double sl, double tp, string comment){
   MqlTradeRequest req;  ZeroMemory(req);
   MqlTradeResult  res;  ZeroMemory(res);
   req.action      = TRADE_ACTION_DEAL;
   req.symbol      = sym;
   req.volume      = volume;
   req.type        = ORDER_TYPE_SELL;
   req.price       = SymbolInfoDouble(sym, SYMBOL_BID);
   req.sl          = sl;
   req.tp          = tp;
   req.deviation   = 30;
   req.magic       = g_tradeMagic;
   req.comment     = comment;
   req.type_filling= g_tradeFilling;
   bool ok = OrderSend(req, res);
   g_tradeRetcode = res.retcode;
   return ok && (res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED);
}

bool NXS_DoClose(ulong ticket){
   if(!PositionSelectByTicket(ticket)) return false;
   string sym = PositionGetString(POSITION_SYMBOL);
   double vol = PositionGetDouble(POSITION_VOLUME);
   long   ptype = PositionGetInteger(POSITION_TYPE);
   MqlTradeRequest req;  ZeroMemory(req);
   MqlTradeResult  res;  ZeroMemory(res);
   req.action      = TRADE_ACTION_DEAL;
   req.position    = ticket;
   req.symbol      = sym;
   req.volume      = vol;
   req.deviation   = 30;
   req.magic       = (long)PositionGetInteger(POSITION_MAGIC);
   req.type_filling= g_tradeFilling;
   if(ptype == POSITION_TYPE_BUY){
      req.type  = ORDER_TYPE_SELL;
      req.price = SymbolInfoDouble(sym, SYMBOL_BID);
   } else {
      req.type  = ORDER_TYPE_BUY;
      req.price = SymbolInfoDouble(sym, SYMBOL_ASK);
   }
   bool ok = OrderSend(req, res);
   g_tradeRetcode = res.retcode;
   return ok && (res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED);
}

bool NXS_DoClosePartial(ulong ticket, double volume){
   if(!PositionSelectByTicket(ticket)) return false;
   string sym = PositionGetString(POSITION_SYMBOL);
   long   ptype = PositionGetInteger(POSITION_TYPE);
   MqlTradeRequest req;  ZeroMemory(req);
   MqlTradeResult  res;  ZeroMemory(res);
   req.action      = TRADE_ACTION_DEAL;
   req.position    = ticket;
   req.symbol      = sym;
   req.volume      = volume;
   req.deviation   = 30;
   req.magic       = (long)PositionGetInteger(POSITION_MAGIC);
   req.type_filling= g_tradeFilling;
   if(ptype == POSITION_TYPE_BUY){
      req.type  = ORDER_TYPE_SELL;
      req.price = SymbolInfoDouble(sym, SYMBOL_BID);
   } else {
      req.type  = ORDER_TYPE_BUY;
      req.price = SymbolInfoDouble(sym, SYMBOL_ASK);
   }
   bool ok = OrderSend(req, res);
   g_tradeRetcode = res.retcode;
   return ok && (res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED);
}

bool NXS_DoModify(ulong ticket, double sl, double tp){
   if(!PositionSelectByTicket(ticket)) return false;
   MqlTradeRequest req;  ZeroMemory(req);
   MqlTradeResult  res;  ZeroMemory(res);
   req.action   = TRADE_ACTION_SLTP;
   req.position = ticket;
   req.symbol   = PositionGetString(POSITION_SYMBOL);
   req.sl       = sl;
   req.tp       = tp;
   bool ok = OrderSend(req, res);
   g_tradeRetcode = res.retcode;
   return ok && (res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED);
}

uint NXS_TradeRetcode(){ return g_tradeRetcode; }

// ----- Position helpers -----
int NXS_CountPositions(){
   int n = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      n++;
   }
   return n;
}

double NXS_FloatingPnL(){
   double s = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      s += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
   }
   return s;
}

#endif
