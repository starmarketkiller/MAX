//+------------------------------------------------------------------+
//| NXS_TestValidityCertificate.mqh                                   |
//| 12/09 - QUANTITATIVE INTEGRITY - Test Validity Certificate v2.     |
//|                                                                    |
//| Obiettivo dichiarato dall'utente: ogni run di Research Mode deve   |
//| produrre AUTOMATICAMENTE un certificato che dichiara se il test e' |
//| affidabile o no. Fonte primaria: Decision/Gate/Execution Trace v1  |
//| (NXS_Trace.mqh) - i contatori g_cert* sono aggiornati da           |
//| NXS_Trace_Emit nello STESSO momento causale in cui stampa la riga, |
//| cosi' il certificato non ri-analizza il Journal (MQL5 non puo'     |
//| farlo in modo affidabile a runtime) e non e' una seconda fonte di  |
//| verita' che puo' divergere dalla prima (vedi CAUSAL_HOOK_MISMATCH, |
//| Failure Memory 12/09).                                             |
//|                                                                    |
//| Design: il classificatore (NXS_Cert_Classify) e' PURO - prende in  |
//| input una struct di contatori/metadati, non legge variabili        |
//| globali. Permette di testarlo con un input sintetico/deliberata-   |
//| mente rotto senza toccare la logica di trading reale.              |
//+------------------------------------------------------------------+
#ifndef __NXS_TESTVALIDITYCERT_MQH__
#define __NXS_TESTVALIDITYCERT_MQH__

enum ENUM_NXS_CERT_VERDICT {
   CERT_PASS = 0,
   CERT_PASS_WITH_WARNINGS,
   CERT_FAIL
};

string NXS_CertVerdictName(ENUM_NXS_CERT_VERDICT v){
   switch(v){
      case CERT_PASS:               return "PASS";
      case CERT_PASS_WITH_WARNINGS: return "PASS_WITH_WARNINGS";
      case CERT_FAIL:               return "FAIL";
      default:                      return "UNKNOWN";
   }
}

// Input puro del classificatore - SOLO contatori/metadati, mai variabili
// globali lette direttamente. Cosi' un test sintetico puo' costruire questa
// struct a mano (funnel rotto apposta) e verificare che NXS_Cert_Classify
// la marchi FAIL, senza eseguire nessuna passata di Tester reale.
struct SNxsCertInput {
   long   generated, blocked, openAttempt, opened, brokerReject;
   long   openedMissingPositionId;      // invariante: ogni OPENED ha position_id
   long   brokerRejectMissingReason;    // invariante: ogni broker reject ha reason
   bool   sourceTFMismatch;             // la stessa strategia ha dichiarato source_tf diversi
   long   invariantFailCount;           // [RESEARCH][INVARIANT_FAIL] osservati (EXPERT_UNKNOWN/autorita' non opt-in)
   bool   researchModeRaw;              // InpResearchExitMode == NXS_RESEARCH_RAW (l'invariante sopra si applica)
   bool   traceActive;                  // g_nxsTraceActive per questo run
   string declaredStrategy;             // NXS_ResearchSelectorName(InpStrategySelector)
   string observedStrategy;             // strategy realmente vista nella prima riga GENERATED
   bool   declaredIsFallbackName;       // true se declaredStrategy e' nel formato "selector_N" (registro non autorevole non lo conosce)
   long   blkPausedCount;               // proxy euristico dichiarato per "test troncato da un gate non opt-in" - vedi nota classify
};

// Classificatore puro: nessuna lettura di globali, nessun I/O. Ritorna il
// verdetto e riempie failReasons/warnReasons con le causali leggibili.
ENUM_NXS_CERT_VERDICT NXS_Cert_Classify(const SNxsCertInput &in, string &failReasons, string &warnReasons){
   failReasons = ""; warnReasons = "";
   bool fail = false, warn = false;

   // MISSING_TELEMETRY: trace mai attivo o zero righe emesse in un run di
   // Research Mode - il certificato stesso non avrebbe alcuna base.
   long totalLines = in.generated + in.blocked + in.openAttempt + in.opened + in.brokerReject;
   if(!in.traceActive || totalLines == 0){
      failReasons += "MISSING_TELEMETRY(trace non attivo o zero righe di trace emesse); ";
      fail = true;
   }

   // FUNNEL_NOT_RECONCILED: invariante centrale del task - ogni segnale
   // GENERATED deve finire in ESATTAMENTE uno stato terminale (BLOCKED,
   // OPENED, BROKER_REJECT). OPEN_ATTEMPT e' intermedio, non terminale.
   long terminal = in.blocked + in.opened + in.brokerReject;
   if(in.traceActive && in.generated != terminal){
      failReasons += StringFormat(
         "FUNNEL_NOT_RECONCILED(generated=%d blocked+opened+broker_reject=%d - segnali spariti o duplicati); ",
         in.generated, terminal);
      fail = true;
   }

   if(in.openedMissingPositionId > 0){
      failReasons += StringFormat("OPENED_MISSING_POSITION_ID(%d occorrenze); ", in.openedMissingPositionId);
      fail = true;
   }
   if(in.brokerRejectMissingReason > 0){
      failReasons += StringFormat("BROKER_REJECT_MISSING_REASON(%d occorrenze); ", in.brokerRejectMissingReason);
      fail = true;
   }

   // EXPERT_UNKNOWN / autorita' di uscita non prevista in RAW - invariante
   // gia' implementato in NXS_ResearchMode.mqh (NXS_ResearchLogExit), qui
   // solo letto come contatore.
   if(in.researchModeRaw && in.invariantFailCount > 0){
      failReasons += StringFormat(
         "UNEXPECTED_EXIT_AUTHORITY_IN_RAW(%d occorrenze INVARIANT_FAIL - EXPERT_UNKNOWN o autorita' non opt-in in un run RAW); ",
         in.invariantFailCount);
      fail = true;
   }

   if(in.sourceTFMismatch){
      failReasons += "SOURCE_TF_MISMATCH(la stessa strategia ha dichiarato source_tf diversi tra due GENERATED); ";
      fail = true;
   }

   // SELECTOR_MISMATCH / registry inconsistency: se il nome dichiarato NON e'
   // un fallback "selector_N" (cioe' il lookup lo conosce) e diverge da quanto
   // osservato nel trace, e' un'inconsistenza di registro vera. Se invece e'
   // un fallback, NXS_ResearchSelectorName dichiara gia' se stesso non
   // autorevole (vedi commento li') - trattato come INDETERMINATO, non FAIL.
   if(!in.declaredIsFallbackName && StringLen(in.observedStrategy) > 0 &&
      in.declaredStrategy != in.observedStrategy){
      failReasons += StringFormat("SELECTOR_MISMATCH(dichiarato=%s osservato=%s); ",
                                   in.declaredStrategy, in.observedStrategy);
      fail = true;
   } else if(in.declaredIsFallbackName){
      warnReasons += StringFormat(
         "REGISTRY_LOOKUP_INDETERMINATO(selector risolto come '%s' - non presente nella lookup non autorevole "
         "NXS_ResearchSelectorName, il nome non e' verificabile ma non e' di per se' un fallimento del test); ",
         in.declaredStrategy);
      warn = true;
   }

   // "Test troncato da un gate non opt-in": non esiste nel motore un segnale
   // diretto e affidabile per un troncamento REALE della passata (MQL5 non
   // espone in modo utilizzabile "la tester pass e' finita prima del previsto
   // per uno stop-out/margin call"). Proxy euristico dichiarato: conteggio
   // BLK_PAUSED (NXS_BlockerDiagnostics.mqh) nella stessa passata. Declassato
   // deliberatamente a WARNING invece di FAIL: e' un segnale, non una prova -
   // dichiarare un limite noto e' preferibile a un FAIL falso positivo (vedi
   // Failure Memory 12/09, principio generale "mai inventare quando manca un
   // meccanismo diretto").
   if(in.blkPausedCount > 0){
      warnReasons += StringFormat(
         "POSSIBLE_TEST_TRUNCATION(BLK_PAUSED=%d - proxy euristico dichiarato, nessun meccanismo diretto "
         "per confermare un troncamento reale della passata); ",
         in.blkPausedCount);
      warn = true;
   }

   if(fail) return CERT_FAIL;
   if(warn) return CERT_PASS_WITH_WARNINGS;
   return CERT_PASS;
}

// --- Raccolta dati reali + scrittura file --------------------------------

string _NXS_Cert_Sanitize(const string s){
   string out = s;
   StringReplace(out, ":", "-");
   StringReplace(out, " ", "_");
   StringReplace(out, "\\", "_");
   StringReplace(out, "/", "_");
   return out;
}

void NXS_Cert_Generate(){
   if(!NXS_IsResearchMode()) return;

   string declaredStrategy = NXS_ResearchSelectorName(InpStrategySelector);
   bool   isFallback = (StringFind(declaredStrategy, "selector_") == 0);

   SNxsCertInput in;
   in.generated                 = g_certGenerated;
   in.blocked                   = g_certBlocked;
   in.openAttempt                = g_certOpenAttempt;
   in.opened                    = g_certOpened;
   in.brokerReject              = g_certBrokerReject;
   in.openedMissingPositionId   = g_certOpenedMissingPositionId;
   in.brokerRejectMissingReason = g_certBrokerRejectMissingReason;
   in.sourceTFMismatch          = g_certSourceTFMismatch;
   in.invariantFailCount        = g_certInvariantFailCount;
   in.researchModeRaw           = (InpResearchExitMode == NXS_RESEARCH_RAW);
   in.traceActive               = g_nxsTraceActive;
   in.declaredStrategy          = declaredStrategy;
   in.observedStrategy          = g_certFirstStrategy;
   in.declaredIsFallbackName    = isFallback;
   in.blkPausedCount            = (BLK_PAUSED >= 0 && BLK_PAUSED < 16) ? g_blockCount[BLK_PAUSED] : 0;

   string failReasons, warnReasons;
   ENUM_NXS_CERT_VERDICT verdict = NXS_Cert_Classify(in, failReasons, warnReasons);

   ENUM_TIMEFRAMES srcTF = NXS_StrategySourceTF(declaredStrategy);
   long   leverage = AccountInfoInteger(ACCOUNT_LEVERAGE);
   string runIdSafe = _NXS_Cert_Sanitize(g_nxsTraceRunId);

   // --- file leggibile per l'utente -----------------------------------
   string txtPath = "NEXUS\\certificates\\" + runIdSafe + ".txt";
   int hTxt = FileOpen(txtPath, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(hTxt != INVALID_HANDLE){
      FileWrite(hTxt, "=== NEXUS Test Validity Certificate v2 ===");
      FileWrite(hTxt, "run_id=" + g_nxsTraceRunId);
      FileWrite(hTxt, "strategy=" + declaredStrategy + " selector=" + IntegerToString(InpStrategySelector));
      FileWrite(hTxt, "source_tf=" + EnumToString(srcTF) + " entry_tf=" + EnumToString((ENUM_TIMEFRAMES)InpTFEntry));
      FileWrite(hTxt, "period_start=" + TimeToString(g_certPeriodStart, TIME_DATE|TIME_SECONDS) +
                       " period_end=" + TimeToString(g_certPeriodEnd, TIME_DATE|TIME_SECONDS));
      FileWrite(hTxt, "research_mode=" + (NXS_IsResearchMode() ? "true" : "false") +
                       " exit_mode=" + (InpResearchExitMode == NXS_RESEARCH_RAW ? "RAW" : "RECIPE"));
      FileWrite(hTxt, "leverage=1:" + IntegerToString(leverage) +
                       " lot_mode=FIXED_LOT fixed_lot=" + DoubleToString(NXS_ResearchLot(), 4));
      FileWrite(hTxt, StringFormat("opt_in: RiskShield=%s ESL=%s DailyDD=%s TotalDD=%s Ruin=%s DPT=%s",
                       (InpResearchUseRiskShield ? "ON" : "OFF"), (InpResearchUseESL ? "ON" : "OFF"),
                       (InpResearchUseDailyDD ? "ON" : "OFF"), (InpResearchUseTotalDD ? "ON" : "OFF"),
                       (InpResearchUseRuin ? "ON" : "OFF"), (InpResearchUseDPT ? "ON" : "OFF")));
      FileWrite(hTxt, "code_build=" + g_nxsTraceBuild);
      FileWrite(hTxt, "broker_time_offset_to_GMT_h=" + IntegerToString(InpServerGMTOffset) +
                       " (InpServerGMTOffset, sempre dichiarato - vedi NXS_Inputs.mqh)");
      FileWrite(hTxt, "");
      FileWrite(hTxt, "--- Funnel ---");
      FileWrite(hTxt, StringFormat("GENERATED=%d BLOCKED=%d OPEN_ATTEMPT=%d OPENED=%d BROKER_REJECT=%d",
                       in.generated, in.blocked, in.openAttempt, in.opened, in.brokerReject));
      for(int g = 0; g < 20; g++){
         if(g_certGateCount[g] == 0) continue;
         FileWrite(hTxt, StringFormat("  gate_reason=%s count=%d",
                          NXS_GateReasonName((ENUM_NXS_GATE_REASON)g), g_certGateCount[g]));
      }
      FileWrite(hTxt, "");
      FileWrite(hTxt, "--- Anomalie ---");
      FileWrite(hTxt, StringFormat("opened_missing_position_id=%d broker_reject_missing_reason=%d "
                       "source_tf_mismatch=%s invariant_fail_count=%d blk_paused_count=%d",
                       in.openedMissingPositionId, in.brokerRejectMissingReason,
                       (in.sourceTFMismatch ? "true" : "false"), in.invariantFailCount, in.blkPausedCount));
      FileWrite(hTxt, "");
      FileWrite(hTxt, "VERDICT=" + NXS_CertVerdictName(verdict));
      if(StringLen(failReasons) > 0) FileWrite(hTxt, "FAIL_REASONS: " + failReasons);
      if(StringLen(warnReasons) > 0) FileWrite(hTxt, "WARNINGS: " + warnReasons);
      FileClose(hTxt);
   } else {
      PrintFormat("[CERT][ERROR] impossibile aprire %s per scrittura (err=%d)", txtPath, GetLastError());
   }

   // --- file machine-readable -------------------------------------------
   string jsonPath = "NEXUS\\certificates\\" + runIdSafe + ".json";
   int hJson = FileOpen(jsonPath, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(hJson != INVALID_HANDLE){
      string gates = "";
      for(int g = 0; g < 20; g++){
         if(g_certGateCount[g] == 0) continue;
         if(StringLen(gates) > 0) gates += ",";
         gates += StringFormat("\"%s\":%d", NXS_GateReasonName((ENUM_NXS_GATE_REASON)g), g_certGateCount[g]);
      }
      string json = StringFormat(
         "{\"run_id\":\"%s\",\"strategy\":\"%s\",\"selector\":%d,\"source_tf\":\"%s\",\"entry_tf\":\"%s\","
         "\"period_start\":\"%s\",\"period_end\":\"%s\",\"research_mode\":%s,\"exit_mode\":\"%s\","
         "\"leverage\":%d,\"lot_mode\":\"FIXED_LOT\",\"fixed_lot\":%.4f,"
         "\"opt_in\":{\"risk_shield\":%s,\"esl\":%s,\"daily_dd\":%s,\"total_dd\":%s,\"ruin\":%s,\"dpt\":%s},"
         "\"code_build\":\"%s\",\"broker_time_offset_h\":%d,"
         "\"funnel\":{\"generated\":%d,\"blocked\":%d,\"open_attempt\":%d,\"opened\":%d,\"broker_reject\":%d},"
         "\"gate_reason_counts\":{%s},"
         "\"anomalies\":{\"opened_missing_position_id\":%d,\"broker_reject_missing_reason\":%d,"
         "\"source_tf_mismatch\":%s,\"invariant_fail_count\":%d,\"blk_paused_count\":%d},"
         "\"verdict\":\"%s\",\"fail_reasons\":\"%s\",\"warnings\":\"%s\"}",
         g_nxsTraceRunId, declaredStrategy, InpStrategySelector, EnumToString(srcTF),
         EnumToString((ENUM_TIMEFRAMES)InpTFEntry),
         TimeToString(g_certPeriodStart, TIME_DATE|TIME_SECONDS), TimeToString(g_certPeriodEnd, TIME_DATE|TIME_SECONDS),
         (NXS_IsResearchMode() ? "true" : "false"), (InpResearchExitMode == NXS_RESEARCH_RAW ? "RAW" : "RECIPE"),
         leverage, NXS_ResearchLot(),
         (InpResearchUseRiskShield ? "true" : "false"), (InpResearchUseESL ? "true" : "false"),
         (InpResearchUseDailyDD ? "true" : "false"), (InpResearchUseTotalDD ? "true" : "false"),
         (InpResearchUseRuin ? "true" : "false"), (InpResearchUseDPT ? "true" : "false"),
         g_nxsTraceBuild, InpServerGMTOffset,
         in.generated, in.blocked, in.openAttempt, in.opened, in.brokerReject,
         gates,
         in.openedMissingPositionId, in.brokerRejectMissingReason,
         (in.sourceTFMismatch ? "true" : "false"), in.invariantFailCount, in.blkPausedCount,
         NXS_CertVerdictName(verdict), failReasons, warnReasons);
      FileWriteString(hJson, json);
      FileClose(hJson);
   } else {
      PrintFormat("[CERT][ERROR] impossibile aprire %s per scrittura (err=%d)", jsonPath, GetLastError());
   }

   // --- riepilogo compatto a fine run ------------------------------------
   PrintFormat("[CERT][SUMMARY] run_id=%s strategy=%s verdict=%s generated=%d blocked=%d opened=%d "
               "broker_reject=%d%s%s",
               g_nxsTraceRunId, declaredStrategy, NXS_CertVerdictName(verdict),
               in.generated, in.blocked, in.opened, in.brokerReject,
               (StringLen(failReasons) > 0 ? (" FAIL_REASONS=" + failReasons) : ""),
               (StringLen(warnReasons) > 0 ? (" WARNINGS=" + warnReasons) : ""));
}

// --- Test sintetico deliberatamente rotto (InpCertRunSyntheticTest) ------
// Dimostra che il classificatore PURO marca FAIL un funnel palesemente
// invalido, senza eseguire nessuna passata di Tester reale e senza toccare i
// contatori g_cert* del run vero (costruisce la sua SNxsCertInput a mano).
void NXS_Cert_RunSyntheticTest(){
   if(!InpCertRunSyntheticTest) return;

   SNxsCertInput broken;
   // Funnel volutamente non riconciliato: 10 GENERATED ma solo 7 terminali
   // (4 BLOCKED + 2 OPENED + 0 BROKER_REJECT = 6, manca anche 1 rispetto ai 7
   // dichiarati qui sotto) - 3 segnali "spariti" senza causa.
   broken.generated                 = 10;
   broken.blocked                   = 4;
   broken.openAttempt               = 3;
   broken.opened                    = 2;
   broken.brokerReject              = 0;
   broken.openedMissingPositionId   = 1;   // una OPENED senza position_id
   broken.brokerRejectMissingReason = 0;
   broken.sourceTFMismatch          = true;
   broken.invariantFailCount        = 2;   // 2 EXPERT_UNKNOWN in un run RAW
   broken.researchModeRaw           = true;
   broken.traceActive               = true;
   broken.declaredStrategy          = "ADX_RSI";
   broken.observedStrategy          = "MACD";   // selector mismatch deliberato
   broken.declaredIsFallbackName    = false;
   broken.blkPausedCount            = 0;

   string failReasons, warnReasons;
   ENUM_NXS_CERT_VERDICT v = NXS_Cert_Classify(broken, failReasons, warnReasons);
   PrintFormat("[CERT][SYNTHETIC_TEST] verdict=%s (atteso=FAIL) fail_reasons=%s warnings=%s",
               NXS_CertVerdictName(v), failReasons, warnReasons);
   if(v != CERT_FAIL)
      Print("[CERT][SYNTHETIC_TEST][ERROR] il classificatore NON ha marcato FAIL un funnel deliberatamente rotto - bug nel classificatore");
}

#endif
