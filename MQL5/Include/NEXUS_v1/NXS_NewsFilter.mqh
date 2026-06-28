//+------------------------------------------------------------------+
//|  NXS_NewsFilter.mqh - MT5 Calendar high-impact news               |
//+------------------------------------------------------------------+
#ifndef __NXS_NEWS_MQH__
#define __NXS_NEWS_MQH__

bool _currencyAllowed(string cur){
   string list = InpNewsCurrencies;
   StringToUpper(list);
   StringToUpper(cur);
   return (StringFind(list, cur) >= 0);
}

bool NXS_NewsBlocking(){
   if(!g_run_UseNewsFilter) return false;
   datetime from = TimeCurrent() - InpNewsMinAfter  * 60;
   datetime to   = TimeCurrent() + InpNewsMinBefore * 60;
   MqlCalendarValue values[];
   int n = CalendarValueHistory(values, from, to);
   if(n <= 0) return false;
   for(int i = 0; i < n; i++){
      MqlCalendarEvent ev;
      if(!CalendarEventById(values[i].event_id, ev)) continue;
      if(ev.importance != CALENDAR_IMPORTANCE_HIGH) continue;
      MqlCalendarCountry cc;
      if(!CalendarCountryById(ev.country_id, cc)) continue;
      if(!_currencyAllowed(cc.currency)) continue;
      datetime ts = values[i].time;
      if(ts >= TimeCurrent() - InpNewsMinAfter * 60 &&
         ts <= TimeCurrent() + InpNewsMinBefore * 60){
         return true;
      }
   }
   return false;
}

#endif
