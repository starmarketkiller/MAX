#ifndef __STRATEGY_RSI_ENGULF_TOUCH_MQH__
#define __STRATEGY_RSI_ENGULF_TOUCH_MQH__

#include <Trade/Trade.mqh>

// Inputs declared in main EA, consumed here via extern.
extern bool   Enable_RSIEngulfTouch;
extern int    RSI_Length;
extern double RSI_OB;
extern double RSI_OS;
extern double Lots;
extern double PipSize;
extern double SL_Pips;
extern double TP1_Pips;
extern double TP2_Pips;
extern double MaxSpreadPips;
extern bool   OneSetPerBar;
extern int    CooldownSeconds;
extern long   MagicBase;

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

      if(m_rsiHandle != INVALID_HANDLE)
         IndicatorRelease(m_rsiHandle);

      m_rsiHandle = iRSI(m_symbol, m_tf, RSI_Length, PRICE_CLOSE);
      if(m_rsiHandle == INVALID_HANDLE)
      {
         Print("[RSIEngulfTouch] Init failed: iRSI handle invalid. err=", GetLastError());
         return false;
      }
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
      if(!Enable_RSIEngulfTouch)
         return;
      if(m_rsiHandle == INVALID_HANDLE)
         return;

      MqlTick tick;
      if(!SymbolInfoTick(m_symbol, tick))
         return;

      double ask = tick.ask;
      double bid = tick.bid;
      if(ask <= 0.0 || bid <= 0.0)
         return;

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

      if(CountMyPositions() > 0)
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

      double rsiCur = 0.0;
      double rsiPrev = 0.0;
      if(!GetRSI(0, rsiCur) || !GetRSI(1, rsiPrev))
      {
         m_lastAsk = ask;
         m_lastBid = bid;
         return;
      }

      bool rsiOS_now_or_prev = (rsiCur <= RSI_OS) || (rsiPrev <= RSI_OS);
      bool rsiOB_now_or_prev = (rsiCur >= RSI_OB) || (rsiPrev >= RSI_OB);

      bool crossUp = (m_lastAsk <= prevOpen) && (ask > prevOpen);
      bool crossDown = (m_lastBid >= prevOpen) && (bid < prevOpen);

      bool longSignal = rsiOS_now_or_prev && prevRed && crossUp;
      bool shortSignal = rsiOB_now_or_prev && prevGreen && crossDown;

      bool entered = false;
      if(longSignal)
         entered = OpenTwoPositions(true, ask, bid);
      else if(shortSignal)
         entered = OpenTwoPositions(false, ask, bid);

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
               " side=", (longSignal ? "BUY" : "SELL"));
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
   CTrade m_trade;

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

   bool OpenOne(bool isBuy, long magic, double sl, double tp)
   {
      m_trade.SetExpertMagicNumber((ulong)magic);
      bool ok = false;
      if(isBuy)
         ok = m_trade.Buy(Lots, m_symbol, 0.0, sl, tp, "RSIEngulfTouch");
      else
         ok = m_trade.Sell(Lots, m_symbol, 0.0, sl, tp, "RSIEngulfTouch");

      if(!ok)
      {
         Print("[RSIEngulfTouch] order failed magic=", magic,
               " retcode=", m_trade.ResultRetcode(),
               " err=", GetLastError());
      }
      return ok;
   }

   bool OpenTwoPositions(bool isBuy, double ask, double bid)
   {
      if(Lots <= 0.0 || PipSize <= 0.0)
         return false;

      double ref = isBuy ? ask : bid;
      int digits = (int)SymbolInfoInteger(m_symbol, SYMBOL_DIGITS);

      double slDist = PipsToPrice(SL_Pips);
      double tp1Dist = PipsToPrice(TP1_Pips);
      double tp2Dist = PipsToPrice(TP2_Pips);

      double sl = isBuy ? (ref - slDist) : (ref + slDist);
      double tp1 = isBuy ? (ref + tp1Dist) : (ref - tp1Dist);
      double tp2 = isBuy ? (ref + tp2Dist) : (ref - tp2Dist);

      sl = NormalizeDouble(sl, digits);
      tp1 = NormalizeDouble(tp1, digits);
      tp2 = NormalizeDouble(tp2, digits);

      bool ok1 = OpenOne(isBuy, MagicBase, sl, tp1);
      bool ok2 = OpenOne(isBuy, MagicBase + 1, sl, tp2);
      return (ok1 && ok2);
   }
};

#endif
