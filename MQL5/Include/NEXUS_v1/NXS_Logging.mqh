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
// 17/07 sera - da chiamare una volta in OnInit, PRIMA di qualsiasi
// NXS_LogTradeCSV. Se InpResetTradesLogOnInit e' true, archivia il file
// corrente (rinominandolo con un timestamp) cosi' la prossima scrittura di
// NXS_LogTradeCSV lo ricrea vuoto (isNew=true, header riscritto). Non
// cancella mai il contenuto senza archivio: se entrambi i tentativi
// falliscono, lascia il file esistente e continua ad accumulare (senza
// bloccare l'EA), ma stampa un errore esplicito.
//
// 20/10/2026 - Phase 7.35: FileMove senza FILE_REWRITE falliva su alcuni
// Tester Windows con err=5020 (destinazione/path), lasciando il CSV
// diagnostico precedente attaccato al run successivo. Ora: nome archivio
// univoco + FILE_REWRITE + fallback FileCopy+FileDelete.
void NXS_ResetTradesLogIfRequested(){
   if(!InpResetTradesLogOnInit) return;
   if(!FileIsExist("NEXUS_trades.csv", FILE_COMMON)) return;
   string archiveName = "NEXUS_trades_archive_"
                        + TimeToString(TimeLocal(), TIME_DATE|TIME_SECONDS)
                        + "_" + IntegerToString((int)GetTickCount()) + ".csv";
   StringReplace(archiveName, ".", "-");
   StringReplace(archiveName, ":", "-");
   StringReplace(archiveName, " ", "_");
   // Prefer atomic rename with rewrite; FILE_COMMON on both ends.
   ResetLastError();
   if(FileMove("NEXUS_trades.csv", FILE_COMMON, archiveName, FILE_COMMON|FILE_REWRITE)){
      PrintFormat("[NEXUS] NEXUS_trades.csv archiviato come %s, log ripartito vuoto.", archiveName);
      return;
   }
   int moveErr = GetLastError();
   ResetLastError();
   if(FileCopy("NEXUS_trades.csv", FILE_COMMON, archiveName, FILE_COMMON|FILE_REWRITE)){
      if(FileDelete("NEXUS_trades.csv", FILE_COMMON)){
         PrintFormat("[NEXUS] NEXUS_trades.csv copiato+cancellato come %s (FileMove err=%d), log ripartito vuoto.",
                     archiveName, moveErr);
         return;
      }
      PrintFormat("[NEXUS] Reset log: FileCopy ok ma FileDelete fallito (err=%d) dopo FileMove err=%d — accumulo possibile.",
                  GetLastError(), moveErr);
      return;
   }
   PrintFormat("[NEXUS] Reset log fallito: FileMove err=%d FileCopy err=%d — continuo ad accumulare sul file esistente.",
               moveErr, GetLastError());
}

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
