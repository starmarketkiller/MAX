//+------------------------------------------------------------------+
//| NXS_ImportDukascopyCustomSymbol.mq5                                 |
//| Phase 5 (task L) - "SAR vs XM" independent Dukascopy validation.    |
//|                                                                      |
//| Standalone, headless MQL5 Script (no NEXUS_v1 includes, no trading  |
//| logic). Creates a Custom Symbol and programmatically imports the    |
//| already phase4-validated Dukascopy XAUUSD tick history into it via  |
//| CustomSymbolCreate()/CustomTicksAdd() - NO manual GUI "Import ticks"|
//| wizard step is used or required.                                    |
//|                                                                      |
//| Input data: binary .bin files produced by                           |
//| server/research_scripts/convert_dukascopy_for_mt5_import.py, one     |
//| per day, fixed 24-byte records {long epoch_ms; double bid; double   |
//| ask;} (epoch_ms already shifted by InpServerGMTOffset hours so the  |
//| resulting H4 bars land on the same wall-clock grid NEXUS's own H4   |
//| bars use elsewhere - see the conversion script's docstring and the  |
//| final report for the full reasoning), plus an index.csv listing     |
//| date,n_ticks,epoch_first_ms_shifted,epoch_last_ms_shifted,rel_path. |
//|                                                                      |
//| Run headlessly via a /config ini with:                              |
//|   [StartUp]                                                          |
//|   Symbol=GOLD                                                        |
//|   Period=H4                                                          |
//|   Script=NXS_ImportDukascopyCustomSymbol                             |
//|   ScriptParameters=                                                  |
//| (confirmed empirically in this session: [StartUp] Script= runs with |
//| zero GUI interaction, PROVIDED the compiled .ex5 sits in the MQL5\  |
//| Scripts folder of the terminal's REAL data folder - i.e. the one     |
//| named in that terminal's own logs\*.log "Terminal" line, which for   |
//| a non-portable install is %APPDATA%\MetaQuotes\Terminal\<hash>\, NOT |
//| necessarily the folder terminal64.exe/MetaEditor64.exe live in - a   |
//| copy dropped only in the install folder is silently ignored: MT5     |
//| logs "expert/script '...' not found from start config" and does      |
//| nothing else, with no dialog and no crash).                          |
//|                                                                      |
//| Writes progress/result markers to MQL5/Files (this symbol's data     |
//| folder), NOT Common, since it's single-terminal, single-run:         |
//|   nxs_duka_import_progress.txt  - appended once per day processed    |
//|   nxs_duka_import_done.txt      - written once at the very end, is   |
//|                                    the single completion signal an    |
//|                                    external watcher should poll for  |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs

input string InpCustomSymbolName = "XAUUSD_DSC";           // custom symbol to create/fill
input string InpOriginSymbol     = "GOLD";                 // real symbol to copy point/digits/tick_value/contract_size from
input string InpCustomGroupPath  = "Custom\\Dukascopy";    // Market Watch group/path for the new symbol
input string InpIndexFile        = "dukascopy\\index.csv"; // relative to MQL5\Files
input string InpBinSubdir        = "dukascopy\\";          // relative to MQL5\Files, prefix for rel_path entries in the index
input string InpDescription      = "XAUUSD Dukascopy real ticks (Phase4-validated, 2019-02-03..2022-02-03) - independent SAR validation";
input bool   InpResetExistingTicks = true;                 // if the symbol already has tick history, wipe it first (CustomTicksDelete over the full range) for a clean, reproducible import
input string InpSpotCheckDate     = "2019-02-04";           // one sample day used for the post-import CopyTicksRange tick-count parity check (must exist in the index)

#define DUKA_RECORD_SIZE 24

struct DukaTick{
   long   epoch_ms;   // already shifted to NEXUS "server time" convention by the Python converter
   double bid;
   double ask;
};

//+------------------------------------------------------------------+
void WriteProgress(const string msg, bool append=true){
   int flags = FILE_WRITE|FILE_TXT|FILE_READ;
   int h;
   if(append && FileIsExist("nxs_duka_import_progress.txt"))
      h = FileOpen("nxs_duka_import_progress.txt", FILE_WRITE|FILE_TXT|FILE_READ);
   else
      h = FileOpen("nxs_duka_import_progress.txt", FILE_WRITE|FILE_TXT);
   if(h == INVALID_HANDLE){ Print("[DUKAIMPORT] impossibile aprire progress file, err=", GetLastError()); return; }
   if(append) FileSeek(h, 0, SEEK_END);
   FileWrite(h, TimeToString(TimeLocal(), TIME_DATE|TIME_SECONDS) + "  " + msg);
   FileClose(h);
   Print("[DUKAIMPORT] ", msg);
}

//+------------------------------------------------------------------+
void OnStart(){
   ulong t0 = GetTickCount64();
   WriteProgress("=== NXS_ImportDukascopyCustomSymbol avviato ===", false);
   WriteProgress(StringFormat("symbol=%s origin=%s index=%s", InpCustomSymbolName, InpOriginSymbol, InpIndexFile));

   // --- 1. crea (o riusa) il simbolo personalizzato -------------------
   bool already = SymbolSelect(InpCustomSymbolName, false); // false = non aggiungere, solo verificare esistenza in elenco completo
   bool exists = (bool)SymbolInfoInteger(InpCustomSymbolName, SYMBOL_CUSTOM);
   if(!exists){
      if(!CustomSymbolCreate(InpCustomSymbolName, InpCustomGroupPath, InpOriginSymbol)){
         WriteProgress(StringFormat("ERRORE FATALE: CustomSymbolCreate fallita err=%d", GetLastError()));
         return;
      }
      WriteProgress("CustomSymbolCreate OK (nuovo simbolo, proprieta' copiate da " + InpOriginSymbol + ")");
   } else {
      WriteProgress("Simbolo personalizzato gia' esistente, riuso.");
   }
   CustomSymbolSetString(InpCustomSymbolName, SYMBOL_DESCRIPTION, InpDescription);
   SymbolSelect(InpCustomSymbolName, true);

   if(InpResetExistingTicks){
      datetime wideFrom = D'2000.01.01';
      datetime wideTo   = D'2035.01.01';
      int delRes = CustomTicksDelete(InpCustomSymbolName, wideFrom, wideTo);
      WriteProgress(StringFormat("CustomTicksDelete pre-import: risultato=%d (pulizia storico precedente)", delRes));
   }

   // --- 2. leggi index.csv ---------------------------------------------
   int hIdx = FileOpen(InpIndexFile, FILE_READ|FILE_CSV|FILE_ANSI, ',');
   if(hIdx == INVALID_HANDLE){
      WriteProgress(StringFormat("ERRORE FATALE: impossibile aprire index file '%s' err=%d", InpIndexFile, GetLastError()));
      return;
   }
   // header
   string h0=FileReadString(hIdx), h1=FileReadString(hIdx), h2=FileReadString(hIdx), h3=FileReadString(hIdx), h4=FileReadString(hIdx);
   WriteProgress(StringFormat("index header: %s,%s,%s,%s,%s", h0,h1,h2,h3,h4));

   long totalTicksAdded = 0;
   int  totalDays = 0;
   int  totalErrors = 0;
   string firstDate="", lastDate="";
   long spotExpected=-1, spotEpochFirst=0, spotEpochLast=0;

   while(!FileIsEnding(hIdx)){
      string dateStr   = FileReadString(hIdx);
      if(StringLen(dateStr) == 0) break;
      long   nTicksExp = (long)FileReadNumber(hIdx);
      long   epochFirst= (long)FileReadNumber(hIdx);
      long   epochLast = (long)FileReadNumber(hIdx);
      string relPath   = FileReadString(hIdx);

      if(dateStr == InpSpotCheckDate){
         spotExpected = nTicksExp;
         spotEpochFirst = epochFirst;
         spotEpochLast = epochLast;
      }

      string binPath = InpBinSubdir + relPath;
      int hBin = FileOpen(binPath, FILE_READ|FILE_BIN);
      if(hBin == INVALID_HANDLE){
         WriteProgress(StringFormat("ERRORE giorno %s: impossibile aprire '%s' err=%d - SALTATO", dateStr, binPath, GetLastError()));
         totalErrors++;
         continue;
      }

      ulong fsize = FileSize(hBin);
      long  nRecords = (long)(fsize / DUKA_RECORD_SIZE);
      if(nRecords != nTicksExp){
         WriteProgress(StringFormat("ATTENZIONE giorno %s: index dice %d tick ma file ha %d record (dim=%d byte)", dateStr, nTicksExp, nRecords, fsize));
      }

      MqlTick arr[];
      ArrayResize(arr, (int)nRecords);
      for(long i=0; i<nRecords; i++){
         long   em  = FileReadLong(hBin);
         double bid = FileReadDouble(hBin);
         double ask = FileReadDouble(hBin);
         arr[i].time      = (datetime)(em/1000);
         arr[i].time_msc  = em;
         arr[i].bid       = bid;
         arr[i].ask       = ask;
         arr[i].last      = 0;
         arr[i].volume    = 0;
         arr[i].volume_real = 0;
         arr[i].flags     = TICK_FLAG_BID|TICK_FLAG_ASK;
      }
      FileClose(hBin);

      int added = CustomTicksAdd(InpCustomSymbolName, arr);
      if(added < 0){
         WriteProgress(StringFormat("ERRORE giorno %s: CustomTicksAdd fallita err=%d (record letti=%d)", dateStr, GetLastError(), nRecords));
         totalErrors++;
      } else {
         totalTicksAdded += added;
         totalDays++;
         if(firstDate=="") firstDate=dateStr;
         lastDate=dateStr;
         if(totalDays % 50 == 0)
            WriteProgress(StringFormat("progresso: %d giorni, %d tick totali finora (ultimo=%s, aggiunti oggi=%d)", totalDays, totalTicksAdded, dateStr, added));
      }
   }
   FileClose(hIdx);

   SymbolSelect(InpCustomSymbolName, true);
   ulong elapsedSec = (GetTickCount64()-t0)/1000;

   WriteProgress(StringFormat("=== IMPORT COMPLETATO: %d giorni, %d tick aggiunti, %d errori, range %s..%s, %d sec ===",
                 totalDays, totalTicksAdded, totalErrors, firstDate, lastDate, elapsedSec));

   // --- 3. verifica A: CopyTicksRange parity per il giorno campione -----
   long spotActual = -1;
   if(spotExpected >= 0){
      MqlTick spotArr[];
      // finestra leggermente allargata per non tagliare il primo/ultimo tick per arrotondamenti
      int got = CopyTicksRange(InpCustomSymbolName, spotArr, COPY_TICKS_ALL, (ulong)(spotEpochFirst-1000), (ulong)(spotEpochLast+1000));
      spotActual = got;
      WriteProgress(StringFormat("SPOT-CHECK tick %s: atteso=%d (da index/manifest phaseH) ottenuto_da_CopyTicksRange=%d", InpSpotCheckDate, spotExpected, got));
   } else {
      WriteProgress(StringFormat("SPOT-CHECK tick: data campione '%s' non trovata nell'index - saltato", InpSpotCheckDate));
   }

   // --- 4. verifica B: allineamento barre H4 sulla griglia server-time --
   string barCheckMsg = "";
   MqlRates rates[];
   int nBars = CopyRates(InpCustomSymbolName, PERIOD_H4, 0, 10, rates);
   if(nBars > 0){
      barCheckMsg = StringFormat("H4 bars disponibili dopo import: %d. Prime barre (server-time label, dovrebbero cadere su multipli di 4h):", nBars);
      WriteProgress(barCheckMsg);
      for(int i=0;i<nBars;i++){
         datetime bt = rates[i].time;
         MqlDateTime dtStruct;
         TimeToStruct(bt, dtStruct);
         bool onGrid = (dtStruct.hour % 4 == 0) && (dtStruct.min==0) && (dtStruct.sec==0);
         WriteProgress(StringFormat("  bar[%d] time=%s hour=%d onGrid4h=%s o=%.3f h=%.3f l=%.3f c=%.3f",
                       i, TimeToString(bt, TIME_DATE|TIME_MINUTES|TIME_SECONDS), dtStruct.hour, (onGrid?"true":"false"),
                       rates[i].open, rates[i].high, rates[i].low, rates[i].close));
      }
   } else {
      WriteProgress(StringFormat("ATTENZIONE: CopyRates H4 post-import ha restituito 0 barre (err=%d) - impossibile verificare l'allineamento", GetLastError()));
   }

   int hDone = FileOpen("nxs_duka_import_done.txt", FILE_WRITE|FILE_TXT);
   if(hDone != INVALID_HANDLE){
      FileWrite(hDone, "DUKA_IMPORT_DONE");
      FileWrite(hDone, "symbol=" + InpCustomSymbolName);
      FileWrite(hDone, "days=" + IntegerToString(totalDays));
      FileWrite(hDone, "ticks_added=" + IntegerToString(totalTicksAdded));
      FileWrite(hDone, "errors=" + IntegerToString(totalErrors));
      FileWrite(hDone, "first_date=" + firstDate);
      FileWrite(hDone, "last_date=" + lastDate);
      FileWrite(hDone, "elapsed_sec=" + IntegerToString((int)elapsedSec));
      FileWrite(hDone, "spot_check_date=" + InpSpotCheckDate);
      FileWrite(hDone, "spot_check_expected_ticks=" + IntegerToString((int)spotExpected));
      FileWrite(hDone, "spot_check_actual_ticks_CopyTicksRange=" + IntegerToString((int)spotActual));
      FileWrite(hDone, "h4_bars_available=" + IntegerToString(nBars));
      FileClose(hDone);
   }
}
