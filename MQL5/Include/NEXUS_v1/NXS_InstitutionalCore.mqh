//+------------------------------------------------------------------+
//|  NXS_InstitutionalCore.mqh - Modello istituzionale (v2.1.0)      |
//|  Una lettura unica del mercato guida tutto:                      |
//|   1) raccoglie i segnali gia' prodotti dalle 37 strategie        |
//|   2) li RAGGRUPPA per direzione (confluenza = 1 posizione forte)  |
//|   3) classifica CONTINUAZIONE vs REVERSAL                         |
//|   4) calcola il TIER dinamico = quanto in alto e' confermato ->  |
//|      determina ampiezza SL/TP e durata (trend largo vs scalp)     |
//|  Le strategie CONFERMANO, non decidono da sole.                  |
//|  Dietro InpUseInstitutionalCore (OFF di default).                |
//+------------------------------------------------------------------+
#ifndef __NXS_INSTITUTIONAL_CORE_MQH__
#define __NXS_INSTITUTIONAL_CORE_MQH__

#define NXS_SETUP_CONTINUATION  0
#define NXS_SETUP_REVERSAL      1

struct SNXSDecision {
   ENUM_NXS_DIR    dir;          // direzione dominante
   double          confidence;   // conviction netta aggregata (dir dominante - opposta)
   int             tier;         // 0=local .. 3=D1: quanto in alto e' confermato
   ENUM_TIMEFRAMES tierTF;       // TF associato al tier (per SL/TP e durata)
   int             setupType;    // NXS_SETUP_CONTINUATION | NXS_SETUP_REVERSAL
   int             contributors; // quante strategie concordano
   double          entryRef;
   double          slPrice;
   double          tpPrice;
   string          topStrat;     // strategia col punteggio piu' alto nel gruppo
   string          group;        // firma della collaborazione: "TSI+ADX_RSI+..."
   string          reason;
   bool            valid;
};

// Conta le posizioni core aperte nella direzione data (per il modello
// "1 posizione per direzione": gli add di grid/recovery arrivano in Fase 3).
int NXS_Inst_OpenPositionsInDir(ENUM_NXS_DIR dir){
   int cnt = 0;
   long want = (dir == DIR_BUY) ? POSITION_TYPE_BUY : POSITION_TYPE_SELL;
   for(int i = PositionsTotal() - 1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      if(PositionGetInteger(POSITION_TYPE) == want) cnt++;
   }
   return cnt;
}

// Tag di contesto per il comment: "TF-C/R" (es. "H4-R" = timeframe H4,
// Reversal / "M15-C" = M15, Continuazione). Cosi' in MT5 si vede a colpo
// d'occhio su che timeframe e con che tipo di setup e' aperta la posizione.
string NXS_Inst_CtxTag(SNXSDecision &d){
   string tf = StringSubstr(EnumToString(d.tierTF), 7);   // "M15","H1","H4","D1"
   string cr = (d.setupType == NXS_SETUP_REVERSAL) ? "R" : "C";
   return tf + "-" + cr;
}

// TF associato a ciascun tier (0=local usa il TF di esecuzione).
ENUM_TIMEFRAMES _nxs_inst_tierTF(int tier){
   if(tier >= 3) return PERIOD_D1;
   if(tier == 2) return PERIOD_H4;
   if(tier == 1) return PERIOD_H1;
   return InpTFEntry;
}

// Quanti concetti del contesto sono allineati con la direzione -> tier.
int _nxs_inst_tier(int dir){
   if(!g_ctx.valid) return 0;
   int a = 0;
   if(g_ctx.structTrend == dir) a++;
   if(g_ctx.bosDir      == dir) a++;
   if(g_ctx.htfBias     == dir) a++;
   if(g_ctx.sweepDir    == dir) a++;
   if(g_ctx.zoneDir     == dir) a++;
   if(g_ctx.reactionDir == dir) a++;
   if(a >= 5) return 3;
   if(a >= 3) return 2;
   if(a >= 1) return 1;
   return 0;
}

// Continuazione (con il trend) o reversal (la direzione cambia a una flip zone).
int _nxs_inst_setupType(int dir){
   if(!g_ctx.valid) return NXS_SETUP_CONTINUATION;
   // Reversal: si va CONTRO il trend di struttura, ma con CHoCH o reazione a
   // favore (tipico ribaltamento ex-zona buy->sell / sell->buy).
   if(g_ctx.structTrend == -dir &&
      (g_ctx.chochDir == dir || g_ctx.reactionDir == dir))
      return NXS_SETUP_REVERSAL;
   return NXS_SETUP_CONTINUATION;
}

// Costruisce la decisione dominante raggruppando i segnali per direzione.
// Ritorna d.valid=false se non c'e' conviction sufficiente.
SNXSDecision NXS_Institutional_Decide(SNXSSignal &all[], int n){
   SNXSDecision d; ZeroMemory(d); d.dir = DIR_NONE; d.valid = false;
   if(!InpUseInstitutionalCore) return d;

   double buySum = 0, sellSum = 0;
   int    buyN = 0, sellN = 0;
   double topBuy = -1, topSell = -1;
   string topBuyName = "", topSellName = "";
   double topBuySL = 0, topSellSL = 0;   // SL strutturale del voto dominante
   for(int i = 0; i < n; i++){
      if(all[i].dir == DIR_BUY){
         buySum += all[i].score; buyN++;
         if(all[i].score > topBuy){ topBuy = all[i].score; topBuyName = all[i].stratName; topBuySL = all[i].slPrice; }
      } else if(all[i].dir == DIR_SELL){
         sellSum += all[i].score; sellN++;
         if(all[i].score > topSell){ topSell = all[i].score; topSellName = all[i].stratName; topSellSL = all[i].slPrice; }
      }
   }
   if(buyN == 0 && sellN == 0) return d;

   int dir = (buySum >= sellSum) ? +1 : -1;
   double net = MathAbs(buySum - sellSum);   // conviction netta: piu' concordano, piu' e' forte
   int contributors = (dir > 0) ? buyN : sellN;
   if(net < InpInstMinConviction) return d;
   if(contributors < InpInstMinContributors) return d;

   int tier   = _nxs_inst_tier(dir);
   int setup  = _nxs_inst_setupType(dir);
   ENUM_TIMEFRAMES tf = _nxs_inst_tierTF(tier);

   // Firma della collaborazione: nomi delle strategie concordi (ordine di score,
   // all[] e' gia' ordinato), troncata per stare nel comment MT5.
   ENUM_NXS_DIR wantDir = (dir > 0) ? DIR_BUY : DIR_SELL;
   string group = "";
   int gAdded = 0;
   for(int i = 0; i < n; i++){
      if(all[i].dir != wantDir) continue;
      string nm = all[i].stratName;
      if(StringLen(group) + StringLen(nm) + 1 > 20){ group += "+"; break; }  // cap: lascia spazio a score+ctx nel comment MT5
      if(gAdded > 0) group += "+";
      group += nm;
      gAdded++;
   }
   if(StringLen(group) == 0) group = ((dir > 0) ? topBuyName : topSellName);

   // SL/TP larghi, scalati sul tier (usa l'ATR del TF di esecuzione x fattore
   // del tier -> nessun doppio conteggio; piu' alto e' il tier, piu' respiro).
   double atr = (g_atr > 0 ? g_atr : g_point * 100.0);
   double tfMult = NXS_TF_SLTPMult(tf);
   double slDist = atr * InpInstBaseSL * tfMult;
   double tpDist = atr * InpInstBaseTP * tfMult;

   d.dir          = (dir > 0) ? DIR_BUY : DIR_SELL;
   d.confidence   = net;
   d.tier         = tier;
   d.tierTF       = tf;
   d.setupType    = setup;
   d.contributors = contributors;
   d.entryRef     = (dir > 0) ? SymbolInfoDouble(g_sym, SYMBOL_ASK)
                              : SymbolInfoDouble(g_sym, SYMBOL_BID);
   d.slPrice      = (dir > 0) ? d.entryRef - slDist : d.entryRef + slDist;
   d.tpPrice      = (dir > 0) ? d.entryRef + tpDist : d.entryRef - tpDist;

   // A) Allarga lo SL del gruppo oltre l'invalidazione strutturale del voto
   //    dominante (es. sotto l'OB / oltre lo sweep), ma non oltre InpInstMaxSLwiden
   //    volte lo SL di tier -> lo stop sta oltre l'invalidazione senza rovinare l'RR.
   double structSL = (dir > 0) ? topBuySL : topSellSL;
   if(InpInstMaxSLwiden > 0 && structSL > 0){
      double cap = slDist * InpInstMaxSLwiden;
      if(dir > 0 && structSL < d.slPrice){          // struttura piu' in basso
         d.slPrice = MathMax(structSL, d.entryRef - cap);
      } else if(dir < 0 && structSL > d.slPrice){   // struttura piu' in alto
         d.slPrice = MathMin(structSL, d.entryRef + cap);
      }
   }
   d.topStrat     = (dir > 0) ? topBuyName : topSellName;
   d.group        = group;
   d.reason = StringFormat("INST %s tier%d %s conv=%.0f [%s]",
                           (dir > 0 ? "BUY" : "SELL"), tier,
                           (setup == NXS_SETUP_REVERSAL ? "REV" : "CONT"),
                           net, group);
   d.valid = true;
   return d;
}

#endif
