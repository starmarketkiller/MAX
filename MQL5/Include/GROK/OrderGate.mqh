#pragma once
#property strict

bool License_CanOpenNewTrades();
bool License_CanManageOpenTrades();
bool SendOrderCore(TradeDir dir, double lots, double sl, double tp, const string comment, int &retcode, int &lasterr);

bool CanOpenNewTrades()
{
   return License_CanOpenNewTrades();
}

bool CanManageOpenTrades()
{
   return License_CanManageOpenTrades();
}

bool TryOpenBuy(double lots, double sl, double tp, const string comment, int &retcode, int &lasterr)
{
   if(!CanOpenNewTrades())
      return false;
   return SendOrderCore(DIR_LONG, lots, sl, tp, comment, retcode, lasterr);
}

bool TryOpenSell(double lots, double sl, double tp, const string comment, int &retcode, int &lasterr)
{
   if(!CanOpenNewTrades())
      return false;
   return SendOrderCore(DIR_SHORT, lots, sl, tp, comment, retcode, lasterr);
}

bool TryOpenByDir(TradeDir dir, double lots, double sl, double tp, const string comment, int &retcode, int &lasterr)
{
   if(dir == DIR_LONG)
      return TryOpenBuy(lots, sl, tp, comment, retcode, lasterr);
   if(dir == DIR_SHORT)
      return TryOpenSell(lots, sl, tp, comment, retcode, lasterr);
   retcode = 0;
   lasterr = 0;
   return false;
}
