//+------------------------------------------------------------------+
//|  NXS_ElliottFilter.mqh                                            |
//|  25/08 - porting in MQL5 della scoperta piu' forte della sessione |
//|  di ricerca (vedi vault "NEXUS EA - Filtro Elliott Wave Multi-    |
//|  Timeframe, il nuovo ingrediente universale (25-08)" e            |
//|  "Combinazione Trailing + Filtro Elliott, gli effetti si          |
//|  sommano (25-08)"): ZigZag (soglia dev=2.0xATR, plateau-check     |
//|  confermato su griglia 4x4) + le 3 regole classiche di un impulso |
//|  Elliott a 5 onde, sul timeframe d'ingresso della strategia E su  |
//|  D1 (unione OR: basta un grado esaurito per sopprimere - la       |
//|  confluenza AND era quasi inerte, vedi vault).                    |
//|                                                                     |
//|  Su 25 strategie testate in Python: 21 migliorano (14 nettamente),|
//|  2 neutre, 1 marginale, 1 sola peggiora (STRUCT_REACT - il filtro |
//|  rimuove i suoi trade migliori, causa capita e documentata).      |
//|  NXS_Profile_UseElliott() sotto riflette esattamente questo       |
//|  verdetto per-strategia, non un default universale.                |
//+------------------------------------------------------------------+
#ifndef __NXS_ELLIOTT_FILTER_MQH__
#define __NXS_ELLIOTT_FILTER_MQH__

double InpElliottDevMult = 2.0;   // plateau-check 25/08: qualunque valore 1.5-3.0 batte il baseline
#define NXS_ELLIOTT_LOOKBACK_BARS 700
#define NXS_ELLIOTT_MAX_PIVOTS    350

// ---------- ATR per timeframe (stesso pattern cache di NXS_EMAv) ----------
int    g_atrCacheTF[8];
int    g_atrCacheH[8];
int    g_atrCacheN = 0;

double NXS_ATRv(ENUM_TIMEFRAMES tf, int shift, int period = 14){
   int h = INVALID_HANDLE;
   for(int i = 0; i < g_atrCacheN; i++)
      if(g_atrCacheTF[i] == (int)tf){ h = g_atrCacheH[i]; break; }
   if(h == INVALID_HANDLE){
      h = iATR(g_sym, tf, period);
      if(h == INVALID_HANDLE) return 0.0;
      if(g_atrCacheN < 8){
         g_atrCacheTF[g_atrCacheN] = (int)tf; g_atrCacheH[g_atrCacheN] = h; g_atrCacheN++;
      }
   }
   double a[]; ArraySetAsSeries(a, true);
   if(CopyBuffer(h, 0, shift, 1, a) <= 0) return 0.0;
   return a[0];
}

// ---------- ZigZag pivot builder (fedele a build_zigzag_full di oggi) ----------
// Ricostruisce i pivot da maxBars fa (piu' vecchio) a shift=1 (ultima barra
// chiusa), stessa logica del riferimento Python: fase di bootstrap (nessuna
// direzione ancora stabilita, tiene i massimi/minimi correnti) poi fase
// direzionale (estende l'estremo o conferma un pivot quando il prezzo
// inverte di almeno devMult*ATR).
int NXS_BuildZigZagPivots(ENUM_TIMEFRAMES tf, double devMult,
                          int &pivotBar[], double &pivotPrice[], bool &pivotIsHigh[]){
   int available = iBars(g_sym, tf);
   int maxBars = MathMin(NXS_ELLIOTT_LOOKBACK_BARS, available - 2);
   if(maxBars < 50) return 0;

   ArrayResize(pivotBar, NXS_ELLIOTT_MAX_PIVOTS);
   ArrayResize(pivotPrice, NXS_ELLIOTT_MAX_PIVOTS);
   ArrayResize(pivotIsHigh, NXS_ELLIOTT_MAX_PIVOTS);
   int pivotCount = 0;

   int dirUp = -1;   // -1=indeterminato, 0=discesa, 1=salita
   double extPrice = 0; int extBar = 0;
   double bootHi = iHigh(g_sym, tf, maxBars), bootLo = iLow(g_sym, tf, maxBars);
   int bootHiBar = maxBars, bootLoBar = maxBars;

   for(int shift = maxBars - 1; shift >= 1; shift--){
      double a = NXS_ATRv(tf, shift);
      if(a <= 0) continue;
      double dev = devMult * a;
      double hi = iHigh(g_sym, tf, shift);
      double lo = iLow(g_sym, tf, shift);

      if(dirUp == -1){
         if(hi > bootHi){ bootHi = hi; bootHiBar = shift; }
         if(lo < bootLo){ bootLo = lo; bootLoBar = shift; }
         if(hi - bootLo >= dev){
            dirUp = 1;
            if(pivotCount < NXS_ELLIOTT_MAX_PIVOTS){
               pivotBar[pivotCount] = bootLoBar; pivotPrice[pivotCount] = bootLo;
               pivotIsHigh[pivotCount] = false; pivotCount++;
            }
            extPrice = hi; extBar = shift;
         } else if(bootHi - lo >= dev){
            dirUp = 0;
            if(pivotCount < NXS_ELLIOTT_MAX_PIVOTS){
               pivotBar[pivotCount] = bootHiBar; pivotPrice[pivotCount] = bootHi;
               pivotIsHigh[pivotCount] = true; pivotCount++;
            }
            extPrice = lo; extBar = shift;
         }
         continue;
      }
      if(dirUp == 1){
         if(hi > extPrice){ extPrice = hi; extBar = shift; }
         else if(extPrice - lo >= dev){
            if(pivotCount < NXS_ELLIOTT_MAX_PIVOTS){
               pivotBar[pivotCount] = extBar; pivotPrice[pivotCount] = extPrice;
               pivotIsHigh[pivotCount] = true; pivotCount++;
            }
            dirUp = 0; extPrice = lo; extBar = shift;
         }
      } else {
         if(lo < extPrice){ extPrice = lo; extBar = shift; }
         else if(hi - extPrice >= dev){
            if(pivotCount < NXS_ELLIOTT_MAX_PIVOTS){
               pivotBar[pivotCount] = extBar; pivotPrice[pivotCount] = extPrice;
               pivotIsHigh[pivotCount] = false; pivotCount++;
            }
            dirUp = 1; extPrice = hi; extBar = shift;
         }
      }
   }
   return pivotCount;
}

// ---------- Stato di esaurimento (le regole Elliott sugli ultimi 6 pivot) ----------
// +1 = impulso RIALZISTA a 5 onde appena concluso (aspettati correzione,
// sopprimi BUY). -1 = idem ribassista. 0 = nessun esaurimento riconoscibile
// in questo momento.
int NXS_ElliottExhaustionState(ENUM_TIMEFRAMES tf, double devMult){
   int pb[]; double pp[]; bool ph[];
   int n = NXS_BuildZigZagPivots(tf, devMult, pb, pp, ph);
   if(n < 6) return 0;
   double P0=pp[n-6], P1=pp[n-5], P2=pp[n-4], P3=pp[n-3], P4=pp[n-2], P5=pp[n-1];
   bool t0=ph[n-6], t1=ph[n-5], t2=ph[n-4], t3=ph[n-3], t4=ph[n-2], t5=ph[n-1];
   // bullish: L H L H L H
   if(!t0 && t1 && !t2 && t3 && !t4 && t5){
      double w1=P1-P0, w3=P3-P2, w5=P5-P4;
      if(w1>0 && w3>0 && w5>0 && P2>P0 && P4>P1 && w3>=w1 && w3>=w5) return 1;
   }
   // bearish: H L H L H L
   if(t0 && !t1 && t2 && !t3 && t4 && !t5){
      double w1=P0-P1, w3=P2-P3, w5=P4-P5;
      if(w1>0 && w3>0 && w5>0 && P2<P0 && P4<P1 && w3>=w1 && w3>=w5) return -1;
   }
   return 0;
}

// ---------- Cache per timeframe, ricalcolata solo a ogni nuova barra ----------
#define NXS_ELLIOTT_TF_CACHE_MAX 4
int      g_elliottCacheTF2[NXS_ELLIOTT_TF_CACHE_MAX];
datetime g_elliottCacheBarTime[NXS_ELLIOTT_TF_CACHE_MAX];
int      g_elliottCacheState[NXS_ELLIOTT_TF_CACHE_MAX];
int      g_elliottCacheN2 = 0;

int NXS_ElliottExhaustionCached(ENUM_TIMEFRAMES tf){
   datetime curBarTime = iTime(g_sym, tf, 1);
   if(curBarTime == 0) return 0;
   for(int i = 0; i < g_elliottCacheN2; i++){
      if(g_elliottCacheTF2[i] == (int)tf){
         if(g_elliottCacheBarTime[i] == curBarTime) return g_elliottCacheState[i];
         int st = NXS_ElliottExhaustionState(tf, InpElliottDevMult);
         g_elliottCacheBarTime[i] = curBarTime;
         g_elliottCacheState[i] = st;
         return st;
      }
   }
   int st2 = NXS_ElliottExhaustionState(tf, InpElliottDevMult);
   if(g_elliottCacheN2 < NXS_ELLIOTT_TF_CACHE_MAX){
      g_elliottCacheTF2[g_elliottCacheN2] = (int)tf;
      g_elliottCacheBarTime[g_elliottCacheN2] = curBarTime;
      g_elliottCacheState[g_elliottCacheN2] = st2;
      g_elliottCacheN2++;
   }
   return st2;
}

// ---------- API pubblica: entry TF (della strategia) + D1, unione OR ----------
bool NXS_ElliottBlocks(int sigDir){
   if(sigDir == 0) return false;
   int exhEntry = NXS_ElliottExhaustionCached(NXS_EffTF());
   int exhD1    = NXS_ElliottExhaustionCached(PERIOD_D1);
   return (exhEntry == sigDir || exhD1 == sigDir);
}

// ---------- Opt-in per strategia (verdetto esatto del 25/08, non un default) ----------
// true = filtro validato e migliorativo in Python oggi, applicalo.
// false = non testato, o testato e scartato (vedi commenti).
bool NXS_Profile_UseElliott(const string name){
   // STRUCT_REACT: UNICA peggiorativa su 25 testate - il filtro rimuove
   // esattamente i suoi trade migliori (PF5.32 tra i rimossi contro 2.28
   // tra i tenuti - vedi vault "Perche' STRUCT_REACT Peggiora col Filtro
   // Elliott"). Non attivare.
   if(name == "STRUCT_REACT") return false;
   // LIQ_SWEEP e LONDON_BO: neutre nel test (ne' danno ne' aiuto misurabile
   // nel campione), lasciate fuori per prudenza - non validate POSITIVE.
   if(name == "LIQ_SWEEP")    return false;
   if(name == "LONDON_BO")    return false;
   // Le altre 20 testate oggi migliorano (9-21 in modo netto) - vedi vault
   // "Filtro Elliott Wave Multi-Timeframe" e "Combinazione Trailing +
   // Filtro Elliott". Nomi ESATTI come usati da s.stratName nel router
   // (verificati 25/08, non tutti coincidono col nome Python - es. qui e'
   // "MALAYSIAN_SNR", non "MALAYSIAN_SNR_BREAKOUT").
   if(name == "ADX_RSI")            return true;
   if(name == "SAR")                return true;
   if(name == "MACD")               return true;
   if(name == "FVG_CONT")           return true;
   if(name == "BREAKOUT_ACC")       return true;
   if(name == "TSI")                return true;
   if(name == "MALAYSIAN_SNR")      return true;
   if(name == "AMD_CONT")           return true;
   if(name == "BOLLINGER")          return true;
   if(name == "RSI_DIV")            return true;
   if(name == "OTE_CONT")           return true;
   if(name == "FVG_MIT")            return true;
   if(name == "EMA_PULLBACK")       return true;
   if(name == "LDN_REVERSAL")       return true;
   if(name == "TURTLE_SOUP")        return true;
   if(name == "Z_SCORE_BREAKOUT")   return true;
   // Tutte le altre (mai testate col filtro Elliott oggi): non attivare
   // finche' non c'e' una verifica Python dedicata - stesso principio
   // "non promuovere senza dati" seguito per ogni altro ingrediente oggi.
   return false;
}

#endif
