//+------------------------------------------------------------------+
//| NXS_BreakoutAccCadenceDiagnostic.mq5                              |
//| Phase 7.9E - EA standalone READ-ONLY, zero rischio (nessun ordine, |
//| nessuna inclusione di NEXUS_v1, nessuna modifica all'EA live).     |
//|                                                                    |
//| Ipotesi da testare: la valutazione di BREAKOUT_ACC nel router live |
//| (NEXUS_EA_v2.mq5:NXS_CollectAllSignals) e' gated da                |
//| NXS_ActivateTF()->NXS_UpdateIndicators(), che richiede TUTTI e 10  |
//| gli indicatori del pass multi-TF (ADX/RSI/Bollinger/MACD/SAR/ATR/  |
//| EMA200/EMA9/EMA21/Ichimoku) pronti sul TF D1 - anche se             |
//| NXS_Strat_BreakoutAcc() stesso non ne usa NESSUNO (solo             |
//| iHighest/iLowest/iClose). Se questi indicatori "estranei" falliscono|
//| spesso su D1 (un TF ausiliario, non quello del grafico) sotto       |
//| Model=1, l'intero pass D1 verrebbe saltato (skip) per la maggior    |
//| parte dei tick, indipendentemente dalla logica di BREAKOUT_ACC -    |
//| spiegando un gap di cadenza di valutazione, non di logica.          |
//|                                                                    |
//| Replica FEDELMENTE, tick per tick, la stessa cadenza reale:         |
//| New Bar Gate su InpTFEntry=M15 (come OnTick reale), poi tentativo  |
//| di attivazione D1 con gli stessi 10 handle, poi (solo se attivato)  |
//| controllo Acceptance identico a NXS_Strat_BreakoutAcc().            |
//+------------------------------------------------------------------+
#property strict

input string InpFromDate = "2019.02.03";
input string InpToDate   = "2026.08.15";

string   g_sym = "GOLD";
ENUM_TIMEFRAMES g_tfEntry = PERIOD_M15;
ENUM_TIMEFRAMES g_tfD1    = PERIOD_D1;
datetime g_lastM15Bar = 0;

// handle D1 (creati una sola volta, come g_mtf_h* nel router reale)
int h_hADX=INVALID_HANDLE, h_hRSI=INVALID_HANDLE, h_hBB=INVALID_HANDLE, h_hMACD=INVALID_HANDLE,
    h_hSAR=INVALID_HANDLE, h_hATR=INVALID_HANDLE, h_hEMA200=INVALID_HANDLE, h_hEMA9=INVALID_HANDLE,
    h_hEMA21=INVALID_HANDLE, h_hICHI=INVALID_HANDLE;
bool g_handlesCreated = false;

long g_nM15Passes = 0;
long g_nActivationSuccess = 0, g_nActivationFail = 0;
long g_failADX=0, g_failRSI=0, g_failBB=0, g_failMACD=0, g_failSAR=0, g_failATR=0,
     g_failEMA200=0, g_failEMA9=0, g_failEMA21=0, g_failICHI=0;

long g_nNewD1BarAfterSuccess = 0;   // quante volte, DOPO un'attivazione riuscita, curBar0(D1) e' nuovo
datetime g_lastD1BarSeen = 0;

long g_nRawAccept = 0, g_nCooldownPass = 0, g_nHtfPass = 0;
datetime g_lastFireTime[2] = {0, 0};   // [0]=buy [1]=sell, stesso schema del vero g_breakoutAccState
long g_cooldownSec = 8 * 86400;         // InpBreakoutAccCooldownBars default = 8, PeriodSeconds(D1)

int hOut = INVALID_HANDLE;

bool CreateD1Handles(){
   h_hADX  = iADX(g_sym, g_tfD1, 14);
   h_hRSI  = iRSI(g_sym, g_tfD1, 14, PRICE_CLOSE);
   h_hBB   = iBands(g_sym, g_tfD1, 20, 0, 2.0, PRICE_CLOSE);
   h_hMACD = iMACD(g_sym, g_tfD1, 12, 26, 9, PRICE_CLOSE);
   h_hSAR  = iSAR(g_sym, g_tfD1, 0.02, 0.2);
   h_hATR  = iATR(g_sym, g_tfD1, 14);
   h_hEMA200 = iMA(g_sym, g_tfD1, 200, 0, MODE_EMA, PRICE_CLOSE);
   h_hEMA9   = iMA(g_sym, g_tfD1, 9, 0, MODE_EMA, PRICE_CLOSE);
   h_hEMA21  = iMA(g_sym, g_tfD1, 21, 0, MODE_EMA, PRICE_CLOSE);
   h_hICHI   = iIchimoku(g_sym, g_tfD1, 9, 26, 52);
   return (h_hADX!=INVALID_HANDLE && h_hRSI!=INVALID_HANDLE && h_hBB!=INVALID_HANDLE &&
           h_hMACD!=INVALID_HANDLE && h_hSAR!=INVALID_HANDLE && h_hATR!=INVALID_HANDLE &&
           h_hEMA200!=INVALID_HANDLE && h_hEMA9!=INVALID_HANDLE && h_hEMA21!=INVALID_HANDLE &&
           h_hICHI!=INVALID_HANDLE);
}

// Replica ESATTA di NXS_UpdateIndicators() ristretta al pass D1 - stessi 10
// indicatori, stesso shift=1, stesso ordine, stesso fail-fast al primo errore.
bool TryActivateD1(){
   double a[];
   if(CopyBuffer(h_hADX, 0, 1, 1, a) <= 0){ g_failADX++; return false; }
   if(CopyBuffer(h_hADX, 1, 1, 1, a) <= 0){ g_failADX++; return false; }
   if(CopyBuffer(h_hADX, 2, 1, 1, a) <= 0){ g_failADX++; return false; }
   if(CopyBuffer(h_hRSI, 0, 1, 1, a) <= 0){ g_failRSI++; return false; }
   if(CopyBuffer(h_hBB, 1, 1, 1, a) <= 0){ g_failBB++; return false; }
   if(CopyBuffer(h_hBB, 2, 1, 1, a) <= 0){ g_failBB++; return false; }
   if(CopyBuffer(h_hBB, 0, 1, 1, a) <= 0){ g_failBB++; return false; }
   if(CopyBuffer(h_hMACD, 0, 1, 1, a) <= 0){ g_failMACD++; return false; }
   if(CopyBuffer(h_hMACD, 1, 1, 1, a) <= 0){ g_failMACD++; return false; }
   if(CopyBuffer(h_hSAR, 0, 1, 1, a) <= 0){ g_failSAR++; return false; }
   if(CopyBuffer(h_hATR, 0, 1, 1, a) <= 0){ g_failATR++; return false; }
   if(CopyBuffer(h_hEMA200, 0, 1, 1, a) <= 0){ g_failEMA200++; return false; }
   if(CopyBuffer(h_hEMA9, 0, 1, 1, a) <= 0){ g_failEMA9++; return false; }
   if(CopyBuffer(h_hEMA21, 0, 1, 1, a) <= 0){ g_failEMA21++; return false; }
   if(CopyBuffer(h_hICHI, 0, 1, 1, a) <= 0){ g_failICHI++; return false; }
   if(CopyBuffer(h_hICHI, 1, 1, 1, a) <= 0){ g_failICHI++; return false; }
   if(CopyBuffer(h_hICHI, 2, 1, 1, a) <= 0){ g_failICHI++; return false; }
   if(CopyBuffer(h_hICHI, 3, 1, 1, a) <= 0){ g_failICHI++; return false; }
   return true;
}

int OnInit(){
   SymbolSelect(g_sym, true);
   g_handlesCreated = CreateD1Handles();
   if(!g_handlesCreated){
      Print("[CADENCE_DIAG][FATAL] creazione handle D1 fallita, err=", GetLastError());
      return INIT_SUCCEEDED;
   }
   hOut = FileOpen("nxs_breakoutacc_cadence_diag.csv", FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI, ',');
   if(hOut != INVALID_HANDLE)
      FileWrite(hOut, "d1_bar_time,c1,c2,range_hi,range_lo,accept_up,accept_dn,raw_dir,cooldown_ok,"
                      "px200_shift0,ema200_shift1,htf_ok,event");
   return INIT_SUCCEEDED;
}

void OnTick(){
   datetime bt = iTime(g_sym, g_tfEntry, 0);
   if(bt == g_lastM15Bar) return;
   g_lastM15Bar = bt;
   g_nM15Passes++;

   bool activated = TryActivateD1();
   if(!activated){ g_nActivationFail++; return; }
   g_nActivationSuccess++;

   datetime curBar0 = iTime(g_sym, g_tfD1, 0);
   if(curBar0 == g_lastD1BarSeen) return;   // stessa barra D1 gia' vista dopo un'attivazione riuscita
   g_lastD1BarSeen = curBar0;
   g_nNewD1BarAfterSuccess++;

   // --- replica ESATTA della logica di NXS_Strat_BreakoutAcc() ---
   int n = 20;
   int idxHi = iHighest(g_sym, g_tfD1, MODE_HIGH, n, 3);
   int idxLo = iLowest(g_sym, g_tfD1, MODE_LOW, n, 3);
   if(idxHi < 0 || idxLo < 0) return;
   double range_hi = iHigh(g_sym, g_tfD1, idxHi);
   double range_lo = iLow(g_sym, g_tfD1, idxLo);
   double c1 = iClose(g_sym, g_tfD1, 1);
   double c2 = iClose(g_sym, g_tfD1, 2);
   bool acceptUp = (c1 > range_hi && c2 > range_hi);
   bool acceptDn = (c1 < range_lo && c2 < range_lo);
   int rawDir = acceptUp ? 1 : (acceptDn ? -1 : 0);

   string ev = "NO_ACCEPTANCE";
   bool cooldownOk = true, htfOk = true;
   double px200 = 0, ema200 = 0;
   if(rawDir != 0){
      g_nRawAccept++;
      int dirIdx = (rawDir == 1) ? 0 : 1;
      cooldownOk = (g_lastFireTime[dirIdx] == 0) || ((curBar0 - g_lastFireTime[dirIdx]) >= g_cooldownSec);
      if(cooldownOk){
         g_nCooldownPass++;
         g_lastFireTime[dirIdx] = curBar0;
         ev = "RAW_ACCEPT_COOLDOWN_PASS";

         // --- replica ESATTA del gate HTF del router (NEXUS_EA_v2.mq5:634-646):
         // px200 = iClose(EffTF, shift0) - la barra D1 ANCORA IN FORMAZIONE al
         // momento della valutazione, NON la chiusura confermata (c1/shift1)
         // usata dagli script offline precedenti (7.9C) - differenza reale,
         // MAI testata empiricamente prima di questo esperimento.
         px200 = iClose(g_sym, g_tfD1, 0);
         double emaBuf[];
         if(CopyBuffer(h_hEMA200, 0, 1, 1, emaBuf) > 0) ema200 = emaBuf[0];
         if(ema200 > 0){
            if(rawDir == 1 && px200 < ema200) htfOk = false;
            if(rawDir == -1 && px200 > ema200) htfOk = false;
         }
         if(htfOk){ g_nHtfPass++; ev = "FINAL_SIGNAL_FIRE"; }
         else ev = "RAW_ACCEPT_COOLDOWN_PASS_HTF_BLOCKED";
      } else {
         ev = "RAW_ACCEPT_COOLDOWN_BLOCKED";
      }
   }
   if(hOut != INVALID_HANDLE)
      FileWrite(hOut, TimeToString(curBar0, TIME_DATE), DoubleToString(c1,2), DoubleToString(c2,2),
                DoubleToString(range_hi,2), DoubleToString(range_lo,2),
                acceptUp?"1":"0", acceptDn?"1":"0", IntegerToString(rawDir),
                cooldownOk?"1":"0", DoubleToString(px200,2), DoubleToString(ema200,2),
                htfOk?"1":"0", ev);
}

void OnDeinit(const int reason){
   if(hOut != INVALID_HANDLE) FileClose(hOut);
   int hSum = FileOpen("nxs_breakoutacc_cadence_diag_summary.txt", FILE_WRITE|FILE_TXT|FILE_COMMON);
   if(hSum != INVALID_HANDLE){
      FileWrite(hSum, "handles_created=" + (g_handlesCreated ? "1" : "0"));
      FileWrite(hSum, "n_m15_passes=" + IntegerToString(g_nM15Passes));
      FileWrite(hSum, "n_activation_success=" + IntegerToString(g_nActivationSuccess));
      FileWrite(hSum, "n_activation_fail=" + IntegerToString(g_nActivationFail));
      FileWrite(hSum, "fail_ADX=" + IntegerToString(g_failADX));
      FileWrite(hSum, "fail_RSI=" + IntegerToString(g_failRSI));
      FileWrite(hSum, "fail_BB=" + IntegerToString(g_failBB));
      FileWrite(hSum, "fail_MACD=" + IntegerToString(g_failMACD));
      FileWrite(hSum, "fail_SAR=" + IntegerToString(g_failSAR));
      FileWrite(hSum, "fail_ATR=" + IntegerToString(g_failATR));
      FileWrite(hSum, "fail_EMA200=" + IntegerToString(g_failEMA200));
      FileWrite(hSum, "fail_EMA9=" + IntegerToString(g_failEMA9));
      FileWrite(hSum, "fail_EMA21=" + IntegerToString(g_failEMA21));
      FileWrite(hSum, "fail_ICHI=" + IntegerToString(g_failICHI));
      FileWrite(hSum, "n_new_d1_bar_after_success=" + IntegerToString(g_nNewD1BarAfterSuccess));
      FileWrite(hSum, "n_raw_accept=" + IntegerToString(g_nRawAccept));
      FileWrite(hSum, "n_cooldown_pass=" + IntegerToString(g_nCooldownPass));
      FileWrite(hSum, "n_htf_pass=" + IntegerToString(g_nHtfPass));
      FileClose(hSum);
   }
   PrintFormat("[CADENCE_DIAG][SUMMARY] m15_passes=%d activation_success=%d activation_fail=%d "
               "new_d1_bar_after_success=%d raw_accept=%d cooldown_pass=%d htf_pass=%d",
               g_nM15Passes, g_nActivationSuccess, g_nActivationFail,
               g_nNewD1BarAfterSuccess, g_nRawAccept, g_nCooldownPass, g_nHtfPass);
}
