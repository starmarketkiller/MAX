# MT5 License Client Integration

## 1) Copy file
Place LicenseClient.mqh into:
MQL5/Include/LicenseClient.mqh
(or keep folder structure you prefer)

## 2) Allow WebRequest domain
MT5 -> Tools -> Options -> Expert Advisors
✅ Allow WebRequest for listed URL
Add:
https://YOUR_DOMAIN_HERE

## 3) Include and call
In EA .mq5:
#include <LicenseClient.mqh>

In OnInit():
EventSetTimer(60);
License_Refresh(); // immediate verify at startup

In OnTimer():
License_Refresh();

In your entry logic:
if(!License_CanOpenNewTrades()) return; // block only new entries

In your trade management logic:
if(!License_CanManageOpenTrades()) return; // optional
