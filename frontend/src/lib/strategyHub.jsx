import { createContext, useCallback, useContext, useState } from "react";
import StrategyDrawer from "@/pages/dashboard/StrategyDrawer";

const StrategyHubContext = createContext({ open: () => {}, close: () => {} });

export function useStrategyHub() {
  return useContext(StrategyHubContext);
}

// Provider unico: tiene la strategia selezionata e monta un solo StrategyDrawer
// condiviso da tutte le sezioni (Strategies, Optimizer, Strat Diag…).
export function StrategyHubProvider({ children }) {
  const [name, setName] = useState(null);
  const open = useCallback((n) => setName(n), []);
  const close = useCallback(() => setName(null), []);
  return (
    <StrategyHubContext.Provider value={{ open, close, current: name }}>
      {children}
      {name && <StrategyDrawer name={name} onClose={close} />}
    </StrategyHubContext.Provider>
  );
}
