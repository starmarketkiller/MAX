#pragma once
#property strict

struct GrokRiskConfig
{
   double baseRiskPct;
   int maxTradesPerDay;
   double maxDailyDDPct;
};

inline GrokRiskConfig Grok_DefaultRiskConfig()
{
   GrokRiskConfig c;
   c.baseRiskPct = 0.5;
   c.maxTradesPerDay = 3;
   c.maxDailyDDPct = 4.0;
   return c;
}
