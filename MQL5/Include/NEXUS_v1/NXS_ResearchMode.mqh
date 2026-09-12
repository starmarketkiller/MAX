//+------------------------------------------------------------------+
//| NXS_ResearchMode.mqh                                               |
//| 10/09 - Research Mode leggero: un solo master switch               |
//| (InpResearchMode) per rendere un backtest di UNA strategia isolato |
//| e ripetibile, senza toccare il comportamento LIVE di default       |
//| (InpResearchMode=false -> nessun cambiamento, verificato a         |
//| compilazione: ogni punto di innesto qui sotto e' un                |
//| "if(NXS_IsResearchMode())", mai una modifica del ramo esistente).  |
//|                                                                     |
//| Scope deliberatamente piccolo rispetto al Reference Engine (Fasi   |
//| 1-4 del vault "NEXUS Audit Forense", NON implementato): niente      |
//| router/gate/score-transform/telemetria estesa, solo gli overlay di  |
//| gestione post-apertura + lotto + multi-TF, con log esplicito per    |
//| ogni protezione che l'utente sceglie di tenere accesa.              |
//+------------------------------------------------------------------+
#ifndef __NXS_RESEARCHMODE_MQH__
#define __NXS_RESEARCHMODE_MQH__

// NXS_IsResearchMode() e' definita in NXS_Globals.mqh (incluso molto prima
// nella catena) - vedi commento li'.

// Lotto fisso dedicato al Research Mode - normalizzato a step/min/max del
// simbolo, stesso pattern di arrotondamento usato altrove nel sizing
// (NXS_CalcLotRisk), ma senza rischio%/moltiplicatori: il numero e' quello
// che l'utente ha messo in InpResearchFixedLot, punto.
double NXS_ResearchLot(){
   double lots = InpResearchFixedLot;
   double vmin  = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);
   double vmax  = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MAX);
   double vstep = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_STEP);
   if(vstep > 0) lots = MathFloor(lots / vstep + 1e-9) * vstep;
   if(vmin > 0)  lots = MathMax(vmin, lots);
   if(vmax > 0)  lots = MathMin(vmax, lots);
   return lots;
}

// Preflight chiamato da OnInit: fail-fast su combinazioni ambigue invece di
// correggerle in silenzio. Non blocca mai il default LIVE (InpResearchMode
// falso ritorna sempre true senza controllare nulla).
bool NXS_ResearchPreflight(){
   if(!NXS_IsResearchMode()) return true;

   if(InpStrategySelector <= 0){
      Print("[RESEARCH][FATAL] InpResearchMode richiede InpStrategySelector > 0 "
            "(una sola strategia alla volta, altrimenti il confronto tra baseline non ha senso)");
      return false;
   }
   if(InpDataCollectionMode){
      Print("[RESEARCH][FATAL] InpDataCollectionMode incompatibile con InpResearchMode "
            "(percorsi di sizing/gate diversi - vedi NXS_Inputs.mqh)");
      return false;
   }
   if(InpUseInstitutionalCore){
      Print("[RESEARCH][FATAL] InpUseInstitutionalCore incompatibile con InpResearchMode");
      return false;
   }
   // InpUseStrategyProfiles/InpProfileMultiTF sono "input": non riassegnabili
   // a runtime (MQL5 non lo permette). Il default di entrambi e' gia' true
   // (vedi NXS_Inputs.mqh), quindi questo scatta solo se il .set li ha messi
   // ESPLICITAMENTE a false - fail-fast piuttosto che ignorare in silenzio un
   // requisito strutturale del modo (vogliamo che ogni strategia giri sul
   // suo TF di profilo, non su un InpTFEntry singolo condiviso).
   if(!InpUseStrategyProfiles || !InpProfileMultiTF){
      PrintFormat("[RESEARCH][FATAL] InpResearchMode richiede InpUseStrategyProfiles=true "
                  "E InpProfileMultiTF=true (erano %s/%s) - correggi il .set",
                  (InpUseStrategyProfiles ? "true" : "false"), (InpProfileMultiTF ? "true" : "false"));
      return false;
   }
   double vmin = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);
   if(InpResearchFixedLot <= 0 || (vmin > 0 && InpResearchFixedLot + 1e-9 < vmin)){
      PrintFormat("[RESEARCH][FATAL] InpResearchFixedLot=%.4f non valido (minimo simbolo=%.4f)",
                  InpResearchFixedLot, vmin);
      return false;
   }
   return true;
}

// Mappa selector numerico (InpStrategySelector, NXS_SelectorAllows) -> nome,
// SOLO per il log leggibile qui sotto - NON e' il registro autorevole (quello
// resta il codice che chiama NXS_SelectorAllows(N) per ogni strategia, vedi
// NEXUS_EA_v2.mq5). Copiata dal commento in NXS_Inputs.mqh (selettore 1-37)
// piu' 39 (FVG_MIT_WINDOW, aggiunta 13/08 dopo quel commento) - se diverge in
// futuro l'unico effetto e' un nome sbagliato in questo log, nessun impatto
// sull'esecuzione reale (che non passa da qui).
string NXS_ResearchSelectorName(int sel){
   switch(sel){
      case 1:  return "ADX_RSI";      case 2:  return "BOLLINGER";
      case 3:  return "MACD";         case 4:  return "SAR";
      case 5:  return "TSI";          case 6:  return "BJORGUM";
      case 7:  return "LIQ_SWEEP";    case 8:  return "FVG_CONT";
      case 9:  return "BREAKOUT_ACC"; case 10: return "LONDON_BO";
      case 11: return "EMA_PULLBACK"; case 12: return "BB_SQUEEZE";
      case 13: return "ICHIMOKU";     case 14: return "RSI_DIV";
      case 15: return "ORDER_BLOCK";  case 16: return "STRUCT_REACT";
      case 17: return "TURTLE_SOUP";  case 18: return "IFVG";
      case 19: return "FVG_MIT";      case 20: return "OB_MIT";
      case 21: return "SH_BMS_RTO";   case 22: return "SMS_BMS_RTO";
      case 23: return "SILVER_BULLET";case 24: return "AMD_REVERSAL";
      case 25: return "OTE_CONT";     case 26: return "MALAYSIAN_SNR";
      case 27: return "CISD";         case 28: return "AMD_CONT";
      case 29: return "JUDAS_SWING";  case 30: return "LDN_REVERSAL";
      case 31: return "NY_REVERSAL";  case 32: return "WEEKLY_EXP";
      case 33: return "PO3";          case 34: return "LIQ_VOID";
      case 35: return "DISP_REBAL";   case 36: return "ELLIOTT";
      case 37: return "RANGE_FADE";   case 39: return "FVG_MIT_WINDOW";
      case 54: return "WICK_SWEEP_REV";
      default: return StringFormat("selector_%d", sel);
   }
}

// Log di avvio esplicito - vedi NXS_ResearchLogInit() chiamata da OnInit
// dopo che simbolo/profilo/ATR sono pronti.
void NXS_ResearchLogInit(){
   if(!NXS_IsResearchMode()) return;
   string stratName = NXS_ResearchSelectorName(InpStrategySelector);
   ENUM_TIMEFRAMES srcTF = NXS_StrategySourceTF(stratName);
   double slMult, tpMult, beR, trailATR; bool htf;
   bool hasProfile = NXS_Profile_Get(stratName, slMult, tpMult, htf, beR, trailATR);
   PrintFormat("[RESEARCH][INIT] strategy=%s selector=%d sourceTF=%s fixedLot=%.4f "
               "exitMgmt=%s ESL=%s dailyDD=%s totalDD=%s DPT=%s ruin=%s SL=%s TP=%s%s",
               stratName, InpStrategySelector, EnumToString(srcTF), NXS_ResearchLot(),
               (InpResearchExitMode == NXS_RESEARCH_RECIPE ? "RECIPE(profilo BE/trail ON)" : "RAW(nessun BE/trail)"),
               (InpResearchUseESL ? "ON" : "OFF"),
               (InpResearchUseDailyDD ? "ON" : "OFF"),
               (InpResearchUseTotalDD ? "ON" : "OFF"),
               (InpResearchUseDPT ? "ON" : "OFF"),
               (InpResearchUseRuin ? "ON" : "OFF"),
               (hasProfile ? StringFormat("%.2fxATR(%s)", slMult, EnumToString(srcTF)) : "nativo/strutturale"),
               (hasProfile ? StringFormat("%.2fxATR(%s)", tpMult, EnumToString(srcTF)) : "nativo/strutturale"),
               (hasProfile && InpResearchExitMode == NXS_RESEARCH_RECIPE ? StringFormat(" beR=%.2f trailATR=%.2f", beR, trailATR) : ""));
}

void NXS_ResearchLogOpen(const string strategy, int dir, double entry, double sl, double tp){
   if(!NXS_IsResearchMode()) return;
   PrintFormat("[RESEARCH][OPEN] strategy=%s time=%s dir=%s entry=%.5f sl=%.5f tp=%.5f",
               strategy, TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES),
               (dir > 0 ? "BUY" : "SELL"), entry, sl, tp);
}

void NXS_ResearchLogBlock(const string strategy, const string reason){
   if(!NXS_IsResearchMode()) return;
   PrintFormat("[RESEARCH][BLOCK] strategy=%s reason=%s", strategy, reason);
}

// 10/09 - STEP 3 originale (SBAGLIATO, corretto lo stesso giorno dopo il
// primo run reale con ESL=ON): si credeva che `closeReason` portasse il
// commento della deal ("NXS:DD" ecc.). In realta' NXS_TradeLedger lo deriva
// SOLO dal campo numerico MT5 DEAL_REASON (NXS_HistorySync.mqh,
// _NXS_HistTrigger: client/mobile/web/expert/sl/tp/stop_out) - qualunque
// chiusura EA esplicita (ESL, TOTAL_DD, DPT, RUIN, MaxHold, ecc.) arriva qui
// SEMPRE come "expert", mai come "NXS:DD"/"NXS:RISK"/ecc. I rami sotto che
// confrontavano closeReason con quelle stringhe erano quindi codice morto,
// mai raggiungibile - scoperto esaminando il primo run ADX_RSI RAW ESL=ON
// (14/36 chiusure finivano in OTHER+INVARIANT_FAIL nonostante ESL fosse
// esplicitamente opt-in per quel run, vedi vault 10/09).
//
// Ora `closeReason=="expert"` interroga l'Exit Authority Registry
// (NXS_ExitAuthority_Consume, NXS_Globals.mqh), popolato ALLA FONTE da ogni
// chiusura di protezione (NXS_Prot_ClosePositionWithReason/_nxs_ruin_flatten)
// PRIMA di inviare la richiesta - li' la causa e' gia' disambiguata (ESL vs
// TOTAL_DD non e' piu' dedotto a posteriori dai flag Inp, e' scritto dalla
// funzione che ha davvero deciso di chiudere). Se il registry non ha nulla
// per quella posizione, la chiusura resta EXPERT_UNKNOWN - un'anomalia vera,
// sempre invariant fail in RAW indipendentemente da qualunque opt-in.
string NXS_ResearchExitAuthority(const string closeReason, ulong position){
   if(StringFind(closeReason, "sl") == 0)          return "BROKER_SL";
   if(StringFind(closeReason, "tp") == 0)          return "BROKER_TP";
   if(StringFind(closeReason, "end of test") >= 0) return "TESTER_END";
   if(closeReason == "expert"){
      string cause;
      if(NXS_ExitAuthority_Consume(position, cause)) return cause;   // ESL/TOTAL_DD/DPT/RUIN/MAX_HOLD/MAX_LOSS_PER_POS/AUTO_CLOSE
      return "EXPERT_UNKNOWN";   // chiusura EA esplicita MAI registrata - vera anomalia
   }
   return "OTHER";   // client/mobile/web/stop_out/rollover/altro - non un OrderSend esplicito dell'EA
}

void NXS_ResearchLogExit(const string strategy, ulong position, const string reason, double pnl){
   if(!NXS_IsResearchMode()) return;
   string authority = NXS_ResearchExitAuthority(reason, position);
   PrintFormat("[RESEARCH][EXIT] strategy=%s position=%I64u exit_authority=%s reason=%s pnl=%.2f",
               strategy, position, authority, reason, pnl);
   // Invariante RAW (contratto in NXS_Inputs.mqh): BROKER_SL/BROKER_TP/
   // TESTER_END sono sempre ammessi. ESL/TOTAL_DD/DPT/RUIN sono ammessi SOLO
   // se il rispettivo opt-in e' acceso per QUESTO run (se scattano con
   // l'opt-in spento e' comunque un bug - NXS_Prot_OnTick dovrebbe averli
   // gia' esclusi in Research Mode). MAX_HOLD/MAX_LOSS_PER_POS/AUTO_CLOSE non
   // hanno mai un opt-in in Research Mode (esclusi incondizionatamente da
   // NXS_Prot_OnTick quando NXS_IsResearchMode()) - se compaiono comunque e'
   // un leak, non un caso ammesso. EXPERT_UNKNOWN e' sempre vietato: e'
   // esattamente il tipo di scoperta che ha portato a questo fix (vedi
   // MaxHold/MaxLossPerPos/AutoClose scoperti nel commit precedente).
   if(InpResearchExitMode == NXS_RESEARCH_RAW){
      bool allowed = (authority == "BROKER_SL" || authority == "BROKER_TP" || authority == "TESTER_END");
      if(!allowed && authority == "ESL")       allowed = InpResearchUseESL;
      if(!allowed && authority == "TOTAL_DD")  allowed = InpResearchUseTotalDD;
      if(!allowed && authority == "DPT")       allowed = InpResearchUseDPT;
      if(!allowed && authority == "RUIN")      allowed = InpResearchUseRuin;
      if(!allowed){
         PrintFormat("[RESEARCH][INVARIANT_FAIL] strategy=%s position=%I64u exit_authority=%s "
                     "reason=%s - RAW ha ricevuto un'uscita non prevista dal contratto",
                     strategy, position, authority, reason);
         g_certInvariantFailCount++;   // Test Validity Certificate v2 - vedi NXS_Trace.mqh
      }
   }
}

#endif
