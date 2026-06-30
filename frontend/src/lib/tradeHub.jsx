import { createContext, useCallback, useContext, useState } from "react";
import TradeLifecycleDrawer from "@/pages/dashboard/TradeLifecycleDrawer";

const TradeHubContext = createContext({ openTrade: () => {}, closeTrade: () => {} });

export function useTradeHub() {
  return useContext(TradeHubContext);
}

// Provider unico per il drawer del ciclo di vita del trade, condiviso da tutte
// le sezioni (Analytics, Journal, Live Chart…) per un drill-down coerente.
export function TradeHubProvider({ children }) {
  const [trade, setTrade] = useState(null);
  const openTrade = useCallback((t) => setTrade(t), []);
  const closeTrade = useCallback(() => setTrade(null), []);
  return (
    <TradeHubContext.Provider value={{ openTrade, closeTrade, current: trade }}>
      {children}
      <TradeLifecycleDrawer trade={trade} onClose={closeTrade} />
    </TradeHubContext.Provider>
  );
}
