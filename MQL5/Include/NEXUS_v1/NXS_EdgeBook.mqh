//+------------------------------------------------------------------+
//| NXS_EdgeBook.mqh                                                   |
//| Credit-safe book mode for the live EA.                             |
//|                                                                     |
//| This is NOT a claim of validated economic edge. Registry and Phase |
//| 7 still say Production = NO-GO. The book only enforces the research |
//| shortlist and hard-denies FAILED / DEFECT_BLOCKED opens outside     |
//| Research Mode isolation.                                            |
//|                                                                     |
//| Shortlist source: docs/EDGE_CREDIT_SAFE_OPERATING_LOOP_V1.md        |
//| Deny source: contracts/edge-validation-registry.json                |
//+------------------------------------------------------------------+
#ifndef __NXS_EDGEBOOK_MQH__
#define __NXS_EDGEBOOK_MQH__

bool NXS_EdgeBook_IsShortlist(const string name){
   return (name == "FVG_CONT"
        || name == "LIQ_SWEEP"
        || name == "ORDER_BLOCK"
        || name == "BREAKOUT_ACC"
        || name == "Z_SCORE_BREAKOUT"
        || name == "EMA_PULLBACK");
}

// Hard deny even in FULL: scientific FAILED or DEFECT_BLOCKED that must not
// open new exposure unless Research Mode is intentionally isolating them.
bool NXS_EdgeBook_IsHardDenied(const string name){
   return (name == "MACD"
        || name == "RSI_DIV"
        || name == "CRT"
        || name == "BB_SQUEEZE"
        || name == "TSI"
        || name == "SH_BMS_RTO"
        || name == "SH_BMS_RTO_V2"
        || name == "SILVER_BULLET");
}

string NXS_EdgeBook_DenyReason(const string name){
   if(InpBookMode == NXS_BOOK_EDGE_SHORTLIST && !NXS_EdgeBook_IsShortlist(name))
      return "edge_book_excluded:" + name;
   if(NXS_EdgeBook_IsHardDenied(name))
      return "edge_book_hard_denied:" + name;
   return "";
}

// Research Mode may isolate a denied name on purpose. Everywhere else the
// book gate applies. Identity is stratName, never the STRAT_* enum.
bool NXS_EdgeBook_Allows(const string name){
   if(NXS_IsResearchMode()) return true;
   if(InpBookMode == NXS_BOOK_EDGE_SHORTLIST)
      return NXS_EdgeBook_IsShortlist(name);
   return !NXS_EdgeBook_IsHardDenied(name);
}

bool NXS_EdgeBook_Preflight(){
   if(InpBookMode != NXS_BOOK_EDGE_SHORTLIST) return true;
   if(InpDataCollectionMode){
      Print("[EDGE_BOOK][FATAL] InpDataCollectionMode incompatibile con "
            "NXS_BOOK_EDGE_SHORTLIST (aprirebbe strategie fuori shortlist)");
      return false;
   }
   if(InpUseInstitutionalCore){
      Print("[EDGE_BOOK][FATAL] InpUseInstitutionalCore incompatibile con "
            "NXS_BOOK_EDGE_SHORTLIST");
      return false;
   }
   if(!InpUseStrategyProfiles){
      Print("[EDGE_BOOK][FATAL] NXS_BOOK_EDGE_SHORTLIST richiede "
            "InpUseStrategyProfiles=true");
      return false;
   }
   Print("[EDGE_BOOK] mode=EDGE_SHORTLIST "
         "allow=FVG_CONT,LIQ_SWEEP,ORDER_BLOCK,BREAKOUT_ACC,Z_SCORE_BREAKOUT,EMA_PULLBACK "
         "note=credit-safe book, not validated production edge");
   return true;
}

#endif // __NXS_EDGEBOOK_MQH__
