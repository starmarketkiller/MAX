#ifndef __STRATEGY_RSI_ENGULF_TOUCH_MQH__
#define __STRATEGY_RSI_ENGULF_TOUCH_MQH__

#include <Trade/Trade.mqh>

enum RSITrendMode
{
   TRENDMODE_DISABLED = 0,
   TRENDMODE_DIRECTIONAL_FILTER_ONLY = 1,
   TRENDMODE_RUNNER_UPGRADE = 2
};

enum SigState
{
   SIG_NONE = 0,
   SIG_LONG_ACTIVE = 1,
   SIG_SHORT_ACTIVE = 2,
   SIG_LONG_TREND = 3,
   SIG_SHORT_TREND = 4
};

// Inputs declared in main EA, consumed here via extern.
extern bool            Enable_RSIEngulfTouch;
extern int             RSI_Length;
extern double          RSI_OB;
extern double          RSI_OS;
extern double          Lots;
extern double          PipSize;
extern double          SL_Pips;
extern double          TP1_Pips;
extern double          TP2_Pips;
extern double          MaxSpreadPips;
extern bool            OneSetPerBar;
extern int             CooldownSeconds;
extern long            MagicBase;
extern ENUM_TIMEFRAMES SignalTF;
extern double          TrendThresholdMultiplier;
extern RSITrendMode    TrendMode;

class RSIEngulfTouchStrategy
{
public:
   RSIEngulfTouchStrategy()
   {
      m_symbol = "";
      m_tf = PERIOD_CURRENT;
      m_rsiHandle = INVALID_HANDLE;
      m_lastBarTime = 0;
      m_lastTradeTime = 0;
      m_lastAsk = 0.0;
      m_lastBid = 0.0;
      m_readyCross = false;
      m_state = SIG_NONE;
      m_stateStartTime = 0;
   }

   bool Init(string symbol, ENUM_TIMEFRAMES tf)
   {
      m_symbol = symbol;
      m_tf = tf;
      m_lastBarTime = 0;
      m_lastTradeTime = 0;
      m_lastAsk = 0.0;
      m_lastBid = 0.0;
      m_readyCross = false;
      m_state = SIG_NONE;
      m_stateStartTime = 0;

      if(m_rsiHandle != INVALID_HANDLE)
         IndicatorRelease(m_rsiHandle);

      m_rsiHandle = iRSI(m_symbol, m_tf, RSI_Length, PRICE_CLOSE);
      if(m_rsiHandle == INVALID_HANDLE)
      {
         Print("[RSIEngulfTouch] Init failed: iRSI handle invalid. err=", GetLastError());
         return false;
      }

      long marginMode = AccountInfoInteger(ACCOUNT_MARGIN_MODE);
      if(marginMode != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
         Print("[RSIEngulfTouch] Warning: account is not hedging mode; dual-position behavior may be limited.");

      return true;
   }

   void Deinit()
   {
      if(m_rsiHandle != INVALID_HANDLE)
      {
         IndicatorRelease(m_rsiHandle);
         m_rsiHandle = INVALID_HANDLE;
      }
   }

   void OnTick()
   {
      if(!Enable_RSIEngulfTouch || m_rsiHandle == INVALID_HANDLE)
         return;

      MqlTick tick;
      if(!SymbolInfoTick(m_symbol, tick))
         return;

      double ask = tick.ask;
      double bid = tick.bid;
      if(ask <= 0.0 || bid <= 0.0)
         return;

      double rsiCur = 0.0;
      double rsiPrev = 0.0;
      if(!GetRSI(0, rsiCur) || !GetRSI(1, rsiPrev))
         return;

      UpdateTrendState(rsiCur, rsiPrev);
      if(TrendMode == TRENDMODE_RUNNER_UPGRADE)
         ManageRunnerPositions(ask, bid);

      if(!m_readyCross)
      {
         m_lastAsk = ask;
         m_lastBid = bid;
         m_readyCross = true;
         return;
      }

      if(SpreadInPips(ask, bid) > MaxSpreadPips)
      {
         m_lastAsk = ask;
         m_lastBid = bid;
         return;
      }

      datetime bar0 = iTime(m_symbol, m_tf, 0);
      if(bar0 <= 0)
      {
         m_lastAsk = ask;
         m_lastBid = bid;
         return;
      }

      double prevOpen = iOpen(m_symbol, m_tf, 1);
      double prevClose = iClose(m_symbol, m_tf, 1);
      if(prevOpen <= 0.0 || prevClose <= 0.0)
      {
         m_lastAsk = ask;
         m_lastBid = bid;
         return;
      }

      bool prevRed = (prevClose < prevOpen);
      bool prevGreen = (prevClose > prevOpen);

      bool rsiOS_now_or_prev = (rsiCur <= RSI_OS) || (rsiPrev <= RSI_OS);
      bool rsiOB_now_or_prev = (rsiCur >= RSI_OB) || (rsiPrev >= RSI_OB);

      bool crossUp = (m_lastAsk <= prevOpen) && (ask > prevOpen);
      bool crossDown = (m_lastBid >= prevOpen) && (bid < prevOpen);

      bool rawLongSignal = rsiOS_now_or_prev && prevRed && crossUp;
      bool rawShortSignal = rsiOB_now_or_prev && prevGreen && crossDown;

      if(rawLongSignal)
         SetState(SIG_LONG_ACTIVE, TimeCurrent());
      else if(rawShortSignal)
         SetState(SIG_SHORT_ACTIVE, TimeCurrent());

      bool longSignal = rawLongSignal;
      bool shortSignal = rawShortSignal;
      if(TrendMode == TRENDMODE_DIRECTIONAL_FILTER_ONLY)
      {
         if(m_state == SIG_LONG_TREND)
            shortSignal = false;
         else if(m_state == SIG_SHORT_TREND)
            longSignal = false;
      }

      if(CountMyPositions() > 0)
      {
         m_lastAsk = ask;
         m_lastBid = bid;
         return;
      }

      if(OneSetPerBar && m_lastBarTime == bar0)
      {
         m_lastAsk = ask;
         m_lastBid = bid;
         return;
      }

      datetime nowTs = TimeCurrent();
      if(m_lastTradeTime > 0 && (nowTs - m_lastTradeTime) < CooldownSeconds)
      {
         m_lastAsk = ask;
         m_lastBid = bid;
         return;
      }

      bool entered = false;
      bool isBuy = false;
      if(longSignal)
      {
         isBuy = true;
         entered = OpenTwoPositions(true, ask, bid);
      }
      else if(shortSignal)
      {
         isBuy = false;
         entered = OpenTwoPositions(false, ask, bid);
      }

      if(entered)
      {
         m_lastBarTime = bar0;
         m_lastTradeTime = nowTs;
         Print("[RSIEngulfTouch] ENTRY symbol=", m_symbol,
               " pipSize=", DoubleToString(PipSize, 5),
               " spreadPips=", DoubleToString(SpreadInPips(ask, bid), 2),
               " prev_open=", DoubleToString(prevOpen, (int)SymbolInfoInteger(m_symbol, SYMBOL_DIGITS)),
               " rsi_cur=", DoubleToString(rsiCur, 2),
               " rsi_prev=", DoubleToString(rsiPrev, 2),
               " side=", (isBuy ? "BUY" : "SELL"),
               " state=", (int)m_state);
      }

      m_lastAsk = ask;
      m_lastBid = bid;
   }

private:
   string m_symbol;
   ENUM_TIMEFRAMES m_tf;
   int m_rsiHandle;
   datetime m_lastBarTime;
   datetime m_lastTradeTime;
   double m_lastAsk;
   double m_lastBid;
   bool m_readyCross;
   SigState m_state;
   datetime m_stateStartTime;
   CTrade m_trade;

   void SetState(SigState newState, datetime startTs)
   {
      if(newState == SIG_NONE)
      {
         m_state = SIG_NONE;
         m_stateStartTime = 0;
         return;
      }
      m_state = newState;
      m_stateStartTime = startTs;
   }

   double PipsToPrice(double pips) const
   {
      return pips * PipSize;
   }

   double SpreadInPips(double ask, double bid) const
   {
      if(PipSize <= 0.0)
         return 0.0;
      return (ask - bid) / PipSize;
   }

   bool GetRSI(int shift, double &value)
   {
      double buf[1];
      int copied = CopyBuffer(m_rsiHandle, 0, shift, 1, buf);
      if(copied < 1)
         return false;
      value = buf[0];
      return true;
   }

   void UpdateTrendState(double rsiCur, double rsiPrev)
   {
      bool longState = (m_state == SIG_LONG_ACTIVE || m_state == SIG_LONG_TREND);
      bool shortState = (m_state == SIG_SHORT_ACTIVE || m_state == SIG_SHORT_TREND);

      if(longState && (rsiCur < 50.0 && rsiPrev >= 50.0))
      {
         SetState(SIG_NONE, 0);
         return;
      }
      if(shortState && (rsiCur > 50.0 && rsiPrev <= 50.0))
      {
         SetState(SIG_NONE, 0);
         return;
      }

      if(TrendMode == TRENDMODE_DISABLED || m_stateStartTime <= 0)
         return;

      int tfSec = PeriodSeconds(m_tf);
      if(tfSec <= 0)
         return;

      double threshold = TrendThresholdMultiplier * (double)tfSec;
      double age = (double)(TimeCurrent() - m_stateStartTime);
      if(age <= threshold)
         return;

      if(m_state == SIG_LONG_ACTIVE)
         m_state = SIG_LONG_TREND;
      else if(m_state == SIG_SHORT_ACTIVE)
         m_state = SIG_SHORT_TREND;
   }

   int CountMyPositions() const
   {
      int count = 0;
      int total = PositionsTotal();
      for(int i = 0; i < total; i++)
      {
         if(!PositionSelectByIndex(i))
            continue;

         string sym = PositionGetString(POSITION_SYMBOL);
         long magic = PositionGetInteger(POSITION_MAGIC);
         if(sym == m_symbol && (magic == MagicBase || magic == (MagicBase + 1)))
            count++;
      }
      return count;
   }

   double NormalizeLots(double lots) const
   {
      double step = SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_STEP);
      double minLot = SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_MIN);
      double maxLot = SymbolInfoDouble(m_symbol, SYMBOL_VOLUME_MAX);
      if(step <= 0.0 || minLot <= 0.0 || maxLot <= 0.0)
         return 0.0;

      double v = MathMax(minLot, MathMin(maxLot, lots));
      v = MathFloor(v / step) * step;

      int decimals = 0;
      double scaled = step;
      while(decimals < 8 && MathAbs(scaled - MathRound(scaled)) > 1e-8)
      {
         scaled *= 10.0;
         decimals++;
      }
      return NormalizeDouble(v, decimals);
   }

   bool IsTradeAllowedOnSymbol() const
   {
      long mode = SymbolInfoInteger(m_symbol, SYMBOL_TRADE_MODE);
      return (mode != SYMBOL_TRADE_MODE_DISABLED && mode != SYMBOL_TRADE_MODE_CLOSEONLY);
   }

   bool OpenOne(bool isBuy, long magic, double lots, double sl, double tp)
   {
      m_trade.SetExpertMagicNumber((ulong)magic);
      bool ok = false;
      if(isBuy)
         ok = m_trade.Buy(lots, m_symbol, 0.0, sl, tp, "RSIEngulfTouch");
      else
         ok = m_trade.Sell(lots, m_symbol, 0.0, sl, tp, "RSIEngulfTouch");

      if(!ok)
      {
         Print("[RSIEngulfTouch] order failed magic=", magic,
               " retcode=", m_trade.ResultRetcode(),
               " err=", GetLastError());
      }
      return ok;
   }

   void ClosePositionByMagic(long magic)
   {
      int total = PositionsTotal();
      for(int i = total - 1; i >= 0; i--)
      {
         if(!PositionSelectByIndex(i))
            continue;
         string sym = PositionGetString(POSITION_SYMBOL);
         long mg = PositionGetInteger(POSITION_MAGIC);
         if(sym != m_symbol || mg != magic)
            continue;
         ulong ticket = (ulong)PositionGetInteger(POSITION_TICKET);
         m_trade.PositionClose(ticket);
      }
   }

   bool OpenTwoPositions(bool isBuy, double ask, double bid)
   {
      if(Lots <= 0.0 || PipSize <= 0.0 || !IsTradeAllowedOnSymbol())
         return false;

      double lots = NormalizeLots(Lots);
      if(lots <= 0.0)
         return false;

      double ref = isBuy ? ask : bid;
      int digits = (int)SymbolInfoInteger(m_symbol, SYMBOL_DIGITS);

      double slDist = PipsToPrice(SL_Pips);
      double tp1Dist = PipsToPrice(TP1_Pips);
      double tp2Dist = PipsToPrice(TP2_Pips);

      double sl = isBuy ? (ref - slDist) : (ref + slDist);
      double tp1 = isBuy ? (ref + tp1Dist) : (ref - tp1Dist);
      double tp2 = isBuy ? (ref + tp2Dist) : (ref - tp2Dist);

      bool useRunner = (TrendMode == TRENDMODE_RUNNER_UPGRADE) &&
                       (m_state == SIG_LONG_TREND || m_state == SIG_SHORT_TREND);

      sl = NormalizeDouble(sl, digits);
      tp1 = NormalizeDouble(tp1, digits);
      if(!useRunner)
         tp2 = NormalizeDouble(tp2, digits);
      else
         tp2 = 0.0;

      bool ok1 = OpenOne(isBuy, MagicBase, lots, sl, tp1);
      bool ok2 = OpenOne(isBuy, MagicBase + 1, lots, sl, tp2);

      if(ok1 && !ok2)
         ClosePositionByMagic(MagicBase);
      else if(!ok1 && ok2)
         ClosePositionByMagic(MagicBase + 1);

      return (ok1 && ok2);
   }

   void ManageRunnerPositions(double ask, double bid)
   {
      if(!(m_state == SIG_LONG_TREND || m_state == SIG_SHORT_TREND) || PipSize <= 0.0)
         return;

      int total = PositionsTotal();
      for(int i = 0; i < total; i++)
      {
         if(!PositionSelectByIndex(i))
            continue;

         string sym = PositionGetString(POSITION_SYMBOL);
         long magic = PositionGetInteger(POSITION_MAGIC);
         if(sym != m_symbol || magic != (MagicBase + 1))
            continue;

         int type = (int)PositionGetInteger(POSITION_TYPE);
         double entry = PositionGetDouble(POSITION_PRICE_OPEN);
         double sl = PositionGetDouble(POSITION_SL);
         double tp = PositionGetDouble(POSITION_TP);
         ulong ticket = (ulong)PositionGetInteger(POSITION_TICKET);

         double price = (type == POSITION_TYPE_BUY) ? bid : ask;
         double profitPips = (type == POSITION_TYPE_BUY) ? ((price - entry) / PipSize)
                                                         : ((entry - price) / PipSize);

         double beTrigger = TP1_Pips;
         double trailDistPips = MathMax(1.0, TP1_Pips * 0.5);
         int digits = (int)SymbolInfoInteger(m_symbol, SYMBOL_DIGITS);

         if(profitPips < beTrigger)
            continue;

         double newSl = entry;
         if(type == POSITION_TYPE_BUY)
         {
            double tr = price - PipsToPrice(trailDistPips);
            if(tr > newSl)
               newSl = tr;
            if(newSl > sl + 0.1 * PipSize)
               m_trade.PositionModify(ticket, NormalizeDouble(newSl, digits), tp);
         }
         else
         {
            double tr = price + PipsToPrice(trailDistPips);
            if(tr < newSl)
               newSl = tr;
            if(sl <= 0.0 || newSl < sl - 0.1 * PipSize)
               m_trade.PositionModify(ticket, NormalizeDouble(newSl, digits), tp);
         }
      }
   }
};

#endif
