import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Lock, Sparkles, TrendingUp, Trophy } from "lucide-react";
import api from "@/lib/api";

/**
 * Slim banner shown on Dashboard / Home when a Locked Profile is active.
 * Shows symbol, label, train+test PF and a link to the Backtest Lab.
 */
export default function LockedProfileBanner({ compact = false }) {
  const [profiles, setProfiles] = useState([]);

  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const { data } = await api.get("/backtest/locked_profile/all");
        if (live) setProfiles(data?.profiles || []);
      } catch { /* silent */ }
    })();
    return () => { live = false; };
  }, []);

  if (!profiles.length) return null;

  return (
    <div className="space-y-2" data-testid="locked-profile-banner">
      {profiles.slice(0, 4).map((p) => {
        const train = p.metrics || {};
        const test  = p.test_metrics || {};
        return (
          <div key={`${p.symbol}-${p.timeframe}`}
            className="rounded-xl border border-violet-500/30 bg-gradient-to-r from-violet-500/10 to-cyan-500/5 p-3 flex items-center gap-3"
            data-testid={`locked-banner-${p.symbol}`}>
            <div className="h-10 w-10 rounded-lg bg-violet-500/20 flex items-center justify-center flex-shrink-0">
              <Lock className="h-5 w-5 text-violet-400"/>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[10px] uppercase tracking-wider text-violet-400 font-bold">
                  Locked Profile attivo
                </span>
                <span className="text-xs font-mono bg-background/60 px-1.5 py-0.5 rounded">
                  {p.symbol} · {p.timeframe}
                </span>
              </div>
              <div className="text-xs text-muted-foreground truncate mt-0.5">{p.label}</div>
              {!compact && (
                <div className="flex flex-wrap gap-3 mt-1.5 text-[11px] font-mono">
                  <span><span className="text-muted-foreground">PF train</span> <b>{train.profit_factor}</b></span>
                  <span><span className="text-muted-foreground">PF test</span> <b className="text-cyan-400">{test.profit_factor ?? "—"}</b></span>
                  <span><span className="text-muted-foreground">Sharpe</span> <b>{train.sharpe}</b></span>
                  <span><span className="text-muted-foreground">DD test</span> <b className="text-rose-400">{test.max_dd_pct ?? "—"}%</b></span>
                  <span><span className="text-muted-foreground">Ret test</span> <b className="text-emerald-400">{test.total_return_pct ?? "—"}%</b></span>
                </div>
              )}
            </div>
            <Link to="/backtest"
              data-testid={`locked-banner-link-${p.symbol}`}
              className="hidden sm:flex items-center gap-1 px-2.5 py-1.5 rounded-md border border-border bg-background hover:bg-secondary/40 text-[11px] uppercase tracking-wider font-medium text-foreground transition-all">
              <Sparkles className="h-3 w-3 text-violet-400"/>
              Modifica
            </Link>
          </div>
        );
      })}
    </div>
  );
}
