#pragma once
#property strict

struct PatternStats
{
   string pattern_id;
   string family;
   int direction; // 1 bull, -1 bear, 0 both
   double rank;
   double failure_rate;
   double target_hit_pct;
   double avg_move;
   int sample_size;
   string notes;
};

struct PatternSignal
{
   bool detected;
   string pattern_id;
   string family;
   int direction;
   double entry_level;
   double invalidation_level;
   double target_level;
   double quality; // 0..1
   string notes;
};

void PE_DefaultStats(PatternStats &s, const string id, const string family, int dir)
{
   s.pattern_id = id;
   s.family = family;
   s.direction = dir;
   s.rank = 50;
   s.failure_rate = 0.5;
   s.target_hit_pct = 0.5;
   s.avg_move = 0.0;
   s.sample_size = 30;
   s.notes = "default";
}

bool PE_IsPivotHigh(const string sym, ENUM_TIMEFRAMES tf, int shift, int lr)
{
   if(shift < lr + 1)
      return false;
   double h = iHigh(sym, tf, shift);
   for(int i = 1; i <= lr; i++)
   {
      if(iHigh(sym, tf, shift - i) >= h) return false;
      if(iHigh(sym, tf, shift + i) > h) return false;
   }
   return true;
}

bool PE_IsPivotLow(const string sym, ENUM_TIMEFRAMES tf, int shift, int lr)
{
   if(shift < lr + 1)
      return false;
   double l = iLow(sym, tf, shift);
   for(int i = 1; i <= lr; i++)
   {
      if(iLow(sym, tf, shift - i) <= l) return false;
      if(iLow(sym, tf, shift + i) < l) return false;
   }
   return true;
}

bool PE_DetectCandles(const string sym, ENUM_TIMEFRAMES tf, double point, double atr, PatternSignal &out)
{
   out.detected = false;
   int s1 = 1, s2 = 2;
   double h1 = iHigh(sym, tf, s1), l1 = iLow(sym, tf, s1), o1 = iOpen(sym, tf, s1), c1 = iClose(sym, tf, s1);
   double h2 = iHigh(sym, tf, s2), l2 = iLow(sym, tf, s2), o2 = iOpen(sym, tf, s2), c2 = iClose(sym, tf, s2);
   double body1 = MathAbs(c1 - o1);
   double range1 = MathMax(point, h1 - l1);
   double upW = h1 - MathMax(o1, c1);
   double dnW = MathMin(o1, c1) - l1;

   if(h1 < h2 && l1 > l2)
   {
      out.detected = true;
      out.pattern_id = "INSIDE_DAY";
      out.family = "CANDLE";
      out.direction = (c1 >= o1 ? 1 : -1);
      out.entry_level = (out.direction > 0 ? h1 : l1);
      out.invalidation_level = (out.direction > 0 ? l1 : h1);
      out.target_level = out.entry_level + out.direction * (h1 - l1);
      out.quality = 0.55;
      out.notes = "inside";
      return true;
   }

   if(h1 > h2 && l1 < l2)
   {
      out.detected = true;
      out.pattern_id = "OUTSIDE_DAY";
      out.family = "CANDLE";
      out.direction = (c1 >= o1 ? 1 : -1);
      out.entry_level = (out.direction > 0 ? h1 : l1);
      out.invalidation_level = (out.direction > 0 ? l1 : h1);
      out.target_level = out.entry_level + out.direction * (h1 - l1);
      out.quality = 0.52;
      out.notes = "outside";
      return true;
   }

   bool bullEng = (c2 < o2 && c1 > o1 && c1 >= o2 && o1 <= c2);
   bool bearEng = (c2 > o2 && c1 < o1 && c1 <= o2 && o1 >= c2);
   if(bullEng || bearEng)
   {
      out.detected = true;
      out.pattern_id = bullEng ? "BULL_ENGULF" : "BEAR_ENGULF";
      out.family = "CANDLE";
      out.direction = bullEng ? 1 : -1;
      out.entry_level = (out.direction > 0 ? h1 : l1);
      out.invalidation_level = (out.direction > 0 ? l1 : h1);
      out.target_level = out.entry_level + out.direction * (h1 - l1) * 1.2;
      out.quality = 0.60;
      out.notes = "engulf";
      return true;
   }

   double wickRatio = (body1 > point ? (MathMax(upW, dnW) / body1) : 0.0);
   if(body1 / range1 <= 0.35 && wickRatio >= 2.0)
   {
      bool hammer = (dnW > upW * 1.5);
      out.detected = true;
      out.pattern_id = hammer ? "HAMMER" : "SHOOTING_STAR";
      out.family = "CANDLE";
      out.direction = hammer ? 1 : -1;
      out.entry_level = (out.direction > 0 ? h1 : l1);
      out.invalidation_level = (out.direction > 0 ? l1 : h1);
      out.target_level = out.entry_level + out.direction * MathMax(range1, atr * 0.8);
      out.quality = 0.58;
      out.notes = "pinbar";
      return true;
   }
   return false;
}

bool PE_DetectRectangle(const string sym, ENUM_TIMEFRAMES tf, int lookback, double point, PatternSignal &out)
{
   out.detected = false;
   int start = MathMax(5, lookback);
   double hi = -DBL_MAX, lo = DBL_MAX;
   for(int i = 2; i <= start; i++)
   {
      hi = MathMax(hi, iHigh(sym, tf, i));
      lo = MathMin(lo, iLow(sym, tf, i));
   }
   if(hi <= lo)
      return false;
   double tol = MathMax(point * 20.0, (hi - lo) * 0.12);
   int touchesHi = 0, touchesLo = 0;
   for(int i = 2; i <= start; i++)
   {
      if(MathAbs(iHigh(sym, tf, i) - hi) <= tol) touchesHi++;
      if(MathAbs(iLow(sym, tf, i) - lo) <= tol) touchesLo++;
   }
   if(touchesHi < 2 || touchesLo < 2)
      return false;

   double c1 = iClose(sym, tf, 1);
   if(c1 > hi + point * 2)
   {
      out.detected = true;
      out.pattern_id = "RECT_BOTTOM";
      out.family = "CHART";
      out.direction = 1;
      out.entry_level = hi;
      out.invalidation_level = lo;
      out.target_level = hi + (hi - lo);
      out.quality = 0.62;
      out.notes = "rect_up";
      return true;
   }
   if(c1 < lo - point * 2)
   {
      out.detected = true;
      out.pattern_id = "RECT_TOP";
      out.family = "CHART";
      out.direction = -1;
      out.entry_level = lo;
      out.invalidation_level = hi;
      out.target_level = lo - (hi - lo);
      out.quality = 0.62;
      out.notes = "rect_dn";
      return true;
   }
   return false;
}

bool PE_DetectDoubleTopBottom(const string sym, ENUM_TIMEFRAMES tf, int lookback, int lr, double point, PatternSignal &out)
{
   out.detected = false;
   int hiShift1 = -1, hiShift2 = -1;
   int loShift1 = -1, loShift2 = -1;
   for(int i = lr + 2; i < lookback; i++)
   {
      if(hiShift1 < 0 && PE_IsPivotHigh(sym, tf, i, lr)) hiShift1 = i;
      else if(hiShift1 > 0 && hiShift2 < 0 && PE_IsPivotHigh(sym, tf, i, lr)) { hiShift2 = i; break; }
   }
   for(int i = lr + 2; i < lookback; i++)
   {
      if(loShift1 < 0 && PE_IsPivotLow(sym, tf, i, lr)) loShift1 = i;
      else if(loShift1 > 0 && loShift2 < 0 && PE_IsPivotLow(sym, tf, i, lr)) { loShift2 = i; break; }
   }

   double c1 = iClose(sym, tf, 1);
   if(hiShift1 > 0 && hiShift2 > 0)
   {
      double h1 = iHigh(sym, tf, hiShift1), h2 = iHigh(sym, tf, hiShift2);
      double tol = MathMax(point * 25.0, MathAbs(h1) * 0.0008);
      if(MathAbs(h1 - h2) <= tol)
      {
         int a = MathMin(hiShift1, hiShift2), b = MathMax(hiShift1, hiShift2);
         double neck = DBL_MAX;
         for(int k = a; k <= b; k++) neck = MathMin(neck, iLow(sym, tf, k));
         if(c1 < neck - point * 2)
         {
            out.detected = true;
            out.pattern_id = "DOUBLE_TOP";
            out.family = "CHART";
            out.direction = -1;
            out.entry_level = neck;
            out.invalidation_level = MathMax(h1, h2);
            out.target_level = neck - (MathMax(h1, h2) - neck);
            out.quality = 0.66;
            out.notes = "dtop";
            return true;
         }
      }
   }

   if(loShift1 > 0 && loShift2 > 0)
   {
      double l1 = iLow(sym, tf, loShift1), l2 = iLow(sym, tf, loShift2);
      double tol = MathMax(point * 25.0, MathAbs(l1) * 0.0008);
      if(MathAbs(l1 - l2) <= tol)
      {
         int a = MathMin(loShift1, loShift2), b = MathMax(loShift1, loShift2);
         double neck = -DBL_MAX;
         for(int k = a; k <= b; k++) neck = MathMax(neck, iHigh(sym, tf, k));
         if(c1 > neck + point * 2)
         {
            out.detected = true;
            out.pattern_id = "DOUBLE_BOTTOM";
            out.family = "CHART";
            out.direction = 1;
            out.entry_level = neck;
            out.invalidation_level = MathMin(l1, l2);
            out.target_level = neck + (neck - MathMin(l1, l2));
            out.quality = 0.66;
            out.notes = "dbot";
            return true;
         }
      }
   }
   return false;
}

bool PE_DetectSimpleTriangle(const string sym, ENUM_TIMEFRAMES tf, int lookback, double point, PatternSignal &out)
{
   out.detected = false;
   int w = MathMax(20, lookback / 2);
   double hiA = -DBL_MAX, hiB = -DBL_MAX, loA = DBL_MAX, loB = DBL_MAX;
   for(int i = w; i >= 2; --i)
   {
      double h = iHigh(sym, tf, i), l = iLow(sym, tf, i);
      if(h > hiA) { hiB = hiA; hiA = h; }
      else if(h > hiB) hiB = h;
      if(l < loA) { loB = loA; loA = l; }
      else if(l < loB) loB = l;
   }
   if(hiA <= loA || hiB <= 0 || loB <= 0) return false;
   double topSlope = hiA - hiB;
   double botSlope = loB - loA;
   double c1 = iClose(sym, tf, 1);

   if(MathAbs(topSlope) <= point * 20 && botSlope > point * 25)
   {
      if(c1 > hiA + point * 2)
      {
         out.detected = true;
         out.pattern_id = "ASC_TRIANGLE";
         out.family = "CHART";
         out.direction = 1;
         out.entry_level = hiA;
         out.invalidation_level = loA;
         out.target_level = hiA + (hiA - loA);
         out.quality = 0.61;
         out.notes = "asc_tri";
         return true;
      }
   }
   if(MathAbs(botSlope) <= point * 20 && topSlope > point * 25)
   {
      if(c1 < loA - point * 2)
      {
         out.detected = true;
         out.pattern_id = "DESC_TRIANGLE";
         out.family = "CHART";
         out.direction = -1;
         out.entry_level = loA;
         out.invalidation_level = hiA;
         out.target_level = loA - (hiA - loA);
         out.quality = 0.61;
         out.notes = "desc_tri";
         return true;
      }
   }
   return false;
}

bool PE_DetectFlagPennant(const string sym, ENUM_TIMEFRAMES tf, double atr, double point, PatternSignal &out)
{
   out.detected = false;
   double move = iClose(sym, tf, 6) - iClose(sym, tf, 16);
   double impulse = MathAbs(move);
   if(impulse < atr * 1.2)
      return false;
   double hi = -DBL_MAX, lo = DBL_MAX;
   for(int i = 2; i <= 6; i++)
   {
      hi = MathMax(hi, iHigh(sym, tf, i));
      lo = MathMin(lo, iLow(sym, tf, i));
   }
   if((hi - lo) > impulse * 0.6)
      return false;
   double c1 = iClose(sym, tf, 1);
   int dir = (move > 0 ? 1 : -1);
   if((dir > 0 && c1 > hi + point * 2) || (dir < 0 && c1 < lo - point * 2))
   {
      out.detected = true;
      out.pattern_id = (MathAbs(iHigh(sym, tf, 2) - iLow(sym, tf, 2)) < (hi - lo) * 0.75) ? "PENNANT" : "FLAG";
      out.family = "CHART";
      out.direction = dir;
      out.entry_level = (dir > 0 ? hi : lo);
      out.invalidation_level = (dir > 0 ? lo : hi);
      out.target_level = out.entry_level + dir * impulse;
      out.quality = 0.63;
      out.notes = "flag_like";
      return true;
   }
   return false;
}

PatternSignal PE_DetectBestPattern(const string sym, ENUM_TIMEFRAMES tf, int lookback, int pivotLR, double point, double atr)
{
   PatternSignal s, best;
   best.detected = false;
   if(PE_DetectDoubleTopBottom(sym, tf, lookback, pivotLR, point, s)) best = s;
   if(!best.detected && PE_DetectRectangle(sym, tf, lookback, point, s)) best = s;
   if(!best.detected && PE_DetectSimpleTriangle(sym, tf, lookback, point, s)) best = s;
   if(!best.detected && PE_DetectFlagPennant(sym, tf, atr, point, s)) best = s;
   if(!best.detected && PE_DetectCandles(sym, tf, point, atr, s)) best = s;
   return best;
}

bool PE_LoadPatternStatsCSV(const string fileName, PatternStats &arr[])
{
   ArrayResize(arr, 0);
   int h = FileOpen(fileName, FILE_READ | FILE_CSV | FILE_ANSI, ';');
   if(h == INVALID_HANDLE)
      return false;

   // header
   if(!FileIsEnding(h))
   {
      FileReadString(h); FileReadString(h); FileReadString(h); FileReadString(h);
      FileReadString(h); FileReadString(h); FileReadString(h); FileReadString(h);
      FileReadString(h);
   }

   while(!FileIsEnding(h))
   {
      PatternStats s;
      s.pattern_id = FileReadString(h);
      if(StringLen(s.pattern_id) == 0)
      {
         if(!FileIsEnding(h))
            FileReadString(h);
         continue;
      }
      s.family = FileReadString(h);
      s.direction = (int)StringToInteger(FileReadString(h));
      s.rank = StringToDouble(FileReadString(h));
      s.failure_rate = StringToDouble(FileReadString(h));
      s.target_hit_pct = StringToDouble(FileReadString(h));
      s.avg_move = StringToDouble(FileReadString(h));
      s.sample_size = (int)StringToInteger(FileReadString(h));
      s.notes = FileReadString(h);

      int sz = ArraySize(arr);
      ArrayResize(arr, sz + 1);
      arr[sz] = s;
   }
   FileClose(h);
   return ArraySize(arr) > 0;
}

PatternStats PE_GetStatsById(const PatternStats &arr[], const string id, int direction)
{
   for(int i = 0; i < ArraySize(arr); i++)
   {
      if(arr[i].pattern_id == id)
      {
         if(arr[i].direction == 0 || arr[i].direction == direction)
            return arr[i];
      }
   }
   PatternStats d;
   PE_DefaultStats(d, id, "UNKNOWN", direction);
   return d;
}

double PE_NormalizeAvgMove(double avg_move)
{
   if(avg_move <= 0.0) return 0.0;
   return MathMin(1.0, avg_move / 3.0);
}

double PE_Clamp01(double v)
{
   if(v < 0.0) return 0.0;
   if(v > 1.0) return 1.0;
   return v;
}

double PE_PatternPriorScore(const PatternStats &s, double kRank, double kFail, double kTarget, double kMove)
{
   double score = 50.0;
   score += (50.0 - s.rank) * kRank;
   score += (1.0 - PE_Clamp01(s.failure_rate)) * kFail;
   score += PE_Clamp01(s.target_hit_pct) * kTarget;
   score += PE_NormalizeAvgMove(s.avg_move) * kMove;
   double n = MathMax(1.0, (double)s.sample_size);
   double alpha = MathMin(1.0, n / 200.0);
   score = 50.0 + (score - 50.0) * alpha;
   if(score < 0.0) score = 0.0;
   if(score > 100.0) score = 100.0;
   return score;
}
