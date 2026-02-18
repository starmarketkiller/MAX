#pragma once
#property strict

enum EPattern50
{
   PAT_THREE_LINE_STRIKE = 0,
   PAT_CONCEALING_BABY_SWALLOW,
   PAT_ABANDONED_BABY,
   PAT_MORNING_STAR,
   PAT_EVENING_STAR,
   PAT_THREE_WHITE_SOLDIERS,
   PAT_THREE_BLACK_CROWS,
   PAT_BULLISH_ENGULFING,
   PAT_BEARISH_ENGULFING,
   PAT_KICKING,
   PAT_PIERCING_LINE,
   PAT_DARK_CLOUD_COVER,
   PAT_THREE_INSIDE_UP,
   PAT_THREE_INSIDE_DOWN,
   PAT_THREE_OUTSIDE_UP,
   PAT_THREE_OUTSIDE_DOWN,
   PAT_INVERTED_HAMMER,
   PAT_SHOOTING_STAR,
   PAT_BELT_HOLD_BULLISH,
   PAT_BELT_HOLD_BEARISH,
   PAT_HAMMER,
   PAT_HANGING_MAN,
   PAT_HARAMI_BULLISH,
   PAT_HARAMI_BEARISH,
   PAT_TWEEZER_BOTTOM,
   PAT_TWEEZER_TOP,
   PAT_DELIBERATION,
   PAT_ADVANCE_BLOCK,
   PAT_LADDER_BOTTOM,
   PAT_MATCHING_LOW,
   PAT_DOJI,
   PAT_LONG_LEGGED_DOJI,
   PAT_GRAVESTONE_DOJI,
   PAT_DRAGONFLY_DOJI,
   PAT_SPINNING_TOP,
   PAT_TASUKI_GAP,
   PAT_UPSIDE_GAP_TWO_CROWS,
   PAT_DOWNSIDE_GAP_THREE_METHODS,
   PAT_RISING_THREE_METHODS,
   PAT_FALLING_THREE_METHODS,
   PAT_HEAD_SHOULDERS,
   PAT_INVERSE_HEAD_SHOULDERS,
   PAT_DOUBLE_TOP,
   PAT_DOUBLE_BOTTOM,
   PAT_ASCENDING_TRIANGLE,
   PAT_DESCENDING_TRIANGLE,
   PAT_SYMMETRICAL_TRIANGLE,
   PAT_FLAG,
   PAT_PENNANT,
   PAT_RECTANGLE_RANGE_BREAKOUT,
   PAT__COUNT
};

struct PatternInfo
{
   EPattern50 id;
   string name;
   int tier;
   int baseScore;
   bool isCandles;
};

static const PatternInfo g_patterns[PAT__COUNT] =
{
   {PAT_THREE_LINE_STRIKE, "Three Line Strike", 3, 85, true},
   {PAT_CONCEALING_BABY_SWALLOW, "Concealing Baby Swallow", 3, 84, true},
   {PAT_ABANDONED_BABY, "Abandoned Baby", 3, 82, true},
   {PAT_MORNING_STAR, "Morning Star", 3, 80, true},
   {PAT_EVENING_STAR, "Evening Star", 3, 80, true},
   {PAT_THREE_WHITE_SOLDIERS, "Three White Soldiers", 3, 78, true},
   {PAT_THREE_BLACK_CROWS, "Three Black Crows", 3, 78, true},
   {PAT_BULLISH_ENGULFING, "Bullish Engulfing", 3, 75, true},
   {PAT_BEARISH_ENGULFING, "Bearish Engulfing", 3, 75, true},
   {PAT_KICKING, "Kicking", 3, 75, true},

   {PAT_PIERCING_LINE, "Piercing Line", 2, 70, true},
   {PAT_DARK_CLOUD_COVER, "Dark Cloud Cover", 2, 70, true},
   {PAT_THREE_INSIDE_UP, "Three Inside Up", 2, 68, true},
   {PAT_THREE_INSIDE_DOWN, "Three Inside Down", 2, 68, true},
   {PAT_THREE_OUTSIDE_UP, "Three Outside Up", 2, 68, true},
   {PAT_THREE_OUTSIDE_DOWN, "Three Outside Down", 2, 68, true},
   {PAT_INVERTED_HAMMER, "Inverted Hammer", 2, 65, true},
   {PAT_SHOOTING_STAR, "Shooting Star", 2, 65, true},
   {PAT_BELT_HOLD_BULLISH, "Belt Hold Bullish", 2, 66, true},
   {PAT_BELT_HOLD_BEARISH, "Belt Hold Bearish", 2, 66, true},

   {PAT_HAMMER, "Hammer", 1, 60, true},
   {PAT_HANGING_MAN, "Hanging Man", 1, 60, true},
   {PAT_HARAMI_BULLISH, "Harami Bullish", 1, 55, true},
   {PAT_HARAMI_BEARISH, "Harami Bearish", 1, 55, true},
   {PAT_TWEEZER_BOTTOM, "Tweezer Bottom", 1, 58, true},
   {PAT_TWEEZER_TOP, "Tweezer Top", 1, 58, true},
   {PAT_DELIBERATION, "Deliberation", 1, 58, true},
   {PAT_ADVANCE_BLOCK, "Advance Block", 1, 58, true},
   {PAT_LADDER_BOTTOM, "Ladder Bottom", 1, 57, true},
   {PAT_MATCHING_LOW, "Matching Low", 1, 56, true},

   {PAT_DOJI, "Doji", 0, 35, true},
   {PAT_LONG_LEGGED_DOJI, "Long-Legged Doji", 0, 38, true},
   {PAT_GRAVESTONE_DOJI, "Gravestone Doji", 0, 40, true},
   {PAT_DRAGONFLY_DOJI, "Dragonfly Doji", 0, 40, true},
   {PAT_SPINNING_TOP, "Spinning Top", 0, 37, true},
   {PAT_TASUKI_GAP, "Tasuki Gap", 0, 45, true},
   {PAT_UPSIDE_GAP_TWO_CROWS, "Upside Gap Two Crows", 0, 48, true},
   {PAT_DOWNSIDE_GAP_THREE_METHODS, "Downside Gap Three Methods", 0, 50, true},
   {PAT_RISING_THREE_METHODS, "Rising Three Methods", 0, 52, true},
   {PAT_FALLING_THREE_METHODS, "Falling Three Methods", 0, 52, true},

   {PAT_HEAD_SHOULDERS, "Head & Shoulders", 2, 72, false},
   {PAT_INVERSE_HEAD_SHOULDERS, "Inverse Head & Shoulders", 2, 72, false},
   {PAT_DOUBLE_TOP, "Double Top", 2, 70, false},
   {PAT_DOUBLE_BOTTOM, "Double Bottom", 2, 70, false},
   {PAT_ASCENDING_TRIANGLE, "Ascending Triangle", 2, 68, false},
   {PAT_DESCENDING_TRIANGLE, "Descending Triangle", 2, 68, false},
   {PAT_SYMMETRICAL_TRIANGLE, "Symmetrical Triangle", 1, 64, false},
   {PAT_FLAG, "Flag", 1, 66, false},
   {PAT_PENNANT, "Pennant", 1, 66, false},
   {PAT_RECTANGLE_RANGE_BREAKOUT, "Rectangle Range Breakout", 1, 62, false}
};

int GetPatternScore(EPattern50 pat)
{
   int i = (int)pat;
   if(i < 0 || i >= PAT__COUNT)
      return 0;
   return g_patterns[i].baseScore;
}

string GetPatternName(EPattern50 pat)
{
   int i = (int)pat;
   if(i < 0 || i >= PAT__COUNT)
      return "UNKNOWN";
   return g_patterns[i].name;
}

struct InstFeatures
{
   bool htfTrendAligned;
   bool bosOrMss;
   bool liquiditySweep;
   bool displacement;
   bool poiTouched;
   bool breakoutRetest;
   bool sessionNY;
   bool volumeSpike;
   bool premiumDiscountOK;
   bool avoidHighLow;
   bool spreadOK;
   bool atrOK;
};

struct InstWeights
{
   int wTrend, wBOS, wSweep, wDisp, wPOI, wRetest, wNY, wVol, wPD, wAvoidHL, wSpreadOK, wATROK;
};

InstWeights GetXauScalpPresetWeights()
{
   InstWeights w;
   w.wTrend = 10;
   w.wBOS = 10;
   w.wSweep = 8;
   w.wDisp = 8;
   w.wPOI = 7;
   w.wRetest = 7;
   w.wNY = 5;
   w.wVol = 5;
   w.wPD = 5;
   w.wAvoidHL = 5;
   w.wSpreadOK = 5;
   w.wATROK = 5;
   return w;
}

int ComputeInstitutionalScore(int patternScore, const InstFeatures &f, const InstWeights &w)
{
   int score = patternScore;
   if(f.htfTrendAligned) score += w.wTrend;
   if(f.bosOrMss) score += w.wBOS;
   if(f.liquiditySweep) score += w.wSweep;
   if(f.displacement) score += w.wDisp;
   if(f.poiTouched) score += w.wPOI;
   if(f.breakoutRetest) score += w.wRetest;
   if(f.sessionNY) score += w.wNY;
   if(f.volumeSpike) score += w.wVol;
   if(f.premiumDiscountOK) score += w.wPD;
   if(f.avoidHighLow) score += w.wAvoidHL;
   if(f.spreadOK) score += w.wSpreadOK;
   if(f.atrOK) score += w.wATROK;

   if(score < 0) score = 0;
   if(score > 150) score = 150;
   return score;
}

double ScoreToRiskMultiplier(int totalScore)
{
   if(totalScore < 60) return 0.0;
   if(totalScore < 80) return 0.5;
   if(totalScore < 100) return 1.0;
   return 1.5;
}
