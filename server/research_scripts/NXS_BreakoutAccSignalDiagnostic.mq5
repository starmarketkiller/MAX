//+------------------------------------------------------------------+
//| NXS_BreakoutAccSignalDiagnostic.mq5                               |
//| Phase 7.9C - script READ-ONLY. Nessun trading, nessun include     |
//| NEXUS_v1, nessuna modifica alla strategia. Replica bar-per-bar    |
//| (usando funzioni native MT5 su barre storiche REALI della cache   |
//| del terminale, NESSUN Tester) la logica esatta di                 |
//| NXS_Strat_BreakoutAcc() + il gate HTF nativo (NEXUS_EA_v2.mq5     |
//| righe ~631-646), verificata riga per riga contro il sorgente      |
//| reale. Registra SIGNAL_GENERATED/SIGNAL_BLOCKED_COOLDOWN/         |
//| SIGNAL_BLOCKED_HTF/SIGNAL_FIRE per ogni barra, non solo i trade    |
//| eventualmente eseguiti - nessun P&L calcolato o letto.            |
//+------------------------------------------------------------------+
#property strict

input string InpFromDate = "2019.02.03";
input string InpToDate   = "2026.08.14";

void OnStart(){
   string sym = "GOLD";
   ENUM_TIMEFRAMES tf = PERIOD_D1;
   datetime fromT = StringToTime(InpFromDate);
   datetime toT   = StringToTime(InpToDate);

   MqlRates rates[];
   int nBars = CopyRates(sym, tf, fromT, toT, rates);
   if(nBars <= 0){
      Print("[DIAG][FATAL] CopyRates failed, err=", GetLastError());
      return;
   }
   // rates[] e' ordinato ASCENDENTE per tempo (indice 0 = piu' vecchio).
   // "n=20, offset shift=3" della logica reale, tradotto in indici ASCENDENTI:
   // per la barra i (appena chiusa, equivalente a "shift1" nel vivo), il range
   // usa le 20 barre [i-21 .. i-2] (stesso calcolo verificato identico anche
   // nella porting Python: c[i-n-1:i-1]).
   int hEMA200 = iMA(sym, tf, 200, 0, MODE_EMA, PRICE_CLOSE);
   if(hEMA200 == INVALID_HANDLE){
      Print("[DIAG][FATAL] iMA EMA200 handle invalid, err=", GetLastError());
      return;
   }

   int hOut = FileOpen("nxs_breakoutacc_mt5_signal_stream.csv", FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI, ',');
   if(hOut == INVALID_HANDLE){
      Print("[DIAG][FATAL] FileOpen failed, err=", GetLastError());
      return;
   }
   FileWrite(hOut, "bar_time,c1,c2,range_hi,range_lo,accept_up,accept_dn,raw_dir,"
                   "cooldown_ok,ema200_at_signal,price_proxy,htf_ok,final_dir,final_reason");

   datetime lastFireTime[2] = {0, 0};  // [0]=buy [1]=sell, stesso schema di g_breakoutAccState
   long cooldownSec = (long)8 * 86400; // InpBreakoutAccCooldownBars=8 * PeriodSeconds(D1)
   int nSignalsGenerated = 0, nBlockedCooldown = 0, nBlockedHTF = 0, nFinalFire = 0;

   // n=20 barre, offset shift3 -> servono almeno 22 barre precedenti + EMA200 stabile.
   for(int i = 21; i < nBars - 1; i++){   // i-1 esiste sempre (c2), i+1 usato come "prossima barra" per bar_time del segnale
      double range_hi = -DBL_MAX, range_lo = DBL_MAX;
      for(int k = i - 21; k <= i - 2; k++){
         if(rates[k].high > range_hi) range_hi = rates[k].high;
         if(rates[k].low  < range_lo) range_lo = rates[k].low;
      }
      double c1 = rates[i].close;
      double c2 = rates[i-1].close;
      bool acceptUp = (c1 > range_hi && c2 > range_hi);
      bool acceptDn = (c1 < range_lo && c2 < range_lo);
      int rawDir = 0;
      if(acceptUp) rawDir = 1;
      else if(acceptDn) rawDir = -1;
      if(rawDir == 0) continue;

      nSignalsGenerated++;
      // curBar0 equivalente storicamente = tempo della barra i+1 (quella che si
      // "apre" subito dopo la conferma su i) - stesso riferimento usato dal
      // vero g_breakoutAccState.lastFireTime nel codice live.
      datetime curBar0 = rates[i+1].time;
      int dirIdx = (rawDir == 1) ? 0 : 1;
      bool cooldownOk = (lastFireTime[dirIdx] == 0) || ((long)(curBar0 - lastFireTime[dirIdx]) >= cooldownSec);
      if(!cooldownOk){
         nBlockedCooldown++;
         FileWrite(hOut, TimeToString(curBar0, TIME_DATE), DoubleToString(c1,2), DoubleToString(c2,2),
                    DoubleToString(range_hi,2), DoubleToString(range_lo,2),
                    acceptUp?"1":"0", acceptDn?"1":"0", IntegerToString(rawDir),
                    "0", "", "", "", "0", "BLOCKED_COOLDOWN");
         continue;
      }

      // EMA200 letta al buffer-shift corrispondente alla barra i (CopyBuffer
      // conta da shift0=piu' recente; converto l'indice ascendente i in shift
      // rispetto all'ultima barra del set caricato).
      int shiftFromEnd = (nBars - 1) - i;
      double emaBuf[];
      double emaVal = 0;
      if(CopyBuffer(hEMA200, 0, shiftFromEnd, 1, emaBuf) > 0) emaVal = emaBuf[0];
      // price proxy = close della barra segnale stessa (c1) - STESSA convenzione
      // usata nel porting Python (htf_native_ema, commento 16/09: "proxy dello
      // shift0 candela in formazione"), applicata simmetricamente qui per
      // isolare le differenze reali fra i due motori, non un artefatto di
      // convenzione diversa fra i due lati di questo confronto.
      double priceProxy = c1;
      bool htfOk = true;
      if(emaVal > 0){
         if(rawDir == 1 && priceProxy < emaVal) htfOk = false;
         if(rawDir == -1 && priceProxy > emaVal) htfOk = false;
      }
      if(!htfOk){
         nBlockedHTF++;
         FileWrite(hOut, TimeToString(curBar0, TIME_DATE), DoubleToString(c1,2), DoubleToString(c2,2),
                    DoubleToString(range_hi,2), DoubleToString(range_lo,2),
                    acceptUp?"1":"0", acceptDn?"1":"0", IntegerToString(rawDir),
                    "1", DoubleToString(emaVal,2), DoubleToString(priceProxy,2), "0", "0", "BLOCKED_HTF");
         continue;
      }

      lastFireTime[dirIdx] = curBar0;
      nFinalFire++;
      FileWrite(hOut, TimeToString(curBar0, TIME_DATE), DoubleToString(c1,2), DoubleToString(c2,2),
                 DoubleToString(range_hi,2), DoubleToString(range_lo,2),
                 acceptUp?"1":"0", acceptDn?"1":"0", IntegerToString(rawDir),
                 "1", DoubleToString(emaVal,2), DoubleToString(priceProxy,2), "1", IntegerToString(rawDir), "SIGNAL_FIRE");
   }
   FileClose(hOut);

   int hSum = FileOpen("nxs_breakoutacc_mt5_signal_summary.txt", FILE_WRITE|FILE_TXT|FILE_COMMON);
   if(hSum != INVALID_HANDLE){
      FileWrite(hSum, "symbol=" + sym);
      FileWrite(hSum, "period=" + InpFromDate + " to " + InpToDate);
      FileWrite(hSum, "n_bars_loaded=" + IntegerToString(nBars));
      FileWrite(hSum, "n_signals_raw_generated=" + IntegerToString(nSignalsGenerated));
      FileWrite(hSum, "n_blocked_cooldown=" + IntegerToString(nBlockedCooldown));
      FileWrite(hSum, "n_blocked_htf=" + IntegerToString(nBlockedHTF));
      FileWrite(hSum, "n_final_fire=" + IntegerToString(nFinalFire));
      FileClose(hSum);
   }
   int hDone = FileOpen("nxs_breakoutacc_mt5_signal_done.txt", FILE_WRITE|FILE_TXT|FILE_COMMON);
   if(hDone != INVALID_HANDLE){
      FileWrite(hDone, "done=1");
      FileClose(hDone);
   }
   IndicatorRelease(hEMA200);
}
