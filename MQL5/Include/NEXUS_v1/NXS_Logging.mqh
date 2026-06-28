//+------------------------------------------------------------------+
//|  NXS_Logging.mqh - CSV logging                                    |
//+------------------------------------------------------------------+
#ifndef __NXS_LOG_MQH__
#define __NXS_LOG_MQH__

void NXS_LogTradeCSV(string action, ulong ticket, string strat, double price,
                     double lots, double sl, double tp, double score, string reason){
   if(!InpLogTrades) return;
   int h = FileOpen("NEXUS_trades.csv", FILE_WRITE|FILE_READ|FILE_CSV|FILE_COMMON, ',');
   if(h == INVALID_HANDLE) return;
   FileSeek(h, 0, SEEK_END);
   FileWrite(h, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
                action, (long)ticket, strat,
                DoubleToString(price, g_digits),
                DoubleToString(lots, 2),
                DoubleToString(sl, g_digits),
                DoubleToString(tp, g_digits),
                DoubleToString(score, 1),
                reason);
   FileClose(h);
}

#endif
