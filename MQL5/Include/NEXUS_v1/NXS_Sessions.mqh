//+------------------------------------------------------------------+
//|  NXS_Sessions.mqh                                                 |
//+------------------------------------------------------------------+
#ifndef __NXS_SESSIONS_MQH__
#define __NXS_SESSIONS_MQH__

ENUM_NXS_SESSION NXS_GetSession(){
   // v2.0.5b: convert server time → GMT for accurate session windowing.
   // Session windows are defined in GMT:
   //   ASIAN   00-07 GMT  (Tokyo)
   //   LONDON  07-12 GMT
   //   OVERLAP 12-15 GMT  (London/NY overlap)
   //   NY      15-20 GMT
   //   AFTERNY 20-24 GMT  (Sydney early + Asian roll)
   datetime serverNow = TimeCurrent();
   datetime gmtNow    = (datetime)((long)serverNow - (long)InpServerGMTOffset * 3600);
   MqlDateTime mt; TimeToStruct(gmtNow, mt);
   int h = mt.hour;
   if(h >= 0  && h <  7)  return SESS_ASIAN;
   if(h >= 7  && h < 12)  return SESS_LONDON;
   if(h >= 12 && h < 15)  return SESS_OVERLAP;
   if(h >= 15 && h < 20)  return SESS_NY;
   return SESS_AFTERNY;
}

double NXS_SessionMinScore(ENUM_NXS_SESSION s){
   switch(s){
      case SESS_ASIAN:   return g_run_AsianScoreMin;
      case SESS_LONDON:  return g_run_LondonScoreMin;
      case SESS_OVERLAP: return g_run_OverlapScoreMin;
      case SESS_NY:      return g_run_NYScoreMin;
      case SESS_AFTERNY: return g_run_AfterNYScoreMin;
   }
   return g_run_MinEntryScore;
}

string NXS_SessionName(ENUM_NXS_SESSION s){
   switch(s){
      case SESS_ASIAN:   return "ASIAN";
      case SESS_LONDON:  return "LONDON";
      case SESS_OVERLAP: return "OVERLAP";
      case SESS_NY:      return "NY";
      case SESS_AFTERNY: return "AFTERNY";
   }
   return "NONE";
}

#endif
