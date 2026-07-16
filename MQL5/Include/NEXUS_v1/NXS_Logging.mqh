//+------------------------------------------------------------------+
//|  NXS_Logging.mqh - CSV logging                                    |
//+------------------------------------------------------------------+
#ifndef __NXS_LOG_MQH__
#define __NXS_LOG_MQH__

// 17/07 - estesa dopo l'audit "il CSV ha tutto quello che serve?": mancavano
// header (colonne posizionali senza nome), un ticket affidabile per il join
// OPEN->CLOSE (era sempre 0 in apertura), e soprattutto nessun modo di
// vedere QUALE timeframe risolto veniva usato per lo scaling di durata/vita
// di una posizione - la colonna resolved_tf esiste apposta: se questo campo
// fosse gia' esistito, il bug della tabella NXS_StrategySourceTF disallineata
// (vedi vault NEXUS EA - Caccia al Bug Esecuzione) si sarebbe visto in 30
// secondi guardando il CSV, invece di un'ora di lettura di codice.
void NXS_LogTradeCSV(string action, ulong ticket, string strat, double price,
                     double lots, double sl, double tp, double score, string reason,
                     double holdSec = 0, double rMultiple = 0, string resolvedTF = ""){
   if(!InpLogTrades) return;
   int h = FileOpen("NEXUS_trades.csv", FILE_WRITE|FILE_READ|FILE_CSV|FILE_COMMON, ',');
   if(h == INVALID_HANDLE) return;
   bool isNew = (FileSize(h) == 0);
   FileSeek(h, 0, SEEK_END);
   if(isNew){
      FileWrite(h, "time", "action", "ticket", "strategy", "price", "lots", "sl", "tp",
                   "score_or_pnl", "reason", "hold_sec", "r_multiple", "resolved_tf");
   }
   FileWrite(h, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
                action, (long)ticket, strat,
                DoubleToString(price, g_digits),
                DoubleToString(lots, 2),
                DoubleToString(sl, g_digits),
                DoubleToString(tp, g_digits),
                DoubleToString(score, 1),
                reason,
                DoubleToString(holdSec, 0),
                DoubleToString(rMultiple, 3),
                resolvedTF);
   FileClose(h);
}

#endif
