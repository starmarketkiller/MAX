import { useCallback, useEffect, useMemo, useState } from "react";
import { Gauge, RefreshCw, Save, TrendingUp, AlertTriangle, Power } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import {
  Card, cls, SectionHeader, KpiCard, fmtMoney, fmtPct, POS_TEXT, NEG_TEXT,
} from "@/pages/dashboard/shared";

function multTone(m) {
  if (m == null) return "";
  if (m > 1.05) return POS_TEXT;
  if (m < 0.95) return NEG_TEXT;
  return "text-muted-foreground";
}
function pfTone(pf) {
  if (pf == null) return "";
  if (pf >= 1.3) return POS_TEXT;
  if (pf < 1.0) return NEG_TEXT;
  return "text-muted-foreground";
}

const CFG_FIELDS = [
  { key: "min_trades",    label: "Trade minimi",       step: 1,    hint: "prima di scalare il rischio" },
  { key: "target_dd_pct", label: "Target DD %",        step: 0.5,  hint: "budget di drawdown per strategia" },
  { key: "max_mult",      label: "Moltiplicatore max", step: 0.1,  hint: "cap massimo sul lotto" },
  { key: "min_mult",      label: "Moltiplicatore min", step: 0.05, hint: "minimo per strategie deboli" },
  { key: "min_pf",        label: "Profit factor min",  step: 0.05, hint: "PF minimo per scalare in su" },
];

export default function OptimizerPage() {
  const [board, setBoard] = useState([]);
  const [cfg, setCfg] = useState(null);
  const [balance, setBalance] = useState(0);
  const [manual, setManual] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState(null);
  const [demo, setDemo] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setErr(null);
    try {
      const { data } = await api.get("/strategies/leaderboard");
      setBoard(data.strategies || []);
      setCfg(data.config || null);
      setBalance(data.balance || 0);
      setDemo(!!data.demo);
    } catch (e) {
      setErr(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const saveCfg = async (patch) => {
    setSaving(true); setErr(null);
    try {
      const { data } = await api.post("/strategies/risk_config", patch);
      setCfg(data.config);
      await load();
    } catch (e) { setErr(formatApiError(e)); } finally { setSaving(false); }
  };

  const saveManual = async (name, value) => {
    setSaving(true); setErr(null);
    try {
      await api.post("/strategies/risk_manual", { overrides: { [name]: value } });
      setManual((m) => { const n = { ...m }; delete n[name]; return n; });
      await load();
    } catch (e) { setErr(formatApiError(e)); } finally { setSaving(false); }
  };

  const totals = useMemo(() => {
    const net = board.reduce((s, r) => s + (r.net || 0), 0);
    const trades = board.reduce((s, r) => s + (r.trades || 0), 0);
    const scaled = board.filter((r) => Math.abs((r.effective_mult ?? 1) - 1) > 1e-6).length;
    const profitable = board.filter((r) => (r.profit_factor ?? 0) >= 1).length;
    return { net, trades, scaled, profitable };
  }, [board]);

  if (loading && !cfg) {
    return <div className="text-sm text-muted-foreground" data-testid="optimizer-loading">Caricamento ottimizzatore…</div>;
  }

  return (
    <div className="space-y-6" data-testid="optimizer-page">
      <SectionHeader
        eyebrow="Loop di ottimizzazione live"
        title="Ottimizzatore strategie"
        icon={Gauge}
        right={
          <button onClick={load} disabled={loading}
            data-testid="optimizer-refresh"
            className="h-9 px-3 rounded-lg border border-border hover:bg-secondary flex items-center gap-2 text-sm">
            <RefreshCw className={cls("h-4 w-4", loading && "animate-spin")} /> Aggiorna
          </button>
        }
      />

      <p className="text-sm text-muted-foreground max-w-3xl">
        Calcola i risultati reali per ogni strategia dai trade che l'EA sincronizza e propone un
        moltiplicatore di rischio: le strategie con drawdown basso e redditizie partono con un lotto
        maggiore, quelle in perdita vengono ridotte. Con l'auto-scaling attivo i moltiplicatori
        vengono inviati all'EA in tempo reale (poll ogni 15s) — nessun riavvio.
      </p>

      {err && (
        <Card className="p-4 border-rose-500/40" testId="optimizer-error">
          <div className="flex items-center gap-2 text-sm text-rose-600 dark:text-rose-400">
            <AlertTriangle className="h-4 w-4" /> {err}
          </div>
        </Card>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard label="Net realizzato" value={fmtMoney(totals.net)} tone={totals.net >= 0 ? "pos" : "neg"} icon={TrendingUp} testId="opt-kpi-net" />
        <KpiCard label="Trade totali" value={totals.trades} testId="opt-kpi-trades" />
        <KpiCard label="Strategie redditizie" value={`${totals.profitable}/${board.length}`} testId="opt-kpi-prof" />
        <KpiCard label="Con rischio scalato" value={totals.scaled} sub={cfg?.enabled ? "auto-scaling ON" : "auto-scaling OFF"} tone={cfg?.enabled ? "pos" : undefined} testId="opt-kpi-scaled" />
      </div>

      {/* Configurazione auto-scaler */}
      <Card className="p-5" testId="optimizer-config">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <div>
            <div className="eyebrow">Auto-scaling rischio</div>
            <h3 className="font-semibold text-lg tracking-tight mt-0.5">Configurazione</h3>
          </div>
          <button
            onClick={() => saveCfg({ enabled: !cfg?.enabled })}
            disabled={saving}
            data-testid="optimizer-toggle-enabled"
            className={cls(
              "h-10 px-4 rounded-lg flex items-center gap-2 text-sm font-semibold border transition-colors",
              cfg?.enabled
                ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/40"
                : "bg-secondary text-muted-foreground border-border hover:bg-secondary/70"
            )}>
            <Power className="h-4 w-4" />
            {cfg?.enabled ? "Auto-scaling ATTIVO" : "Auto-scaling SPENTO"}
          </button>
        </div>

        {!cfg?.enabled && (
          <div className="text-xs text-amber-600 dark:text-amber-400 mb-4 flex items-center gap-1.5">
            <AlertTriangle className="h-3.5 w-3.5" />
            Spento: l'EA usa il lotto normale. Attivalo solo su conto demo finché non sei soddisfatto.
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {CFG_FIELDS.map((f) => (
            <label key={f.key} className="block" data-testid={`optimizer-cfg-${f.key}`}>
              <div className="text-xs font-medium text-foreground">{f.label}</div>
              <input
                type="number" step={f.step}
                defaultValue={cfg?.[f.key]}
                onBlur={(e) => {
                  const v = parseFloat(e.target.value);
                  if (!Number.isNaN(v) && v !== cfg?.[f.key]) saveCfg({ [f.key]: v });
                }}
                className="mt-1 w-full h-9 px-2 rounded-lg border border-border bg-background text-sm font-mono" />
              <div className="text-[10px] text-muted-foreground mt-1">{f.hint}</div>
            </label>
          ))}
        </div>
      </Card>

      {/* Leaderboard */}
      <Card className="p-0 overflow-hidden" testId="optimizer-leaderboard">
        {demo || board.length === 0 ? (
          <div className="p-6 text-sm text-muted-foreground" data-testid="optimizer-empty">
            Nessun trade per strategia ancora sincronizzato. Avvia l'EA su demo con tutte le strategie
            attive: man mano che chiude operazioni, qui comparirà la classifica e i moltiplicatori suggeriti.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wider text-muted-foreground border-b border-border">
                  <th className="px-4 py-3">Strategia</th>
                  <th className="px-3 py-3 text-right">Trade</th>
                  <th className="px-3 py-3 text-right">Win%</th>
                  <th className="px-3 py-3 text-right">PF</th>
                  <th className="px-3 py-3 text-right">Net</th>
                  <th className="px-3 py-3 text-right">Max DD%</th>
                  <th className="px-3 py-3 text-right">Suggerito</th>
                  <th className="px-3 py-3 text-right">Effettivo</th>
                  <th className="px-3 py-3 text-right">Override</th>
                </tr>
              </thead>
              <tbody>
                {board.map((r) => {
                  const ov = manual[r.name];
                  return (
                    <tr key={r.name} className="border-b border-border/60 hover:bg-secondary/40"
                        data-testid={`optimizer-row-${r.name}`}>
                      <td className="px-4 py-2.5 font-medium">
                        {r.name}
                        <div className="text-[10px] text-muted-foreground font-normal">{r.reason}</div>
                      </td>
                      <td className="px-3 py-2.5 text-right tabular">{r.trades}</td>
                      <td className="px-3 py-2.5 text-right tabular">{fmtPct(r.win_rate)}</td>
                      <td className={cls("px-3 py-2.5 text-right tabular font-semibold", pfTone(r.profit_factor))}>{r.profit_factor}</td>
                      <td className={cls("px-3 py-2.5 text-right tabular", r.net >= 0 ? POS_TEXT : NEG_TEXT)}>{fmtMoney(r.net)}</td>
                      <td className="px-3 py-2.5 text-right tabular">{fmtPct(r.max_dd_pct)}</td>
                      <td className="px-3 py-2.5 text-right tabular text-muted-foreground">×{r.suggested_mult}</td>
                      <td className={cls("px-3 py-2.5 text-right tabular font-bold", multTone(r.effective_mult))}>
                        ×{r.effective_mult}
                        <span className="ml-1 text-[9px] uppercase text-muted-foreground font-normal">{r.risk_source}</span>
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <input
                            type="number" step="0.1" min="0" placeholder="auto"
                            value={ov ?? ""}
                            onChange={(e) => setManual((m) => ({ ...m, [r.name]: e.target.value }))}
                            className="w-16 h-8 px-2 rounded border border-border bg-background text-xs font-mono text-right"
                            data-testid={`optimizer-override-input-${r.name}`} />
                          <button
                            onClick={() => saveManual(r.name, ov === "" || ov == null ? null : parseFloat(ov))}
                            disabled={saving}
                            title="Salva override (vuoto = auto)"
                            data-testid={`optimizer-override-save-${r.name}`}
                            className="h-8 w-8 rounded border border-border hover:bg-secondary flex items-center justify-center">
                            <Save className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
