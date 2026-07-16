//+------------------------------------------------------------------+
//|  NXS_Strategies.mqh - 15 trading strategies (KODEXAI + HYDRA+SMC) |
//+------------------------------------------------------------------+
#ifndef __NXS_STRATEGIES_MQH__
#define __NXS_STRATEGIES_MQH__

// ------ v2.0.21: timeframe di origine del segnale -> SL/TP e vita posizione ------
// Mappa le strategie HTF/session-based al loro TF di origine. Le altre usano il
// TF di esecuzione (ritorna 0 = PERIOD_CURRENT -> gestito come TF di esecuzione).
ENUM_TIMEFRAMES NXS_StrategySourceTF(const string name){
   if(name == "WEEKLY_EXP") return PERIOD_D1;
   if(name == "PO3")        return PERIOD_H4;
   if(name == "JUDAS_SWING" || name == "LDN_REVERSAL" || name == "NY_REVERSAL" ||
      name == "AMD_CONT"    || name == "CISD"         || name == "LIQ_VOID"    ||
      name == "SILVER_BULLET" || name == "OTE_CONT"   || name == "ICHIMOKU")
      return PERIOD_H1;
   return InpTFEntry;
}

// Moltiplicatore SL/TP in base al TF di origine (usa l'ATR del TF di esecuzione
// con un fattore -> nessun doppio conteggio con l'ATR del TF alto).
double NXS_TF_SLTPMult(ENUM_TIMEFRAMES stf){
   if(stf == PERIOD_CURRENT) stf = InpTFEntry;
   int sec  = PeriodSeconds(stf);
   int base = PeriodSeconds(InpTFEntry);
   if(sec <= base)  return 1.0;
   if(sec <= 3600)  return g_run_TF_SLTP_H1;   // fino a H1
   if(sec <= 14400) return g_run_TF_SLTP_H4;   // fino a H4
   return g_run_TF_SLTP_D1;                     // H4+/D1
}

// Fattore di scala per MinLife/MaxHold in base al TF di origine.
double NXS_TF_LifeFactor(ENUM_TIMEFRAMES stf){
   if(stf == PERIOD_CURRENT) stf = InpTFEntry;
   int sec  = PeriodSeconds(stf);
   int base = PeriodSeconds(InpTFEntry);
   if(sec <= base)  return 1.0;
   if(sec <= 3600)  return InpTF_Life_H1;
   if(sec <= 14400) return InpTF_Life_H4;
   return InpTF_Life_D1;
}

// Ricava il TF di origine di una posizione dal commento "InpComment|STRAT|score".
ENUM_TIMEFRAMES NXS_PosSourceTF(const string comment){
   int p1 = StringFind(comment, "|");
   if(p1 < 0) return InpTFEntry;
   int p2 = StringFind(comment, "|", p1 + 1);
   string strat = (p2 > p1) ? StringSubstr(comment, p1 + 1, p2 - p1 - 1)
                            : StringSubstr(comment, p1 + 1);
   return NXS_StrategySourceTF(strat);
}

void NXS_DefaultSLTP(SNXSSignal &sig){
   double slMult = g_run_AtrSLMult;          // tunabile dal sito (default = InpATR_SL_Mult)
   if(InpUseAdaptiveSL && g_atrAvg > 0){
      slMult = (g_atr > g_atrAvg) ? InpSL_HighVol_Mult : InpSL_LowVol_Mult;
   }
   slMult = MathMax(slMult, InpMinSLMult);   // v2.0.14 — floor SL (rumore M5 gold)
   double tpMult = g_run_AtrTPMult;          // tunabile dal sito (default = InpATR_TP_Mult)
   // v2.2.8 — profilo PER-STRATEGIA dal backtest: se la strategia ha una ricetta
   // ottimale, i SUOI SL/TP sostituiscono i globali ("operare come nel backtest").
   if(InpUseStrategyProfiles){
      double pSl, pTp;
      if(NXS_Profile_SLTP(sig.stratName, pSl, pTp) && pSl > 0 && pTp > 0){
         slMult = pSl; tpMult = pTp;
      }
   }
   // v2.0.21 — SL/TP proporzionati al TF di origine del segnale.
   if(sig.sourceTF == PERIOD_CURRENT) sig.sourceTF = NXS_StrategySourceTF(sig.stratName);
   double tfMult = NXS_TF_SLTPMult(sig.sourceTF);
   // v2.3.0 — in multi-TF g_atr e' GIA' l'ATR del TF della strategia: niente
   // doppio conteggio, tfMult=1 (altrimenti scalerebbe due volte).
   if(InpUseStrategyProfiles && InpProfileMultiTF) tfMult = 1.0;
   double sl = g_atr * slMult * tfMult;
   double tp = g_atr * tpMult * tfMult;
   if(sig.dir == DIR_BUY){
      sig.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      sig.slPrice  = NormPrice(sig.entryRef - sl);
      sig.tpPrice  = NormPrice(sig.entryRef + tp);
   } else if(sig.dir == DIR_SELL){
      sig.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
      sig.slPrice  = NormPrice(sig.entryRef + sl);
      sig.tpPrice  = NormPrice(sig.entryRef - tp);
   }
}

// v2.3.8 — mini-cache di handle EMA(period) per TF, usata dalle strategie
// riportate dal sito che vogliono medie non presenti negli handle base
// (es. EMA20/EMA50). Auto-contenuta: non tocca il sistema handle principale.
int             g_emaCacheP[32];
ENUM_TIMEFRAMES g_emaCacheTF[32];
int             g_emaCacheH[32];
int             g_emaCacheN = 0;
double NXS_EMAv(int period, ENUM_TIMEFRAMES tf, int shift){
   int h = INVALID_HANDLE;
   for(int i = 0; i < g_emaCacheN; i++)
      if(g_emaCacheP[i] == period && g_emaCacheTF[i] == tf){ h = g_emaCacheH[i]; break; }
   if(h == INVALID_HANDLE){
      h = iMA(g_sym, tf, period, 0, MODE_EMA, PRICE_CLOSE);
      if(h == INVALID_HANDLE) return 0.0;
      if(g_emaCacheN < 32){
         g_emaCacheP[g_emaCacheN] = period; g_emaCacheTF[g_emaCacheN] = tf;
         g_emaCacheH[g_emaCacheN] = h; g_emaCacheN++;
      }
   }
   double a[]; ArraySetAsSeries(a, true);
   if(CopyBuffer(h, 0, shift, 1, a) <= 0) return 0.0;
   return a[0];
}

//------------------------------------ K1 ADX_RSI (riportata alla logica del sito:
// trend EMA50 + banda RSI. La vecchia usava ADX+EMA200 -> divergeva dal backtest.
// v2.5.1 - il "backtest" a cui si divergeva era il motore sito, che pero' non
// ha mai calcolato un vero ADX (verificato 15/07, vedi vault NEXUS EA -
// Ricerca Esterna e Test A-B per Strategia): la rimozione dell'ADX inseguiva
// un riferimento difettoso. Test A/B sul motore sito (10y XAUUSD D1, ADX(14)
// Wilder reale) mostra che la soglia da manuale (25) rovina il trigger, ma
// ADX>20 (stessa soglia gia' usata altrove in questo EA, vedi g_adx in
// NXS_Strategies_Institutional.mqh) dimezza circa il drawdown mantenendo PF
// e campione. g_adx e' gia' calcolato da iADX() per ogni tick (NEXUS_EA_v2.mq5),
// non serve nuovo wiring. Non ancora validato su MT5 - da confermare con un
// backtest isolato prima di considerarlo definitivo.)
SNXSSignal NXS_Strat_ADXRSI(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_ADX_RSI; s.stratName = "ADX_RSI";
   if(!InpStrat_ADX_RSI || !NXS_SelectorAllows(1)) return s;
   if(g_adx < 20.0) return s;                // v2.5.1: filtro forza trend, vedi nota sopra
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   double e50 = NXS_EMAv(50, tf, 1), e50p = NXS_EMAv(50, tf, 2);
   if(e50 <= 0 || e50p <= 0) return s;
   double r  = g_rsi;                       // RSI(14) sul TF attivo
   double px = iClose(g_sym, tf, 1);
   bool trendUp = e50 > e50p;
   if(trendUp && r > 45 && r < 65 && px > e50){
      s.dir = DIR_BUY;  s.score = 62; s.reason = "ADXRSI bull (site)";
   } else if(!trendUp && r > 35 && r < 55 && px < e50){
      s.dir = DIR_SELL; s.score = 62; s.reason = "ADXRSI bear (site)";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ K2 Bollinger Mean Reversion
SNXSSignal NXS_Strat_Bollinger(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_BOLLINGER; s.stratName = "BOLLINGER";
   if(!InpStrat_BOLLINGER || !NXS_SelectorAllows(2)) return s;
   // Riportata alla logica del sito (sig_bollinger): rientro dalla banda con
   // il CLOSE (non low/high) e NESSUN filtro RSI. La vecchia usava low/high +
   // RSI<35/>65 -> troppo restrittiva e disallineata (158 setup, 0 vinti).
   //   ppx <= lower < px  -> long  ;  ppx >= upper > px -> short
   double px  = iClose(g_sym, NXS_EffTF(), 1);   // close[i]
   double ppx = iClose(g_sym, NXS_EffTF(), 2);   // close[i-1]
   if(ppx <= g_bbLower && g_bbLower < px){
      s.dir = DIR_BUY;  s.score = 62; s.reason = "BB_lower_reentry";
   } else if(ppx >= g_bbUpper && g_bbUpper > px){
      s.dir = DIR_SELL; s.score = 62; s.reason = "BB_upper_reentry";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ K3 MACD Trend
SNXSSignal NXS_Strat_MACD(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_MACD; s.stratName = "MACD";
   if(!InpStrat_MACD || !NXS_SelectorAllows(3)) return s;
   double price = iClose(g_sym, NXS_EffTF(), 1);
   if(g_macd > g_macdSig && g_macd > 0 && price > g_ema200){
      s.dir = DIR_BUY;  s.score = 65; s.reason = "MACD_bull_above_ema200";
   } else if(g_macd < g_macdSig && g_macd < 0 && price < g_ema200){
      s.dir = DIR_SELL; s.score = 65; s.reason = "MACD_bear_below_ema200";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ K4 Parabolic SAR
SNXSSignal NXS_Strat_SAR(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_SAR; s.stratName = "SAR";
   if(!InpStrat_SAR || !NXS_SelectorAllows(4)) return s;
   double price = iClose(g_sym, NXS_EffTF(), 1);
   if(g_sar < price && g_ema9 > g_ema21){
      s.dir = DIR_BUY;  s.score = 60; s.reason = "SAR_below_price";
   } else if(g_sar > price && g_ema9 < g_ema21){
      s.dir = DIR_SELL; s.score = 60; s.reason = "SAR_above_price";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ K5 TSI Momentum (simplified RSI/EMA proxy)
// Riportata alla logica del sito: RSI>52 + prezzo sopra EMA20 con EMA20 in
// salita (short speculare). La vecchia usava EMA9/21 + RSI 55/45 -> divergeva
// (PF 0.40 sul broker mentre sul sito era forte).
SNXSSignal NXS_Strat_TSI(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_TSI; s.stratName = "TSI";
   if(!InpStrat_TSI || !NXS_SelectorAllows(5)) return s;
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   double e20 = NXS_EMAv(20, tf, 1), e20p = NXS_EMAv(20, tf, 2);
   if(e20 <= 0 || e20p <= 0) return s;
   double r  = g_rsi;
   double px = iClose(g_sym, tf, 1);
   if(r > 52 && px > e20 && e20 > e20p){
      s.dir = DIR_BUY;  s.score = 66; s.reason = "TSI bull (site)";
   } else if(r < 48 && px < e20 && e20 < e20p){
      s.dir = DIR_SELL; s.score = 66; s.reason = "TSI bear (site)";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ K6 Bjorgum Key Levels
SNXSSignal NXS_Strat_Bjorgum(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_BJORGUM; s.stratName = "BJORGUM";
   if(!InpStrat_BJORGUM || !NXS_SelectorAllows(6)) return s;
   int hh = iHighest(g_sym, NXS_EffTF(), MODE_HIGH, 30, 2);
   int ll = iLowest (g_sym, NXS_EffTF(), MODE_LOW,  30, 2);
   double pivHi = iHigh(g_sym, NXS_EffTF(), hh);
   double pivLo = iLow (g_sym, NXS_EffTF(), ll);
   double c1 = iClose(g_sym, NXS_EffTF(), 1);
   double dist = g_atr * 0.5;
   if(MathAbs(c1 - pivLo) <= dist && c1 > pivLo){
      s.dir = DIR_BUY;  s.score = 68; s.reason = "Bjorgum_bounce_low";    // v2.0.9 +4
   } else if(MathAbs(c1 - pivHi) <= dist && c1 < pivHi){
      s.dir = DIR_SELL; s.score = 68; s.reason = "Bjorgum_reject_high";   // v2.0.9 +4
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H1 Liquidity Sweep / Manipulation Reversal
// 16/07: usava NXS_DetectSweep() generico (estremo di 20 barre qualsiasi) -
// unica strategia rimasta su quella definizione debole, mentre TURTLE_SOUP/
// SH_BMS_RTO/JUDAS_SWING/LDN_REVERSAL/PO3/AMD_REVERSAL/SILVER_BULLET usano
// gia' NXS_DetectSweepExt() (PDH/PDL/Asia High-Low/equal H-L, i veri
// riferimenti di liquidita' ICT). Passata a SNXSSweepExt. Test A/B sul sito
// (config reale SL1.5/TP3.0): su 4h senza HTF, PF 0.86->1.32 e DD quasi
// dimezzato (20.37%->8.71%); su D1+HTF (config profilo attuale) il campione
// cresce 14->141 trade restando positivo (PF 3.30->1.27) - risolve il
// problema di campione troppo piccolo mai risolto in 8 anni di dati reali
// (26 trade totali). Non uniformemente migliore su ogni TF - vedi vault
// Liq Sweep per il dettaglio completo. Non ancora validato su MT5.
//
// 16/07 seguito: l'utente ha mostrato 2 screenshot di setup ICT reali - in
// entrambi lo sweep coincide sempre con una vera candela Order Block
// (corpo forte/"delivery candle"), non un rimbalzo qualsiasi. Aggiunto lo
// stesso filtro corpo>=0.7xATR gia' provato con successo sul sito (PF
// 1.27->1.63, DD quasi dimezzato sulla config D1+HTF). Non ancora
// validato su MT5.
SNXSSignal NXS_Strat_LiqSweep(SNXSSweepExt &sw){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_LIQ_SWEEP; s.stratName = "LIQ_SWEEP";
   if(!InpStrat_LIQ_SWEEP || !NXS_SelectorAllows(7)) return s;
   if(!sw.confirmed) return s;
   double c1 = iClose(g_sym, NXS_EffTF(), 1);
   double o1 = iOpen (g_sym, NXS_EffTF(), 1);
   if(MathAbs(c1 - o1) < 0.7 * g_atr) return s;   // candela "delivery"/OB, non un rimbalzo qualsiasi
   if(sw.dir == DIR_BUY && c1 > o1){
      s.dir = DIR_BUY;  s.score = 72; s.reason = "Sweep_low_reversal";
   } else if(sw.dir == DIR_SELL && c1 < o1){
      s.dir = DIR_SELL; s.score = 72; s.reason = "Sweep_high_reversal";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H2 Displacement FVG Continuation
// 16/07: filtro EMA50 (proxy di trend locale) sostituito col trend
// ESTERNO vero (g_structH1, mai letta prima da nessuna strategia - vedi
// vault NEXUS EA - Struttura Interna vs Esterna). Test A/B sul sito, config
// reale (H4+HTF): PF 1.45->2.07, DD 18.31%->12.48%, campione ~40% piu'
// piccolo. Non ancora validato su MT5 reale.
SNXSSignal NXS_Strat_FVG(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_FVG_CONT; s.stratName = "FVG_CONT";
   if(!InpStrat_FVG_CONT || !NXS_SelectorAllows(8)) return s;
   // Gap a 3 candele (low[1]>high[3]) + trend ESTERNO (H1) concorde, non piu'
   // solo close vs EMA50 locale.
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   double h3 = iHigh(g_sym, tf, 3);
   double l3 = iLow (g_sym, tf, 3);
   double h1 = iHigh(g_sym, tf, 1);
   double l1 = iLow (g_sym, tf, 1);
   double c1 = iClose(g_sym, tf, 1);
   if(l1 > h3 && g_structH1.trend == 1){
      s.dir = DIR_BUY;  s.score = 70; s.reason = "FVG_cont bull (ext)";
   } else if(h1 < l3 && g_structH1.trend == -1){
      s.dir = DIR_SELL; s.score = 70; s.reason = "FVG_cont bear (ext)";
   }
   // v2.4.2: conferma reazione (structure+react engine) -> filtra i gap in cui
   // il prezzo passa senza reagire (causa delle perdite SMC).
   if(s.dir != DIR_NONE && InpUseSMCReactionGate &&
      !NXS_SMCReactionOK(tf, (s.dir == DIR_BUY ? 1 : -1))){
      s.dir = DIR_NONE; s.reason = "";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H3 Breakout Acceptance
SNXSSignal NXS_Strat_BreakoutAcc(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_BREAKOUT_ACC; s.stratName = "BREAKOUT_ACC";
   if(!InpStrat_BREAKOUT_ACC || !NXS_SelectorAllows(9)) return s;
   int n = 20;
   double range_hi = iHigh(g_sym, NXS_EffTF(), iHighest(g_sym, NXS_EffTF(), MODE_HIGH, n, 3));
   double range_lo = iLow (g_sym, NXS_EffTF(), iLowest (g_sym, NXS_EffTF(), MODE_LOW,  n, 3));
   double c1 = iClose(g_sym, NXS_EffTF(), 1);
   double c2 = iClose(g_sym, NXS_EffTF(), 2);
   if(c1 > range_hi && c2 > range_hi){
      s.dir = DIR_BUY;  s.score = 68; s.reason = "Acceptance_above_range";
   } else if(c1 < range_lo && c2 < range_lo){
      s.dir = DIR_SELL; s.score = 68; s.reason = "Acceptance_below_range";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H4 London Breakout
SNXSSignal NXS_Strat_LondonBO(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_LONDON_BO; s.stratName = "LONDON_BO";
   if(!InpStrat_LONDON_BO || !NXS_SelectorAllows(10)) return s;
   if(g_session != SESS_LONDON) return s;
   // use Asian range
   SNXSAMD amd = NXS_GetAMD();
   if(amd.asianHigh <= 0) return s;
   double c1 = iClose(g_sym, NXS_EffTF(), 1);
   if(c1 > amd.asianHigh){
      s.dir = DIR_BUY;  s.score = 70; s.reason = "London_BO_above_asia";
   } else if(c1 < amd.asianLow){
      s.dir = DIR_SELL; s.score = 70; s.reason = "London_BO_below_asia";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H5 EMA Pullback
// Riportata alla logica del sito: trend EMA20>EMA50, pullback = il prezzo era
// sotto EMA20 e ci richiude sopra (o viceversa). La vecchia usava EMA9/21+RSI.
SNXSSignal NXS_Strat_EMAPullback(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_EMA_PULLBACK; s.stratName = "EMA_PULLBACK";
   if(!InpStrat_EMA_PULLBACK || !NXS_SelectorAllows(11)) return s;
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   double e20 = NXS_EMAv(20, tf, 1), e50 = NXS_EMAv(50, tf, 1), e20p = NXS_EMAv(20, tf, 2);
   if(e20 <= 0 || e50 <= 0 || e20p <= 0) return s;
   bool up = e20 > e50;
   double px = iClose(g_sym, tf, 1), ppx = iClose(g_sym, tf, 2);
   if(up && ppx < e20p && px > e20){
      s.dir = DIR_BUY;  s.score = 64; s.reason = "EMA_PB bull (site)";
   } else if(!up && ppx > e20p && px < e20){
      s.dir = DIR_SELL; s.score = 64; s.reason = "EMA_PB bear (site)";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H6 BB Squeeze Breakout
SNXSSignal NXS_Strat_BBSqueeze(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_BB_SQUEEZE; s.stratName = "BB_SQUEEZE";
   if(!InpStrat_BB_SQUEEZE || !NXS_SelectorAllows(12)) return s;
   double width = g_bbUpper - g_bbLower;
   if(width <= 0 || g_atr <= 0) return s;
   if(width > g_atr * 2.5) return s; // not a squeeze
   double c1 = iClose(g_sym, NXS_EffTF(), 1);
   if(c1 > g_bbUpper){
      s.dir = DIR_BUY;  s.score = 70; s.reason = "Squeeze_breakout_up";
   } else if(c1 < g_bbLower){
      s.dir = DIR_SELL; s.score = 70; s.reason = "Squeeze_breakout_down";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H7 Ichimoku Kumo Break
SNXSSignal NXS_Strat_Ichimoku(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_ICHIMOKU; s.stratName = "ICHIMOKU";
   if(!InpStrat_ICHIMOKU || !NXS_SelectorAllows(13)) return s;
   double price = iClose(g_sym, NXS_EffTF(), 1);
   double kumoTop = MathMax(g_ichiSpanA, g_ichiSpanB);
   double kumoBot = MathMin(g_ichiSpanA, g_ichiSpanB);
   if(kumoTop <= 0 || kumoBot <= 0) return s;
   double prev = iClose(g_sym, NXS_EffTF(), 2);
   if(prev <= kumoTop && price > kumoTop && g_ichiTenkan > g_ichiKijun){
      s.dir = DIR_BUY;  s.score = 65; s.reason = "Kumo_break_up";
   } else if(prev >= kumoBot && price < kumoBot && g_ichiTenkan < g_ichiKijun){
      s.dir = DIR_SELL; s.score = 65; s.reason = "Kumo_break_down";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H8 RSI Divergence
SNXSSignal NXS_Strat_RSIDiv(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_RSI_DIV; s.stratName = "RSI_DIV";
   if(!InpStrat_RSI_DIV || !NXS_SelectorAllows(14)) return s;
   double rsiArr[]; ArraySetAsSeries(rsiArr, true);
   if(CopyBuffer(g_hRSI, 0, 1, 15, rsiArr) <= 0) return s;
   double l1 = iLow(g_sym, NXS_EffTF(), 1);
   double l8 = iLow(g_sym, NXS_EffTF(), 8);
   double h1 = iHigh(g_sym, NXS_EffTF(), 1);
   double h8 = iHigh(g_sym, NXS_EffTF(), 8);
   // bullish divergence: lower low in price, higher low in RSI
   if(l1 < l8 && rsiArr[0] > rsiArr[7] && rsiArr[0] < 40){
      s.dir = DIR_BUY;  s.score = 68; s.reason = "RSI_bull_div";
   } else if(h1 > h8 && rsiArr[0] < rsiArr[7] && rsiArr[0] > 60){
      s.dir = DIR_SELL; s.score = 68; s.reason = "RSI_bear_div";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ S1 Order Block Retest
// 16/07: aggiunta la conferma di struttura ESTERNA (g_structH1, gia'
// calcolata ogni tick da NXS_UpdateStructureH1 ma finora letta da zero
// strategie - vedi vault NEXUS EA - Struttura Interna vs Esterna). Test A/B
// sul sito: PF migliora su quasi ogni TF/config (es. D1+HTF, config reale:
// 1.50->1.77, DD 5.85%->3.94%), campione si dimezza circa. Nota di
// fedelta': sul sito il test verificava il trend esterno AL MOMENTO
// dell'impulso (serie storica); qui in MQL5 g_structH1 e' solo lo stato
// CORRENTE (non uno storico per barra), quindi il controllo e' "il trend
// H1 conferma ORA la direzione del retest" - stessa idea, punto di verifica
// leggermente diverso per limite strutturale di MQL5. Non ancora validato
// su MT5 reale.
SNXSSignal NXS_Strat_OrderBlock(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_ORDER_BLOCK; s.stratName = "ORDER_BLOCK";
   if(!InpStrat_ORDER_BLOCK || !NXS_SelectorAllows(15)) return s;
   // Sito: impulso (body>1.2 ATR) 3-10 barre fa, poi retest del body con rifiuto.
   for(int i = 3; i <= 10; i++){
      double o = iOpen (g_sym, NXS_EffTF(), i);
      double c = iClose(g_sym, NXS_EffTF(), i);
      double body = MathAbs(c - o);
      if(body < 1.2 * g_atr) continue;
      double obTop = MathMax(o, c);
      double obBot = MathMin(o, c);
      double c1 = iClose(g_sym, NXS_EffTF(), 1);
      double o1 = iOpen (g_sym, NXS_EffTF(), 1);
      double l1 = iLow  (g_sym, NXS_EffTF(), 1);
      double h1 = iHigh (g_sym, NXS_EffTF(), 1);
      double obMid = (obTop + obBot) * 0.5;
      // bullish OB: impulso su, il ritest TAGGA la zona (l1<=obTop) e la candela
      // la RESPINGE - chiude rialzista sopra il midpoint (rejection), non mentre
      // il prezzo sta ancora cadendo dentro il blocco. Ora richiede anche che il
      // trend H1 (struttura esterna) confermi la stessa direzione.
      if(c > o && l1 <= obTop && c1 > o1 && c1 > obMid && g_structH1.trend == 1){
         s.dir = DIR_BUY;  s.score = 70; s.reason = "OB_retest_bull"; break;
      }
      if(c < o && h1 >= obBot && c1 < o1 && c1 < obMid && g_structH1.trend == -1){
         s.dir = DIR_SELL; s.score = 70; s.reason = "OB_retest_bear"; break;
      }
   }
   // v2.4.2: conferma reazione (structure+react engine) sul retest -> entra solo
   // se il prezzo RESPINGE il blocco, non se lo attraversa. Vale anche per OB_MIT
   // (usa questa funzione). Filtra la causa delle perdite (PF 0.67 / 0.38).
   if(s.dir != DIR_NONE && InpUseSMCReactionGate &&
      !NXS_SMCReactionOK(NXS_EffTF(), (s.dir == DIR_BUY ? 1 : -1))){
      s.dir = DIR_NONE; s.reason = "";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ S2 Structure Reaction (addendum)
SNXSSignal NXS_Strat_StructureReaction(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_STRUCT_REACT; s.stratName = "STRUCT_REACT";
   if(!InpUseStructReact || !NXS_SelectorAllows(16)) return s;
   if(!g_reaction.detected) return s;

   double base = 55;
   double q = g_reaction.quality;
   double score = base + q * 0.35;  // 55 .. ~90

   // Bonus when reaction aligned with structure trend
   if(g_reaction.direction == g_struct.trend) score += 6;
   // BOS/CHOCH confirmation
   if(g_reaction.direction == 1 && (g_struct.bosUp   || g_struct.chochUp))   score += 5;
   if(g_reaction.direction ==-1 && (g_struct.bosDown || g_struct.chochDown)) score += 5;
   if(score > 95) score = 95;

   s.dir   = (g_reaction.direction == 1) ? DIR_BUY : DIR_SELL;
   s.score = score;
   s.reason= "StructReact_" + g_reaction.levelType;
   NXS_DefaultSLTP(s);
   return s;
}

#endif
