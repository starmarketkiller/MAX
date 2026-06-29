//+------------------------------------------------------------------+
//|  NXS_Defines.mqh                                                  |
//|  NEXUS EA v1.0 - Italian Traders Club                             |
//|  Enums and base structs                                           |
//+------------------------------------------------------------------+
#ifndef __NXS_DEFINES_MQH__
#define __NXS_DEFINES_MQH__

#define NEXUS_VERSION       "2.0.15"
#define MAX_GRID_LAYERS     3
#define MAX_PYRAMID         3
#define MAX_STRATEGIES      15

// magic offsets
#define MAGIC_CORE          0
#define MAGIC_GRID          1000
#define MAGIC_PYRAMID       2000
#define MAGIC_SPLIT         3000

enum ENUM_NXS_DIR    { DIR_NONE = 0, DIR_BUY = 1, DIR_SELL = -1 };
enum ENUM_NXS_REGIME { REGIME_UNKNOWN, REGIME_STRONG_TREND, REGIME_WEAK_TREND,
                       REGIME_RANGING, REGIME_VOLATILE, REGIME_CHOPPY };
enum ENUM_NXS_SESSION{ SESS_NONE, SESS_ASIAN, SESS_LONDON, SESS_OVERLAP, SESS_NY, SESS_AFTERNY };
enum ENUM_NXS_HTF    { HTF_NEUTRAL, HTF_BULL, HTF_BEAR };
enum ENUM_NXS_VEL    { VEL_NEUTRAL, VEL_BULL, VEL_BEAR, VEL_BULL_PB, VEL_BEAR_PB };
enum ENUM_NXS_AMD    { AMD_NONE, AMD_ACCUMULATION, AMD_MANIPULATION, AMD_DISTRIBUTION };

enum ENUM_NXS_STRAT {
   STRAT_ADX_RSI = 0,
   STRAT_BOLLINGER,
   STRAT_MACD,
   STRAT_SAR,
   STRAT_TSI,
   STRAT_BJORGUM,
   STRAT_LIQ_SWEEP,
   STRAT_FVG_CONT,
   STRAT_BREAKOUT_ACC,
   STRAT_LONDON_BO,
   STRAT_EMA_PULLBACK,
   STRAT_BB_SQUEEZE,
   STRAT_ICHIMOKU,
   STRAT_RSI_DIV,
   STRAT_ORDER_BLOCK,
   STRAT_STRUCT_REACT
};

struct SNXSSignal {
   ENUM_NXS_DIR    dir;
   double          score;
   ENUM_NXS_STRAT  strat;
   string          stratName;
   string          reason;
   double          slPrice;
   double          tpPrice;
   double          entryRef;
};

#endif
