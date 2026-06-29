import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";
import { Loader2, TrendingUp, Sparkles, Wand2, Brain, Library } from "lucide-react";
import BacktestForm from "@/pages/backtest/BacktestForm";
import BacktestMetrics from "@/pages/backtest/BacktestMetrics";
import BacktestCharts from "@/pages/backtest/BacktestCharts";
import BacktestOptimizer from "@/pages/backtest/BacktestOptimizer";
import BacktestManagementReport from "@/pages/backtest/BacktestManagementReport";
import BacktestStrategyLibrary from "@/pages/backtest/BacktestStrategyLibrary";

const DEFAULT_CFG = {
  symbol: "XAUUSD",
  period: "3y",
  interval: "1d",
  initial_balance: 10000,
  risk_pct: 1.0,
  atr_sl_mult: 1.8,
  atr_tp_mult: 2.8,
  max_concurrent: 1,
  min_score: 60,
  strategies: null,            // null = ALL 36 strategies
  // Gates (default OFF to match user's request: gates should improve, not block)
  adx_min: 0.0,
  htf_bias: false,
  htf_interval: "1d",
  session_london: true,
  session_ny: true,
  session_asian: true,
  cooldown_bars: 3,
  daily_dd_cap: 5.0,
  // Execution
  partial_tp_pct: 0.0,
  breakeven_R: 0.0,
  trailing_atr_mult: 0.0,
  spread_max_pts: 999,
  // Management
  grid_enabled: false,
  grid_step_atr: 1.0,
  grid_max_levels: 3,
  grid_size_mult: 1.5,
  pyramid_enabled: false,
  pyramid_step_R: 1.0,
  pyramid_max_adds: 2,
  pyramid_size_pct: 0.5,
};

export default function BacktestPage() {
  const [symbols, setSymbols] = useState(["XAUUSD", "EURUSD", "BTCUSD", "US30"]);
  const [catalog, setCatalog] = useState(null);   // {families, all, intervals}
  const [presets, setPresets] = useState([]);
  const [cfg, setCfg] = useState(DEFAULT_CFG);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("run");          // 'run' | 'optimize' | 'mgmt'

  useEffect(() => {
    (async () => {
      try {
        const [sym, cat, pst] = await Promise.all([
          api.get("/backtest/symbols"),
          api.get("/backtest/strategies"),
          api.get("/backtest/presets"),
        ]);
        if (sym.data?.symbols) setSymbols(sym.data.symbols);
        setCatalog(cat.data);
        setPresets(pst.data?.presets || []);
        if (cat.data?.all?.length) {
          setCfg((c) => ({ ...c, strategies: cat.data.all.slice() }));
        }
      } catch (e) { console.warn("backtest catalog load failed", e); }
    })();
  }, []);

  const applyPreset = (preset) => {
    setCfg((c) => ({
      ...c,
      ...preset.cfg,
      // If preset doesn't specify strategies, keep "all"
      strategies: preset.cfg.strategies ?? c.strategies,
    }));
  };

  // Apply one Library row to the Run config and switch tab.
  const applyLibraryRow = useCallback((row) => {
    setCfg((c) => ({
      ...c, symbol: row.symbol, interval: row.timeframe,
      strategies: [row.strategy],
      atr_sl_mult: row.atr_sl_mult, atr_tp_mult: row.atr_tp_mult,
      grid_enabled:        row.overrides?.grid_enabled ?? false,
      grid_step_atr:       row.overrides?.grid_step_atr ?? 1.0,
      grid_max_levels:     row.overrides?.grid_max_levels ?? 3,
      grid_size_mult:      row.overrides?.grid_size_mult ?? 1.5,
      pyramid_enabled:     row.overrides?.pyramid_enabled ?? false,
      pyramid_step_R:      row.overrides?.pyramid_step_R ?? 1.0,
      pyramid_max_adds:    row.overrides?.pyramid_max_adds ?? 2,
      pyramid_size_pct:    row.overrides?.pyramid_size_pct ?? 0.5,
      breakeven_R:         row.overrides?.breakeven_R ?? 0.0,
      trailing_atr_mult:   row.overrides?.trailing_atr_mult ?? 0.0,
    }));
    setTab("run");
  }, []);

  // Single-strategy auto-load from the Library
  const [autoLoadedPreset, setAutoLoadedPreset] = useState(null);
  useEffect(() => {
    if (!cfg.strategies || cfg.strategies.length !== 1) {
      setAutoLoadedPreset(null);
      return;
    }
    const strat = cfg.strategies[0];
    const sym = cfg.symbol;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get(
          `/backtest/library_preset?symbol=${sym}&strategy=${strat}`);
        if (cancelled) return;
        const p = data.preset;
        setAutoLoadedPreset({ strategy: p.strategy, symbol: p.symbol,
                               timeframe: p.timeframe, variant: p.variant, metrics: p.metrics });
        setCfg((c) => ({
          ...c, interval: p.timeframe,
          atr_sl_mult: p.atr_sl_mult, atr_tp_mult: p.atr_tp_mult,
          grid_enabled:        p.overrides?.grid_enabled ?? false,
          grid_step_atr:       p.overrides?.grid_step_atr ?? 1.0,
          grid_max_levels:     p.overrides?.grid_max_levels ?? 3,
          grid_size_mult:      p.overrides?.grid_size_mult ?? 1.5,
          pyramid_enabled:     p.overrides?.pyramid_enabled ?? false,
          pyramid_step_R:      p.overrides?.pyramid_step_R ?? 1.0,
          pyramid_max_adds:    p.overrides?.pyramid_max_adds ?? 2,
          pyramid_size_pct:    p.overrides?.pyramid_size_pct ?? 0.5,
          breakeven_R:         p.overrides?.breakeven_R ?? 0.0,
          trailing_atr_mult:   p.overrides?.trailing_atr_mult ?? 0.0,
        }));
      } catch { setAutoLoadedPreset(null); }
    })();
    return () => { cancelled = true; };
  }, [cfg.strategies, cfg.symbol]);

  const run = async () => {
    if (cfg.strategies && cfg.strategies.length === 0) {
      setError("Seleziona almeno una strategia."); return;
    }
    setBusy(true); setError(""); setResult(null);
    try {
      const { data } = await api.post("/backtest/run", cfg);
      setResult(data);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || "Errore backtest");
    } finally {
      setBusy(false);
    }
  };

  const m = result?.metrics;

  return (
    <div className="space-y-6" data-testid="backtest-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-sky-500"/> Backtest Lab v3
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Replay completo delle <strong>36 strategie NEXUS</strong> con tutti i gate dell&apos;EA
            (HTF bias, ADX, sessioni, cooldown, partial TP, breakeven, trailing).
          </p>
        </div>
        <div className="flex items-center gap-1 p-1 bg-secondary/40 rounded-lg" data-testid="bt-tabs">
          <button
            onClick={() => setTab("run")}
            data-testid="bt-tab-run"
            className={`px-3 py-1.5 rounded-md text-xs font-mono uppercase tracking-wider transition-all ${
              tab === "run" ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}>
            <TrendingUp className="h-3.5 w-3.5 inline mr-1.5"/>Run
          </button>
          <button
            onClick={() => setTab("optimize")}
            data-testid="bt-tab-optimize"
            className={`px-3 py-1.5 rounded-md text-xs font-mono uppercase tracking-wider transition-all ${
              tab === "optimize" ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}>
            <Wand2 className="h-3.5 w-3.5 inline mr-1.5"/>AI Optimize
          </button>
          <button
            onClick={() => setTab("mgmt")}
            data-testid="bt-tab-mgmt"
            className={`px-3 py-1.5 rounded-md text-xs font-mono uppercase tracking-wider transition-all ${
              tab === "mgmt" ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}>
            <Brain className="h-3.5 w-3.5 inline mr-1.5"/>Mgmt Report
          </button>
          <button
            onClick={() => setTab("library")}
            data-testid="bt-tab-library"
            className={`px-3 py-1.5 rounded-md text-xs font-mono uppercase tracking-wider transition-all ${
              tab === "library" ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}>
            <Library className="h-3.5 w-3.5 inline mr-1.5"/>Library
          </button>
        </div>
      </div>

      {tab === "run" ? (
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
          <div className="xl:col-span-4 space-y-4">
            {autoLoadedPreset && (
              <div className="rounded-xl border border-cyan-500/40 bg-cyan-500/5 p-3 flex items-start gap-2"
                data-testid="bt-autoloaded-banner">
                <Sparkles className="h-4 w-4 text-cyan-400 mt-0.5 flex-shrink-0"/>
                <div className="text-[11px] leading-relaxed">
                  <div className="font-bold text-cyan-300">Preset auto-caricato dalla Library</div>
                  <div className="text-muted-foreground">
                    {autoLoadedPreset.strategy} · TF {autoLoadedPreset.timeframe} · variant <b>{autoLoadedPreset.variant}</b>
                    {" "}· Sharpe <b>{autoLoadedPreset.metrics?.sharpe}</b> · PF <b>{autoLoadedPreset.metrics?.profit_factor}</b> · DD <b className="text-rose-400">{autoLoadedPreset.metrics?.max_dd_pct}%</b>
                  </div>
                </div>
              </div>
            )}
            {presets.length > 0 && (
              <div className="rounded-xl border border-violet-500/30 bg-violet-500/5 p-3 space-y-2" data-testid="bt-presets">
                <div className="text-[10px] uppercase tracking-wider text-violet-300 font-bold flex items-center gap-1">
                  <Sparkles className="h-3 w-3"/>Preset rapidi
                </div>
                <div className="grid grid-cols-2 gap-1.5">
                  {presets.map((p) => (
                    <button key={p.key} onClick={() => applyPreset(p)}
                      data-testid={`bt-preset-${p.key}`}
                      className="text-left px-2 py-1.5 rounded border border-border bg-background hover:border-violet-500/50 hover:bg-violet-500/5 transition-all"
                      title={p.description}>
                      <div className="text-[11px] font-semibold leading-tight">{p.label}</div>
                      <div className="text-[9px] text-muted-foreground truncate">{p.description}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}
            <BacktestForm
              symbols={symbols}
              catalog={catalog}
              cfg={cfg}
              setCfg={setCfg}
              busy={busy}
              error={error}
              onRun={run}
            />
          </div>
          <div className="xl:col-span-8 space-y-4">
            {!result && !busy && (
              <div className="rounded-xl border border-dashed border-border p-12 text-center text-muted-foreground">
                <TrendingUp className="h-12 w-12 mx-auto mb-3 opacity-30"/>
                Configura i parametri a sinistra e clicca <strong>Esegui Backtest</strong>.
              </div>
            )}
            {busy && (
              <div className="rounded-xl border border-border p-12 text-center">
                <Loader2 className="h-12 w-12 mx-auto mb-3 animate-spin text-sky-500"/>
                <div className="text-muted-foreground">
                  Scarico {cfg.symbol} ed eseguo il backtest...
                </div>
              </div>
            )}
            {result && m && (
              <>
                <BacktestMetrics metrics={m} tradesCount={result.trades_count} bars={result.bars}/>
                <BacktestCharts result={result} cfg={cfg}/>
              </>
            )}
          </div>
        </div>
      ) : tab === "optimize" ? (
        <BacktestOptimizer baseCfg={cfg} symbols={symbols} catalog={catalog}/>
      ) : tab === "mgmt" ? (
        <BacktestManagementReport baseCfg={cfg}/>
      ) : (
        <BacktestStrategyLibrary symbols={symbols} baseCfg={cfg} onApplyRow={applyLibraryRow}/>
      )}
    </div>
  );
}
