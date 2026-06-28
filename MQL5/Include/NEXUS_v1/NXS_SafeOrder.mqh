//+------------------------------------------------------------------+
//|  NXS_SafeOrder.mqh - OrderSend retry wrapper with backoff         |
//|  Retries on REQUOTE / OFF_QUOTES / PRICE_CHANGED up to N times.   |
//+------------------------------------------------------------------+
#ifndef __NXS_SAFE_ORDER_MQH__
#define __NXS_SAFE_ORDER_MQH__

bool _NXS_IsRetryable(uint rc){
   return (rc == 10004 /* REQUOTE */ ||
           rc == 10020 /* PRICE_CHANGED */ ||
           rc == 10021 /* OFF_QUOTES */ ||
           rc == 10022 /* TIMEOUT */);
}

bool NXS_SafeBuy(double volume, string sym, double sl, double tp, string comment){
   int attempts = MathMax(1, InpOrderRetries);
   for(int i = 0; i < attempts; i++){
      bool ok = NXS_DoBuy(volume, sym, sl, tp, comment);
      uint rc = NXS_TradeRetcode();
      if(ok) return true;
      if(!_NXS_IsRetryable(rc)){
         PrintFormat("[NEXUS SAFE] Buy non-retryable failure rc=%d", rc);
         return false;
      }
      PrintFormat("[NEXUS SAFE] Buy retry %d/%d rc=%d", i+1, attempts, rc);
      Sleep(150 * (i + 1));   // backoff
   }
   return false;
}

bool NXS_SafeSell(double volume, string sym, double sl, double tp, string comment){
   int attempts = MathMax(1, InpOrderRetries);
   for(int i = 0; i < attempts; i++){
      bool ok = NXS_DoSell(volume, sym, sl, tp, comment);
      uint rc = NXS_TradeRetcode();
      if(ok) return true;
      if(!_NXS_IsRetryable(rc)){
         PrintFormat("[NEXUS SAFE] Sell non-retryable failure rc=%d", rc);
         return false;
      }
      PrintFormat("[NEXUS SAFE] Sell retry %d/%d rc=%d", i+1, attempts, rc);
      Sleep(150 * (i + 1));
   }
   return false;
}

#endif
