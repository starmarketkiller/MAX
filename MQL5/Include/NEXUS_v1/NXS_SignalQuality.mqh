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

// #9 Veto di regime: la strategia va scartata se opera nell'ambiente sbagliato.
// Conservativo: veta solo i mismatch piu' netti (mean-reversion in forte trend,
// trend/breakout in range/choppy). Tutto il resto (SMC/struttura/reversal) passa.
bool _nxs_regime_veto(const string nm){
   if(!InpInstRegimeVeto) return false;
   bool meanRev = (nm == "BOLLINGER" || nm == "BB_SQUEEZE" || nm == "RANGE_FADE" ||
                   nm == "RSI_DIV"   || StringFind(nm, "MALAYSIAN_SNR") >= 0);
   if(meanRev && g_regime == REGIME_STRONG_TREND) return true;
   bool trendFollow = (nm == "ADX_RSI" || nm == "MACD" || nm == "SAR" || nm == "TSI" ||
                       nm == "EMA_PULLBACK" || nm == "ICHIMOKU" || nm == "BJORGUM" ||
                       nm == "BREAKOUT_ACC" || nm == "LONDON_BO");
   if(trendFollow && (g_regime == REGIME_RANGING || g_regime == REGIME_CHOPPY)) return true;
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
