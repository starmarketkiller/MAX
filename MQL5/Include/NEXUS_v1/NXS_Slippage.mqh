//+------------------------------------------------------------------+
//|  NXS_Slippage.mqh - Hard spread cap + Slippage controls           |
//|  Phase 1 robustness: blocks entry during spread spikes,           |
//|  validates margin & broker stop-level before sending orders.      |
//+------------------------------------------------------------------+
#ifndef __NXS_SLIPPAGE_MQH__
#define __NXS_SLIPPAGE_MQH__

// ----- Hard spread guard (in points) -----
bool NXS_HardSpreadOK(string &reason){
   int spreadPts = (int)SymbolInfoInteger(g_sym, SYMBOL_SPREAD);
   int cap = InpHardMaxSpreadPts;
   if(cap <= 0) cap = g_profile.maxSpreadPts;   // fallback to profile default
   if(cap > 0 && spreadPts > cap){
      reason = StringFormat("hard_spread_cap (%d>%d)", spreadPts, cap);
      return false;
   }
   return true;
}

// ----- Margin pre-flight: ensures broker allows the requested order -----
bool NXS_MarginCheck(ENUM_ORDER_TYPE otype, double lots, double price, string &reason){
   double marginRequired = 0;
   if(!OrderCalcMargin(otype, g_sym, lots, price, marginRequired)){
      reason = StringFormat("margin_calc_failed err=%d", GetLastError());
      return false;
   }
   double marginFree = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   // require 1.5x safety buffer so we don't trigger margin-call on next tick
   if(marginRequired * 1.5 > marginFree){
      reason = StringFormat("insufficient_margin req=%.2f free=%.2f", marginRequired, marginFree);
      return false;
   }
   return true;
}

// ----- Broker stop-level: SL/TP must be at least N points from price -----
// Returns adjusted sl/tp if too close, false if cannot fit.
bool NXS_AdjustStopsForBroker(ENUM_ORDER_TYPE otype, double price, double &sl, double &tp, string &reason){
   int stopsLevel = (int)SymbolInfoInteger(g_sym, SYMBOL_TRADE_STOPS_LEVEL);
   if(stopsLevel <= 0) return true;
   double minDist = stopsLevel * g_point;
   if(otype == ORDER_TYPE_BUY){
      if(sl > 0 && (price - sl) < minDist){
         double newSl = price - minDist;
         PrintFormat("[NEXUS SLIP] SL adjusted for broker: %.5f -> %.5f (stopsLevel=%d)", sl, newSl, stopsLevel);
         sl = newSl;
      }
      if(tp > 0 && (tp - price) < minDist){
         double newTp = price + minDist;
         PrintFormat("[NEXUS SLIP] TP adjusted for broker: %.5f -> %.5f (stopsLevel=%d)", tp, newTp, stopsLevel);
         tp = newTp;
      }
   } else if(otype == ORDER_TYPE_SELL){
      if(sl > 0 && (sl - price) < minDist){
         double newSl = price + minDist;
         PrintFormat("[NEXUS SLIP] SL adjusted for broker: %.5f -> %.5f (stopsLevel=%d)", sl, newSl, stopsLevel);
         sl = newSl;
      }
      if(tp > 0 && (price - tp) < minDist){
         double newTp = price - minDist;
         PrintFormat("[NEXUS SLIP] TP adjusted for broker: %.5f -> %.5f (stopsLevel=%d)", tp, newTp, stopsLevel);
         tp = newTp;
      }
   }
   return true;
}


// AUDITPATCH: price digits are not sufficient for many CFDs/metals; stops must
// be aligned to SYMBOL_TRADE_TICK_SIZE.
double NXS_NormalizePriceToTick(double price){
   if(price <= 0) return price;
   double tick = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_SIZE);
   int digits  = (int)SymbolInfoInteger(g_sym, SYMBOL_DIGITS);
   if(tick <= 0) return NormalizeDouble(price, digits);
   return NormalizeDouble(MathRound(price / tick) * tick, digits);
}

bool NXS_ValidateStopSides(ENUM_ORDER_TYPE otype, double price, double sl, double tp, string &reason){
   if(otype == ORDER_TYPE_BUY){
      if(sl > 0 && sl >= price){ reason = "buy_sl_not_below_price"; return false; }
      if(tp > 0 && tp <= price){ reason = "buy_tp_not_above_price"; return false; }
   } else if(otype == ORDER_TYPE_SELL){
      if(sl > 0 && sl <= price){ reason = "sell_sl_not_above_price"; return false; }
      if(tp > 0 && tp >= price){ reason = "sell_tp_not_below_price"; return false; }
   }
   return true;
}

// ----- Pre-flight bundle called by Execution before OrderSend -----
bool NXS_PreFlight(ENUM_ORDER_TYPE otype, double lots, double price,
                   double &sl, double &tp, string &reason){
   if(!NXS_HardSpreadOK(reason)) return false;
   if(!NXS_MarginCheck(otype, lots, price, reason)) return false;
   if(!NXS_AdjustStopsForBroker(otype, price, sl, tp, reason)) return false;
   sl = NXS_NormalizePriceToTick(sl);
   tp = NXS_NormalizePriceToTick(tp);
   if(!NXS_ValidateStopSides(otype, price, sl, tp, reason)) return false;
   // Volume sanity
   double minLot = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MAX);
   if(lots < minLot){ reason = StringFormat("lot_below_min %.4f<%.4f", lots, minLot); return false; }
   if(lots > maxLot){ reason = StringFormat("lot_above_max %.4f>%.4f", lots, maxLot); return false; }
   return true;
}

#endif
