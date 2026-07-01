//+------------------------------------------------------------------+
//|  NXS_MarketContext.mqh - Market Context Layer (v2.0.19)           |
//|  Aggrega gli stati di mercato GIA' calcolati (HTF, struttura,     |
//|  sweep, reazione, zone FVG/OB, AMD) in un punteggio di confluenza |
//|  direzionale e lo applica come bonus/penalita' allo score dei     |
//|  segnali. Non calcola nuovi indicatori: solo aggregazione+peso.   |
//|  Dietro InpUseMarketContext (OFF di default).                     |
//+------------------------------------------------------------------+
#ifndef __NXS_MARKET_CONTEXT_MQH__
#define __NXS_MARKET_CONTEXT_MQH__

struct SNXSContext {
   int    htfBias;       // +1 bull, -1 bear, 0 neutral
   int    structTrend;   // +1/-1/0
   int    bosDir;        // +1/-1/0
   int    chochDir;      // +1/-1/0
   int    reactionDir;   // +1/-1/0
   double reactionQ;     // 0-100
   int    sweepDir;      // +1/-1/0 (solo se confermato)
   int    zoneDir;       // +1/-1/0 (zona FVG/OB attiva dominante vicino al prezzo)
   bool   amdActive;     // fase AMD manipulation/distribution
   bool   valid;
};
SNXSContext g_ctx;

int _NXS_HtfToDir(ENUM_NXS_HTF b){
   if(b == HTF_BULL) return +1;
   if(b == HTF_BEAR) return -1;
   return 0;
}

// Aggrega lo stato di mercato in uno snapshot direzionale. Legge g_struct,
// g_reaction, g_levels (gia' aggiornati sul nuovo bar) + htf/sweep/amd correnti.
void NXS_Context_Update(SNXSHTF &htf, SNXSSweep &sweep, SNXSAMD &amd){
   g_ctx.htfBias     = _NXS_HtfToDir(htf.bias);
   g_ctx.structTrend = g_struct.trend;
   g_ctx.bosDir      = g_struct.bosUp ? +1 : (g_struct.bosDown ? -1 : 0);
   g_ctx.chochDir    = g_struct.chochUp ? +1 : (g_struct.chochDown ? -1 : 0);
   g_ctx.reactionDir = g_reaction.detected ? g_reaction.direction : 0;
   g_ctx.reactionQ   = g_reaction.detected ? g_reaction.quality : 0.0;
   g_ctx.sweepDir    = (sweep.confirmed ? (int)sweep.dir : 0);
   g_ctx.amdActive   = (amd.phase == AMD_MANIPULATION || amd.phase == AMD_DISTRIBUTION);

   // Zona FVG/OB attiva dominante entro InpCtxZoneATR*ATR dal prezzo corrente.
   double price = iClose(g_sym, InpTFEntry, 0);
   double tol   = MathMax(g_atr, g_point * 10.0) * InpCtxZoneATR;
   int bull = 0, bear = 0;
   for(int i = 0; i < g_levelCount; i++){
      if(!g_levels[i].active) continue;
      if(g_levels[i].mitigated && g_levels[i].mitigations >= 2) continue;
      double mid = (g_levels[i].priceTop + g_levels[i].priceBot) * 0.5;
      if(MathAbs(price - mid) > tol) continue;
      ENUM_NXS_LEVEL_TYPE t = g_levels[i].type;
      if(t == NXS_LVL_FVG_BULL || t == NXS_LVL_OB_BULL)      bull++;
      else if(t == NXS_LVL_FVG_BEAR || t == NXS_LVL_OB_BEAR) bear++;
   }
   g_ctx.zoneDir = (bull > bear) ? +1 : (bear > bull ? -1 : 0);
   g_ctx.valid = true;
}

// Punteggio di confluenza di contesto per una direzione (+1 BUY / -1 SELL).
// Quando piu' condizioni istituzionali si allineano (sweep+reazione+zona),
// il loro peso puo' superare la penalita' del contro-HTF -> il setup vince.
double NXS_Context_DirectionalScore(int dir){
   if(!g_ctx.valid || dir == 0) return 0.0;
   double s = 0.0;
   // HTF: bonus se allineato, penalita' se contro
   if(g_ctx.htfBias == dir)       s += InpCtxW_HTF;
   else if(g_ctx.htfBias == -dir) s -= InpCtxW_HTF * InpCtxCounterFactor;
   // Trend di struttura
   if(g_ctx.structTrend == dir)       s += InpCtxW_Struct;
   else if(g_ctx.structTrend == -dir) s -= InpCtxW_Struct * 0.5;
   // BOS / CHoCH in direzione
   if(g_ctx.bosDir   == dir) s += InpCtxW_BOS;
   if(g_ctx.chochDir == dir) s += InpCtxW_CHoCH;
   // Reazione (pesata per qualita')
   if(g_ctx.reactionDir == dir) s += InpCtxW_React * (g_ctx.reactionQ / 100.0);
   // Liquidity sweep confermato
   if(g_ctx.sweepDir == dir) s += InpCtxW_Sweep;
   // Zona FVG/OB attiva vicina
   if(g_ctx.zoneDir == dir) s += InpCtxW_Zone;
   // Regime AMD attivo (non direzionale)
   if(g_ctx.amdActive) s += InpCtxW_AMD;
   return s;
}

// Applica bonus/penalita' di contesto allo score di un segnale, con tetti.
double NXS_Context_ApplyBonus(int dir, double baseScore){
   if(!InpUseMarketContext) return baseScore;
   double ctx = NXS_Context_DirectionalScore(dir);
   ctx = MathMax(-InpCtxMaxPenalty, MathMin(InpCtxMaxBonus, ctx));
   double outv = baseScore + ctx;
   return MathMax(0.0, MathMin(100.0, outv));
}

#endif
