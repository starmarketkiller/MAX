//+------------------------------------------------------------------+
//|  NXS_SafeOrder.mqh - OrderSend retry wrapper                      |
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

// AUD0-EXEC-003: il backoff usava Sleep() dentro il gestore eventi di
// trading. Con 3 tentativi si arrivava a ~900ms di blocco totale del thread
// dell'EA: in quella finestra non giravano il controllo del Virtual SL, le
// protezioni d'emergenza, il timer e OnTradeTransaction.
//
// La pausa e' ora sostituita da un'attesa NON bloccante sul tick corrente:
// si spende al massimo `InpOrderRetryBudgetMs` millisecondi complessivi e si
// verifica che la quotazione sia effettivamente cambiata prima di riprovare.
// Se il budget si esaurisce, il tentativo viene abbandonato e ripreso al tick
// successivo dal chiamante, invece di trattenere il thread.
#ifndef NXS_ORDER_RETRY_BUDGET_MS
#define NXS_ORDER_RETRY_BUDGET_MS 250
#endif

//: Attende un cambio di quotazione senza cedere il thread a Sleep().
//: Ritorna true se il prezzo si e' mosso entro il budget residuo.
bool _NXS_WaitQuoteChange(string sym, double refBid, double refAsk,
                          uint startMs, uint budgetMs){
   while((GetTickCount() - startMs) < budgetMs){
      double bid = SymbolInfoDouble(sym, SYMBOL_BID);
      double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
      if(bid != refBid || ask != refAsk) return true;
      // Nessuna Sleep: si cede solo il minimo indispensabile al terminale.
      if(IsStopped()) return false;
   }
   return false;
}

bool NXS_SafeBuy(double volume, string sym, double sl, double tp, string comment){
   int attempts = MathMax(1, InpOrderRetries);
   uint startMs = GetTickCount();
   for(int i = 0; i < attempts; i++){
      double refBid = SymbolInfoDouble(sym, SYMBOL_BID);
      double refAsk = SymbolInfoDouble(sym, SYMBOL_ASK);

      bool ok = NXS_DoBuy(volume, sym, sl, tp, comment);
      uint rc = NXS_TradeRetcode();
      if(ok) return true;
      if(!_NXS_IsRetryable(rc)){
         PrintFormat("[NEXUS SAFE] Buy non-retryable failure rc=%d", rc);
         return false;
      }
      if(i + 1 >= attempts) break;

      // Un requote si risolve solo con una quotazione nuova: riprovare sullo
      // stesso prezzo produrrebbe lo stesso rifiuto.
      if(!_NXS_WaitQuoteChange(sym, refBid, refAsk, startMs, NXS_ORDER_RETRY_BUDGET_MS)){
         PrintFormat("[NEXUS SAFE] Buy retry abbandonato dopo %dms (rc=%d): "
                     "si riprova al prossimo tick invece di bloccare l'EA",
                     (int)(GetTickCount() - startMs), rc);
         return false;
      }
      PrintFormat("[NEXUS SAFE] Buy retry %d/%d rc=%d (quotazione aggiornata)",
                  i + 1, attempts, rc);
   }
   return false;
}

bool NXS_SafeSell(double volume, string sym, double sl, double tp, string comment){
   int attempts = MathMax(1, InpOrderRetries);
   uint startMs = GetTickCount();
   for(int i = 0; i < attempts; i++){
      double refBid = SymbolInfoDouble(sym, SYMBOL_BID);
      double refAsk = SymbolInfoDouble(sym, SYMBOL_ASK);

      bool ok = NXS_DoSell(volume, sym, sl, tp, comment);
      uint rc = NXS_TradeRetcode();
      if(ok) return true;
      if(!_NXS_IsRetryable(rc)){
         PrintFormat("[NEXUS SAFE] Sell non-retryable failure rc=%d", rc);
         return false;
      }
      if(i + 1 >= attempts) break;

      if(!_NXS_WaitQuoteChange(sym, refBid, refAsk, startMs, NXS_ORDER_RETRY_BUDGET_MS)){
         PrintFormat("[NEXUS SAFE] Sell retry abbandonato dopo %dms (rc=%d): "
                     "si riprova al prossimo tick invece di bloccare l'EA",
                     (int)(GetTickCount() - startMs), rc);
         return false;
      }
      PrintFormat("[NEXUS SAFE] Sell retry %d/%d rc=%d (quotazione aggiornata)",
                  i + 1, attempts, rc);
   }
   return false;
}

#endif
