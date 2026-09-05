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

//+------------------------------------------------------------------+
//| NXS-PROT-006 — AUTORITA' UNICA per la chiusura a durata massima   |
//|                                                                   |
//| Il limite di hold era calcolato in DUE punti indipendenti:         |
//|   - NXS_Management.mqh   : 40 barre del TF di profilo, fallback    |
//|                            InpMaxHoldHours (4h)                    |
//|   - NXS_Protections.mqh  : InpProt_MaxHoldHours (12h) x LifeFactor |
//| Entrambi leggevano la strategia dal COMMENTO della posizione. Se   |
//| il commento mancava o era troncato dal broker (MT5 tronca a 31     |
//| caratteri e alcuni broker lo riscrivono), i due moduli ricadevano  |
//| su fallback DIVERSI e chiudevano la stessa posizione a orari       |
//| diversi: vinceva chi scattava prima, in modo non riproducibile.    |
//|                                                                   |
//| Questo risolutore e' l'unica fonte del limite. Restituisce anche   |
//| `resolved`, che PARTIZIONA la competenza in modo esaustivo e       |
//| mutuamente esclusivo:                                             |
//|   resolved == true  -> la posizione ha un profilo reale: agisce    |
//|                        SOLO NXS_Management.mqh (integrato con      |
//|                        breakeven e trailing nello stesso loop)     |
//|   resolved == false -> strategia ignota o commento illeggibile:    |
//|                        agisce SOLO NXS_Protections.mqh, con il     |
//|                        limite CONSERVATIVO (il minore dei due)     |
//| Nessuna posizione ha due giudici, nessuna resta senza.             |
//+------------------------------------------------------------------+
long NXS_MaxHold_LimitSec(const string posComment, bool &resolved){
   resolved = false;
   string strat = "";
   int p1 = StringFind(posComment, "|");
   if(p1 >= 0){
      int p2 = StringFind(posComment, "|", p1 + 1);
      strat = (p2 > p1) ? StringSubstr(posComment, p1 + 1, p2 - p1 - 1)
                        : StringSubstr(posComment, p1 + 1);
   }

   if(InpUseStrategyProfiles && StringLen(strat) > 0){
      ENUM_TIMEFRAMES ptf = NXS_Profile_TF(strat);
      if(ptf != PERIOD_CURRENT){
         resolved = true;
         return (long)PeriodSeconds(ptf) * InpProfileMaxHoldBars;
      }
   }

   // Nessun profilo: si usa il PIU' STRETTO fra i due limiti storici invece di
   // lasciarli competere. Un limite piu' corto chiude prima — sul lato sicuro.
   long a = (long)InpMaxHoldHours * 3600;
   long b = (long)(InpProt_MaxHoldHours * 3600 *
                   NXS_TF_LifeFactor(NXS_PosSourceTF(posComment)));
   if(a <= 0) return b;
   if(b <= 0) return a;
   return (a < b) ? a : b;
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

// 28/08 - stesso pattern di NXS_EMAv ma SMA (serve per MACD+SMA200, che a
// differenza del nostro MACD nativo usa medie semplici, non esponenziali).
int             g_smaCacheP[16];
ENUM_TIMEFRAMES g_smaCacheTF[16];
int             g_smaCacheH[16];
int             g_smaCacheN = 0;
double NXS_SMAv(int period, ENUM_TIMEFRAMES tf, int shift){
   int h = INVALID_HANDLE;
   for(int i = 0; i < g_smaCacheN; i++)
      if(g_smaCacheP[i] == period && g_smaCacheTF[i] == tf){ h = g_smaCacheH[i]; break; }
   if(h == INVALID_HANDLE){
      h = iMA(g_sym, tf, period, 0, MODE_SMA, PRICE_CLOSE);
      if(h == INVALID_HANDLE) return 0.0;
      if(g_smaCacheN < 16){
         g_smaCacheP[g_smaCacheN] = period; g_smaCacheTF[g_smaCacheN] = tf;
         g_smaCacheH[g_smaCacheN] = h; g_smaCacheN++;
      }
   }
   double a[]; ArraySetAsSeries(a, true);
   if(CopyBuffer(h, 0, shift, 1, a) <= 0) return 0.0;
   return a[0];
}

// 28/08 - WMA (stesso pattern), serve come mattone per la Hull MA vera (non
// approssimata con una EMA) usata dallo script Ichimoku+HullMA+MACD.
int             g_wmaCacheP[16];
ENUM_TIMEFRAMES g_wmaCacheTF[16];
int             g_wmaCacheH[16];
int             g_wmaCacheN = 0;
double NXS_WMAv(int period, ENUM_TIMEFRAMES tf, int shift){
   int h = INVALID_HANDLE;
   for(int i = 0; i < g_wmaCacheN; i++)
      if(g_wmaCacheP[i] == period && g_wmaCacheTF[i] == tf){ h = g_wmaCacheH[i]; break; }
   if(h == INVALID_HANDLE){
      h = iMA(g_sym, tf, period, 0, MODE_LWMA, PRICE_CLOSE);
      if(h == INVALID_HANDLE) return 0.0;
      if(g_wmaCacheN < 16){
         g_wmaCacheP[g_wmaCacheN] = period; g_wmaCacheTF[g_wmaCacheN] = tf;
         g_wmaCacheH[g_wmaCacheN] = h; g_wmaCacheN++;
      }
   }
   double a[]; ArraySetAsSeries(a, true);
   if(CopyBuffer(h, 0, shift, 1, a) <= 0) return 0.0;
   return a[0];
}

// Hull MA vera: WMA(2*WMA(n/2)-WMA(n), round(sqrt(n))). WMA(n/2) e WMA(n)
// vengono lette da handle nativi (cache sopra); la WMA finale sulla serie
// derivata va fatta a mano (non e' una serie con un proprio handle MT5).
double NXS_HMAv(int period, ENUM_TIMEFRAMES tf, int shift){
   int halfP = MathMax(1, period / 2);
   int sqrtP = (int)MathMax(1, MathRound(MathSqrt(period)));
   double sum = 0, wsum = 0;
   for(int k = 0; k < sqrtP; k++){
      double wHalf = NXS_WMAv(halfP, tf, shift + k);
      double wFull = NXS_WMAv(period, tf, shift + k);
      if(wHalf <= 0 || wFull <= 0) return 0.0;
      double raw = 2.0 * wHalf - wFull;
      double weight = (double)(sqrtP - k);   // piu' peso alla barra piu' recente
      sum += raw * weight;
      wsum += weight;
   }
   return (wsum > 0) ? sum / wsum : 0.0;
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
// 17/07 notte - allineamento temporale corretto, da audit esterno canonico:
// g_bbLower/g_bbUpper sono globali cache SOLO a shift1 (vedi NEXUS_EA_v2.mq5,
// CopyBuffer con shift=1) - il confronto usava ppx (close[2]) contro la banda
// di shift1, non quella di shift2. Prezzo storico confrontato con una banda
// temporalmente diversa. Ora legge esplicitamente Lower/Upper a shift 1 E 2.
SNXSSignal NXS_Strat_Bollinger(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_BOLLINGER; s.stratName = "BOLLINGER";
   if(!InpStrat_BOLLINGER || !NXS_SelectorAllows(2)) return s;
   double bbUp[], bbLo[];
   ArraySetAsSeries(bbUp, true); ArraySetAsSeries(bbLo, true);
   if(CopyBuffer(g_hBB, 1, 1, 2, bbUp) < 2) return s;   // bbUp[0]=shift1, bbUp[1]=shift2
   if(CopyBuffer(g_hBB, 2, 1, 2, bbLo) < 2) return s;
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   double px  = iClose(g_sym, tf, 1);   // close[1]
   double ppx = iClose(g_sym, tf, 2);   // close[2]

   // 03/09 - gate a chiusura barra (piano BOLLINGER+RSI+candela, step 5):
   // il setup (bar 1/2) resta vero per l'intera durata della barra 0 in
   // formazione - senza questo gate rischia di rivalutare RSI/candela ad
   // ogni tick invece che una volta alla chiusura, stesso principio del
   // lastFireTime di NXS_Strat_PivotWick (bug di inseguimento gia' trovato
   // su BAR_UPDN/BREAKOUT_ACC il 02/09).
   static datetime lastEvalBar = 0;
   datetime curBar1 = iTime(g_sym, tf, 1);
   if(curBar1 == lastEvalBar) return s;

   bool touchLower = (ppx <= bbLo[1] && bbLo[0] < px);
   bool touchUpper = (ppx >= bbUp[1] && bbUp[0] > px);
   if(!touchLower && !touchUpper) return s;
   int dir = touchLower ? DIR_BUY : DIR_SELL;

   // 04/09 - lock di direzione: test H4 nudo ha trovato BUY PF1.33 (71
   // trade) contro SELL PF0.61 (138 trade, trascina l'aggregato in
   // perdita) - conferma diretta della scoperta Python del 24/08.
   if(InpBollingerBuyOnly && dir == DIR_SELL) return s;

   // 03/09 - filtro RSI(14): richiede che l'estremo di prezzo NON sia
   // confermato da un estremo di RSI (divergenza) - vedi vault "Piano
   // BOLLINGER+RSI (02-09)". Se RSI conferma l'estremo (ipervenduto/
   // ipercomprato vero), il tocco e' scartato: l'ipotesi e' che
   // l'assenza di conferma segnali momentum in esaurimento, non un vero
   // eccesso da cui rimbalzare.
   if(InpBollingerUseRSIFilter){
      double rsiArr[];
      ArraySetAsSeries(rsiArr, true);
      if(CopyBuffer(g_hRSI, 0, 1, 1, rsiArr) < 1) return s;
      double rsi1 = rsiArr[0];
      if(dir == DIR_BUY  && rsi1 <= InpBollingerRSIOversold)   return s;
      if(dir == DIR_SELL && rsi1 >= InpBollingerRSIOverbought) return s;
   }

   // 03/09 - filtro candela di inversione: hammer/engulfing rialzista sul
   // tocco della banda inferiore, shooting star/engulfing ribassista su
   // quella superiore. Valutato sulla barra di tocco (index 1, chiusa).
   if(InpBollingerUseCandleFilter){
      double o1 = iOpen(g_sym, tf, 1), c1 = iClose(g_sym, tf, 1);
      double h1 = iHigh(g_sym, tf, 1), l1 = iLow(g_sym, tf, 1);
      double o2 = iOpen(g_sym, tf, 2), c2 = iClose(g_sym, tf, 2);
      double range1 = h1 - l1;
      if(range1 <= 0) return s;
      double body1 = MathAbs(c1 - o1);
      bool hammer     = (MathMin(o1,c1) - l1 >= 2.0*body1) && (h1 - MathMax(o1,c1) <= body1);
      bool shootStar  = (h1 - MathMax(o1,c1) >= 2.0*body1) && (MathMin(o1,c1) - l1 <= body1);
      bool bullEngulf = (c2 < o2) && (c1 > o1) && (c1 >= o2) && (o1 <= c2);
      bool bearEngulf = (c2 > o2) && (c1 < o1) && (c1 <= o2) && (o1 >= c2);
      if(dir == DIR_BUY  && !(hammer || bullEngulf)) return s;
      if(dir == DIR_SELL && !(shootStar || bearEngulf)) return s;
   }

   lastEvalBar = curBar1;
   if(dir == DIR_BUY){ s.dir = DIR_BUY;  s.score = 62; s.reason = "BB_lower_reentry"; }
   else              { s.dir = DIR_SELL; s.score = 62; s.reason = "BB_upper_reentry"; }
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
// 31/08 - filtro candela di allineamento, trovato analizzando i 112 trade
// nudi di stanotte (dati reali, non ipotesi): quando la candela H4 appena
// chiusa concorda con la direzione del segnale (bullish per buy, bearish
// per sell), win rate 69% (77% tra i grandi vincenti); quando e' contraria,
// 46% (50% tra i grandi perdenti - quasi casuale). Filtrando SOLO gli
// allineati sui dati storici: PF 1.33->1.92, netto $1227.85->$1594.93 su
// meno trade (112->58). Gli scartati da soli erano in perdita netta
// (PF 0.81, -$367.08) - non diluivano solo il risultato, lo peggioravano.
bool NXS_SAR_CandleAligned(int dir){
   double o1 = iOpen(g_sym, NXS_EffTF(), 1), c1 = iClose(g_sym, NXS_EffTF(), 1);
   bool bullish = (c1 > o1);
   return (bullish && dir == DIR_BUY) || (!bullish && dir == DIR_SELL);
}

// 31/08 - "pressione" delle ultime 2h (8 barre M15): quante chiudono al
// rialzo/ribasso + somma dei corpi netti. Contro-intuitivo ma confermato
// sui dati: SAR va MEGLIO quando la pressione recente e' CONTRARIA alla
// direzione del segnale (cattura un'inversione vera) che quando e'
// allineata (rischia di inseguire un movimento gia' esteso). Da solo:
// PF1.00 (allineata) vs PF1.69 (contraria). Combinato col filtro candela
// (non ridondante, si sommano): entrambi allineati -> PF3.47 su 18 trade;
// nessuno dei due -> PF0.04 su 13 trade (quasi tutte perdite).
bool NXS_SAR_PressureContrary(int dir){
   int up = 0; double netBody = 0;
   int N = 8;
   for(int i = 1; i <= N; i++){
      double o = iOpen(g_sym, PERIOD_M15, i), c = iClose(g_sym, PERIOD_M15, i);
      if(c > o) up++;
      netBody += (c - o);
   }
   bool pressureBuy = (up >= N/2) && (netBody > 0);
   return (!pressureBuy && dir == DIR_BUY) || (pressureBuy && dir == DIR_SELL);
}

SNXSSignal NXS_Strat_SAR(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_SAR; s.stratName = "SAR";
   if(!InpStrat_SAR || !NXS_SelectorAllows(4)) return s;
   double price = iClose(g_sym, NXS_EffTF(), 1);
   if(g_sar < price && g_ema9 > g_ema21){
      s.dir = DIR_BUY;  s.score = 60; s.reason = "SAR_below_price";
   } else if(g_sar > price && g_ema9 < g_ema21){
      s.dir = DIR_SELL; s.score = 60; s.reason = "SAR_above_price";
   }
   if(s.dir != DIR_NONE && InpSAR_RequireCandleAlign && !NXS_SAR_CandleAligned(s.dir)){
      s.dir = DIR_NONE; s.reason = "candle_misaligned";
   }
   if(s.dir != DIR_NONE && InpSAR_RequirePressureContrary && !NXS_SAR_PressureContrary(s.dir)){
      s.dir = DIR_NONE; s.reason = "pressure_aligned_not_contrary";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ K4b BarUpDn (price-action puro)
// 28/08 - portata da uno script Pine Script TradingView pubblico ("BarUpDn",
// ChartArt): nessun indicatore, solo la relazione OHLC tra due barre
// consecutive. Barra corrente verde E apre sopra la chiusura precedente ->
// buy; barra rossa E apre sotto la chiusura precedente -> sell (mirror).
//
// 02/09 - BUG TROVATO (ipotesi dell'utente, confermata sui dati): nessuno
// stato "gia' tradato questo pattern" - la condizione torna vera piu' volte
// durante un trend sostenuto, quindi il motore insegue lo stesso movimento
// con ingressi ripetuti invece di prenderlo una volta sola. Verificato: 134
// dei 210 trade nudi (M15, 2024) erano raggruppati (stesso verso, entro 6h
// l'uno dall'altro) - il primo di un gruppo spesso vince, gli inseguimenti
// quasi sempre perdono.
//
// PRIMO TENTATIVO (fallito): one-shot che si resetta appena una barra non
// soddisfa piu' il pattern - inefficace, perche' in un trend reale il
// pattern non si ripete su barre CONSECUTIVE perfette, si interrompe e
// riprende in modo intermittente (conteggio trade sceso solo 210->207).
// CORREZIONE: raffreddamento per direzione basato sul numero di barre
// (InpBarUpDnCooldownBars), non sulla continuita' del pattern - blocca lo
// stesso verso per N barre dopo un ingresso, indipendentemente da quante
// volte il pattern si ripresenta nel frattempo.
struct SNXSBarUpDnState { datetime lastBarTime; datetime lastFireTime[2]; };  // [0]=buy [1]=sell
SNXSBarUpDnState g_barUpDnState;

SNXSSignal NXS_Strat_BarUpDn(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_STRUCT_REACT; s.stratName = "BAR_UPDN";
   if(!InpStrat_BarUpDn || !NXS_SelectorAllows(43)) return s;
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   datetime curBar0 = iTime(g_sym, tf, 0);
   if(g_barUpDnState.lastBarTime == curBar0) return s;   // gia' valutata questa barra
   g_barUpDnState.lastBarTime = curBar0;

   double o1 = iOpen(g_sym, tf, 1), c1 = iClose(g_sym, tf, 1);
   double c2 = iClose(g_sym, tf, 2);
   bool bull = (c1 > o1 && o1 > c2);
   bool bear = (c1 < o1 && o1 < c2);

   long periodSec = PeriodSeconds(tf);
   long cooldownSec = (long)InpBarUpDnCooldownBars * periodSec;
   bool buyOk  = (g_barUpDnState.lastFireTime[0] == 0) || ((curBar0 - g_barUpDnState.lastFireTime[0]) >= cooldownSec);
   bool sellOk = (g_barUpDnState.lastFireTime[1] == 0) || ((curBar0 - g_barUpDnState.lastFireTime[1]) >= cooldownSec);

   if(bull && buyOk){
      s.dir = DIR_BUY;  s.score = 58; s.reason = "BarUpDn_bull";
      g_barUpDnState.lastFireTime[0] = curBar0;
   } else if(bear && sellOk){
      s.dir = DIR_SELL; s.score = 58; s.reason = "BarUpDn_bear";
      g_barUpDnState.lastFireTime[1] = curBar0;
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ K4c PMax (SuperTrend ATR-adattivo)
// 28/08 - portata da uno script Pine Script TradingView pubblico ("PMax
// Explorer", KivancOzbilgic): stop-and-reverse ATR-adattivo, concettualmente
// piu' robusto del Parabolic SAR nativo (step/max fissi) - candidato mirato
// dopo che SAR e' risultato negativo (PF0.92) sul motore reale. Replica
// fedele di Pmax_Func: longStop/shortStop "agganciati" (si muovono solo
// nella direzione favorevole finche' il trend regge), dir cambia solo
// quando la MA rompe lo stop opposto. Stato persistente per barra chiusa
// (stesso pattern di NXS_Strat_TSI - un aggiornamento per barra, non per
// tick, altrimenti il flip non e' univoco).
struct SNXSPMaxState {
   bool     init;
   datetime lastBarTime;
   double   longStop, shortStop;
   int      dir;   // +1 o -1
};
SNXSPMaxState g_pmaxState;

SNXSSignal NXS_Strat_PMax(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_STRUCT_REACT; s.stratName = "PMAX";
   if(!InpStrat_PMax || !NXS_SelectorAllows(44)) return s;
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   datetime curBar0 = iTime(g_sym, tf, 0);
   if(g_pmaxState.lastBarTime == curBar0) return s;   // gia' valutata su questa barra

   double atr = NXS_ATRv(tf, 1, InpPMax_ATRPeriod);
   double ma  = NXS_EMAv(InpPMax_MALength, tf, 1);
   if(atr <= 0 || ma <= 0) return s;

   double longStop  = ma - InpPMax_ATRMult * atr;
   double shortStop = ma + InpPMax_ATRMult * atr;

   if(!g_pmaxState.init){
      g_pmaxState.init = true;
      g_pmaxState.longStop  = longStop;
      g_pmaxState.shortStop = shortStop;
      g_pmaxState.dir = 1;
      g_pmaxState.lastBarTime = curBar0;
      return s;
   }

   double maPrev = NXS_EMAv(InpPMax_MALength, tf, 2);
   if(maPrev > g_pmaxState.longStop)  longStop  = MathMax(longStop,  g_pmaxState.longStop);
   if(maPrev < g_pmaxState.shortStop) shortStop = MathMin(shortStop, g_pmaxState.shortStop);

   int dir = g_pmaxState.dir;
   if(dir == -1 && ma > g_pmaxState.shortStop)     dir = 1;
   else if(dir == 1 && ma < g_pmaxState.longStop)  dir = -1;
   bool flip = (dir != g_pmaxState.dir);

   g_pmaxState.longStop  = longStop;
   g_pmaxState.shortStop = shortStop;
   g_pmaxState.dir = dir;
   g_pmaxState.lastBarTime = curBar0;

   if(flip){
      if(dir == 1){ s.dir = DIR_BUY;  s.score = 60; s.reason = "PMax_flip_bull"; }
      else        { s.dir = DIR_SELL; s.score = 60; s.reason = "PMax_flip_bear"; }
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ K4d MACD+SMA200 (medie semplici, non esponenziali)
// 28/08 - portata da uno script Pine Script TradingView pubblico ("MACD +
// SMA 200 Strategy", ChartArt): a differenza del nostro MACD nativo (K3,
// EMA-based su iMACD), qui MACD e signal sono costruiti su medie MOBILI
// SEMPLICI (SMA), con un filtro di trend SMA200 aggiuntivo. Segnale: hist
// (macd-signal) attraversa lo zero verso l'alto, macd>0, fastMA>slowMA, e il
// close di "slowLength" barre fa era sopra la SMA200 (replica esatta della
// condizione originale close[slowLength]>veryslowMA, non semplificata).
// Bar-gated: la ricostruzione del signal (SMA(macd,9)) richiede una piccola
// media manuale su piu' barre, troppo costosa per ricalcolarla ad ogni tick.
struct SNXSMacdSmaState { datetime lastBarTime; };
SNXSMacdSmaState g_macdSmaState;

double _nxs_macdsma_hist(ENUM_TIMEFRAMES tf, int shift, int fastLen, int slowLen, int sigLen){
   double sum = 0;
   for(int k = 0; k < sigLen; k++){
      double f = NXS_SMAv(fastLen, tf, shift + k);
      double sl = NXS_SMAv(slowLen, tf, shift + k);
      sum += (f - sl);
   }
   double signal = sum / sigLen;
   double macdNow = NXS_SMAv(fastLen, tf, shift) - NXS_SMAv(slowLen, tf, shift);
   return macdNow - signal;
}

SNXSSignal NXS_Strat_MacdSma200(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_STRUCT_REACT; s.stratName = "MACD_SMA200";
   if(!InpStrat_MacdSma200 || !NXS_SelectorAllows(45)) return s;
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   datetime curBar0 = iTime(g_sym, tf, 0);
   if(g_macdSmaState.lastBarTime == curBar0) return s;
   g_macdSmaState.lastBarTime = curBar0;

   int fastLen = 12, slowLen = 26, sigLen = 9, verySlowLen = 200;
   double fastMA = NXS_SMAv(fastLen, tf, 1), slowMA = NXS_SMAv(slowLen, tf, 1);
   double veryslowMA = NXS_SMAv(verySlowLen, tf, 1);
   if(fastMA <= 0 || slowMA <= 0 || veryslowMA <= 0) return s;

   double macd = fastMA - slowMA;
   double histCur  = _nxs_macdsma_hist(tf, 1, fastLen, slowLen, sigLen);
   double histPrev = _nxs_macdsma_hist(tf, 2, fastLen, slowLen, sigLen);
   double closeSlowAgo = iClose(g_sym, tf, 1 + slowLen);

   bool crossUp   = (histPrev <= 0 && histCur > 0);
   bool crossDown = (histPrev >= 0 && histCur < 0);

   if(crossUp && macd > 0 && fastMA > slowMA && closeSlowAgo > veryslowMA){
      s.dir = DIR_BUY;  s.score = 60; s.reason = "MACD_SMA200_bull";
   } else if(crossDown && macd < 0 && fastMA < slowMA && closeSlowAgo < veryslowMA){
      s.dir = DIR_SELL; s.score = 60; s.reason = "MACD_SMA200_bear";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ K4e Ichimoku + Hull MA + MACD (script Pine pubblico)
// 28/08 - portata da uno script Pine Script TradingView pubblico ("Ichimoku +
// Daily-Candle_X + HULL-MA_X + MacD"). Inizialmente scartata per sospetto
// repaint, poi corretta la valutazione: la revisione (set 2020) usa
// barmerge.lookahead_off su ogni security() e ha commissione/slippage -
// merita un vero test MT5, non uno scarto a priori (vedi vault).
//
// 5 condizioni in AND (fedeli all'originale, non semplificate):
// 1) Hull MA in salita: hma(price,14) > hma(price,14) di 1 barra fa - dato
//    che la Hull MA e' un filtro lineare, hma(price[1],n) a una barra equivale
//    esattamente a hma(price,n) alla barra precedente, quindi si riduce a un
//    confronto NXS_HMAv(shift=1) vs NXS_HMAv(shift=2).
// 2) Trend giornaliero: apertura D1 di ieri (chiusa) > apertura D1 di
//    l'altro ieri (chiusa) - "Daily-Candle_cross" originale.
// 3) Prezzo (apertura, fonte di default dello script) sopra la Hull MA di 1
//    barra fa.
// 4) Cloud Ichimoku rialzista (leadLine1>leadLine2, letti dagli stessi
//    buffer gia' cachati per il TF attivo).
// 5) MACD costruito su Hull MA (non EMA) sopra la sua signal line - la
//    signal line dell'originale e' anch'essa una Hull MA (hma(MACD,9));
//    qui approssimata con una media semplice del MACD sulle ultime
//    round(sqrt(9))=3 barre per restare dentro un costo di calcolo
//    ragionevole - unica semplificazione dichiarata, il resto e' fedele.
struct SNXSIcHullState { datetime lastBarTime; };
SNXSIcHullState g_icHullState;

SNXSSignal NXS_Strat_IchimokuHullMacd(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_STRUCT_REACT; s.stratName = "ICHIMOKU_HULL_MACD";
   if(!InpStrat_IchimokuHull || !NXS_SelectorAllows(47)) return s;
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   datetime curBar0 = iTime(g_sym, tf, 0);
   if(g_icHullState.lastBarTime == curBar0) return s;
   g_icHullState.lastBarTime = curBar0;

   int hmaLen = 14, macdFast = 12, macdSlow = 26, macdSig = 9;
   double hma1 = NXS_HMAv(hmaLen, tf, 1), hma2 = NXS_HMAv(hmaLen, tf, 2);
   if(hma1 <= 0 || hma2 <= 0) return s;

   double dOpen1 = iOpen(g_sym, PERIOD_D1, 1), dOpen2 = iOpen(g_sym, PERIOD_D1, 2);
   if(dOpen1 <= 0 || dOpen2 <= 0) return s;

   double price = iOpen(g_sym, tf, 1);   // "Source of Price" default = open

   double leadLine1 = g_ichiSpanA, leadLine2 = g_ichiSpanB;
   if(leadLine1 <= 0 || leadLine2 <= 0) return s;

   double macdNow = NXS_HMAv(macdFast, tf, 1) - NXS_HMAv(macdSlow, tf, 1);
   double sigSum = 0; int sigN = (int)MathMax(1, MathRound(MathSqrt(macdSig)));
   for(int k = 0; k < sigN; k++)
      sigSum += NXS_HMAv(macdFast, tf, 1 + k) - NXS_HMAv(macdSlow, tf, 1 + k);
   double aMacd = sigSum / sigN;
   if(macdNow == 0 && aMacd == 0) return s;

   bool hullUp   = hma1 > hma2;
   bool hullDown = hma1 < hma2;
   bool dailyUp   = dOpen1 > dOpen2;
   bool dailyDown = dOpen1 < dOpen2;

   if(hullUp && dailyUp && price > hma2 && leadLine1 > leadLine2 && macdNow > aMacd){
      s.dir = DIR_BUY;  s.score = 62; s.reason = "IchiHullMacd_bull";
   } else if(hullDown && dailyDown && price < hma2 && leadLine1 < leadLine2 && macdNow < aMacd){
      s.dir = DIR_SELL; s.score = 62; s.reason = "IchiHullMacd_bear";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ K4f 3Commas Bot (EMA cross + stop su swing ATR)
// 28/08 - portata da uno script Pine Script TradingView pubblico ("3Commas
// Bot" / "Bj Bot"): incrocio EMA21/EMA50 (default script, altri tipi di MA
// dell'originale non replicati - solo EMA/EMA), stop ancorato allo swing
// low/high (lookback 5 barre, default script) +-1xATR(14), target a R:R
// 1:1 (RnR=1, default originale - non alterato). Nessun trailing (l'opzione
// era OFF di default nello script). Concettualmente simile al nostro
// SAR (incrocio EMA9/21) ma con periodo diverso e stop/target strutturati
// invece di ATR generico - un secondo meccanismo da confrontare.
struct SNXS3CommasState { datetime lastBarTime; };
SNXS3CommasState g_3commasState;

SNXSSignal NXS_Strat_3CommasBot(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_STRUCT_REACT; s.stratName = "3COMMAS_BOT";
   if(!InpStrat_3CommasBot || !NXS_SelectorAllows(48)) return s;
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   datetime curBar0 = iTime(g_sym, tf, 0);
   if(g_3commasState.lastBarTime == curBar0) return s;
   g_3commasState.lastBarTime = curBar0;

   int maLen1 = 21, maLen2 = 50, swingLB = 5;
   double atr = NXS_ATRv(tf, 1, 14);
   if(atr <= 0) return s;

   double ma1cur = NXS_EMAv(maLen1, tf, 1), ma2cur = NXS_EMAv(maLen2, tf, 1);
   double ma1prev = NXS_EMAv(maLen1, tf, 2), ma2prev = NXS_EMAv(maLen2, tf, 2);
   if(ma1cur <= 0 || ma2cur <= 0 || ma1prev <= 0 || ma2prev <= 0) return s;

   bool crossUp   = (ma1prev <= ma2prev && ma1cur > ma2cur);
   bool crossDown = (ma1prev >= ma2prev && ma1cur < ma2cur);
   if(!crossUp && !crossDown) return s;

   int loIdx = iLowest(g_sym, tf, MODE_LOW, swingLB, 1);
   int hiIdx = iHighest(g_sym, tf, MODE_HIGH, swingLB, 1);
   double lowestLow  = (loIdx >= 0) ? iLow(g_sym, tf, loIdx)  : 0;
   double highestHigh= (hiIdx >= 0) ? iHigh(g_sym, tf, hiIdx) : 0;
   if(lowestLow <= 0 || highestHigh <= 0) return s;

   double close1 = iClose(g_sym, tf, 1);
   if(crossUp){
      double stop = lowestLow - atr;
      double risk = close1 - stop;
      if(risk <= 0) return s;
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = stop; s.tpPrice = close1 + risk;   // RnR 1:1, default script originale
      s.score = 58; s.reason = "3CommasBot_bull";
   } else {
      double stop = highestHigh + atr;
      double risk = stop - close1;
      if(risk <= 0) return s;
      s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
      s.slPrice = stop; s.tpPrice = close1 - risk;
      s.score = 58; s.reason = "3CommasBot_bear";
   }
   return s;
}

//------------------------------------ K6 Pivot Extension + Wick Rejection (#49)
// 02/09 - idea originale dell'utente, vista a mano su TradingView (GOLD,
// linee orizzontali estese dai pivot di swing). Precisata dall'utente dopo
// la prima versione (mono-TF): i livelli di supporto/resistenza vengono
// dai pivot (OHLC high/low) di PIU' TIMEFRAME insieme (M15/M30/H1/H4/D1),
// ma il segnale di reversal (buy da supporto, sell da resistenza) va
// valutato solo sulla barra CHIUSA di esecuzione M15 - un pool di livelli
// multi-TF, un solo trigger intraday. Il caso "rompe invece di rimbalzare"
// (breakout) e' volutamente fuori scope qui: e' gia' il lavoro di
// BREAKOUT_ACC e delle altre strategie di rottura del motore.
//
// Diversa da MALAYSIAN_SNR (quella usa il massimo/minimo di CHIUSURA su
// una finestra H4/W1 fissa + filtro di storyline direzionale) - qui sono
// veri pivot frattali (N barre a sinistra e a destra piu' basse/alte),
// pool per timeframe, wick di rigetto OPZIONALE (default off: basta il
// tocco del livello, gia' un OHLC della candela pivot - richiesto
// dall'utente dopo che la versione con wick obbligatorio non produceva
// trade). Mai verificata su MT5. Gate a chiusura barra M15 + raffreddamento
// per direzione fin dall'inizio (bug di inseguimento gia' trovato stanotte
// su BAR_UPDN/BREAKOUT_ACC senza questa protezione).
#define NXS_PIVOTWICK_MAXLVL 8
#define NXS_PIVOTWICK_NTF    5
int g_pivotWickTFs[NXS_PIVOTWICK_NTF] = { PERIOD_M15, PERIOD_M30, PERIOD_H1, PERIOD_H4, PERIOD_D1 };

struct SNXSPivotWickState {
   datetime lastBarTime;                            // gate sulla barra M15 di esecuzione
   datetime lastPivotBar[NXS_PIVOTWICK_NTF];         // una scansione pivot per barra chiusa, per TF
   double   pivHi[NXS_PIVOTWICK_NTF][NXS_PIVOTWICK_MAXLVL];
   double   pivLo[NXS_PIVOTWICK_NTF][NXS_PIVOTWICK_MAXLVL];
   bool     pivHiUsed[NXS_PIVOTWICK_NTF][NXS_PIVOTWICK_MAXLVL];   // 03/09 - zona "fresh/non-fresh"
   bool     pivLoUsed[NXS_PIVOTWICK_NTF][NXS_PIVOTWICK_MAXLVL];
   datetime lastFireTime[2];   // [0]=buy [1]=sell
};
SNXSPivotWickState g_pivotWickState;

void _nxs_pivotwick_push_row(double &arr[][NXS_PIVOTWICK_MAXLVL], bool &used[][NXS_PIVOTWICK_MAXLVL], int row, double level){
   for(int i = NXS_PIVOTWICK_MAXLVL - 1; i > 0; i--){
      arr[row][i] = arr[row][i - 1];
      used[row][i] = used[row][i - 1];
   }
   arr[row][0] = level;
   used[row][0] = false;
}

// Scandaglia UN timeframe per un nuovo pivot frattale, una volta per barra
// chiusa DI QUEL TF (indipendente dal gate M15 della funzione principale).
void _nxs_pivotwick_scan_tf(int tfIdx, ENUM_TIMEFRAMES tf, int L){
   datetime curBarTF = iTime(g_sym, tf, 0);
   if(curBarTF <= 0 || g_pivotWickState.lastPivotBar[tfIdx] == curBarTF) return;
   g_pivotWickState.lastPivotBar[tfIdx] = curBarTF;

   int p = L + 1;   // shift appena confermato come pivot (L barre note a destra)
   double hiP = iHigh(g_sym, tf, p);
   double loP = iLow(g_sym, tf, p);
   if(hiP <= 0 || loP <= 0) return;
   bool isHiPivot = true, isLoPivot = true;
   for(int i = p - L; i <= p + L; i++){
      if(i == p) continue;
      double hh = iHigh(g_sym, tf, i);
      double ll = iLow(g_sym, tf, i);
      if(hh <= 0 || ll <= 0) continue;
      if(hh >= hiP) isHiPivot = false;
      if(ll <= loP) isLoPivot = false;
   }
   if(isHiPivot) _nxs_pivotwick_push_row(g_pivotWickState.pivHi, g_pivotWickState.pivHiUsed, tfIdx, hiP);
   if(isLoPivot) _nxs_pivotwick_push_row(g_pivotWickState.pivLo, g_pivotWickState.pivLoUsed, tfIdx, loP);
}

SNXSSignal NXS_Strat_PivotWick(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_STRUCT_REACT; s.stratName = "PIVOT_WICK";
   if(!InpStrat_PivotWick || !NXS_SelectorAllows(49)) return s;
   ENUM_TIMEFRAMES execTF = NXS_EffTF();   // M15 dal profilo (NXS_Profile_TF)
   datetime curBar0 = iTime(g_sym, execTF, 0);
   if(g_pivotWickState.lastBarTime == curBar0) return s;   // gia' valutata questa barra
   g_pivotWickState.lastBarTime = curBar0;

   int L = InpPivotWickLookback;
   for(int t = 0; t < NXS_PIVOTWICK_NTF; t++)
      _nxs_pivotwick_scan_tf(t, (ENUM_TIMEFRAMES)g_pivotWickTFs[t], L);

   double atr = NXS_ATRv(execTF, 1, 14);
   if(atr <= 0) return s;
   double tol = InpPivotWickTouchTolATR * atr;
   double minWick = InpPivotWickMinWickATR * atr;

   double o1 = iOpen(g_sym, execTF, 1), c1 = iClose(g_sym, execTF, 1);
   double h1 = iHigh(g_sym, execTF, 1), l1 = iLow(g_sym, execTF, 1);
   double body   = MathAbs(c1 - o1);
   double upWick = h1 - MathMax(o1, c1);
   double dnWick = MathMin(o1, c1) - l1;

   long periodSec   = PeriodSeconds(execTF);
   long cooldownSec = (long)InpPivotWickCooldownBars * periodSec;
   bool buyOk  = (g_pivotWickState.lastFireTime[0] == 0) || ((curBar0 - g_pivotWickState.lastFireTime[0]) >= cooldownSec);
   bool sellOk = (g_pivotWickState.lastFireTime[1] == 0) || ((curBar0 - g_pivotWickState.lastFireTime[1]) >= cooldownSec);

   // Condizione di rigetto: se richiesta (InpPivotWickRequireWick), un vero
   // wick sulla candela di tocco M15; altrimenti basta il tocco del livello
   // (gia' un OHLC della candela pivot: high/low, su qualunque dei TF pool).
   bool wickBull = !InpPivotWickRequireWick ||
                   (dnWick >= minWick && dnWick >= InpPivotWickWickRatio * body &&
                    dnWick >= InpPivotWickWickRatio * upWick && c1 > o1);
   bool wickBear = !InpPivotWickRequireWick ||
                   (upWick >= minWick && upWick >= InpPivotWickWickRatio * body &&
                    upWick >= InpPivotWickWickRatio * dnWick && c1 < o1);

   // 03/09 - conferma su CHIUSURA (Rayner Teo, vedi vault "Revisione contro
   // Materiale Esterno"): il solo tocco intrabar (wick) puo' essere uno stop
   // hunt che inverte subito dopo. Se richiesta (InpPivotWickRequireCloseConfirm),
   // valutata per-livello sotto (la chiusura deve rientrare nella stessa
   // zona di tolleranza del livello, non solo il minimo/massimo).

   // 03/09 - filtro anti-buildup (Rayner Teo): un consolidamento stretto
   // (range piccolo vs ATR) nelle ultime N barre PRIMA del tocco e' un
   // segnale di debolezza del livello (probabile rottura, non rigetto) -
   // se richiesto, scarta il tocco in quelle condizioni.
   bool buildupOk = true;
   if(InpPivotWickAvoidBuildup){
      double hiN = iHigh(g_sym, execTF, iHighest(g_sym, execTF, MODE_HIGH, InpPivotWickBuildupBars, 2));
      double loN = iLow (g_sym, execTF, iLowest (g_sym, execTF, MODE_LOW,  InpPivotWickBuildupBars, 2));
      double rangeN = hiN - loN;
      buildupOk = (rangeN >= InpPivotWickBuildupMinATR * atr);
   }

   // BUY: tocco M15 di un livello pivot minimo di QUALUNQUE TF del pool,
   // non ancora "consumato" (InpPivotWickOneShotLevel)
   if(buyOk && wickBull && buildupOk){
      for(int t = 0; t < NXS_PIVOTWICK_NTF && s.dir == DIR_NONE; t++){
         for(int i = 0; i < NXS_PIVOTWICK_MAXLVL; i++){
            if(g_pivotWickState.pivLo[t][i] <= 0) continue;
            if(InpPivotWickOneShotLevel && g_pivotWickState.pivLoUsed[t][i]) continue;
            bool touched = (l1 >= g_pivotWickState.pivLo[t][i] - tol && l1 <= g_pivotWickState.pivLo[t][i] + tol);
            bool closeOk = !InpPivotWickRequireCloseConfirm ||
                           (c1 >= g_pivotWickState.pivLo[t][i] - tol && c1 <= g_pivotWickState.pivLo[t][i] + tol);
            if(touched && closeOk){
               s.dir = DIR_BUY; s.score = 60; s.reason = "PivotWick_buy_" + EnumToString((ENUM_TIMEFRAMES)g_pivotWickTFs[t]);
               g_pivotWickState.lastFireTime[0] = curBar0;
               if(InpPivotWickOneShotLevel) g_pivotWickState.pivLoUsed[t][i] = true;
               break;
            }
         }
      }
   }
   // SELL: tocco M15 di un livello pivot massimo di QUALUNQUE TF del pool,
   // non ancora "consumato"
   if(s.dir == DIR_NONE && sellOk && wickBear && buildupOk){
      for(int t = 0; t < NXS_PIVOTWICK_NTF && s.dir == DIR_NONE; t++){
         for(int i = 0; i < NXS_PIVOTWICK_MAXLVL; i++){
            if(g_pivotWickState.pivHi[t][i] <= 0) continue;
            if(InpPivotWickOneShotLevel && g_pivotWickState.pivHiUsed[t][i]) continue;
            bool touched = (h1 <= g_pivotWickState.pivHi[t][i] + tol && h1 >= g_pivotWickState.pivHi[t][i] - tol);
            bool closeOk = !InpPivotWickRequireCloseConfirm ||
                           (c1 <= g_pivotWickState.pivHi[t][i] + tol && c1 >= g_pivotWickState.pivHi[t][i] - tol);
            if(touched && closeOk){
               s.dir = DIR_SELL; s.score = 60; s.reason = "PivotWick_sell_" + EnumToString((ENUM_TIMEFRAMES)g_pivotWickTFs[t]);
               g_pivotWickState.lastFireTime[1] = curBar0;
               if(InpPivotWickOneShotLevel) g_pivotWickState.pivHiUsed[t][i] = true;
               break;
            }
         }
      }
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
// 02/09 - BUG TROVATO (ipotesi dell'utente, confermata sui dati): stesso
// difetto di BAR_UPDN sotto - nessuno stato "gia' tradato questo breakout",
// la condizione di accettazione resta vera per ogni barra finche' il
// prezzo non rientra nel range, quindi il motore insegue lo stesso
// movimento aprendo un nuovo trade a ogni barra invece di prenderlo una
// volta sola. Verificato: 106 dei 201 trade nudi (M15, 2024) erano
// raggruppati (stesso verso, entro 6h) - es. 7 sell consecutivi tra il 3
// e il 5 gennaio 2024 sullo stesso movimento, solo il primo (+$20.36) in
// profitto, i 6 inseguimenti tutti in perdita (-$2/-5 ciascuno). Sul D1
// nativo il danno era diluito (una barra al giorno); su M15 lo stesso bug
// spara decine di volte in piu'.
//
// PRIMO TENTATIVO (fallito su BAR_UPDN, stesso schema qui): one-shot che
// si resetta appena l'accettazione non e' piu' vera - inefficace perche'
// il rientro nel range e' spesso intermittente (una barra dentro, la
// successiva di nuovo fuori), il reset scatta troppo presto. CORREZIONE:
// raffreddamento per direzione a numero di barre (InpBreakoutAccCooldownBars).
struct SNXSBreakoutAccState { datetime lastBarTime; datetime lastFireTime[2]; };  // [0]=buy [1]=sell
SNXSBreakoutAccState g_breakoutAccState;

SNXSSignal NXS_Strat_BreakoutAcc(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_BREAKOUT_ACC; s.stratName = "BREAKOUT_ACC";
   if(!InpStrat_BREAKOUT_ACC || !NXS_SelectorAllows(9)) return s;
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   datetime curBar0 = iTime(g_sym, tf, 0);
   if(g_breakoutAccState.lastBarTime == curBar0) return s;   // gia' valutata questa barra
   g_breakoutAccState.lastBarTime = curBar0;

   int n = 20;
   double range_hi = iHigh(g_sym, tf, iHighest(g_sym, tf, MODE_HIGH, n, 3));
   double range_lo = iLow (g_sym, tf, iLowest (g_sym, tf, MODE_LOW,  n, 3));
   double c1 = iClose(g_sym, tf, 1);
   double c2 = iClose(g_sym, tf, 2);
   bool acceptUp = (c1 > range_hi && c2 > range_hi);
   bool acceptDn = (c1 < range_lo && c2 < range_lo);

   long periodSec = PeriodSeconds(tf);
   long cooldownSec = (long)InpBreakoutAccCooldownBars * periodSec;
   bool buyOk  = (g_breakoutAccState.lastFireTime[0] == 0) || ((curBar0 - g_breakoutAccState.lastFireTime[0]) >= cooldownSec);
   bool sellOk = (g_breakoutAccState.lastFireTime[1] == 0) || ((curBar0 - g_breakoutAccState.lastFireTime[1]) >= cooldownSec);

   if(acceptUp && buyOk){
      s.dir = DIR_BUY;  s.score = 68; s.reason = "Acceptance_above_range";
      g_breakoutAccState.lastFireTime[0] = curBar0;
   } else if(acceptDn && sellOk){
      s.dir = DIR_SELL; s.score = 68; s.reason = "Acceptance_below_range";
      g_breakoutAccState.lastFireTime[1] = curBar0;
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ Z-Score Breakout (24/08 - porting da server/backtest.py sig_z_score_breakout)
// Ipotesi "quant" (Z-Score + regime SMA200): interpretazione BREAKOUT
// (scommette sulla continuazione) delle bande a 2 deviazioni standard,
// OPPOSTA a BOLLINGER gia' nel motore (mean-reversion, scommette sul
// ritorno alla media) - stesse bande statistiche, ipotesi di mercato
// opposta. Regime: SMA200 sullo stesso TF (bull se close>SMA200, bear se
// close<SMA200), z-score sulla finestra di 20 barre.
//
// Stop NON via profilo ATR: strutturale M5 (minimo/massimo delle ultime
// 12 candele M5 chiuse prima dell'ingresso, pavimento 0.3xATR(H1)),
// stessa famiglia di stop gia' validata su SAR/MACD/ICHIMOKU (vedi vault
// "NEXUS EA - Stop Strutturale M5 su Segnali H1 16-08"). Target 4.0xATR.
// Validata su H1 il 17/08 (`full_catalog_native_stop_17-08.py`): retail
// PF1.29 (4/5 finestre), ECN PF1.71 (5/5 finestre), 557 trade - il
// miglior risultato retail di tutta quell'indagine.
//
// GAP NOTO (come SWING_FALSEBREAK): il filtro di regime ER (Efficiency
// Ratio, lookback lungo) usato nella validazione NON e' un gate live qui.
double _zsb_smaN(int n){
   double s = 0;
   for(int k = 1; k <= n; k++) s += iClose(g_sym, NXS_EffTF(), k);
   return s / n;
}
double _zsb_stdN(int n, double mean){
   double s = 0;
   for(int k = 1; k <= n; k++){
      double d = iClose(g_sym, NXS_EffTF(), k) - mean;
      s += d * d;
   }
   return MathSqrt(s / n);
}
// Minimo/massimo delle 12 candele M5 chiuse piu' recenti (shift 1..12 su
// PERIOD_M5) - stesso concetto di make_m5_stop() nello script Python, qui
// letto direttamente dal terminale invece che dalla cache JSON offline.
double _zsb_m5StructStop(int dir){
   double best = (dir == 1) ? DBL_MAX : -DBL_MAX;
   int found = 0;
   for(int k = 1; k <= 12; k++){
      if(dir == 1){
         double l = iLow(g_sym, PERIOD_M5, k);
         if(l > 0){ if(l < best) best = l; found++; }
      } else {
         double h = iHigh(g_sym, PERIOD_M5, k);
         if(h > 0){ if(h > best) best = h; found++; }
      }
   }
   return (found >= 3) ? best : 0.0;   // stesso min 3 candele del Python (len(window)<3 -> None)
}

SNXSSignal NXS_Strat_ZScoreBreakout(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_BREAKOUT_ACC; s.stratName = "Z_SCORE_BREAKOUT";
   if(!InpStrat_ZScoreBreakout || !NXS_SelectorAllows(42)) return s;
   double atr = (g_atr > 0) ? g_atr : g_point;   // NXS_Strategies.mqh e' incluso prima di _smc_atr() in NXS_Strategies_SMC.mqh, niente dipendenza cross-file
   if(atr <= 0) return s;
   double mean20 = _zsb_smaN(20);
   double sd20   = _zsb_stdN(20, mean20);
   if(sd20 <= 0) return s;
   double c1 = iClose(g_sym, NXS_EffTF(), 1);
   double z  = (c1 - mean20) / sd20;
   double htfSma = _zsb_smaN(200);
   bool bullRegime = c1 > htfSma;
   bool bearRegime = c1 < htfSma;
   int dir = 0;
   if(bullRegime && z > 2.0) dir = 1;
   else if(bearRegime && z < -2.0) dir = -1;
   if(dir == 0) return s;

   double m5lvl = _zsb_m5StructStop(dir);
   if(m5lvl <= 0) return s;
   double entry = (dir == 1) ? SymbolInfoDouble(g_sym, SYMBOL_ASK) : SymbolInfoDouble(g_sym, SYMBOL_BID);
   double riskDist = MathAbs(entry - m5lvl);
   double floorDist = 0.3 * atr;
   if(riskDist < floorDist) riskDist = floorDist;
   if(riskDist <= 0) return s;

   s.dir      = (dir == 1) ? DIR_BUY : DIR_SELL;
   s.entryRef = entry;
   s.slPrice  = (dir == 1) ? entry - riskDist : entry + riskDist;
   s.tpPrice  = (dir == 1) ? entry + 4.0 * atr : entry - 4.0 * atr;
   s.score    = 71.0;
   s.reason   = (dir == 1) ? "ZSB:bull_z>2+M5struct" : "ZSB:bear_z<-2+M5struct";
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
// 27/08 - resi input (stesso bug del gruppo SL/TP in NXS_Inputs.mqh):
// invisibili al Tester/Optimization cosi' com'erano.
input int    InpEMAPB_TrendPersistBars = 5;
input double InpEMAPB_MinDistATR       = 1.0;
input double InpEMAPB_TouchToleranceATR= 0.15;
input bool   InpEMAPB_RequirePressureAligned = false;

// 01/09 - trovato analizzando 80 trade nudi reali (Oct2023-Aug2026, campione
// esteso): a differenza di SAR (dove la pressione CONTRARIA vinceva - cattura
// un'inversione), qui vince la pressione ALLINEATA alla direzione del
// segnale - coerente con la natura di EMA_PULLBACK, una strategia da
// CONTINUAZIONE (il trend deve essere ancora vivo, non esaurito). Verificato
// che regge anche col campione grande (PF1.61 allineata vs 0.72 contraria,
// contro un PF2.23/0.45 iniziale sul campione piccolo - direzione confermata,
// solo meno estrema). Filtrando storicamente solo gli allineati: PF
// 1.51->1.74, netto $821.76->$877.44.
//
// TESTATO SUL VERO TESTER (01/09, periodo esteso 2023-2026): NON migliora.
// PF1.42->1.35, netto $698.88->$581.97, quasi nessuna riduzione dei trade
// (84->83, contro il 21% di blocco atteso offline). Confermato con
// diagnostica temporanea che il gate FUNZIONA correttamente a livello di
// codice (blocca davvero quando la pressione e' contraria) - non e' un bug.
// Stessa lezione di SAR: bloccare un segnale sposta il timing di tutti i
// successivi, un effetto a cascata che l'analisi offline (righe fisse di
// una tabella) non cattura. Lasciato come input disattivabile (default
// false) per riferimento, ma NON adottato - la baseline nuda estesa
// (PF1.42, $698.88, 84 trade) resta il riferimento per EMA_PULLBACK.
bool NXS_EMAPB_PressureAligned(int dir){
   int up = 0; double netBody = 0;
   int N = 8;
   for(int i = 1; i <= N; i++){
      double o = iOpen(g_sym, PERIOD_M15, i), c = iClose(g_sym, PERIOD_M15, i);
      if(c > o) up++;
      netBody += (c - o);
   }
   bool pressureBuy = (up >= N/2) && (netBody > 0);
   return (pressureBuy && dir == DIR_BUY) || (!pressureBuy && dir == DIR_SELL);
}

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
   if(s.dir != DIR_NONE && InpEMAPB_RequirePressureAligned && !NXS_EMAPB_PressureAligned(s.dir)){
      s.dir = DIR_NONE; s.reason = "pressure_contrary";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H6 BB Squeeze Breakout
// 17/07 notte - squeeze relativo alla propria storia, da audit esterno
// canonico: "width <= 2.5xATR" era una soglia assoluta debole, con
// parametri standard la bandwidth puo' spesso rientrarci senza che sia una
// vera contrazione. Ora percentile della bandwidth su una finestra (150
// barre), richiede che lo squeeze sia durato almeno InpBBSQ_MinSqueezeBars
// barre consecutive, breakout solo se la bandwidth sta gia' riespandendo.
// Calcolo bar-gated (una volta per barra chiusa), one-shot per squeeze
// (niente segnali ripetuti sullo stesso squeeze).
int    InpBBSQ_LookbackBars   = 150;
double InpBBSQ_PercentileMax  = 20.0;
int    InpBBSQ_MinSqueezeBars = 5;

struct SNXSBBSqueezeState {
   datetime lastBarTime;
   int      squeezeBars;   // barre consecutive gia' in squeeze
   bool     consumed;      // squeeze corrente gia' usato per un breakout
};
SNXSBBSqueezeState g_bbsqState;

SNXSSignal NXS_Strat_BBSqueeze(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_BB_SQUEEZE; s.stratName = "BB_SQUEEZE";
   if(!InpStrat_BB_SQUEEZE || !NXS_SelectorAllows(12)) return s;
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   datetime curBar0 = iTime(g_sym, tf, 0);
   if(g_bbsqState.lastBarTime == curBar0) return s;   // gia' valutata questa barra
   g_bbsqState.lastBarTime = curBar0;

   int n = InpBBSQ_LookbackBars + 2;
   double up[], lo[], mid[];
   ArraySetAsSeries(up, true); ArraySetAsSeries(lo, true); ArraySetAsSeries(mid, true);
   if(CopyBuffer(g_hBB, 1, 1, n, up)  < n) return s;
   if(CopyBuffer(g_hBB, 2, 1, n, lo)  < n) return s;
   if(CopyBuffer(g_hBB, 0, 1, n, mid) < n) return s;

   double bw1 = (mid[0] > 0) ? (up[0] - lo[0]) / mid[0] : 0;   // bandwidth shift1 (barra chiusa)
   double bw2 = (mid[1] > 0) ? (up[1] - lo[1]) / mid[1] : 0;   // bandwidth shift2
   if(bw1 <= 0) return s;

   int below = 0;
   for(int i = 2; i < n; i++){
      double bwi = (mid[i] > 0) ? (up[i] - lo[i]) / mid[i] : 0;
      if(bwi < bw1) below++;
   }
   double percentile = 100.0 * below / InpBBSQ_LookbackBars;
   bool isSqueeze = (percentile <= InpBBSQ_PercentileMax);

   if(isSqueeze){
      g_bbsqState.squeezeBars++;
   } else {
      g_bbsqState.squeezeBars = 0;
      g_bbsqState.consumed = false;
      return s;   // niente breakout se non siamo (o non siamo appena usciti da) uno squeeze
   }
   if(g_bbsqState.squeezeBars < InpBBSQ_MinSqueezeBars || g_bbsqState.consumed) return s;

   double c1 = iClose(g_sym, tf, 1);
   bool expanding = bw1 > bw2;
   if(!expanding) return s;
   if(c1 > up[0]){
      s.dir = DIR_BUY;  s.score = 70; s.reason = "Squeeze_breakout_up";
   } else if(c1 < lo[0]){
      s.dir = DIR_SELL; s.score = 70; s.reason = "Squeeze_breakout_down";
   }
   if(s.dir != DIR_NONE){
      g_bbsqState.consumed = true;   // one-shot: niente altri segnali su questo stesso squeeze
      NXS_DefaultSLTP(s);
   }
   return s;
}

//------------------------------------ H7 Ichimoku Kumo Break
// 17/07 notte - allineamento temporale corretto, da audit esterno canonico:
// g_ichiSpanA/B/Tenkan/Kijun sono globali cache SOLO a shift1 - "prev"
// (close a shift2) veniva confrontato con la cloud di shift1, non quella
// di shift2 (i buffer Senkou di MT5 sono gia' pre-shiftati internamente
// per il rendering "26 barre avanti", ma vanno comunque letti allo shift
// coerente con la barra che si sta valutando). Ora legge esplicitamente
// entrambi gli shift.
SNXSSignal NXS_Strat_Ichimoku(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_ICHIMOKU; s.stratName = "ICHIMOKU";
   if(!InpStrat_ICHIMOKU || !NXS_SelectorAllows(13)) return s;
   double spanA[], spanB[], tenkan[], kijun[];
   ArraySetAsSeries(spanA, true); ArraySetAsSeries(spanB, true);
   ArraySetAsSeries(tenkan, true); ArraySetAsSeries(kijun, true);
   if(CopyBuffer(g_hICHI, 2, 1, 2, spanA)  < 2) return s;
   if(CopyBuffer(g_hICHI, 3, 1, 2, spanB)  < 2) return s;
   if(CopyBuffer(g_hICHI, 0, 1, 2, tenkan) < 2) return s;
   if(CopyBuffer(g_hICHI, 1, 1, 2, kijun)  < 2) return s;

   double kumoTop1 = MathMax(spanA[0], spanB[0]), kumoBot1 = MathMin(spanA[0], spanB[0]);
   double kumoTop2 = MathMax(spanA[1], spanB[1]), kumoBot2 = MathMin(spanA[1], spanB[1]);
   if(kumoTop1 <= 0 || kumoBot1 <= 0 || kumoTop2 <= 0 || kumoBot2 <= 0) return s;
   double price = iClose(g_sym, NXS_EffTF(), 1);
   double prev  = iClose(g_sym, NXS_EffTF(), 2);
   if(prev <= kumoTop2 && price > kumoTop1 && tenkan[0] > kijun[0]){
      s.dir = DIR_BUY;  s.score = 65; s.reason = "Kumo_break_up";
   } else if(prev >= kumoBot2 && price < kumoBot1 && tenkan[0] < kijun[0]){
      s.dir = DIR_SELL; s.score = 65; s.reason = "Kumo_break_down";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H8b RSI Divergence su pivot (script Pine pubblico)
// 28/08 - portata da uno script Pine Script TradingView pubblico ("RSI
// Divergence Indicator"): metodo di rilevamento diverso dal nostro RSI_DIV
// nativo appena sopra (finestra fissa 8 barre) - qui i pivot RSI veri
// (minimo/massimo locale su lbL+lbR barre) e la distanza tra due pivot deve
// stare in un range (5-60 barre di default), come nello script originale.
// Non un sostituto: un secondo meccanismo da confrontare, dato che il
// nostro nativo e' gia' forte (PF1.21 reale).
struct SNXSRsiDivPineState { datetime lastBarTime; };
SNXSRsiDivPineState g_rsiDivPineState;

bool _nxs_rsidivpine_pivot_low(const double &rsi[], int n, int idx, int lbL, int lbR){
   if(idx - lbL < 0 || idx + lbR >= n) return false;
   double v = rsi[idx];
   for(int k = idx - lbL; k <= idx + lbR; k++){ if(k != idx && rsi[k] < v) return false; }
   return true;
}
bool _nxs_rsidivpine_pivot_high(const double &rsi[], int n, int idx, int lbL, int lbR){
   if(idx - lbL < 0 || idx + lbR >= n) return false;
   double v = rsi[idx];
   for(int k = idx - lbL; k <= idx + lbR; k++){ if(k != idx && rsi[k] > v) return false; }
   return true;
}

SNXSSignal NXS_Strat_RsiDivPine(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_RSI_DIV; s.stratName = "RSI_DIV_PINE";
   if(!InpStrat_RsiDivPine || !NXS_SelectorAllows(46)) return s;
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   datetime curBar0 = iTime(g_sym, tf, 0);
   if(g_rsiDivPineState.lastBarTime == curBar0) return s;
   g_rsiDivPineState.lastBarTime = curBar0;

   int lbL = 1, lbR = 3, rangeLower = 5, rangeUpper = 60;
   int need = rangeUpper + lbR + lbL + 10;
   double rsi[]; ArraySetAsSeries(rsi, true);
   if(CopyBuffer(g_hRSI, 0, 0, need, rsi) < need) return s;
   int n = ArraySize(rsi);

   // scansione dal pivot piu' recente possibile (shift lbR) verso il passato:
   // raccoglie i primi due pivot low e i primi due pivot high confermati.
   int plIdx[2] = {-1,-1}, phIdx[2] = {-1,-1}, plN = 0, phN = 0;
   for(int i = lbR; i < n - lbL && (plN < 2 || phN < 2); i++){
      if(plN < 2 && _nxs_rsidivpine_pivot_low (rsi, n, i, lbL, lbR)) plIdx[plN++] = i;
      if(phN < 2 && _nxs_rsidivpine_pivot_high(rsi, n, i, lbL, lbR)) phIdx[phN++] = i;
   }

   // Bullish regular: pivot RSI piu' recente > pivot precedente (minimo piu'
   // alto), prezzo piu' basso, pivot fresco (confermato adesso, non vecchio).
   if(plN == 2 && plIdx[0] <= lbR + 1){
      int dist = plIdx[1] - plIdx[0];
      if(dist >= rangeLower && dist <= rangeUpper){
         double loRecent = iLow(g_sym, tf, plIdx[0]), loPrev = iLow(g_sym, tf, plIdx[1]);
         if(rsi[plIdx[0]] > rsi[plIdx[1]] && loRecent < loPrev){
            s.dir = DIR_BUY; s.score = 60; s.reason = "RSI_DIV_PINE_bull";
         }
      }
   }
   if(s.dir == DIR_NONE && phN == 2 && phIdx[0] <= lbR + 1){
      int dist = phIdx[1] - phIdx[0];
      if(dist >= rangeLower && dist <= rangeUpper){
         double hiRecent = iHigh(g_sym, tf, phIdx[0]), hiPrev = iHigh(g_sym, tf, phIdx[1]);
         if(rsi[phIdx[0]] < rsi[phIdx[1]] && hiRecent > hiPrev){
            s.dir = DIR_SELL; s.score = 60; s.reason = "RSI_DIV_PINE_bear";
         }
      }
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
