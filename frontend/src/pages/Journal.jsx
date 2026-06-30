import { useCallback, useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { Tag, Star, Save, RefreshCcw, Search, Activity } from "lucide-react";
import { useStrategyHub } from "@/lib/strategyHub";
import { useTradeHub } from "@/lib/tradeHub";

function classNames(...c) { return c.filter(Boolean).join(" "); }
const TAG_PRESETS = ["A+ setup", "FOMO", "news", "scalp", "swing", "rivincita",
                     "alta volatilità", "spread alto", "ottimo entry", "uscita anticipata"];

function StarRating({ value, onChange, testid }) {
  return (
    <div className="flex items-center gap-0.5" data-testid={testid}>
      {[1, 2, 3, 4, 5].map((i) => (
        <button key={i} type="button" onClick={() => onChange(i === value ? 0 : i)}
                className="p-0.5">
          <Star className={classNames("h-4 w-4 transition-colors",
            i <= (value || 0) ? "fill-amber-400 text-amber-400" : "text-muted-foreground/40")}/>
        </button>
      ))}
    </div>
  );
}

function TradeRow({ trade, onSaved }) {
  const { open: openStrategy } = useStrategyHub();
  const { openTrade } = useTradeHub();
  const [editing, setEditing] = useState(false);
  const [tags, setTags] = useState(trade.journal_tags || []);
  const [note, setNote] = useState(trade.journal_note || "");
  const [rating, setRating] = useState(trade.journal_rating || 0);
  const [busy, setBusy] = useState(false);
  const [tagInput, setTagInput] = useState("");

  const availablePresets = useMemo(
    () => TAG_PRESETS.filter(t => !tags.includes(t)),
    [tags]
  );

  const save = async () => {
    setBusy(true);
    try {
      await api.post(`/trades/${trade.ticket}/tag`, {
        tags, note, rating: rating || null,
      });
      setEditing(false);
      onSaved && onSaved();
    } catch (e) { console.error(e); }
    finally { setBusy(false); }
  };
  const addTag = (t) => {
    const tt = t.trim();
    if (!tt) return;
    if (tags.includes(tt)) return;
    setTags([...tags, tt]);
    setTagInput("");
  };
  const removeTag = (t) => setTags(tags.filter(x => x !== t));

  const pnlPos = (trade.pnl || 0) >= 0;
  const dt = trade.closeTime ? new Date(trade.closeTime).toLocaleString() : "—";

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden"
         data-testid={`journal-trade-${trade.ticket}`}>
      <div role="button" tabIndex={0} onClick={() => setEditing(!editing)}
              onKeyDown={(e) => { if (e.key === "Enter") setEditing(!editing); }}
              className="w-full px-4 py-3 grid grid-cols-12 gap-3 items-center text-left hover:bg-secondary/30 transition-colors cursor-pointer">
        <div className="col-span-2 sm:col-span-1">
          <div className="font-mono text-xs text-muted-foreground">#{trade.ticket}</div>
        </div>
        <div className="col-span-3 sm:col-span-2">
          <div className="font-semibold text-sm">{trade.symbol}</div>
          <div className={classNames("text-xs", trade.side === "BUY" ? "text-emerald-600" : "text-rose-600")}>
            {trade.side} {trade.lots} lot
          </div>
        </div>
        <div className="col-span-3 sm:col-span-2">
          {trade.strategy ? (
            <button onClick={(e) => { e.stopPropagation(); openStrategy(trade.strategy); }}
              data-testid={`journal-open-strat-${trade.ticket}`}
              className="text-xs text-muted-foreground hover:text-primary hover:underline transition-colors">
              {trade.strategy}
            </button>
          ) : <div className="text-xs text-muted-foreground">—</div>}
          <div className="text-xs">{dt}</div>
        </div>
        <div className="col-span-2">
          <div className={classNames("font-bold", pnlPos ? "text-emerald-600" : "text-rose-600")}>
            {pnlPos ? "+" : ""}{(trade.pnl || 0).toFixed(2)}€
          </div>
        </div>
        <div className="col-span-2 hidden sm:flex items-center gap-1 flex-wrap">
          {(tags || []).slice(0, 3).map((t) => (
            <span key={t} className="px-1.5 py-0.5 rounded-full bg-secondary text-[10px]">{t}</span>
          ))}
          {tags.length > 3 && <span className="text-[10px] text-muted-foreground">+{tags.length-3}</span>}
        </div>
        <div className="col-span-2 hidden sm:flex justify-end items-center gap-2">
          <div className="pointer-events-none">
            <StarRating value={rating} onChange={() => {}} testid={`journal-stars-${trade.ticket}`}/>
          </div>
          <button onClick={(e) => { e.stopPropagation(); openTrade(trade); }}
            title="Ciclo di vita del trade"
            data-testid={`journal-lifecycle-${trade.ticket}`}
            className="h-7 w-7 rounded-lg border border-border hover:bg-secondary flex items-center justify-center">
            <Activity className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {editing && (
        <div className="border-t border-border bg-secondary/20 p-4 space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Tag className="h-3.5 w-3.5"/> Tag
            </div>
            <StarRating value={rating} onChange={setRating} testid={`journal-rate-${trade.ticket}`}/>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {tags.map((t) => (
              <button key={t} type="button" onClick={() => removeTag(t)}
                      className="px-2 py-0.5 rounded-full bg-sky-500/15 text-sky-700 dark:text-sky-300 text-xs hover:bg-sky-500/25"
                      data-testid={`journal-tag-rm-${t}`}>
                {t} ×
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <input value={tagInput} onChange={(e) => setTagInput(e.target.value)}
                   onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag(tagInput); } }}
                   placeholder="Aggiungi tag e Invio..."
                   className="flex-1 px-3 py-1.5 text-sm rounded-md bg-background border border-border"
                   data-testid={`journal-tag-input-${trade.ticket}`}/>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {availablePresets.map((t) => (
              <button key={t} type="button" onClick={() => addTag(t)}
                      className="px-2 py-0.5 rounded-full bg-secondary text-xs hover:bg-secondary/80">
                + {t}
              </button>
            ))}
          </div>
          <textarea value={note} onChange={(e) => setNote(e.target.value)}
                    rows={3} placeholder="Note: cosa hai imparato? cosa avresti fatto diversamente?"
                    className="w-full px-3 py-2 text-sm rounded-md bg-background border border-border resize-y"
                    data-testid={`journal-note-${trade.ticket}`}/>
          <div className="flex justify-end gap-2">
            <button onClick={() => { setEditing(false); setTags(trade.journal_tags || []); setNote(trade.journal_note || ""); setRating(trade.journal_rating || 0); }}
                    className="px-3 py-1.5 rounded-md border border-border text-sm hover:bg-secondary">
              Annulla
            </button>
            <button onClick={save} disabled={busy}
                    className="flex items-center gap-1 px-4 py-1.5 rounded-md bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-sm"
                    data-testid={`journal-save-${trade.ticket}`}>
              <Save className="h-3.5 w-3.5"/> {busy ? "Salvataggio..." : "Salva"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function JournalPage() {
  const [trades, setTrades] = useState([]);
  const [tagStats, setTagStats] = useState([]);
  const [filter, setFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [t, ts] = await Promise.all([
        api.get("/analytics/trades", { params: { limit: 200 } }),
        api.get("/journal/tags"),
      ]);
      setTrades(t.data || []);
      setTagStats(ts.data.tags || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    return trades.filter(t => {
      if (tagFilter && !(t.journal_tags || []).includes(tagFilter)) return false;
      if (filter) {
        const q = filter.toLowerCase();
        const hay = `${t.ticket} ${t.symbol} ${t.strategy} ${t.side} ${(t.journal_tags||[]).join(" ")} ${t.journal_note||""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [trades, filter, tagFilter]);

  return (
    <div className="space-y-6" data-testid="journal-page">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Trading Journal</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Aggiungi tag, voti e note ai tuoi trade per costruire un playbook personale.
          </p>
        </div>
        <button onClick={load} disabled={loading}
                className="flex items-center gap-2 px-3 py-2 rounded-md border border-border text-sm hover:bg-secondary">
          <RefreshCcw className={classNames("h-3.5 w-3.5", loading && "animate-spin")}/>
          Aggiorna
        </button>
      </div>

      {tagStats.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="text-xs font-semibold uppercase text-muted-foreground mb-3">Tag performance</div>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => setTagFilter("")}
                    className={classNames("px-2.5 py-1 rounded-md text-xs",
                      !tagFilter ? "bg-sky-600 text-white" : "bg-secondary hover:bg-secondary/80")}>
              tutti
            </button>
            {tagStats.map((ts) => (
              <button key={ts.tag} onClick={() => setTagFilter(ts.tag === tagFilter ? "" : ts.tag)}
                      className={classNames("flex items-center gap-2 px-2.5 py-1 rounded-md text-xs",
                        tagFilter === ts.tag ? "bg-sky-600 text-white" : "bg-secondary hover:bg-secondary/80")}
                      data-testid={`tagstat-${ts.tag}`}>
                <span>{ts.tag}</span>
                <span className="text-[10px] opacity-70">×{ts.count}</span>
                <span className={classNames("text-[10px] font-bold",
                  ts.pnl >= 0 ? "text-emerald-500" : "text-rose-500")}>
                  {ts.pnl >= 0 ? "+" : ""}{ts.pnl.toFixed(0)}€
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground"/>
        <input value={filter} onChange={(e) => setFilter(e.target.value)}
               placeholder="Cerca per simbolo, strategia, tag, note..."
               className="w-full pl-9 pr-4 py-2 rounded-md bg-card border border-border text-sm"
               data-testid="journal-search"/>
      </div>

      <div className="space-y-2">
        {filtered.length === 0 ? (
          <div className="text-center py-12 px-6 text-muted-foreground border border-dashed border-border rounded-xl">
            {loading ? (
              "Caricamento..."
            ) : trades.length === 0 ? (
              <div className="space-y-3 text-left max-w-2xl mx-auto" data-testid="journal-empty-help">
                <div className="text-base font-semibold text-foreground">Nessun trade nel database</div>
                <div className="text-sm">
                  Il backend non ha ricevuto trade chiusi dall'EA. Le cause più comuni:
                </div>
                <ul className="text-sm space-y-1.5 list-disc pl-5">
                  <li>L'URL del backend non è whitelistato in MT5 → <b>Strumenti → Opzioni → Expert Advisors → Consenti WebRequest</b> e aggiungi <code className="text-xs bg-secondary px-1 rounded">{import.meta.env?.VITE_BACKEND_HOST || window.location.origin}</code></li>
                  <li>Stai usando una versione vecchia dell'EA (richiesto v2.0.13+). <a href="/setup" className="text-sky-500 underline">Scarica l'ultima versione</a></li>
                  <li>L'EA è offline o staccato dal grafico</li>
                  <li>Trade chiusi prima dell'avvio EA: usa il pulsante <b>"Resync Last 7d"</b> nel Setup Wizard, oppure restart EA (chiama auto-sync su OnInit)</li>
                </ul>
              </div>
            ) : (
              "Nessun trade trovato con questi filtri."
            )}
          </div>
        ) : filtered.map((t) => (
          <TradeRow key={t.ticket} trade={t} onSaved={load}/>
        ))}
      </div>
    </div>
  );
}
