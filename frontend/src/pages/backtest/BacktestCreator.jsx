import { useCallback, useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { Loader2, Wand2, Save, FlaskConical, Trophy, Target, Download, Copy, Lock } from "lucide-react";
import { toast } from "sonner";

const VCLS = {
  FORTE: "text-emerald-400", OK: "text-sky-400", DEBOLE: "text-amber-400",
  CRITICA: "text-rose-400", POCHI_DATI: "text-muted-foreground", NO_SETUP: "text-muted-foreground",
};

function parseNums(s, fallback) {
  const arr = String(s || "").split(",").map((x) => parseFloat(x.trim())).filter((x) => !isNaN(x));
  return arr.length ? arr : fallback;
}

export default function BacktestCreator({ symbols = [], catalog, baseCfg }) {
  const allStrats = useMemo(() => catalog?.all || [], [catalog]);
  const [symbol, setSymbol] = useState(baseCfg?.symbol || "XAUUSD");
  const [pool, setPool] = useState([]);
  const [sizes, setSizes] = useState({ 1: true, 2: true, 3: false });
  const [slGrid, setSlGrid] = useState("1.5, 2.0");
  const [tpGrid, setTpGrid] = useState("2.5, 3.5");
  const [minTrades, setMinTrades] = useState(8);
  const [maxCombos, setMaxCombos] = useState(80);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [res, setRes] = useState(null);
  const [perStrat, setPerStrat] = useState(null);   // tabella best-per-strategia
  const [copied, setCopied] = useState(false);
  const [saved, setSaved] = useState([]);

  useEffect(() => {
    // pool iniziale = tutte le strategie disponibili
    if (allStrats.length && pool.length === 0) setPool(allStrats.slice());
  }, [allStrats]); // eslint-disable-line

  const loadSaved = useCallback(async () => {
    try { const { data } = await api.get("/backtest/creator/saved"); setSaved(data.setups || []); }
    catch { /* noop */ }
  }, []);
  useEffect(() => { loadSaved(); }, [loadSaved]);

  const toggleStrat = (s) =>
    setPool((p) => (p.includes(s) ? p.filter((x) => x !== s) : [...p, s]));

  const run = async () => {
    if (pool.length === 0) { setError("Seleziona almeno una strategia nel pool."); return; }
    const combo_sizes = Object.entries(sizes).filter(([, v]) => v).map(([k]) => Number(k));
    if (!combo_sizes.length) { setError("Seleziona almeno una dimensione combinazione."); return; }
    setBusy(true); setError(""); setRes(null);
    try {
      const { data } = await api.post("/backtest/creator", {
        symbol, timeframe: "D1", pool, combo_sizes,
        param_grid: { atr_sl: parseNums(slGrid, [1.8]), atr_tp: parseNums(tpGrid, [2.8]) },
        risk_pct: baseCfg?.risk_pct ?? 1.0, initial_balance: baseCfg?.initial_balance ?? 10000,
        min_trades: Number(minTrades) || 8, max_combos: Number(maxCombos) || 80,
      });
      setRes(data);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || "Errore creator");
    } finally { setBusy(false); }
  };

  const saveSetup = async (row) => {
    try { await api.post("/backtest/creator/save", { setup: row }); await loadSaved(); }
    catch { /* noop */ }
  };

  // Best per strategia: per OGNI strategia trova i SUOI parametri migliori.
  const runPerStrategy = async () => {
    if (pool.length === 0) { setError("Seleziona almeno una strategia nel pool."); return; }
    setBusy(true); setError(""); setPerStrat(null); setRes(null);
    try {
      const { data } = await api.post("/backtest/optimize_per_strategy", {
        symbol, timeframe: "D1", pool,
        param_grid: { atr_sl: parseNums(slGrid, [1.2, 1.5, 1.8, 2.2, 2.6]),
                      atr_tp: parseNums(tpGrid, [2.0, 2.8, 3.5, 4.5]) },
        risk_pct: baseCfg?.risk_pct ?? 1.0, initial_balance: baseCfg?.initial_balance ?? 10000,
        min_trades: Number(minTrades) || 8,
      });
      setPerStrat(data);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || "Errore ottimizzazione");
    } finally { setBusy(false); }
  };

  // Manda una strategia trovata direttamente nella sezione Strategie (Locked Profile):
  // l'EA la applica al prossimo OnInit. Questo è il flusso Creator -> Strategie manuale.
  const lockRow = async (r) => {
    const rawTf = (r.tf || perStrat?.timeframe || "1d").toLowerCase();
    const tfLabel = rawTf === "1d" ? "D1" : rawTf.toUpperCase();
    try {
      await api.post("/backtest/locked_profile", {
        symbol, timeframe: tfLabel,
        label: `Creator · ${r.strategy} · ${tfLabel} · SL${r.atr_sl}/TP${r.atr_tp} (${r.verdict})`,
        base_cfg: {
          symbol, period: "3y", interval: rawTf, strategies: [r.strategy],
          atr_sl_mult: r.atr_sl, atr_tp_mult: r.atr_tp,
          min_score: 50, max_concurrent: 1,
          risk_pct: r.risk_pct != null ? r.risk_pct : (baseCfg?.risk_pct ?? 1.0),
          htf_bias: !!r.htf_filter, cooldown_bars: 0, initial_balance: baseCfg?.initial_balance ?? 10000,
        },
        overrides: {
          htf_filter: r.htf_filter, breakeven_r: r.breakeven_r,
          trailing_atr: r.trailing_atr, verdict: r.verdict,
        },
        metrics: { profit_factor: r.pf, win_rate: r.wr, max_dd: r.dd, sharpe: r.robust,
                   total_return: r.net, n_trades: r.trades },
      });
      toast.success(`${r.strategy} inviata a Strategie (Locked Profile) — l'EA la applica al prossimo avvio`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message || "Errore lock");
    }
  };

  // Multi-TF: per OGNI strategia trova il TIMEFRAME migliore (D1/H4/H1) + params
  // + gate + rischio. Alcune rendono in daily, altre H4/H1: le tiene sul loro TF.
  const runMultiTF = async () => {
    if (pool.length === 0) { setError("Seleziona almeno una strategia nel pool."); return; }
    setBusy(true); setError(""); setPerStrat(null); setRes(null);
    try {
      const { data } = await api.post("/backtest/optimize_multi_tf", {
        symbol, pool, timeframes: ["1d", "4h", "1h"],
        param_grid: { atr_sl: parseNums(slGrid, [1.0, 1.5, 2.0]),
                      atr_tp: parseNums(tpGrid, [2.0, 3.0, 4.5]) },
        initial_balance: baseCfg?.initial_balance ?? 10000,
        min_trades: Number(minTrades) || 8, target_dd: 10.0,
      });
      setPerStrat(data);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || "Errore multi-TF");
    } finally { setBusy(false); }
  };

  const exportTable = () => {
    if (!perStrat?.table) return;
    const payload = { symbol: perStrat.symbol, timeframe: perStrat.timeframe,
                      generated: new Date().toISOString(), table: perStrat.table };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `nexus_best_per_strategy_${perStrat.symbol}.json`;
    a.click(); URL.revokeObjectURL(url);
  };

  const copyTable = async () => {
    if (!perStrat?.table) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(perStrat.table, null, 2));
      setCopied(true); setTimeout(() => setCopied(false), 1500);
    } catch { /* noop */ }
  };

  return (
    <div className="space-y-5" data-testid="bt-creator">
      <div className="rounded-xl border border-border p-4">
        <div className="flex items-center gap-2 mb-1">
          <Wand2 className="h-5 w-5 text-violet-400" />
          <h2 className="text-lg font-bold">Strategy Creator</h2>
        </div>
        <p className="text-sm text-muted-foreground">
          Genera <b>combinazioni</b> di strategie × griglia di parametri, le testa sul motore e
          le classifica coi verdetti. Onesto: gira su dati <b>daily</b> — usalo per il
          <b> ranking relativo</b> (quali combo/parametri battono le altre), non come verità intraday.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Config */}
        <div className="space-y-3">
          <div className="rounded-xl border border-border p-3">
            <label className="text-[10px] uppercase tracking-wide text-muted-foreground">Simbolo</label>
            <select value={symbol} onChange={(e) => setSymbol(e.target.value)}
              className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-sm">
              {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div className="rounded-xl border border-border p-3 space-y-2">
            <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Combinazioni</div>
            <div className="flex gap-2">
              {[1, 2, 3].map((k) => (
                <button key={k} onClick={() => setSizes((s) => ({ ...s, [k]: !s[k] }))}
                  className={`px-3 py-1 rounded text-xs font-mono border ${
                    sizes[k] ? "border-violet-500/50 bg-violet-500/10 text-violet-300" : "border-border text-muted-foreground"}`}>
                  {k}x
                </button>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <label>ATR SL <input value={slGrid} onChange={(e) => setSlGrid(e.target.value)}
                className="w-full mt-0.5 px-2 py-1 rounded border border-border bg-background" /></label>
              <label>ATR TP <input value={tpGrid} onChange={(e) => setTpGrid(e.target.value)}
                className="w-full mt-0.5 px-2 py-1 rounded border border-border bg-background" /></label>
              <label>min trade <input type="number" value={minTrades} onChange={(e) => setMinTrades(e.target.value)}
                className="w-full mt-0.5 px-2 py-1 rounded border border-border bg-background" /></label>
              <label>max test <input type="number" value={maxCombos} onChange={(e) => setMaxCombos(e.target.value)}
                className="w-full mt-0.5 px-2 py-1 rounded border border-border bg-background" /></label>
            </div>
            <button onClick={run} disabled={busy}
              data-testid="bt-creator-run"
              className="w-full mt-1 px-3 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-sm inline-flex items-center justify-center gap-1.5 disabled:opacity-50">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FlaskConical className="h-4 w-4" />}
              Genera &amp; Testa (combo)
            </button>
            <button onClick={runPerStrategy} disabled={busy}
              data-testid="bt-creator-perstrat"
              className="w-full px-3 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-sm inline-flex items-center justify-center gap-1.5 disabled:opacity-50">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Target className="h-4 w-4" />}
              Best per strategia
            </button>
            <button onClick={runMultiTF} disabled={busy}
              data-testid="bt-creator-multitf"
              className="w-full px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm inline-flex items-center justify-center gap-1.5 disabled:opacity-50">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Target className="h-4 w-4" />}
              Multi-TF (best TF + rischio)
            </button>
            {error && <div className="text-xs text-rose-400">{error}</div>}
          </div>
          {/* Pool */}
          <div className="rounded-xl border border-border p-3">
            <div className="flex items-center justify-between mb-1">
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Pool ({pool.length})</div>
              <div className="flex gap-1">
                <button onClick={() => setPool(allStrats.slice())} className="text-[10px] text-sky-400">tutte</button>
                <button onClick={() => setPool([])} className="text-[10px] text-muted-foreground">nessuna</button>
              </div>
            </div>
            <div className="max-h-52 overflow-y-auto grid grid-cols-2 gap-1">
              {allStrats.map((s) => (
                <button key={s} onClick={() => toggleStrat(s)}
                  className={`text-left px-2 py-1 rounded text-[10px] font-mono border ${
                    pool.includes(s) ? "border-sky-500/40 bg-sky-500/10" : "border-border text-muted-foreground"}`}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Risultati */}
        <div className="lg:col-span-2 space-y-3">
          {/* Tabella BEST PER STRATEGIA (parametri ottimali per ognuna) */}
          {perStrat?.table && (
            <div className="rounded-xl border border-sky-500/30 bg-sky-500/5 overflow-hidden">
              <div className="flex items-center justify-between px-3 py-2 border-b border-sky-500/20">
                <div className="text-xs font-bold text-sky-300 flex items-center gap-1.5">
                  <Target className="h-4 w-4" /> Parametri ottimali per strategia ({perStrat.table.length})
                </div>
                <div className="flex gap-1.5">
                  <button onClick={copyTable} className="text-[11px] px-2 py-1 rounded border border-border hover:bg-secondary inline-flex items-center gap-1">
                    <Copy className="h-3 w-3" />{copied ? "copiato!" : "copia"}
                  </button>
                  <button onClick={exportTable} className="text-[11px] px-2 py-1 rounded border border-sky-500/40 text-sky-300 hover:bg-sky-500/10 inline-flex items-center gap-1">
                    <Download className="h-3 w-3" /> esporta JSON
                  </button>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-[10px] uppercase tracking-wide text-muted-foreground border-b border-border">
                      <th className="text-left px-3 py-2">Strategia</th>
                      <th className="text-center px-2 py-2">TF</th>
                      <th className="text-right px-2 py-2">R%</th>
                      <th className="text-right px-2 py-2">ATR SL</th>
                      <th className="text-right px-2 py-2">ATR TP</th>
                      <th className="text-center px-2 py-2">HTF</th>
                      <th className="text-center px-2 py-2">BE</th>
                      <th className="text-center px-2 py-2">Trail</th>
                      <th className="text-right px-2 py-2">N</th>
                      <th className="text-right px-2 py-2">PF</th>
                      <th className="text-right px-2 py-2">Net</th>
                      <th className="text-right px-2 py-2">DD%</th>
                      <th className="text-left px-2 py-2">Verdetto</th>
                      <th className="px-2 py-2"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {perStrat.table.map((r) => (
                      <tr key={r.strategy} className="border-b border-border/50 hover:bg-secondary/30">
                        <td className="px-3 py-1.5 font-mono font-semibold">{r.strategy}</td>
                        <td className="px-2 py-1.5 text-center font-mono text-[11px] text-emerald-300">{r.tf ? r.tf.toUpperCase() : "—"}</td>
                        <td className="px-2 py-1.5 text-right font-mono text-[11px] text-amber-300">{r.risk_pct != null ? r.risk_pct : "—"}</td>
                        <td className="px-2 py-1.5 text-right font-mono text-sky-300">{r.atr_sl}</td>
                        <td className="px-2 py-1.5 text-right font-mono text-sky-300">{r.atr_tp}</td>
                        <td className="px-2 py-1.5 text-center font-mono text-[11px]">{r.htf_filter ? "✓" : "—"}</td>
                        <td className="px-2 py-1.5 text-center font-mono text-[11px]">{r.breakeven_r ? r.breakeven_r + "R" : "—"}</td>
                        <td className="px-2 py-1.5 text-center font-mono text-[11px]">{r.trailing_atr ? r.trailing_atr : "—"}</td>
                        <td className="px-2 py-1.5 text-right font-mono">{r.trades}</td>
                        <td className="px-2 py-1.5 text-right font-mono">{r.pf}</td>
                        <td className={`px-2 py-1.5 text-right font-mono ${r.net >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{r.net}</td>
                        <td className="px-2 py-1.5 text-right font-mono text-muted-foreground">{r.dd}</td>
                        <td className={`px-2 py-1.5 font-mono text-[11px] ${VCLS[r.verdict] || ""}`}>{r.verdict}</td>
                        <td className="px-2 py-1.5 text-right">
                          <button onClick={() => lockRow(r)} title="Invia a Strategie (Locked Profile)"
                            className="text-violet-400 hover:text-violet-300 inline-flex items-center gap-1 text-[10px]">
                            <Lock className="h-3 w-3" /> Strategie
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="px-3 py-2 text-[10px] text-muted-foreground border-t border-border">
                Ogni riga ha i parametri MIGLIORI per quella strategia (non globali). <b>Lock → Strategie</b> la
                manda subito all&apos;EA. Oppure esporta e mandami il file:
                rendo l&apos;EA coerente con questi valori per-strategia.
              </div>
            </div>
          )}

          {res?.results && (
            <div className="text-xs text-muted-foreground">
              {res.combos_tested} combinazioni testate su {res.symbol} · migliori {res.results.length}
            </div>
          )}
          {res?.results?.length > 0 ? (
            <div className="rounded-xl border border-border overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wide text-muted-foreground border-b border-border">
                    <th className="text-left px-3 py-2">Setup (combo)</th>
                    <th className="text-right px-2 py-2">SL/TP</th>
                    <th className="text-right px-2 py-2">N</th>
                    <th className="text-right px-2 py-2">PF</th>
                    <th className="text-right px-2 py-2">Net</th>
                    <th className="text-right px-2 py-2">DD%</th>
                    <th className="text-left px-2 py-2">Verdetto</th>
                    <th className="text-right px-2 py-2">Robust</th>
                    <th className="px-2 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {res.results.map((r, i) => (
                    <tr key={i} className="border-b border-border/50 hover:bg-secondary/30">
                      <td className="px-3 py-1.5 font-mono text-[11px]">{r.name}</td>
                      <td className="px-2 py-1.5 text-right font-mono text-[11px] text-muted-foreground">{r.atr_sl}/{r.atr_tp}</td>
                      <td className="px-2 py-1.5 text-right font-mono">{r.trades}</td>
                      <td className="px-2 py-1.5 text-right font-mono">{r.pf}</td>
                      <td className={`px-2 py-1.5 text-right font-mono ${r.net >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{r.net}</td>
                      <td className="px-2 py-1.5 text-right font-mono text-muted-foreground">{r.dd}</td>
                      <td className={`px-2 py-1.5 font-mono text-[11px] ${VCLS[r.verdict] || ""}`}>{r.verdict}</td>
                      <td className="px-2 py-1.5 text-right font-mono">{r.robust}</td>
                      <td className="px-2 py-1.5 text-right">
                        <button onClick={() => saveSetup(r)} title="Salva setup"
                          className="text-violet-400 hover:text-violet-300"><Save className="h-3.5 w-3.5" /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : !busy && (
            <div className="rounded-xl border border-dashed border-border p-10 text-center text-muted-foreground text-sm">
              Configura pool e parametri a sinistra, poi <b>Genera &amp; Testa</b>.
            </div>
          )}

          {saved.length > 0 && (
            <div className="rounded-xl border border-violet-500/30 bg-violet-500/5 p-3">
              <div className="text-[10px] uppercase tracking-wide text-violet-300 font-bold flex items-center gap-1 mb-1">
                <Trophy className="h-3 w-3" /> Setup salvati ({saved.length})
              </div>
              <div className="space-y-1">
                {saved.slice(0, 8).map((s, i) => (
                  <div key={i} className="text-[11px] font-mono flex justify-between">
                    <span>{s.name} · {s.atr_sl}/{s.atr_tp}</span>
                    <span className="text-muted-foreground">PF {s.pf} · net {s.net} · {s.verdict}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
