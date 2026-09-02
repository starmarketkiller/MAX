//+------------------------------------------------------------------+
//|  NXS_SignalQuality.mqh - Qualita' dei voti pre-raggruppamento     |
//|                                                                    |
//|  Nel modello istituzionale la conviction e' la SOMMA degli score   |
//|  dei segnali concordi. Se i voti sono grezzi, un voto chiaramente   |
//|  controtrend (es. un OB_MIT che compra dentro un downtrend) pesa    |
//|  quanto un voto valido e sporca la decisione. Qui, DOPO l'update    |
//|  del contesto e PRIMA del raggruppamento:                          |
//|   1) RR sanity: scarta i voti con SL troppo stretto o RR degenere. |
//|   2) DROP controtrend: scarta i voti contro HTF+struttura senza     |
//|      conferma di reversal (CHoCH/reazione/sweep a favore).         |
//|   3) Qualita' -> score: allinea lo score al contesto, cosi' la      |
//|      conviction sommata riflette la QUALITA', non solo il numero.  |
//|  Riusa NXS_Context_DirectionalScore/g_ctx (NXS_MarketContext.mqh). |
//+------------------------------------------------------------------+
#ifndef __NXS_SIGNAL_QUALITY_MQH__
#define __NXS_SIGNAL_QUALITY_MQH__

// 02/09 - BUG TROVATO dopo step40/41: g_regime e' calcolato UNA SOLA VOLTA
// per tick, in cima a OnTick, PRIMA che il ciclo multi-TF attivi il
// timeframe proprio di ogni strategia (NXS_ActivateTF). Alla fine di quel
// ciclo NXS_ActivateOriginal() riporta g_activeTF a InpTFEntry (M15 di
// default) - quindi g_regime finisce sempre calcolato sull'ADX di M15, MAI
// sul TF nativo della strategia da valutare (es. H4 per SAR). Risultato
// osservato: veto collegato e valutato correttamente, ma su 32/32 trade di
// SAR (12gen-12apr26, config vera) non ha mai scartato nulla - stava
// guardando il timeframe sbagliato, non "il mercato non era mai
// ranging/choppy". Qui sotto: stessa formula di NXS_DetectRegime()
// (NXS_MarketAnalysis.mqh) ma calcolata FRESCA sul TF della strategia
// (NXS_Profile_TF(nm)), con handle in cache per TF (stesso pattern di
// NXS_ATRv in NXS_ElliottFilter.mqh) - non tocca g_activeTF, sicuro da
// chiamare senza disturbare il contesto della strategia in corso.
int g_adxCacheTF[8];
int g_adxCacheH[8];
int g_adxCacheN = 0;

double NXS_ADXv(ENUM_TIMEFRAMES tf, int shift, int period = 14){
   int h = INVALID_HANDLE;
   for(int i = 0; i < g_adxCacheN; i++)
      if(g_adxCacheTF[i] == (int)tf){ h = g_adxCacheH[i]; break; }
   if(h == INVALID_HANDLE){
      h = iADX(g_sym, tf, period);
      if(h == INVALID_HANDLE) return 0.0;
      if(g_adxCacheN < 8){
         g_adxCacheTF[g_adxCacheN] = (int)tf; g_adxCacheH[g_adxCacheN] = h; g_adxCacheN++;
      }
   }
   double a[]; ArraySetAsSeries(a, true);
   if(CopyBuffer(h, 0, shift, 1, a) <= 0) return 0.0;
   return a[0];
}

ENUM_NXS_REGIME NXS_DetectRegimeTF(ENUM_TIMEFRAMES tf){
   double adxNow = NXS_ADXv(tf, 1, 14);
   double atrNow = NXS_ATRv(tf, 1, 14);
   if(adxNow <= 0 || atrNow <= 0) return REGIME_UNKNOWN;
   double sum = 0; int cnt = 0;
   for(int i = 2; i <= 21; i++){
      double a = NXS_ATRv(tf, i, 14);
      if(a > 0){ sum += a; cnt++; }
   }
   double atrPrev = (cnt > 0) ? sum / cnt : 0;
   bool volatile_ = (atrPrev > 0 && atrNow > atrPrev * 1.5);
   if(adxNow >= 30) return volatile_ ? REGIME_VOLATILE : REGIME_STRONG_TREND;
   if(adxNow >= 20) return REGIME_WEAK_TREND;
   if(adxNow <  15 && volatile_) return REGIME_CHOPPY;
   return REGIME_RANGING;
}

// #9 Veto di regime: la strategia va scartata se opera nell'ambiente sbagliato.
// Conservativo: veta solo i mismatch piu' netti (mean-reversion in forte trend,
// trend/breakout in range/choppy). Tutto il resto (SMC/struttura/reversal) passa.
bool _nxs_regime_veto(const string nm){
   // 02/09 - la classificazione sotto e' condivisa da due chiamanti: il
   // modello istituzionale (InpInstRegimeVeto, sotto) e il percorso a
   // profili (InpProfileRegimeVeto, vedi NXS_OpenTrade in NXS_Execution.mqh
   // - mai collegato prima, richiesto dall'utente per testare se il veto di
   // regime avrebbe evitato dei trade nella peggior sequenza di perdite di
   // SAR, 12/01-12/04/2026, 34/41 perdenti). Basta uno dei due flag attivo.
   if(!InpInstRegimeVeto && !InpProfileRegimeVeto) return false;
   bool meanRev = (nm == "BOLLINGER" || nm == "BB_SQUEEZE" || nm == "RANGE_FADE" ||
                   nm == "RSI_DIV"   || StringFind(nm, "MALAYSIAN_SNR") >= 0);
   bool trendFollow = (nm == "ADX_RSI" || nm == "MACD" || nm == "SAR" || nm == "TSI" ||
                       nm == "EMA_PULLBACK" || nm == "ICHIMOKU" || nm == "BJORGUM" ||
                       nm == "BREAKOUT_ACC" || nm == "LONDON_BO");
   if(!meanRev && !trendFollow) return false;
   ENUM_TIMEFRAMES tf = NXS_Profile_TF(nm);
   if(tf == PERIOD_CURRENT) tf = NXS_EffTF();   // strategie senza TF dedicato nel profilo
   ENUM_NXS_REGIME regime = NXS_DetectRegimeTF(tf);
   if(meanRev && regime == REGIME_STRONG_TREND) return true;
   if(trendFollow && (regime == REGIME_RANGING || regime == REGIME_CHOPPY)) return true;
   return false;
}

void NXS_ApplyContextQuality(SNXSSignal &all[], int n){
   if(!InpInstUseContextQuality) return;
   double atr = (g_atr > 0 ? g_atr : g_point * 100.0);

   // --- Soglia di volatilita' minima: mercato flat -> nessun voto ---
   // (l'ATR corrente sotto una frazione della sua media = chop che brucia stop).
   if(InpInstMinATRfactor > 0 && g_atrAvg > 0 && g_atr < InpInstMinATRfactor * g_atrAvg){
      for(int k = 0; k < n; k++) all[k].dir = DIR_NONE;
      return;
   }

   // --- Range Premium/Discount su H1 (calcolato una volta) ---
   double pdHi = 0, pdLo = 0; bool pdOk = false;
   if(InpInstPremDiscVeto){
      int hh = iHighest(g_sym, PERIOD_H1, MODE_HIGH, InpPDLookbackH1, 1);
      int ll = iLowest (g_sym, PERIOD_H1, MODE_LOW,  InpPDLookbackH1, 1);
      if(hh >= 0 && ll >= 0){
         pdHi = iHigh(g_sym, PERIOD_H1, hh);
         pdLo = iLow (g_sym, PERIOD_H1, ll);
         pdOk = (pdHi > pdLo);
      }
   }
   double pxNow = SymbolInfoDouble(g_sym, SYMBOL_BID);

   for(int i = 0; i < n; i++){
      if(all[i].dir == DIR_NONE) continue;
      int d = (int)all[i].dir;

      // --- 0) Veto di regime: fuori dal suo ambiente, il voto non conta ---
      if(_nxs_regime_veto(all[i].stratName)){
         all[i].dir = DIR_NONE;
         all[i].reason = "drop:regime";
         continue;
      }

      // --- 0a) MTF: i due tempi devono essere d'accordo ---
      // La direzione deve concordare col bias H4 (continuazione), salvo reversal
      // confermato (CHoCH/reazione a favore). Toglie il rumore dei trade a caso.
      if(InpMTFRequireHTF && g_ctx.valid && g_ctx.htfBias != 0){
         bool agreesHTF = (g_ctx.htfBias == d);
         bool revExc    = (g_ctx.chochDir == d || g_ctx.reactionDir == d);
         if(!agreesHTF && !revExc){
            all[i].dir = DIR_NONE;
            all[i].reason = "drop:vs H4 bias";
            continue;
         }
      }

      // --- 0b) Premium/Discount: niente compra-il-massimo / vendi-il-minimo ---
      if(pdOk){
         double pos = (pxNow - pdLo) / (pdHi - pdLo);   // 0=minimo range, 1=massimo
         if((d > 0 && pos > InpPDExtreme) ||            // buy in premium profondo
            (d < 0 && pos < 1.0 - InpPDExtreme)){       // sell in sconto profondo
            all[i].dir = DIR_NONE;
            all[i].reason = "drop:prem/disc";
            continue;
         }
      }

      // --- 1) RR sanity (solo sui voti che portano SL/entry propri) ---
      if(all[i].slPrice > 0 && all[i].entryRef > 0){
         double slDist = MathAbs(all[i].entryRef - all[i].slPrice);
         if(InpInstMinSLATR > 0 && slDist < atr * InpInstMinSLATR){
            all[i].dir = DIR_NONE;
            all[i].reason = StringFormat("drop:SL<%.2fATR", InpInstMinSLATR);
            continue;
         }
         if(InpInstMinRR > 0 && all[i].tpPrice > 0){
            double tpDist = MathAbs(all[i].tpPrice - all[i].entryRef);
            if(slDist > 0 && tpDist / slDist < InpInstMinRR){
               all[i].dir = DIR_NONE;
               all[i].reason = StringFormat("drop:RR<%.2f", InpInstMinRR);
               continue;
            }
         }
      }

      if(!g_ctx.valid) continue;

      // --- 2) DROP controtrend chiaro senza conferma di reversal ---
      bool htfAgainst    = (g_ctx.htfBias     == -d);
      bool structAgainst = (g_ctx.structTrend == -d);
      bool revConfirm    = (g_ctx.chochDir  == d ||
                            g_ctx.reactionDir == d ||
                            g_ctx.sweepDir    == d);
      if(InpInstCtxDropCounter && htfAgainst && structAgainst && !revConfirm){
         all[i].dir = DIR_NONE;
         all[i].reason = "drop:contro HTF+struct no-rev";
         continue;
      }

      // --- 3) Qualita' di contesto -> score (conviction significativa) ---
      double ctx = NXS_Context_DirectionalScore(d);
      ctx = MathMax(-InpCtxMaxPenalty, MathMin(InpCtxMaxBonus, ctx));
      all[i].score = MathMax(0.0, MathMin(100.0, all[i].score + ctx));
   }
}

#endif
