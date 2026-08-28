//+------------------------------------------------------------------+
//|  NXS_BlockerDiagnostics.mqh                                       |
//|  Phase 1 - Count and log every reason an entry was blocked        |
//+------------------------------------------------------------------+
#ifndef __NXS_BLOCKER_DIAG_MQH__
#define __NXS_BLOCKER_DIAG_MQH__

enum ENUM_NXS_BLOCK {
   BLK_NONE = 0,
   BLK_NO_SIGNAL,
   BLK_COOLDOWN,
   BLK_MTF,
   BLK_HTF,
   BLK_VELOCITY,
   BLK_NEWS,
   BLK_SPREAD,
   BLK_PROTECTIONS,
   BLK_SCORE_BELOW,
   BLK_PREFLIGHT,
   BLK_LICENSE,
   BLK_PAUSED,
   BLK_SEND_FAILED,
   // 25/08 - separata dal PREFLIGHT generico su richiesta esplicita
   // dell'utente durante il debug live (account 318337486): il rifiuto
   // "lotto minimo rischierebbe X contro budget Y" (NXS_CalcLotRisk,
   // lot_calc_zero) e' una causa DIVERSA e diagnosticabile a se' (conto
   // troppo piccolo per lo stop della strategia su questo simbolo), non
   // un errore generico di margine/stop/volume come le altre cause che
   // restano in PREFLIGHT.
   BLK_RISK_SIZE,
   // 25/08 - filtro Elliott multi-timeframe (NXS_ElliottFilter.mqh):
   // segnale soppresso perche' un impulso a 5 onde si e' appena esaurito
   // nella stessa direzione, sul TF d'ingresso o su D1 (vedi
   // NXS_ElliottBlocks). Categoria dedicata, non PREFLIGHT generico.
   BLK_ELLIOTT,
   BLK_MAX
};

string g_blockNames[16] = {
   "NONE","NO_SIGNAL","COOLDOWN","MTF","HTF","VELOCITY","NEWS",
   "SPREAD","PROTECTIONS","SCORE_BELOW","PREFLIGHT","LICENSE","PAUSED","SEND_FAILED",
   "RISK_SIZE","ELLIOTT"
};

long g_blockCount[16];
long g_decisionTicks = 0;
datetime g_lastDecisionReport = 0;

// v2.1.7 — mappa la causa PRECISA di un fallimento apertura (g_nxsLastOpenFailure)
// sul bucket giusto, invece di buttare tutto in PREFLIGHT ("ambiguous" nei test).
// Cosi' il prossimo test dice davvero PERCHE' non ha aperto.
ENUM_NXS_BLOCK NXS_BlkFromFailure(const string r){
   if(StringLen(r) == 0)                        return BLK_PREFLIGHT;
   if(StringFind(r, "cooldown")           >= 0) return BLK_COOLDOWN;
   if(StringFind(r, "spread")             >= 0) return BLK_SPREAD;
   if(StringFind(r, "exhaustion")         >= 0 ||
      StringFind(r, "exposure")           >= 0 ||
      StringFind(r, "bar_dir_cap")        >= 0) return BLK_PROTECTIONS;
   if(StringFind(r, "license")            >= 0) return BLK_LICENSE;
   if(StringFind(r, "disabled_dashboard") >= 0) return BLK_PAUSED;
   if(StringFind(r, "retcode")            >= 0 ||
      StringFind(r, "order_send")         >= 0 ||
      StringFind(r, "send_failed")        >= 0) return BLK_SEND_FAILED;
   if(StringFind(r, "lot_calc_zero")      >= 0) return BLK_RISK_SIZE;
   if(StringFind(r, "elliott")            >= 0) return BLK_ELLIOTT;
   return BLK_PREFLIGHT;   // margin, invalid stops, sl distance
}

void NXS_Blk_Reset(){
   for(int i = 0; i < BLK_MAX; i++) g_blockCount[i] = 0;
   g_decisionTicks = 0;
   g_lastDecisionReport = 0;
}

void NXS_Blk_Bump(ENUM_NXS_BLOCK b){
   if(b >= 0 && b < BLK_MAX) g_blockCount[b]++;
}

void NXS_Blk_DecisionTick(){ g_decisionTicks++; }

// Print the dominant blocker counters every 60s.
// v2.0.8c: always-on summary (ignores InpDebugDecisionLog), so the trader can
// always see WHY trades aren't opening even with verbose logs disabled.
void NXS_Blk_MaybeReport(){
   datetime now = TimeCurrent();
   if(g_lastDecisionReport == 0){ g_lastDecisionReport = now; return; }
   if(now - g_lastDecisionReport < 60) return;          // every 60s
   g_lastDecisionReport = now;

   // Build summary
   string out = StringFormat("[NEXUS BLOCK] decision_ticks=%I64d", g_decisionTicks);
   bool anyBlocker = false;
   for(int i = 1; i < BLK_MAX; i++){
      if(g_blockCount[i] == 0) continue;
      out += StringFormat(" %s=%I64d", g_blockNames[i], g_blockCount[i]);
      anyBlocker = true;
   }
   if(!anyBlocker && g_decisionTicks == 0){
      out += " (no signals processed — check Spread/News/Protections upstream)";
   }
   if(!anyBlocker && g_decisionTicks > 0){
      out += " (decision loop ran, no strategy generated signal — check HTF bias vs intent)";
   }
   Print(out);
}

// Decision log per signal evaluation (v2.0.3: base, penalized, final, threshold)
void NXS_Blk_LogDecision(string strat, string dir,
                         double base, double penalized, double finalScore,
                         double threshold, string gates, string reason){
   if(!InpDebugDecisionLog) return;
   PrintFormat("[NEXUS DECISION] strat=%s dir=%s base=%.1f pen=%.1f final=%.1f thr=%.1f gates={%s} reason=%s",
               strat, dir, base, penalized, finalScore, threshold, gates, reason);
}

#endif
