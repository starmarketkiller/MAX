import { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { Calculator, TrendingUp, AlertTriangle, Info } from "lucide-react";

function classNames(...c) { return c.filter(Boolean).join(" "); }
const SYMBOLS = {
  XAUUSD: { pip: 0.01, value_per_lot_per_pip: 1.0,  label: "Gold (XAUUSD)" },
  GOLD:   { pip: 0.01, value_per_lot_per_pip: 1.0,  label: "Gold (GOLD)" },
  EURUSD: { pip: 0.0001, value_per_lot_per_pip: 10, label: "EUR/USD" },
  GBPUSD: { pip: 0.0001, value_per_lot_per_pip: 10, label: "GBP/USD" },
  USDJPY: { pip: 0.01, value_per_lot_per_pip: 9.2,  label: "USD/JPY (approx)" },
  USDCHF: { pip: 0.0001, value_per_lot_per_pip: 11, label: "USD/CHF (approx)" },
  US30:   { pip: 1.0, value_per_lot_per_pip: 1.0,   label: "US30 (Dow)" },
  NAS100: { pip: 1.0, value_per_lot_per_pip: 1.0,   label: "NAS100" },
  BTCUSD: { pip: 1.0, value_per_lot_per_pip: 1.0,   label: "BTC/USD" },
};

function rrrTone(rrr) {
  if (rrr >= 1.5) return "good";
  if (rrr >= 1) return "warn";
  return "bad";
}


function Field({ label, suffix, children, hint }) {
  return (
    <label className="block space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</span>
        {hint && <span className="text-[10px] text-muted-foreground">{hint}</span>}
      </div>
      <div className="relative">
        {children}
        {suffix && <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">{suffix}</span>}
      </div>
    </label>
  );
}

function MetricCard({ label, value, hint, tone = "default" }) {
  const cls = {
    default: "border-border bg-card",
    good:    "border-emerald-500/30 bg-emerald-500/5",
    warn:    "border-amber-500/30 bg-amber-500/5",
    bad:     "border-rose-500/30 bg-rose-500/5",
    primary: "border-sky-500/30 bg-sky-500/5",
  }[tone];
  return (
    <div className={classNames("rounded-xl border p-4", cls)}>
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="text-2xl font-bold mt-1 font-mono">{value}</div>
      {hint && <div className="text-xs text-muted-foreground mt-1">{hint}</div>}
    </div>
  );
}

export default function RiskCalculator() {
  const [balance, setBalance] = useState(1000);
  const [riskPct, setRiskPct] = useState(1.0);
  const [symbol, setSymbol] = useState("XAUUSD");
  const [entry, setEntry] = useState(2050.0);
  const [sl, setSl] = useState(2045.0);
  const [tp, setTp] = useState(2060.0);

  // Auto-fill from EA state
  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/ea/status");
        if (data?.balance) setBalance(Number(data.balance.toFixed(2)));
        if (data?.symbol) {
          const root = String(data.symbol).replace(/[^A-Z]/g, "").slice(0, 6);
          if (SYMBOLS[root]) setSymbol(root);
        }
      } catch (e) { console.warn("risk-calc auto-fill failed", e); }
    })();
  }, []);

  const calc = useMemo(() => {
    const cfg = SYMBOLS[symbol] || SYMBOLS.XAUUSD;
    const slDist = Math.abs(entry - sl);
    const tpDist = Math.abs(tp - entry);
    const slPips = cfg.pip > 0 ? slDist / cfg.pip : 0;
    const tpPips = cfg.pip > 0 ? tpDist / cfg.pip : 0;
    const riskMoney = balance * (riskPct / 100);
    const pipValuePerLot = cfg.value_per_lot_per_pip;
    const lots = slPips > 0 && pipValuePerLot > 0 ? riskMoney / (slPips * pipValuePerLot) : 0;
    const rrr = slDist > 0 ? tpDist / slDist : 0;
    const potentialProfit = lots * tpPips * pipValuePerLot;
    const potentialLoss   = lots * slPips * pipValuePerLot;
    return {
      slDist, tpDist, slPips, tpPips, riskMoney, lots,
      lotsRounded: Math.max(0.01, Math.round(lots * 100) / 100),
      rrr, potentialProfit, potentialLoss,
    };
  }, [balance, riskPct, symbol, entry, sl, tp]);

  // Validations
  const warns = [];
  if (calc.rrr < 1) warns.push({ tone: "bad", msg: `R:R sotto 1 (${calc.rrr.toFixed(2)}) — rendimento atteso negativo` });
  else if (calc.rrr < 1.5) warns.push({ tone: "warn", msg: `R:R basso (${calc.rrr.toFixed(2)}) — punta ad almeno 1.5` });
  if (riskPct > 2) warns.push({ tone: "warn", msg: `Rischio per trade > 2% — sopra il limite prudente` });
  if (riskPct > 5) warns.push({ tone: "bad", msg: `Rischio > 5% per trade — molto pericoloso` });
  if (calc.lotsRounded < 0.01) warns.push({ tone: "warn", msg: "Lot troppo piccolo — SL troppo largo per il rischio scelto" });

  return (
    <div className="space-y-6" data-testid="risk-calc-page">
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Calculator className="h-6 w-6 text-sky-500"/> Risk Calculator
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Calcola la dimensione corretta del lotto in base al rischio e all&apos;SL.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-border bg-card p-5 space-y-4">
          <div className="font-semibold flex items-center gap-2">
            <Info className="h-4 w-4 text-sky-500"/> Parametri
          </div>
          <Field label="Symbol">
            <select value={symbol} onChange={(e) => setSymbol(e.target.value)}
                    className="w-full px-3 py-2 rounded-md bg-background border border-border text-sm"
                    data-testid="risk-symbol">
              {Object.entries(SYMBOLS).map(([k, v]) => (
                <option key={k} value={k}>{v.label}</option>
              ))}
            </select>
          </Field>
          <Field label="Balance" suffix="€/$" hint="Auto-fill da EA">
            <input type="number" min="0" step="10" value={balance}
                   onChange={(e) => setBalance(Number(e.target.value))}
                   className="w-full px-3 py-2 pr-12 rounded-md bg-background border border-border text-sm font-mono"
                   data-testid="risk-balance"/>
          </Field>
          <Field label="Rischio per trade" suffix="%">
            <input type="number" min="0" step="0.1" value={riskPct}
                   onChange={(e) => setRiskPct(Number(e.target.value))}
                   className="w-full px-3 py-2 pr-10 rounded-md bg-background border border-border text-sm font-mono"
                   data-testid="risk-pct"/>
          </Field>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Entry">
              <input type="number" step="0.01" value={entry}
                     onChange={(e) => setEntry(Number(e.target.value))}
                     className="w-full px-2.5 py-2 rounded-md bg-background border border-border text-sm font-mono"
                     data-testid="risk-entry"/>
            </Field>
            <Field label="Stop Loss">
              <input type="number" step="0.01" value={sl}
                     onChange={(e) => setSl(Number(e.target.value))}
                     className="w-full px-2.5 py-2 rounded-md bg-background border border-border text-sm font-mono"
                     data-testid="risk-sl"/>
            </Field>
            <Field label="Take Profit">
              <input type="number" step="0.01" value={tp}
                     onChange={(e) => setTp(Number(e.target.value))}
                     className="w-full px-2.5 py-2 rounded-md bg-background border border-border text-sm font-mono"
                     data-testid="risk-tp"/>
            </Field>
          </div>

          {warns.length > 0 && (
            <div className="space-y-1.5 pt-2">
              {warns.map((w) => (
                <div key={`${w.tone}-${w.msg.slice(0,16)}`} className={classNames("flex items-start gap-2 text-xs p-2 rounded-md",
                  w.tone === "bad" ? "bg-rose-500/10 text-rose-700 dark:text-rose-300"
                                   : "bg-amber-500/10 text-amber-700 dark:text-amber-300")}>
                  <AlertTriangle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0"/>
                  <span>{w.msg}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-4">
          <MetricCard tone="primary" label="Lot size raccomandato"
                      value={calc.lotsRounded.toFixed(2)}
                      hint={`Esatto: ${calc.lots.toFixed(4)} lot`}/>
          <div className="grid grid-cols-2 gap-3">
            <MetricCard label="Rischio in $/€" value={`${calc.riskMoney.toFixed(2)}`}
                        hint={`${riskPct}% di ${balance.toFixed(0)}`}/>
            <MetricCard tone={rrrTone(calc.rrr)}
                        label="Risk:Reward" value={`1 : ${calc.rrr.toFixed(2)}`}/>
            <MetricCard label="SL in pip" value={calc.slPips.toFixed(1)}
                        hint={`Distanza: ${calc.slDist.toFixed(2)}`}/>
            <MetricCard label="TP in pip" value={calc.tpPips.toFixed(1)}
                        hint={`Distanza: ${calc.tpDist.toFixed(2)}`}/>
            <MetricCard tone="bad"  label="Loss potenziale"
                        value={`-${calc.potentialLoss.toFixed(2)}`}/>
            <MetricCard tone="good" label="Profit potenziale"
                        value={`+${calc.potentialProfit.toFixed(2)}`}/>
          </div>
          <div className="rounded-xl border border-sky-500/30 bg-sky-500/5 p-4 text-sm">
            <div className="font-semibold flex items-center gap-2 mb-1">
              <TrendingUp className="h-4 w-4 text-sky-500"/> Suggerimento
            </div>
            <p className="text-muted-foreground">
              Per applicare automaticamente questo lot size, l&apos;EA NEXUS usa già il calcolo
              identico con i parametri da <code className="font-mono text-xs">InpRiskPercent</code> e
              il SL dinamico. Questo calcolatore è utile per <strong>trade manuali</strong> o per validare le scelte dell&apos;EA.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
