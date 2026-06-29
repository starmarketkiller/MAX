import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";
import { Link2, Save, RotateCcw, RefreshCcw, Zap, Repeat, Plus, X } from "lucide-react";

function cls(...c) { return c.filter(Boolean).join(" "); }

const STRATEGIES = [
  "ADX_RSI","BOLLINGER","MACD","SAR","TSI","BJORGUM","LIQ_SWEEP","FVG_CONT",
  "BREAKOUT_ACC","LONDON_BO","EMA_PULLBACK","BB_SQUEEZE","ICHIMOKU","RSI_DIV",
  "ORDER_BLOCK","STRUCT_REACT","TURTLE_SOUP","IFVG","FVG_MIT","OB_MIT",
  "SH_BMS_RTO","SMS_BMS_RTO","SILVER_BULLET","AMD_REVERSAL","OTE_CONT",
  "MALAYSIAN_SNR","CISD","AMD_CONT","JUDAS_SWING","LDN_REVERSAL","NY_REVERSAL",
  "WEEKLY_EXP","PO3","LIQ_VOID","DISP_REBAL","RANGE_FADE",
];

function ChainBridgeEditor({ from, targets, allStrategies, onChange, onRemove }) {
  const [selecting, setSelecting] = useState(false);
  const candidates = allStrategies.filter((s) => s !== from && !targets.includes(s));

  return (
    <div className="rounded-lg border border-border bg-secondary/30 p-3" data-testid={`chain-bridge-${from}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-mono font-bold text-sky-400 text-sm">{from}</span>
          <span className="text-muted-foreground text-xs">→ continua con</span>
        </div>
        <button onClick={onRemove}
                className="p-1 rounded hover:bg-rose-500/20 text-rose-400"
                data-testid={`remove-bridge-${from}`}>
          <X className="h-3.5 w-3.5"/>
        </button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {targets.map((t) => (
          <span key={t} className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-sky-500/15 text-sky-300 text-[11px] font-mono">
            {t}
            <button onClick={() => onChange(targets.filter((x) => x !== t))}
                    className="hover:text-rose-400">×</button>
          </span>
        ))}
        {!selecting && candidates.length > 0 && (
          <button onClick={() => setSelecting(true)}
                  className="px-2 py-0.5 rounded border border-dashed border-border text-[11px] hover:bg-secondary"
                  data-testid={`add-target-${from}`}>
            + add
          </button>
        )}
        {selecting && (
          <select autoFocus
                  onBlur={() => setSelecting(false)}
                  onChange={(e) => { onChange([...targets, e.target.value]); setSelecting(false); }}
                  className="bg-card border border-border rounded text-[11px] px-1 py-0.5">
            <option value="">— scegli —</option>
            {candidates.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        )}
      </div>
    </div>
  );
}

export default function StrategyChainPage() {
  const [cfg, setCfg] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(null);
  const [newBridge, setNewBridge] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get("/strategy_chain/config");
      setCfg(r.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setSaving(true);
    try {
      const r = await api.put("/strategy_chain/config", cfg);
      setCfg(r.data);
      setSavedAt(new Date());
    } catch (e) {
      alert(`Errore: ${e?.response?.data?.detail || e.message}`);
    } finally { setSaving(false); }
  };

  if (loading || !cfg) {
    return <div className="text-muted-foreground">Caricamento...</div>;
  }

  const bridgeKeys = Object.keys(cfg.bridges || {});

  return (
    <div className="space-y-6" data-testid="strategy-chain-page">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Link2 className="h-6 w-6 text-purple-500" /> Strategy Chain & Continuation
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
            Quando una strategia chiude in profitto, l'EA può aprire automaticamente un trade di
            <b> continuazione</b> nella stessa direzione se il setup è compatibile. Lo
            <b> Smart Close & Reverse</b> abbassa la soglia di chiusura quando reaction + HTF sono concordi.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} disabled={loading}
                  className="flex items-center gap-2 px-3 py-2 rounded-md border border-border text-sm hover:bg-secondary"
                  data-testid="chain-refresh-btn">
            <RefreshCcw className="h-3.5 w-3.5" /> Ricarica
          </button>
          <button onClick={save} disabled={saving}
                  className="flex items-center gap-2 px-3 py-2 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white text-sm"
                  data-testid="chain-save-btn">
            <Save className="h-4 w-4" /> {saving ? "Salvataggio..." : "Salva"}
          </button>
        </div>
      </div>

      {savedAt && (
        <div className="rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs p-2">
          Configurazione salvata alle {savedAt.toLocaleTimeString()} — l'EA leggerà i nuovi parametri al prossimo poll.
        </div>
      )}

      {/* Toggle blocks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ToggleCard
          icon={Repeat}
          title="Smart Continuation"
          desc="Dopo profit, riapri sulla stessa direzione se pullback ATR ≥ soglia e strategia compatibile"
          enabled={cfg.enable_continuation}
          onChange={(v) => setCfg({ ...cfg, enable_continuation: v })}
          testId="toggle-continuation"
        >
          <Slider
            label="Finestra continuazione (min)"
            value={Math.round((cfg.continuation_window_sec || 1800) / 60)}
            min={5} max={120} step={5}
            onChange={(v) => setCfg({ ...cfg, continuation_window_sec: v * 60 })}
            testId="slider-window"
          />
          <Slider
            label="Lot mult continuazione"
            value={cfg.continuation_lot_mult || 0.6}
            min={0.2} max={1.0} step={0.05}
            onChange={(v) => setCfg({ ...cfg, continuation_lot_mult: v })}
            fmt={(v) => v.toFixed(2)}
            testId="slider-lot"
          />
          <Slider
            label="Max continuazioni / trade"
            value={cfg.max_continuations || 3}
            min={1} max={10} step={1}
            onChange={(v) => setCfg({ ...cfg, max_continuations: v })}
            testId="slider-max"
          />
          <Slider
            label="Pullback minimo (× ATR)"
            value={cfg.min_pullback_atr || 0.3}
            min={0.1} max={1.0} step={0.05}
            onChange={(v) => setCfg({ ...cfg, min_pullback_atr: v })}
            fmt={(v) => v.toFixed(2)}
            testId="slider-pullback"
          />
        </ToggleCard>

        <ToggleCard
          icon={Zap}
          title="Smart Close & Reverse"
          desc="Abbassa soglia di chiusura se reaction ≥ 75 AND HTF concorde (re-entry intelligente)"
          enabled={cfg.enable_smart_reverse}
          onChange={(v) => setCfg({ ...cfg, enable_smart_reverse: v })}
          testId="toggle-smart-reverse"
        >
          <Slider
            label="Min score reverse (downside cap)"
            value={cfg.smart_reverse_min_score || 60}
            min={40} max={90} step={5}
            onChange={(v) => setCfg({ ...cfg, smart_reverse_min_score: v })}
            testId="slider-reverse-score"
          />
          <p className="text-[11px] text-muted-foreground">
            Esempio: se la soglia base è 70, ma reaction=80 e HTF concorde, lo Smart Reverse
            la abbassa a 55 → close + entrata opposta più aggressiva.
          </p>
        </ToggleCard>
      </div>

      {/* Bridges editor */}
      <div className="rounded-xl border border-border bg-card p-5">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="font-semibold text-sm">Strategy Bridges</h3>
            <p className="text-xs text-muted-foreground">
              Definisci quali strategie possono "passare il testimone" dopo una chiusura in profitto
            </p>
          </div>
          <div className="flex items-center gap-2">
            <select value={newBridge} onChange={(e) => setNewBridge(e.target.value)}
                    className="bg-card border border-border rounded px-2 py-1 text-xs"
                    data-testid="new-bridge-select">
              <option value="">+ aggiungi strategia base</option>
              {STRATEGIES.filter((s) => !bridgeKeys.includes(s)).map((s) =>
                <option key={s} value={s}>{s}</option>
              )}
            </select>
            <button
              disabled={!newBridge}
              onClick={() => {
                setCfg({ ...cfg, bridges: { ...cfg.bridges, [newBridge]: [] } });
                setNewBridge("");
              }}
              className="px-2 py-1 rounded bg-sky-600 disabled:opacity-50 text-white text-xs"
              data-testid="add-bridge-btn"
            >
              <Plus className="h-3 w-3 inline" /> Add
            </button>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {bridgeKeys.map((k) => (
            <ChainBridgeEditor
              key={k} from={k}
              targets={cfg.bridges[k] || []}
              allStrategies={STRATEGIES}
              onChange={(newTargets) => setCfg({
                ...cfg,
                bridges: { ...cfg.bridges, [k]: newTargets },
              })}
              onRemove={() => {
                const b = { ...cfg.bridges };
                delete b[k];
                setCfg({ ...cfg, bridges: b });
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function ToggleCard({ icon: Icon, title, desc, enabled, onChange, children, testId }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-3" data-testid={testId}>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <Icon className="h-5 w-5 text-purple-400 mt-0.5" />
          <div>
            <div className="text-sm font-semibold">{title}</div>
            <div className="text-[11px] text-muted-foreground">{desc}</div>
          </div>
        </div>
        <button onClick={() => onChange(!enabled)}
                className={cls("relative inline-flex h-5 w-9 rounded-full transition",
                  enabled ? "bg-emerald-600" : "bg-secondary")}
                data-testid={`${testId}-switch`}>
          <span className={cls(
            "absolute top-0.5 h-4 w-4 rounded-full bg-white transition",
            enabled ? "left-[18px]" : "left-0.5"
          )} />
        </button>
      </div>
      {enabled && <div className="space-y-3 pt-2 border-t border-border">{children}</div>}
    </div>
  );
}

function Slider({ label, value, min, max, step, onChange, fmt, testId }) {
  return (
    <div data-testid={testId}>
      <div className="flex justify-between text-[11px] mb-1">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono font-bold">{fmt ? fmt(value) : value}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
             onChange={(e) => onChange(Number(e.target.value))}
             className="w-full accent-purple-500" />
    </div>
  );
}
