//+------------------------------------------------------------------+
//|  NXS_Globals.mqh - Globals, indicator handles, raw trade helpers  |
//|  NO dependency on <Trade\Trade.mqh> - uses only native MQL5 API.  |
//+------------------------------------------------------------------+
#ifndef __NXS_GLOBALS_MQH__
#define __NXS_GLOBALS_MQH__

// v2.0.36: single-strategy screening selector (see InpStrategySelector in
// NXS_Inputs.mqh for the index mapping). 0 = no override, everyone respects
// their own InpStrat_*/InpUseStrat_* toggle as before.
bool NXS_SelectorAllows(int idx){
   return (InpStrategySelector == 0 || InpStrategySelector == idx);
}

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
// v2.2.1 — sizing account-level adattivo: streak dedicati (non toccati da
// anti-revenge) e moltiplicatore lotto che sale sulle vincite / scende sulle
// perdite, dentro [floor, cap].
int    g_streakWins       = 0;
int    g_streakLosses     = 0;
double g_streakLotMult    = 1.0;
datetime g_dayStart       = 0;
double g_balanceDayStart  = 0;
datetime g_lastTradeTime  = 0;
datetime g_antiRevengeUntil = 0;
datetime g_lastPushTime   = 0;
datetime g_lastPollTime   = 0;
datetime g_lastBarTime    = 0;
datetime g_lastH1BarTime  = 0;
datetime g_lastHistSyncTime = 0;
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

// ----- JSON string escaping (shared by NXS_WebBridge.mqh + NXS_Protections.mqh) -----
string _JsonEsc(string s){
   string r = s;
   StringReplace(r, "\\", "\\\\");
   StringReplace(r, "\"", "\\\"");
   return r;
}

// ----- ISO-8601 time formatting (shared by WebBridge + Protections + HistorySync) -----
// MT5's TimeToString() emits "YYYY.MM.DD HH:MM:SS", which JS's Date() parser
// does not reliably accept and renders as "Invalid Date" in the dashboard.
string NXS_IsoTime(datetime t){
   if(t <= 0) return "";
   MqlDateTime mt; TimeToStruct(t, mt);
   return StringFormat("%04d-%02d-%02dT%02d:%02d:%02d",
                       mt.year, mt.mon, mt.day, mt.hour, mt.min, mt.sec);
}

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

// Looks up a closed position's opening-deal time via its position id. Needed by
// OnTradeTransaction, which fires after the position is already gone from
// PositionSelect*, so POSITION_TIME can no longer be read directly there.
datetime NXS_FindPositionOpenTime(ulong positionId, datetime fallback){
   if(!HistorySelectByPosition(positionId)) return fallback;
   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++){
      ulong dt = HistoryDealGetTicket(i);
      if(dt == 0) continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(dt, DEAL_ENTRY) == DEAL_ENTRY_IN)
         return (datetime)HistoryDealGetInteger(dt, DEAL_TIME);
   }
   return fallback;
}

// Looks up a closed position's OPENING-deal comment via its position id, so
// the strategy tag ("prefix|STRAT|score", stamped by NXS_OpenTrade) can be
// recovered even when the broker blanks/overwrites the CLOSING deal's own
// comment on SL/TP/stop-out fills (the same reason NXS_FindPositionOpenTime
// exists — see OnTradeTransaction).
string NXS_FindPositionOpenComment(ulong positionId, string fallback){
   if(!HistorySelectByPosition(positionId)) return fallback;
   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++){
      ulong dt = HistoryDealGetTicket(i);
      if(dt == 0) continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(dt, DEAL_ENTRY) == DEAL_ENTRY_IN)
         return HistoryDealGetString(dt, DEAL_COMMENT);
   }
   return fallback;
}

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

// v2.0.30: symbol-aware exposure cap. A flat lot count means very different
// notional risk on BTCUSD vs GOLD given their contract sizes, so this picks
// a per-symbol override (InpMaxDirExposureLots_BTC/_GOLD) when one is set
// (>0) and the chart symbol matches by substring, else falls back to the
// generic InpMaxDirExposureLots.
double NXS_EffectiveMaxDirExposureLots(){
   if(StringFind(g_sym, "BTC") >= 0 && InpMaxDirExposureLots_BTC > 0)
      return InpMaxDirExposureLots_BTC;
   if((StringFind(g_sym, "XAU") >= 0 || StringFind(g_sym, "GOLD") >= 0) && InpMaxDirExposureLots_GOLD > 0)
      return InpMaxDirExposureLots_GOLD;
   return InpMaxDirExposureLots;
}

// Sum of lots currently open in one direction (core + grid/pyramid/split, any
// NEXUS magic) — used by the v2.0.26 total-exposure cap.
double NXS_DirExposureLots(ENUM_NXS_DIR dir){
   double sum = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      long ptype = PositionGetInteger(POSITION_TYPE);
      bool sameDir = (dir == DIR_BUY  && ptype == POSITION_TYPE_BUY) ||
                     (dir == DIR_SELL && ptype == POSITION_TYPE_SELL);
      if(sameDir) sum += PositionGetDouble(POSITION_VOLUME);
   }
   return sum;
}

// ----- v2.0.26 — new-entry-per-bar/direction cap -----
// Shared by NXS_OpenTrade (classic path) and NXR_OpenTrade (NXR path, which
// InpNXR_Enable routes almost all live signals through) so a confluence of
// several strategies/triggers on the same bar can only open ONE fresh
// position per direction — extra agreeing signals still count toward
// confluence scoring, they just can't each open their own position.
// Grid/Pyramid/Split add-ons bypass this entirely: they call NXS_DoBuy/
// NXS_DoSell directly, never NXS_OpenTrade/NXR_OpenTrade.
datetime g_barDirCapBarTime     = 0;
int      g_newTradesThisBarBuy  = 0;
int      g_newTradesThisBarSell = 0;

void NXS_BarDirCapRollover(){
   datetime bt = iTime(g_sym, InpTFEntry, 0);
   if(bt != g_barDirCapBarTime){
      g_barDirCapBarTime     = bt;
      g_newTradesThisBarBuy  = 0;
      g_newTradesThisBarSell = 0;
   }
}

bool NXS_BarDirCapAllows(ENUM_NXS_DIR dir){
   NXS_BarDirCapRollover();
   int count = (dir == DIR_BUY) ? g_newTradesThisBarBuy : g_newTradesThisBarSell;
   return count < InpMaxNewTradesPerBarDir;
}

void NXS_BarDirCapRegisterOpen(ENUM_NXS_DIR dir){
   NXS_BarDirCapRollover();
   if(dir == DIR_BUY) g_newTradesThisBarBuy++;
   else if(dir == DIR_SELL) g_newTradesThisBarSell++;
}

#endif
