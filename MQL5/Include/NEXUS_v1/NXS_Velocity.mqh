//+------------------------------------------------------------------+
//|  NXS_Velocity.mqh - ZLEMA + ATR band gate                         |
//+------------------------------------------------------------------+
#ifndef __NXS_VELOCITY_MQH__
#define __NXS_VELOCITY_MQH__

struct SNXSVel { ENUM_NXS_VEL state; double slope; };

// Zero-Lag EMA built from price array via EMA-of-(price + (price - EMA))
double _zlema(int period, int shift){
   double prices[];
   if(CopyClose(g_sym, InpTFEntry, shift, period * 3, prices) <= 0) return 0;
   double k = 2.0 / (period + 1.0);
   int    lag = (int)MathRound((period - 1) / 2.0);
   int sz = ArraySize(prices);
   if(sz < period + lag + 2) return 0;
   double ema = prices[0];
   for(int i = 1; i < sz; i++){
      double p = prices[i];
      double pl = (i - lag >= 0) ? prices[i - lag] : prices[i];
      double zl = p + (p - pl);
      ema = ema + k * (zl - ema);
   }
   return ema;
}

SNXSVel NXS_GetVelocity(){
   SNXSVel r; r.state = VEL_NEUTRAL; r.slope = 0.0;
   if(!g_run_UseVelocityGate){ r.state = VEL_NEUTRAL; return r; }

   double z1 = _zlema(InpVel_ZLEMA, 1);
   double z2 = _zlema(InpVel_ZLEMA, 2);
   if(z1 <= 0 || z2 <= 0) return r;
   r.slope = (z1 - z2);
   double thr = g_atr * InpVel_ATRMult;
   double price = iClose(g_sym, InpTFEntry, 1);

   if(r.slope > thr)       r.state = (price > z1) ? VEL_BULL    : VEL_BULL_PB;
   else if(r.slope < -thr) r.state = (price < z1) ? VEL_BEAR    : VEL_BEAR_PB;
   else                    r.state = VEL_NEUTRAL;
   return r;
}

// Phase 1: VEL_NEUTRAL no longer hard-blocks. Modes:
//   0=block (legacy), 1=penalty (router), 2=allow.
// Returns true ONLY if the velocity is clearly opposite to the requested
// direction OR if the user explicitly chose mode 0.
bool NXS_VelocityBlocks(ENUM_NXS_DIR dir, SNXSVel &v){
   if(!g_run_UseVelocityGate) return false;
   if(v.state == VEL_NEUTRAL){
      // GateMode Discovery/Debug explicitly delegates neutral velocity to router.
      if(InpGateMode >= 2) return false;
      return (InpVelocityNeutralMode == 0);
   }
   // DebugTrade may observe/execute opposite-velocity candidates; the router
   // applies a substantial score penalty before they arrive here.
   if(InpGateMode >= 3) return false;
   if(dir == DIR_BUY  && (v.state == VEL_BEAR || v.state == VEL_BEAR_PB)) return true;
   if(dir == DIR_SELL && (v.state == VEL_BULL || v.state == VEL_BULL_PB)) return true;
   return false;
}

string NXS_VelName(ENUM_NXS_VEL v){
   switch(v){
      case VEL_BULL:    return "BULL";
      case VEL_BEAR:    return "BEAR";
      case VEL_BULL_PB: return "BULL_PB";
      case VEL_BEAR_PB: return "BEAR_PB";
   }
   return "NEUTRAL";
}

#endif
