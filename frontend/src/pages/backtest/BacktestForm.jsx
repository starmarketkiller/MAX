import { useState } from "react";
import { Play, Loader2, AlertCircle, Layers, Shield, Filter, Zap, CheckSquare, Square, GitMerge, Pyramid } from "lucide-react";

function cn(...c) { return c.filter(Boolean).join(" "); }

const PERIOD_OPTIONS = [
  { v: "6mo", l: "6 mesi" }, { v: "1y", l: "1 anno" },
  { v: "2y", l: "2 anni" }, { v: "3y", l: "3 anni" },
  { v: "5y", l: "5 anni" }, { v: "10y", l: "10 anni" },
];

const INTERVAL_OPTIONS = [
  { v: "1d",  l: "Daily",      hint: "max 10y" },
  { v: "4h",  l: "4 ore",      hint: "max 2y" },
  { v: "1h",  l: "1 ora",      hint: "max 2y" },
  { v: "30m", l: "30 min",     hint: "max 60g" },
  { v: "15m", l: "15 min",     hint: "max 60g" },
  { v: "5m",  l: "5 min",      hint: "max 60g" },
];

const HTF_OPTIONS = [
  { v: "1wk", l: "Weekly" }, { v: "1d", l: "Daily" },
  { v: "4h",  l: "H4" },     { v: "1h", l: "H1" },
];

const FAMILY_COLORS = {
  TREND:         "border-emerald-500/40 bg-emerald-500/5",
  REVERSAL:      "border-amber-500/40 bg-amber-500/5",
  SMC:           "border-cyan-500/40 bg-cyan-500/5",
  INSTITUTIONAL: "border-violet-500/40 bg-violet-500/5",
};

function Field({ label, hint, children }) {
  return (
    <label className="block space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">{label}</span>
        {hint && <span className="text-[10px] text-muted-foreground/70">{hint}</span>}
      </div>
      {children}
    </label>
  );
}

function NumInput({ value, onChange, step, min, max, testid }) {
  return (
    <input type="number" step={step} min={min} max={max}
      value={value} onChange={(e) => onChange(Number(e.target.value))}
      className="w-full px-2.5 py-1.5 rounded-md bg-background border border-border text-sm font-mono"
      data-testid={testid}/>
  );
}

function Toggle({ checked, onChange, label, testid }) {
  return (
    <button onClick={onChange} type="button" data-testid={testid}
      className={cn("w-full flex items-center justify-between px-3 py-2 rounded-md border text-xs",
        checked ? "border-sky-500/50 bg-sky-500/10 text-sky-300" : "border-border bg-background text-muted-foreground")}>
      <span className="uppercase tracking-wide font-medium">{label}</span>
      <span className={cn("h-4 w-4 rounded border-2 flex items-center justify-center",
        checked ? "border-sky-400 bg-sky-500" : "border-border")}>
        {checked && <span className="text-[10px] text-white">✓</span>}
      </span>
    </button>
  );
}

const TABS = [
  { id: "strategies", label: "Strategie", icon: Layers },
  { id: "risk",       label: "Risk",      icon: Shield },
  { id: "filters",    label: "Filtri",    icon: Filter },
  { id: "execution",  label: "Esecuzione", icon: Zap },
  { id: "management", label: "Gestione",  icon: GitMerge },
];

export default function BacktestForm({ symbols, catalog, cfg, setCfg, busy, error, onRun }) {
  const [tab, setTab] = useState("strategies");
  const families = catalog?.families || {};
  const allStrats = catalog?.all || [];
  const selected = new Set(cfg.strategies || []);

  const toggleStrat = (id) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    setCfg((c) => ({ ...c, strategies: [...next] }));
  };
  const selectAll = () => setCfg((c) => ({ ...c, strategies: allStrats.slice() }));
  const selectNone = () => setCfg((c) => ({ ...c, strategies: [] }));
  const selectFamily = (fam) => {
    const next = new Set(selected);
    families[fam].forEach((s) => next.add(s.id));
    setCfg((c) => ({ ...c, strategies: [...next] }));
  };

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="p-3 border-b border-border space-y-2.5">
        <div className="grid grid-cols-3 gap-2">
          <Field label="Symbol">
            <select value={cfg.symbol} onChange={(e) => setCfg({...cfg, symbol: e.target.value})}
              className="w-full px-2 py-1.5 rounded-md bg-background border border-border text-sm" data-testid="bt-symbol">
              {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </Field>
          <Field label="Period">
            <select value={cfg.period} onChange={(e) => setCfg({...cfg, period: e.target.value})}
              className="w-full px-2 py-1.5 rounded-md bg-background border border-border text-sm" data-testid="bt-period">
              {PERIOD_OPTIONS.map((o) => <option key={o.v} value={o.v}>{o.l}</option>)}
            </select>
          </Field>
          <Field label="TF" hint={INTERVAL_OPTIONS.find(o => o.v === cfg.interval)?.hint || ""}>
            <select value={cfg.interval} onChange={(e) => setCfg({...cfg, interval: e.target.value})}
              className="w-full px-2 py-1.5 rounded-md bg-background border border-border text-sm" data-testid="bt-interval">
              {INTERVAL_OPTIONS.map((o) => <option key={o.v} value={o.v}>{o.l}</option>)}
            </select>
          </Field>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border bg-secondary/30">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button key={t.id} onClick={() => setTab(t.id)} type="button"
              data-testid={`bt-form-tab-${t.id}`}
              className={cn("flex-1 px-2 py-2 text-[10px] uppercase tracking-wider font-medium flex items-center justify-center gap-1 transition-all",
                tab === t.id ? "bg-card text-foreground border-b-2 border-sky-500" : "text-muted-foreground hover:text-foreground")}>
              <Icon className="h-3 w-3"/>{t.label}
            </button>
          );
        })}
      </div>

      <div className="p-3 space-y-3 max-h-[440px] overflow-y-auto">
        {tab === "strategies" && (
          <>
            <div className="flex items-center justify-between text-[10px] uppercase tracking-wider text-muted-foreground">
              <span>Selezionate: <span className="font-bold text-foreground">{selected.size}</span>/{allStrats.length}</span>
              <div className="flex gap-1">
                <button onClick={selectAll} type="button" data-testid="bt-select-all"
                  className="px-2 py-0.5 rounded border border-border hover:border-sky-500/50">Tutte</button>
                <button onClick={selectNone} type="button" data-testid="bt-select-none"
                  className="px-2 py-0.5 rounded border border-border hover:border-rose-500/50">Nessuna</button>
              </div>
            </div>
            {Object.entries(families).map(([fam, list]) => (
              <div key={fam} className={cn("rounded-lg border p-2 space-y-1.5", FAMILY_COLORS[fam])}>
                <div className="flex items-center justify-between">
                  <div className="text-[10px] uppercase font-mono tracking-wider opacity-80">{fam} <span className="opacity-50">({list.length})</span></div>
                  <button onClick={() => selectFamily(fam)} type="button"
                    data-testid={`bt-fam-${fam.toLowerCase()}`}
                    className="text-[10px] underline opacity-70 hover:opacity-100">attiva tutte</button>
                </div>
                <div className="grid grid-cols-2 gap-1">
                  {list.map((s) => (
                    <button key={s.id} onClick={() => toggleStrat(s.id)} type="button"
                      data-testid={`bt-strat-${s.id}`}
                      className={cn("flex items-center gap-1.5 px-2 py-1 rounded text-[11px] font-mono transition-all",
                        selected.has(s.id) ? "bg-background border border-border" : "bg-background/30 hover:bg-background/60")}>
                      {selected.has(s.id) ? <CheckSquare className="h-3 w-3 text-sky-400"/> : <Square className="h-3 w-3 text-muted-foreground/40"/>}
                      <span className="truncate flex-1 text-left">{s.id}</span>
                      <span className="opacity-50 text-[9px]">{s.score_base}</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </>
        )}

        {tab === "risk" && (
          <div className="grid grid-cols-2 gap-2">
            <Field label="Balance"><NumInput value={cfg.initial_balance} onChange={(v) => setCfg({...cfg, initial_balance: v})} step="100" testid="bt-balance"/></Field>
            <Field label="Rischio %" hint="per trade"><NumInput value={cfg.risk_pct} onChange={(v) => setCfg({...cfg, risk_pct: v})} step="0.1" testid="bt-risk"/></Field>
            <Field label="Min Score" hint="0-100"><NumInput value={cfg.min_score} onChange={(v) => setCfg({...cfg, min_score: v})} step="1" min={0} max={100} testid="bt-score"/></Field>
            <Field label="Max Concurrent"><NumInput value={cfg.max_concurrent} onChange={(v) => setCfg({...cfg, max_concurrent: v})} step="1" min={1} testid="bt-maxconcurrent"/></Field>
            <Field label="ATR × SL"><NumInput value={cfg.atr_sl_mult} onChange={(v) => setCfg({...cfg, atr_sl_mult: v})} step="0.1" testid="bt-atrsl"/></Field>
            <Field label="ATR × TP"><NumInput value={cfg.atr_tp_mult} onChange={(v) => setCfg({...cfg, atr_tp_mult: v})} step="0.1" testid="bt-atrtp"/></Field>
            <Field label="Daily DD cap %" hint="stop giornaliero"><NumInput value={cfg.daily_dd_cap} onChange={(v) => setCfg({...cfg, daily_dd_cap: v})} step="0.5" testid="bt-dailydd"/></Field>
            <Field label="Cooldown bars"><NumInput value={cfg.cooldown_bars} onChange={(v) => setCfg({...cfg, cooldown_bars: v})} step="1" min={0} testid="bt-cooldown"/></Field>
          </div>
        )}

        {tab === "filters" && (
          <>
            <div className="grid grid-cols-2 gap-2">
              <Field label="ADX min" hint="0 = off"><NumInput value={cfg.adx_min} onChange={(v) => setCfg({...cfg, adx_min: v})} step="1" min={0} testid="bt-adxmin"/></Field>
              <Field label="HTF interval" hint="MTF bias">
                <select value={cfg.htf_interval} onChange={(e) => setCfg({...cfg, htf_interval: e.target.value})}
                  className="w-full px-2 py-1.5 rounded-md bg-background border border-border text-sm" data-testid="bt-htfinterval">
                  {HTF_OPTIONS.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
                </select>
              </Field>
            </div>
            <div className="space-y-1.5 pt-2">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Gates</div>
              <Toggle label="HTF bias filter" checked={cfg.htf_bias} testid="bt-htfbias"
                onChange={() => setCfg({...cfg, htf_bias: !cfg.htf_bias})}/>
              <div className="grid grid-cols-3 gap-1.5">
                <Toggle label="London" checked={cfg.session_london} testid="bt-sess-london"
                  onChange={() => setCfg({...cfg, session_london: !cfg.session_london})}/>
                <Toggle label="NY" checked={cfg.session_ny} testid="bt-sess-ny"
                  onChange={() => setCfg({...cfg, session_ny: !cfg.session_ny})}/>
                <Toggle label="Asian" checked={cfg.session_asian} testid="bt-sess-asian"
                  onChange={() => setCfg({...cfg, session_asian: !cfg.session_asian})}/>
              </div>
            </div>
          </>
        )}

        {tab === "execution" && (
          <div className="grid grid-cols-2 gap-2">
            <Field label="Partial TP %" hint="@ +1R (0=off)"><NumInput value={cfg.partial_tp_pct} onChange={(v) => setCfg({...cfg, partial_tp_pct: v})} step="0.1" min={0} max={1} testid="bt-partial"/></Field>
            <Field label="Breakeven R" hint="sposta SL @ +XR"><NumInput value={cfg.breakeven_R} onChange={(v) => setCfg({...cfg, breakeven_R: v})} step="0.1" min={0} testid="bt-be"/></Field>
            <Field label="Trail ATR×" hint="trailing stop"><NumInput value={cfg.trailing_atr_mult} onChange={(v) => setCfg({...cfg, trailing_atr_mult: v})} step="0.1" min={0} testid="bt-trail"/></Field>
            <Field label="Spread max pts" hint="cap esecuzione"><NumInput value={cfg.spread_max_pts} onChange={(v) => setCfg({...cfg, spread_max_pts: v})} step="1" min={0} testid="bt-spread"/></Field>
          </div>
        )}

        {tab === "management" && (
          <div className="space-y-3">
            <div className="rounded-md border border-rose-500/30 bg-rose-500/5 p-2 text-[11px] leading-relaxed text-rose-200/80">
              <b className="text-rose-300">⚠️ Strumenti avanzati.</b> Grid e Pyramiding modificano la posizione aperta.
              Il Coach ti suggerirà quale strategia li tollera meglio (vedi "AI Optimize").
            </div>

            {/* Pyramiding */}
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-2 space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-xs font-mono uppercase tracking-wider text-emerald-300 flex items-center gap-1">
                  <Pyramid className="h-3.5 w-3.5"/> Pyramiding
                </div>
                <Toggle label={cfg.pyramid_enabled ? "ON" : "OFF"} checked={cfg.pyramid_enabled} testid="bt-pyramid-on"
                  onChange={() => setCfg({...cfg, pyramid_enabled: !cfg.pyramid_enabled})}/>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <Field label="Step R" hint="aggiunge @ +X*R"><NumInput value={cfg.pyramid_step_R} onChange={(v) => setCfg({...cfg, pyramid_step_R: v})} step="0.1" min={0.5} testid="bt-pyr-step"/></Field>
                <Field label="Max add"><NumInput value={cfg.pyramid_max_adds} onChange={(v) => setCfg({...cfg, pyramid_max_adds: v})} step="1" min={1} max={5} testid="bt-pyr-max"/></Field>
                <Field label="Size %" hint="of initial"><NumInput value={cfg.pyramid_size_pct} onChange={(v) => setCfg({...cfg, pyramid_size_pct: v})} step="0.1" min={0.1} max={2} testid="bt-pyr-size"/></Field>
              </div>
            </div>

            {/* Grid recovery */}
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-2 space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-xs font-mono uppercase tracking-wider text-amber-300 flex items-center gap-1">
                  <GitMerge className="h-3.5 w-3.5"/> Grid Recovery
                </div>
                <Toggle label={cfg.grid_enabled ? "ON" : "OFF"} checked={cfg.grid_enabled} testid="bt-grid-on"
                  onChange={() => setCfg({...cfg, grid_enabled: !cfg.grid_enabled})}/>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <Field label="Step ATR" hint="adverse trigger"><NumInput value={cfg.grid_step_atr} onChange={(v) => setCfg({...cfg, grid_step_atr: v})} step="0.1" min={0.3} testid="bt-grid-step"/></Field>
                <Field label="Max lvl"><NumInput value={cfg.grid_max_levels} onChange={(v) => setCfg({...cfg, grid_max_levels: v})} step="1" min={1} max={6} testid="bt-grid-max"/></Field>
                <Field label="Size ×" hint="1.0=flat 2.0=mart"><NumInput value={cfg.grid_size_mult} onChange={(v) => setCfg({...cfg, grid_size_mult: v})} step="0.1" min={1.0} max={3.0} testid="bt-grid-mult"/></Field>
              </div>
              {cfg.grid_size_mult > 1.6 && cfg.grid_enabled && (
                <div className="text-[10px] text-rose-400 flex items-center gap-1"><AlertCircle className="h-3 w-3"/>Martingala-like: rischio elevato di DD esplosivo.</div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="p-3 border-t border-border space-y-2">
        <button onClick={onRun} disabled={busy}
          className={cn("w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-md text-sm",
            "bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white font-semibold transition-all")}
          data-testid="bt-run-btn">
          {busy ? <><Loader2 className="h-4 w-4 animate-spin"/>Esecuzione...</> : <><Play className="h-4 w-4"/>Esegui Backtest</>}
        </button>
        {error && (
          <div className="flex items-start gap-2 p-2 rounded-md bg-rose-500/10 text-rose-700 dark:text-rose-300 text-xs" data-testid="bt-error">
            <AlertCircle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0"/><span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
}
