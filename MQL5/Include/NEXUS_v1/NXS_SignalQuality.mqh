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

void NXS_ApplyContextQuality(SNXSSignal &all[], int n){
   if(!InpInstUseContextQuality) return;
   double atr = (g_atr > 0 ? g_atr : g_point * 100.0);

   for(int i = 0; i < n; i++){
      if(all[i].dir == DIR_NONE) continue;
      int d = (int)all[i].dir;

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
