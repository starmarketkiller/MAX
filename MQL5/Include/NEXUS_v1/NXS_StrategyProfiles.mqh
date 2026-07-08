//+------------------------------------------------------------------+
//|  NXS_StrategyProfiles.mqh - Profili PER-STRATEGIA dal backtest    |
//|                                                                    |
//|  "L'EA deve operare come nel backtest": ogni strategia usa i SUOI  |
//|  parametri (ATR SL/TP) e i SUOI gate, non quelli globali. I valori |
//|  vengono dall'ottimizzazione per-strategia su dati reali           |
//|  (results/best_per_strategy_XAUUSD_D1.json).                       |
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
   // default = "nessun profilo"
   slMult = 0; tpMult = 0; htf = false; beR = 0; trailATR = 0;

   // --- Ricetta ottimale per-strategia (XAUUSD, dati reali, backtest v2.2.7) ---
   if(name == "TSI")          { slMult=1.0; tpMult=3.5; htf=true;  beR=0.0; trailATR=0.0; return true; }
   if(name == "MACD")         { slMult=1.2; tpMult=5.5; htf=true;  beR=0.0; trailATR=2.5; return true; }
   if(name == "ADX_RSI")      { slMult=1.0; tpMult=3.5; htf=false; beR=0.0; trailATR=0.0; return true; }
   if(name == "ICHIMOKU")     { slMult=1.5; tpMult=5.5; htf=false; beR=0.0; trailATR=0.0; return true; }
   if(name == "EMA_PULLBACK") { slMult=1.2; tpMult=5.5; htf=true;  beR=1.0; trailATR=0.0; return true; }
   if(name == "BREAKOUT_ACC") { slMult=1.0; tpMult=5.5; htf=true;  beR=0.0; trailATR=2.5; return true; }
   if(name == "LONDON_BO")    { slMult=1.0; tpMult=5.5; htf=true;  beR=0.0; trailATR=2.5; return true; }
   if(name == "BOLLINGER")    { slMult=2.6; tpMult=2.8; htf=true;  beR=0.0; trailATR=2.5; return true; }
   if(name == "RANGE_FADE")   { slMult=2.6; tpMult=2.8; htf=true;  beR=0.0; trailATR=2.5; return true; }
   if(name == "BB_SQUEEZE")   { slMult=1.0; tpMult=5.5; htf=false; beR=1.5; trailATR=0.0; return true; }
   if(name == "RSI_DIV")      { slMult=1.0; tpMult=3.5; htf=false; beR=0.0; trailATR=0.0; return true; }
   // Le 26 SMC/Institutional/Elliott: da ottimizzare su MT5 (non nel motore
   // Python). Finche' non hanno profilo, usano i valori globali.
   return false;
}

// Comodo: solo SL/TP (per NXS_DefaultSLTP). Ritorna true se c'e' il profilo.
bool NXS_Profile_SLTP(const string name, double &slMult, double &tpMult){
   bool htf; double beR, trailATR;
   return NXS_Profile_Get(name, slMult, tpMult, htf, beR, trailATR);
}

// Solo il gate HTF per la strategia (per il filtro qualita' per-strategia).
// hasProfile=true se la strategia ha un profilo; htf=valore richiesto.
bool NXS_Profile_HTF(const string name, bool &htf){
   double sl, tp, be, tr;
   bool h;
   if(NXS_Profile_Get(name, sl, tp, h, be, tr)){ htf = h; return true; }
   htf = false; return false;
}

#endif
