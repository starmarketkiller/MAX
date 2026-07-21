//+------------------------------------------------------------------+
//| Generated adapter for contracts/strategy-registry.json schema 1 |
//+------------------------------------------------------------------+
#ifndef __NXS_STRATEGY_REGISTRY_MQH__
#define __NXS_STRATEGY_REGISTRY_MQH__

#define NXS_STRATEGY_REGISTRY_SCHEMA 1
#define NXS_LIVE_STRATEGY_COUNT 38
#define NXS_SELECTOR_STRATEGY_COUNT 37

string NXS_StrategyCanonicalId(string strategyId){
   int n = StringLen(strategyId);
   if(n > 4 && StringSubstr(strategyId, n-4) == "_NXR") return StringSubstr(strategyId, 0, n-4);
   return strategyId;
}

bool NXS_StrategyKnown(string strategyId){
   string id = NXS_StrategyCanonicalId(strategyId);
   return id=="ADX_RSI" || id=="BOLLINGER" || id=="MACD" || id=="SAR" ||
          id=="TSI" || id=="BJORGUM" || id=="LIQ_SWEEP" || id=="FVG_CONT" ||
          id=="BREAKOUT_ACC" || id=="LONDON_BO" || id=="EMA_PULLBACK" ||
          id=="BB_SQUEEZE" || id=="ICHIMOKU" || id=="RSI_DIV" ||
          id=="ORDER_BLOCK" || id=="STRUCT_REACT" || id=="TURTLE_SOUP" ||
          id=="IFVG" || id=="FVG_MIT" || id=="OB_MIT" || id=="SH_BMS_RTO" ||
          id=="SMS_BMS_RTO" || id=="SILVER_BULLET" || id=="AMD_REVERSAL" ||
          id=="OTE_CONT" || id=="MALAYSIAN_SNR" || id=="CISD" || id=="AMD_CONT" ||
          id=="JUDAS_SWING" || id=="LDN_REVERSAL" || id=="NY_REVERSAL" ||
          id=="WEEKLY_EXP" || id=="PO3" || id=="LIQ_VOID" || id=="DISP_REBAL" ||
          id=="ELLIOTT" || id=="RANGE_FADE" || id=="THREE_BAR_DELIVERY_BREAK";
}

#endif
