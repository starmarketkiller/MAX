//+------------------------------------------------------------------+
//|  NXS_StrategyProfiles.mqh - Profili PER-STRATEGIA dal backtest    |
//|                                                                    |
//|  "L'EA deve operare come nel backtest": ogni strategia usa i SUOI  |
//|  parametri (ATR SL/TP), i SUOI gate, il SUO timeframe e il SUO     |
//|  rischio. I valori vengono dall'ottimizzazione MULTI-TIMEFRAME per |
//|  strategia su dati reali (XAUUSD, D1/H4/H1 -> ognuna tenuta sul TF |
//|  dove rende meglio). Fonte: results/best_per_strategy_multitf_*.   |
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
   // --- Ricetta multi-TF ottimale per-strategia (XAUUSD, dati reali) ---
   if(name == "ADX_RSI")           { slMult=1.0; tpMult=3.0; htf=false; beR=0.0; trailATR=0.0; return true; }  // 1d OK PF1.39 R0.91
   if(name == "BB_SQUEEZE")        { slMult=1.0; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // 1d POCHI_DATI PF2.92 R2.0
   if(name == "BJORGUM")           { slMult=1.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 4h FORTE PF3.46 R2.0
   if(name == "BOLLINGER")         { slMult=1.0; tpMult=2.0; htf=false; beR=0.0; trailATR=0.0; return true; }  // 1d OK PF1.17 R0.94
   if(name == "BREAKOUT_ACC")      { slMult=1.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF1.86 R0.63
   if(name == "CISD")              { slMult=1.5; tpMult=3.0; htf=true ; beR=0.0; trailATR=2.0; return true; }  // 4h FORTE PF5.95 R2.0
   if(name == "DISP_REBAL")        { slMult=1.0; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // 4h FORTE PF1.68 R2.0
   if(name == "EMA_PULLBACK")      { slMult=1.0; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // 4h FORTE PF1.65 R0.75
   if(name == "FVG_CONT")          { slMult=1.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 4h FORTE PF1.67 R0.65
   if(name == "FVG_MIT")           { slMult=1.5; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF2.04 R2.0
   if(name == "ICHIMOKU")          { slMult=1.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 4h FORTE PF1.75 R1.13
   if(name == "IFVG")              { slMult=1.5; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 4h FORTE PF2.51 R2.0
   if(name == "LIQ_SWEEP")         { slMult=1.5; tpMult=3.0; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF2.48 R2.0
   if(name == "LIQ_VOID")          { slMult=1.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 4h FORTE PF1.67 R0.65
   if(name == "LONDON_BO")         { slMult=1.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF1.86 R0.63
   if(name == "MACD")              { slMult=1.0; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // 4h FORTE PF1.72 R1.08
   if(name == "MALAYSIAN_SNR")     { slMult=2.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF1.96 R2.0
   if(name == "OB_MIT")            { slMult=1.0; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF1.66 R1.29
   if(name == "ORDER_BLOCK")       { slMult=1.0; tpMult=3.0; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF1.55 R1.71
   if(name == "OTE_CONT")          { slMult=2.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF1.78 R2.0
   if(name == "RANGE_FADE")        { slMult=1.0; tpMult=2.0; htf=false; beR=0.0; trailATR=0.0; return true; }  // 1d OK PF1.17 R0.94
   if(name == "RSI_DIV")           { slMult=1.0; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // 1h OK PF1.29 R0.94
   if(name == "SAR")               { slMult=1.0; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // 4h FORTE PF1.65 R0.75
   if(name == "SH_BMS_RTO")        { slMult=1.0; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF1.66 R1.29
   if(name == "SMS_BMS_RTO")       { slMult=1.0; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF1.66 R1.29
   if(name == "STRUCT_REACT")      { slMult=1.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1h FORTE PF1.87 R2.0
   if(name == "TSI")               { slMult=1.5; tpMult=4.5; htf=true ; beR=1.0; trailATR=0.0; return true; }  // 1d FORTE PF1.68 R1.04
   if(name == "TURTLE_SOUP")       { slMult=1.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1h FORTE PF1.83 R2.0
   if(name == "WEEKLY_EXP")        { slMult=1.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF1.86 R0.63
   // Le session/Elliott (SILVER_BULLET, AMD_*, JUDAS, LDN/NY_REVERSAL, PO3,
   // ELLIOTT): da ottimizzare su MT5/intraday -> nessun profilo, usano i globali.
   return false;
}

// Timeframe ottimale per la strategia (multi-TF). L'EA deve cercare il trigger
// di ogni strategia su QUESTO timeframe. Se non c'e' profilo -> PERIOD_CURRENT
// (usa il TF di ingresso globale InpTFEntry, retrocompatibile).
ENUM_TIMEFRAMES NXS_Profile_TF(const string name){
   if(name == "ADX_RSI")           return PERIOD_D1;
   if(name == "BB_SQUEEZE")        return PERIOD_D1;
   if(name == "BJORGUM")           return PERIOD_H4;
   if(name == "BOLLINGER")         return PERIOD_D1;
   if(name == "BREAKOUT_ACC")      return PERIOD_D1;
   if(name == "CISD")              return PERIOD_H4;
   if(name == "DISP_REBAL")        return PERIOD_H4;
   if(name == "EMA_PULLBACK")      return PERIOD_H4;
   if(name == "FVG_CONT")          return PERIOD_H4;
   if(name == "FVG_MIT")           return PERIOD_D1;
   if(name == "ICHIMOKU")          return PERIOD_H4;
   if(name == "IFVG")              return PERIOD_H4;
   if(name == "LIQ_SWEEP")         return PERIOD_D1;
   if(name == "LIQ_VOID")          return PERIOD_H4;
   if(name == "LONDON_BO")         return PERIOD_D1;
   if(name == "MACD")              return PERIOD_H4;
   if(name == "MALAYSIAN_SNR")     return PERIOD_D1;
   if(name == "OB_MIT")            return PERIOD_D1;
   if(name == "ORDER_BLOCK")       return PERIOD_D1;
   if(name == "OTE_CONT")          return PERIOD_D1;
   if(name == "RANGE_FADE")        return PERIOD_D1;
   if(name == "RSI_DIV")           return PERIOD_H1;
   if(name == "SAR")               return PERIOD_H4;
   if(name == "SH_BMS_RTO")        return PERIOD_D1;
   if(name == "SMS_BMS_RTO")       return PERIOD_D1;
   if(name == "STRUCT_REACT")      return PERIOD_H1;
   if(name == "TSI")               return PERIOD_D1;
   if(name == "TURTLE_SOUP")       return PERIOD_H1;
   if(name == "WEEKLY_EXP")        return PERIOD_D1;
   return PERIOD_CURRENT;
}

// Rischio % per-strategia (dimensionato a budget di drawdown ~10% nel backtest).
// Ritorna <=0 se non c'e' profilo -> usa il rischio globale InpRiskPercent.
double NXS_Profile_Risk(const string name){
   if(name == "ADX_RSI")           return 0.91;
   if(name == "BB_SQUEEZE")        return 2.0;
   if(name == "BJORGUM")           return 2.0;
   if(name == "BOLLINGER")         return 0.94;
   if(name == "BREAKOUT_ACC")      return 0.63;
   if(name == "CISD")              return 2.0;
   if(name == "DISP_REBAL")        return 2.0;
   if(name == "EMA_PULLBACK")      return 0.75;
   if(name == "FVG_CONT")          return 0.65;
   if(name == "FVG_MIT")           return 2.0;
   if(name == "ICHIMOKU")          return 1.13;
   if(name == "IFVG")              return 2.0;
   if(name == "LIQ_SWEEP")         return 2.0;
   if(name == "LIQ_VOID")          return 0.65;
   if(name == "LONDON_BO")         return 0.63;
   if(name == "MACD")              return 1.08;
   if(name == "MALAYSIAN_SNR")     return 2.0;
   if(name == "OB_MIT")            return 1.29;
   if(name == "ORDER_BLOCK")       return 1.71;
   if(name == "OTE_CONT")          return 2.0;
   if(name == "RANGE_FADE")        return 0.94;
   if(name == "RSI_DIV")           return 0.94;
   if(name == "SAR")               return 0.75;
   if(name == "SH_BMS_RTO")        return 1.29;
   if(name == "SMS_BMS_RTO")       return 1.29;
   if(name == "STRUCT_REACT")      return 2.0;
   if(name == "TSI")               return 1.04;
   if(name == "TURTLE_SOUP")       return 2.0;
   if(name == "WEEKLY_EXP")        return 0.63;
   return 0.0;
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
// (multi-TF: STRUCT_REACT e DISP_REBAL ora sono FORTE sul loro TF -> abilitate).
bool NXS_Profile_Enabled(const string name){
   if(name == "BB_SQUEEZE")   return false;   // POCHI_DATI (troppi pochi trade)
   return true;
}

#endif
