//+------------------------------------------------------------------+
//| NXS_ExportM15.mq5                                                  |
//| 29/08 - esporta le barre M15 GOLD (CopyRates, dati ufficiali del   |
//| terminale) per simulare la gestione intraday (trailing/timeout/   |
//| max-loss) con la stessa granularita' del motore vero.              |
//|                                                                    |
//| 01/09 - RISCRITTA a costruzione incrementale (OnTick, una barra    |
//| nuova alla volta) invece di un CopyRates in blocco su OnInit: su   |
//| range lontani nel tempo (es. 2023) il CopyRates in blocco fallisce |
//| sempre (err=4401, cronologia non ancora sincronizzata al momento   |
//| esatto di OnInit) anche con centinaia di tentativi - il vero       |
//| motore di trading invece funziona perche' costruisce la sua        |
//| cronologia progressivamente man mano che il tempo simulato avanza, |
//| mai tutta insieme all'istante zero. Stesso principio qui.          |
//+------------------------------------------------------------------+
#property strict
input string   InpSymbol = "GOLD";
input string   InpOutFile= "nxs_m15_gold.csv";

int      fh = INVALID_HANDLE;
datetime lastBar = 0;
long     nWritten = 0;

int OnInit(){
   fh = FileOpen(InpOutFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE){
      PrintFormat("[NXS EXPORT M15] impossibile aprire il file (err=%d)", GetLastError());
      return INIT_FAILED;
   }
   FileWrite(fh, "time", "open", "high", "low", "close");
   return INIT_SUCCEEDED;
}

void OnTick(){
   datetime cur = iTime(InpSymbol, PERIOD_M15, 0);
   if(cur == lastBar || cur == 0) return;
   // barra precedente ora chiusa (shift=1) - scrive quella, non quella in formazione
   if(lastBar != 0){
      double o = iOpen(InpSymbol, PERIOD_M15, 1), h = iHigh(InpSymbol, PERIOD_M15, 1);
      double l = iLow(InpSymbol, PERIOD_M15, 1),  c = iClose(InpSymbol, PERIOD_M15, 1);
      datetime bt = iTime(InpSymbol, PERIOD_M15, 1);
      FileWrite(fh, TimeToString(bt, TIME_DATE|TIME_MINUTES), o, h, l, c);
      nWritten++;
      if(nWritten % 5000 == 0) PrintFormat("[NXS EXPORT M15] progresso: %d barre scritte, ultima=%s", nWritten, TimeToString(bt));
   }
   lastBar = cur;
}

void OnDeinit(const int reason){
   if(fh != INVALID_HANDLE){
      FileClose(fh);
      PrintFormat("[NXS EXPORT M15] COMPLETATO: %d barre scritte su %s", nWritten, InpOutFile);
   }
}
