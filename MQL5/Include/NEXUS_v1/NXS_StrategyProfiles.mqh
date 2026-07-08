//+------------------------------------------------------------------+
//|  NXS_StrategyProfiles.mqh - Profili PER-STRATEGIA dal backtest    |
//|                                                                    |
//|  "L'EA deve operare come nel backtest": ogni strategia usa i SUOI  |
//|  parametri (ATR SL/TP) e i SUOI gate, non quelli globali. I valori |
//|  vengono dall'ottimizzazione per-strategia su dati reali (XAUUSD   |
//|  D1, results/best_per_strategy_XAUUSD_D1.json).                    |
//|                                                                    |
//|  Dietro InpUseStrategyProfiles. Se una strategia non ha profilo,   |
//|  restano i valori globali (retrocompatibile).                      |
//+------------------------------------------------------------------+
#ifndef __NXS_STRATEGY_PROFILES_MQH__
#define __NXS_STRATEGY_PROFILES_MQH__

// Ritorna true se la strategia ha un profilo dal backtest, riempiendo i suoi
// parametri: slMult/tpMult (x ATR), htf (richiede allineamento HTF), beR
// (breakeven a beR x rischio, 0=off), trailATR (trailing a trailATR x ATR, 0=off).
bool NXS_Profile_Get(const string name, double &slMult, double &tpMult,
                     bool &htf, double &beR, double &trailATR){
   slMult = 0; tpMult = 0; htf = false; beR = 0; trailATR = 0;
   // --- Ricetta ottimale per-strategia (XAUUSD D1, dati reali) ---
   if(name == "ADX_RSI")       { slMult=1.0; tpMult=3.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // OK   PF1.37
   if(name == "BB_SQUEEZE")    { slMult=1.0; tpMult=5.5; htf=false; beR=1.5; trailATR=0.0; return true; }  // thin PF5.21
   if(name == "BJORGUM")       { slMult=1.5; tpMult=3.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // FORTE PF2.59
   if(name == "BOLLINGER")     { slMult=2.6; tpMult=2.8; htf=true;  beR=0.0; trailATR=2.5; return true; }  // FORTE PF2.07
   if(name == "BREAKOUT_ACC")  { slMult=1.0; tpMult=5.5; htf=true;  beR=0.0; trailATR=2.5; return true; }  // FORTE PF2.03
   if(name == "CISD")          { slMult=1.5; tpMult=2.0; htf=true;  beR=0.0; trailATR=0.0; return true; }  // FORTE PF1.76
   if(name == "DISP_REBAL")    { slMult=2.6; tpMult=3.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // thin
   if(name == "EMA_PULLBACK")  { slMult=1.2; tpMult=5.5; htf=true;  beR=1.0; trailATR=0.0; return true; }  // FORTE PF2.14
   if(name == "FVG_CONT")      { slMult=1.0; tpMult=3.5; htf=true;  beR=0.0; trailATR=2.5; return true; }  // FORTE PF1.68
   if(name == "FVG_MIT")       { slMult=1.2; tpMult=5.5; htf=true;  beR=0.0; trailATR=0.0; return true; }  // FORTE PF2.39
   if(name == "ICHIMOKU")      { slMult=1.5; tpMult=5.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // FORTE PF1.79
   if(name == "IFVG")          { slMult=1.2; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // OK   PF1.46
   if(name == "LIQ_SWEEP")     { slMult=1.0; tpMult=2.8; htf=true;  beR=0.0; trailATR=0.0; return true; }  // FORTE PF3.11
   if(name == "LIQ_VOID")      { slMult=1.0; tpMult=3.5; htf=true;  beR=0.0; trailATR=2.5; return true; }  // FORTE PF1.68
   if(name == "LONDON_BO")     { slMult=1.0; tpMult=5.5; htf=true;  beR=0.0; trailATR=2.5; return true; }  // FORTE PF2.03
   if(name == "MACD")          { slMult=1.2; tpMult=5.5; htf=true;  beR=0.0; trailATR=2.5; return true; }  // FORTE PF1.61
   if(name == "MALAYSIAN_SNR") { slMult=1.8; tpMult=5.5; htf=true;  beR=0.0; trailATR=0.0; return true; }  // FORTE PF1.79
   if(name == "OB_MIT")        { slMult=1.2; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // FORTE PF1.90
   if(name == "ORDER_BLOCK")   { slMult=1.2; tpMult=4.5; htf=false; beR=0.0; trailATR=2.5; return true; }  // FORTE PF1.65
   if(name == "OTE_CONT")      { slMult=1.2; tpMult=2.8; htf=false; beR=0.0; trailATR=0.0; return true; }  // FORTE PF1.90
   if(name == "RANGE_FADE")    { slMult=2.6; tpMult=2.8; htf=true;  beR=0.0; trailATR=2.5; return true; }  // FORTE PF2.07
   if(name == "RSI_DIV")       { slMult=1.0; tpMult=3.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // DEBOLE PF1.11
   if(name == "SAR")           { slMult=1.2; tpMult=5.5; htf=true;  beR=1.0; trailATR=0.0; return true; }  // FORTE PF2.14
   if(name == "SH_BMS_RTO")    { slMult=1.2; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // FORTE PF1.90
   if(name == "SMS_BMS_RTO")   { slMult=1.2; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // FORTE PF1.90
   if(name == "STRUCT_REACT")  { slMult=2.2; tpMult=5.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // CRITICA (vedi Enabled)
   if(name == "TSI")           { slMult=1.0; tpMult=3.5; htf=true;  beR=0.0; trailATR=0.0; return true; }  // FORTE PF1.57
   if(name == "TURTLE_SOUP")   { slMult=1.0; tpMult=2.8; htf=true;  beR=0.0; trailATR=0.0; return true; }  // FORTE PF2.77
   if(name == "WEEKLY_EXP")    { slMult=1.0; tpMult=5.5; htf=true;  beR=0.0; trailATR=2.5; return true; }  // FORTE PF2.03
   // Le session/Elliott (SILVER_BULLET, AMD_*, JUDAS, LDN/NY_REVERSAL, PO3,
   // ELLIOTT): da ottimizzare su MT5/intraday -> nessun profilo, usano i globali.
   return false;
}

// Solo SL/TP (per NXS_DefaultSLTP). Ritorna true se c'e' il profilo.
bool NXS_Profile_SLTP(const string name, double &slMult, double &tpMult){
   bool htf; double beR, trailATR;
   return NXS_Profile_Get(name, slMult, tpMult, htf, beR, trailATR);
}

// Gate HTF per la strategia. hasProfile=true se ha profilo; htf=valore richiesto.
bool NXS_Profile_HTF(const string name, bool &htf){
   double sl, tp, be, tr; bool h;
   if(NXS_Profile_Get(name, sl, tp, h, be, tr)){ htf = h; return true; }
   htf = false; return false;
}

// Va tradata? false per le strategie che nel backtest PERDONO o hanno dati
// insufficienti -> "operare come nel backtest" = non aprire quelle inutili.
bool NXS_Profile_Enabled(const string name){
   if(name == "STRUCT_REACT") return false;   // CRITICA (PF 0.74)
   if(name == "DISP_REBAL")   return false;   // dati insufficienti (2 trade)
   if(name == "BB_SQUEEZE")   return false;   // dati insufficienti (5 trade)
   return true;
}

#endif
