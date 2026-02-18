# MT5 License Client Integration

## Install
Copy `mql5/LicenseClient.mqh` into your include path and include from EA.

## MT5 WebRequest whitelist
Tools -> Options -> Expert Advisors -> Allow WebRequest
Add your tunnel URL, e.g.:
`https://xxxx.ngrok-free.app`

## EA hooks
- OnInit: `EventSetTimer(60); License_Refresh();`
- OnTimer: `License_Refresh();`
- OnDeinit: `EventKillTimer();`
- Before new entries: `if(!License_CanOpenNewTrades()) return;`
- For management path: `if(!License_CanManageOpenTrades()) return;`

## Behavior
- Verify only on startup + periodic interval (`InpVerifyHours`, default 6h)
- Grace period default 48h if API unreachable
- When grace expires, block only new openings
