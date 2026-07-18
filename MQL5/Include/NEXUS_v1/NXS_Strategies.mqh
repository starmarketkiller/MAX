//+------------------------------------------------------------------+
//|  NXS_Strategies.mqh - 15 trading strategies (KODEXAI + HYDRA+SMC) |
//+------------------------------------------------------------------+
#ifndef __NXS_STRATEGIES_MQH__
#define __NXS_STRATEGIES_MQH__

// ------ v2.0.21: timeframe di origine del segnale -> SL/TP e vita posizione ------
// Mappa le strategie HTF/session-based al loro TF di origine. Le altre usano il
// TF di esecuzione (ritorna 0 = PERIOD_CURRENT -> gestito come TF di esecuzione).
//
// 17/07 FIX - bug grave trovato indagando perche' SAR/MACD/RSI_DIV/ADX_RSI su
// MT5 reale chiudono a una frazione minuscola di R con holding ~4-6h anche
// sulle strategie D1: questa tabella era una copia VECCHIA e mai sincronizzata
// di NXS_Profile_TF() (in NXS_StrategyProfiles.mqh) - copriva solo 10 strategie
// su ~30, e per 4 di quelle 10 (CISD/LIQ_VOID/OTE_CONT/ICHIMOKU) il valore era
// anche SBAGLIATO (diceva H1, il profilo vero e' H4/H4/H4/D1). Tutte le altre
// (ADX_RSI, SAR, MACD, RSI_DIV, BOLLINGER, TSI, BJORGUM, LIQ_SWEEP, FVG_CONT,
// ORDER_BLOCK, TURTLE_SOUP, IFVG, FVG_MIT, OB_MIT, SH_BMS_RTO, SMS_BMS_RTO,
// AMD_REVERSAL, MALAYSIAN_SNR, DISP_REBAL, RANGE_FADE, BREAKOUT_ACC,
// LONDON_BO, EMA_PULLBACK, BB_SQUEEZE, STRUCT_REACT...) cadevano nel default
// InpTFEntry (M15) -> NXS_TF_LifeFactor() restituiva 1.0 invece di 20x/60x ->
// NXS_Prot_CheckMaxHold() (NXS_Protections.mqh) applicava un cap PIATTO di
// InpProt_MaxHoldHours (12h di default) su strategie D1/H4 pensate per durare
// giorni, chiudendole forzatamente molto prima che SL o TP potessero essere
// toccati - stesso bug per NXS_Prot_CheckMaxLossPerPos()/InpProt_MinLifeMin.
// Ora NXS_Profile_TF() e' l'UNICA fonte di verita' (stessa mappa usata dal
// trigger e dal SL/TP) - niente piu' tabella duplicata che puo' disallinearsi.
ENUM_TIMEFRAMES NXS_StrategySourceTF(const string name){
   ENUM_TIMEFRAMES ptf = NXS_Profile_TF(name);
   if(ptf != PERIOD_CURRENT) return ptf;
   // Solo le session/Elliott senza profilo (vedi NXS_StrategyProfiles.mqh)
   // restano sulla vecchia mappa manuale.
   if(name == "WEEKLY_EXP") return PERIOD_D1;
   if(name == "PO3")        return PERIOD_H4;
   if(name == "JUDAS_SWING" || name == "LDN_REVERSAL" || name == "NY_REVERSAL" ||
      name == "AMD_CONT"    || name == "SILVER_BULLET")
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
// 17/07 notte - vero True Strength Index (Blau), da audit esterno canonico:
// la versione precedente non calcolava TSI, era un filtro RSI+EMA20 col
// nome sbagliato. TSI = 100 x doubleEMA(priceChange) / doubleEMA(abs(priceChange)),
// confrontato con una signal line (EMA del TSI). Calcolo iterativo aggiornato
// una sola volta per barra chiusa (bar-gated, come SH_BMS_RTO stanotte) -
// niente ricalcolo dell'intera serie storica ad ogni tick.
struct SNXSTSIState {
   bool     init;
   datetime lastBarTime;
   double   sm1, sm2;        // doppio EMA di priceChange
   double   sm1Abs, sm2Abs;  // doppio EMA di abs(priceChange)
   double   signal;          // EMA(TSI, signalPeriod)
   double   tsiPrev, signalPrev;   // valori PRIMA dell'aggiornamento di questa barra (per il cross)
   double   prevClose;
   int      barsSeen;
};
SNXSTSIState g_tsiState;

SNXSSignal NXS_Strat_TSI(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_TSI; s.stratName = "TSI";
   if(!InpStrat_TSI || !NXS_SelectorAllows(5)) return s;
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   datetime curBar0 = iTime(g_sym, tf, 0);
   double c1 = iClose(g_sym, tf, 1);

   if(!g_tsiState.init){
      g_tsiState.init = true; g_tsiState.prevClose = iClose(g_sym, tf, 2);
      g_tsiState.lastBarTime = 0; g_tsiState.barsSeen = 0;
   }
   if(g_tsiState.lastBarTime != curBar0){
      // Nuova barra chiusa: aggiorna il doppio smoothing una sola volta.
      g_tsiState.tsiPrev = (g_tsiState.sm2Abs > 0) ? 100.0 * g_tsiState.sm2 / g_tsiState.sm2Abs : 0.0;
      g_tsiState.signalPrev = g_tsiState.signal;

      double pc  = c1 - g_tsiState.prevClose;
      double apc = MathAbs(pc);
      double aLong  = 2.0 / (InpTSI_LongPeriod  + 1.0);
      double aShort = 2.0 / (InpTSI_ShortPeriod + 1.0);
      double aSig   = 2.0 / (InpTSI_SignalPeriod + 1.0);
      g_tsiState.sm1    = pc  * aLong  + g_tsiState.sm1    * (1.0 - aLong);
      g_tsiState.sm1Abs = apc * aLong  + g_tsiState.sm1Abs * (1.0 - aLong);
      g_tsiState.sm2    = g_tsiState.sm1    * aShort + g_tsiState.sm2    * (1.0 - aShort);
      g_tsiState.sm2Abs = g_tsiState.sm1Abs * aShort + g_tsiState.sm2Abs * (1.0 - aShort);
      double tsiNow = (g_tsiState.sm2Abs > 0) ? 100.0 * g_tsiState.sm2 / g_tsiState.sm2Abs : 0.0;
      g_tsiState.signal = tsiNow * aSig + g_tsiState.signal * (1.0 - aSig);

      g_tsiState.prevClose = c1;
      g_tsiState.lastBarTime = curBar0;
      g_tsiState.barsSeen++;
   }
   // Warmup: serve tempo perche' il doppio EMA converga (non e' inizializzato
   // con la media storica reale, parte da 0) - stessa logica di cautela gia'
   // usata altrove nel file per gli indicatori con stato iterativo.
   if(g_tsiState.barsSeen < InpTSI_LongPeriod * 3) return s;

   double tsi    = (g_tsiState.sm2Abs > 0) ? 100.0 * g_tsiState.sm2 / g_tsiState.sm2Abs : 0.0;
   double signal = g_tsiState.signal;
   bool crossUp   = (g_tsiState.tsiPrev <= g_tsiState.signalPrev) && (tsi > signal);
   bool crossDown = (g_tsiState.tsiPrev >= g_tsiState.signalPrev) && (tsi < signal);
   if(crossUp){
      s.dir = DIR_BUY;  s.score = 66; s.reason = "TSI_cross_up";
   } else if(crossDown){
      s.dir = DIR_SELL; s.score = 66; s.reason = "TSI_cross_down";
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
   // 17/07 notte - un solo motore di rilevamento sweep (NXS_DetectSweepExt,
   // esteso a daily/weekly/monthly), ma il reason riporta ESATTAMENTE quale
   // livello ha scatenato il segnale (sw.levelTag: Daily/Weekly/Monthly-
   // High/Low, Asia-High/Low, Equal-High/Low) - diagnostica per capire quale
   // livello produce l'edge, senza duplicare la strategia 3 volte.
   if(sw.dir == DIR_BUY && c1 > o1){
      s.dir = DIR_BUY;  s.score = 72; s.reason = "Sweep_low_reversal:" + sw.levelTag;
   } else if(sw.dir == DIR_SELL && c1 < o1){
      s.dir = DIR_SELL; s.score = 72; s.reason = "Sweep_high_reversal:" + sw.levelTag;
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
// 17/07 notte - validazione breakout aggiunta, da audit esterno canonico:
// prima qualsiasi close marginale oltre l'Asia contava come breakout.
// Timezone/DST della sessione restano un lavoro a parte, condiviso e
// centralizzato per NY_REVERSAL (non duplicato qui).
double InpLondonBO_MinBodyATR = 0.5;   // corpo minimo della barra di breakout
double InpLondonBO_BufferATR  = 0.15;  // margine oltre il livello, non un tocco marginale
double InpLondonBO_MinCLV     = 0.6;   // close location value: chiusura vicina all'estremo del range di barra

SNXSSignal NXS_Strat_LondonBO(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_LONDON_BO; s.stratName = "LONDON_BO";
   if(!InpStrat_LONDON_BO || !NXS_SelectorAllows(10)) return s;
   if(g_session != SESS_LONDON) return s;
   // use Asian range
   SNXSAMD amd = NXS_GetAMD();
   if(amd.asianHigh <= 0) return s;
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   double c1 = iClose(g_sym, tf, 1), o1 = iOpen(g_sym, tf, 1);
   double h1 = iHigh (g_sym, tf, 1), l1 = iLow (g_sym, tf, 1);
   double body1 = MathAbs(c1 - o1);
   double range1 = h1 - l1;
   if(body1 < g_atr * InpLondonBO_MinBodyATR || range1 <= 0) return s;
   double clvUp   = (c1 - l1) / range1;   // vicino al massimo di barra = convinzione rialzista
   double clvDown = (h1 - c1) / range1;   // vicino al minimo di barra = convinzione ribassista
   if(c1 > amd.asianHigh + g_atr * InpLondonBO_BufferATR && clvUp >= InpLondonBO_MinCLV){
      s.dir = DIR_BUY;  s.score = 70; s.reason = "London_BO_above_asia";
   } else if(c1 < amd.asianLow - g_atr * InpLondonBO_BufferATR && clvDown >= InpLondonBO_MinCLV){
      s.dir = DIR_SELL; s.score = 70; s.reason = "London_BO_below_asia";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H5 EMA Pullback
// 17/07 notte - da semplice reclaim EMA20 a vero pullback, da audit esterno
// canonico: prima bastava un cross istantaneo di EMA20 con EMA20>EMA50 nel
// tick corrente - non dimostrava un trend persistente ne' un vero impulso
// precedente ne' una rejection. Ora richiede: (1) trend persistente per N
// barre (non solo l'istante attuale), (2) un impulso precedente che si sia
// allontanato dall'EMA20 di una distanza minima, (3) pullback con vera
// rejection (non solo un cross), (4) niente entry se EMA50 viene rotta.
int    InpEMAPB_TrendPersistBars = 5;
double InpEMAPB_MinDistATR       = 1.0;
double InpEMAPB_TouchToleranceATR= 0.15;

SNXSSignal NXS_Strat_EMAPullback(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_EMA_PULLBACK; s.stratName = "EMA_PULLBACK";
   if(!InpStrat_EMA_PULLBACK || !NXS_SelectorAllows(11)) return s;
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   double e20 = NXS_EMAv(20, tf, 1), e50 = NXS_EMAv(50, tf, 1);
   if(e20 <= 0 || e50 <= 0) return s;
   bool up = e20 > e50;

   // (1) Trend persistente: EMA20>EMA50 (o il contrario) e EMA20 nella direzione
   // giusta per le ultime InpEMAPB_TrendPersistBars barre, non solo ora.
   for(int k = 1; k <= InpEMAPB_TrendPersistBars; k++){
      double e20k = NXS_EMAv(20, tf, k), e50k = NXS_EMAv(50, tf, k), e20kp = NXS_EMAv(20, tf, k + 1);
      if(e20k <= 0 || e50k <= 0 || e20kp <= 0) return s;
      bool trendOkK = up ? (e20k > e50k && e20k >= e20kp) : (e20k < e50k && e20k <= e20kp);
      if(!trendOkK) return s;
   }
   // (2) Impulso precedente: negli ultimi 10 barre prima del pullback il prezzo
   // deve essersi allontanato dall'EMA20 di almeno InpEMAPB_MinDistATR x ATR.
   bool hadImpulse = false;
   for(int k = 2; k <= 12; k++){
      double e20k = NXS_EMAv(20, tf, k);
      if(e20k <= 0) continue;
      double pxk = up ? iHigh(g_sym, tf, k) : iLow(g_sym, tf, k);
      double dist = up ? (pxk - e20k) : (e20k - pxk);
      if(dist >= g_atr * InpEMAPB_MinDistATR){ hadImpulse = true; break; }
   }
   if(!hadImpulse) return s;

   // (3) Pullback con vera rejection sulla barra chiusa, non solo un cross.
   double c1 = iClose(g_sym, tf, 1), o1 = iOpen(g_sym, tf, 1);
   double l1 = iLow(g_sym, tf, 1),   h1 = iHigh(g_sym, tf, 1);
   double tol = g_atr * InpEMAPB_TouchToleranceATR;
   if(up){
      bool touched = (l1 <= e20 + tol);
      bool reclaim = (c1 > e20) && (c1 > o1) && (c1 > e50);   // (4) niente entry sotto EMA50
      if(touched && reclaim){ s.dir = DIR_BUY;  s.score = 64; s.reason = "EMA_PB_bull:pullback+reject"; }
   } else {
      bool touched = (h1 >= e20 - tol);
      bool reclaim = (c1 < e20) && (c1 < o1) && (c1 < e50);
      if(touched && reclaim){ s.dir = DIR_SELL; s.score = 64; s.reason = "EMA_PB_bear:pullback+reject"; }
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
// 17/07 notte - origine della zona corretta, da audit esterno canonico
// (ICT/SMC): un order block bullish e' l'ULTIMA candela bearish prima del
// displacement che rompe struttura (BOS), non il corpo del displacement
// stesso. La versione precedente usava la candela impulso come se fosse
// l'OB - "displacement body zone", non un vero order block. Ora: (1) il
// displacement deve rompere uno swing precedente (BOS, prima mancava),
// (2) la zona e' l'ultima candela di colore opposto prima dell'impulso,
// (3) la zona e' persistente e "fresh" fino al primo retest o
// invalidazione (prima si ricalcolava tutto da zero ogni tick, nessuna
// vera nozione di zona gia' usata/consumata).
int InpOB_SwingLookback = 15;   // barre per il riferimento swing (BOS) pre-impulso
int InpOB_MaxWaitBars   = 20;   // barre max di attesa del retest prima che la zona scada

struct SNXSOBState {
   bool     active;
   double   obLo, obHi;
   datetime lastBarTime;
   int      barsWaited;
};
SNXSOBState g_obBuy, g_obSell;

SNXSSignal NXS_OB_UpdateSide(int dir, SNXSOBState &st, ENUM_TIMEFRAMES tf, double atr, datetime curBar0){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_ORDER_BLOCK; s.stratName = "ORDER_BLOCK";
   bool newBar = (st.lastBarTime != curBar0);

   if(!st.active){
      if(!newBar) return s;
      st.lastBarTime = curBar0;
      // Cerca un displacement valido fra 3 e 10 barre fa (come il sito), ma
      // ora deve anche rompere uno swing precedente (BOS) per contare.
      for(int i = 3; i <= 10; i++){
         double o = iOpen (g_sym, tf, i), c = iClose(g_sym, tf, i);
         double body = MathAbs(c - o);
         if(body < 1.2 * atr) continue;
         bool rightColor = (dir == +1) ? (c > o) : (c < o);
         if(!rightColor) continue;
         int hiIdx = iHighest(g_sym, tf, MODE_HIGH, InpOB_SwingLookback, i + 1);
         int loIdx = iLowest (g_sym, tf, MODE_LOW,  InpOB_SwingLookback, i + 1);
         double swingRef = (dir == +1) ? (hiIdx >= 0 ? iHigh(g_sym, tf, hiIdx) : 0)
                                        : (loIdx >= 0 ? iLow (g_sym, tf, loIdx) : 0);
         bool bos = (dir == +1) ? (swingRef > 0 && c > swingRef) : (swingRef > 0 && c < swingRef);
         if(!bos) continue;
         // Origine: ultima candela di colore OPPOSTO prima dell'impulso (fino a 6 barre indietro).
         double originA = o, originB = c;
         bool found = false;
         for(int k = i + 1; k <= i + 6; k++){
            double ok = iOpen(g_sym, tf, k), ck = iClose(g_sym, tf, k);
            bool oppositeColor = (dir == +1) ? (ck < ok) : (ck > ok);
            if(oppositeColor){ originA = ok; originB = ck; found = true; break; }
         }
         if(!found) continue;
         st.obLo = MathMin(originA, originB);
         st.obHi = MathMax(originA, originB);
         st.active = true; st.barsWaited = 0;
         break;
      }
      return s;
   }

   // Zona attiva, in attesa del retest.
   if(newBar){
      st.lastBarTime = curBar0;
      st.barsWaited++;
      if(st.barsWaited > InpOB_MaxWaitBars){ st.active = false; return s; }
      double c1 = iClose(g_sym, tf, 1);
      // Invalidazione: chiusura che attraversa completamente la zona nel verso sbagliato.
      if((dir == +1 && c1 < st.obLo) || (dir == -1 && c1 > st.obHi)){ st.active = false; return s; }
   }
   if(st.obHi <= st.obLo) return s;
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   bool touched = (bid >= st.obLo && bid <= st.obHi);
   if(!touched) return s;
   double c1 = iClose(g_sym, tf, 1), o1 = iOpen(g_sym, tf, 1);
   bool rejection = (dir == +1) ? (c1 > o1) : (c1 < o1);
   if(!rejection) return s;   // richiede comunque una candela di rigetto, non solo il tocco
   if(dir == +1){
      s.dir = DIR_BUY;  s.score = 70; s.reason = "OB_retest_bull";
   } else {
      s.dir = DIR_SELL; s.score = 70; s.reason = "OB_retest_bear";
   }
   st.active = false;   // one-shot: la zona e' consumata dopo il primo retest
   return s;
}

SNXSSignal NXS_Strat_OrderBlock(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_ORDER_BLOCK; s.stratName = "ORDER_BLOCK";
   if(!InpStrat_ORDER_BLOCK || !NXS_SelectorAllows(15)) return s;
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   double atr = g_atr;
   datetime curBar0 = iTime(g_sym, tf, 0);
   s = NXS_OB_UpdateSide(+1, g_obBuy, tf, atr, curBar0);
   if(s.dir == DIR_NONE) s = NXS_OB_UpdateSide(-1, g_obSell, tf, atr, curBar0);
   // v2.4.1 - trend H1 (struttura esterna) deve confermare la stessa direzione del retest.
   if(s.dir == DIR_BUY  && g_structH1.trend != 1)  { s.dir = DIR_NONE; s.reason = ""; }
   if(s.dir == DIR_SELL && g_structH1.trend != -1) { s.dir = DIR_NONE; s.reason = ""; }
   // v2.4.2: conferma reazione (structure+react engine) sul retest -> entra solo
   // se il prezzo RESPINGE il blocco, non se lo attraversa. Vale anche per OB_MIT
   // (usa questa funzione).
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
