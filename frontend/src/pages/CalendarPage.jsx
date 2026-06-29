import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";
import { Calendar, RefreshCcw, AlertCircle, TrendingUp } from "lucide-react";

function classNames(...c) { return c.filter(Boolean).join(" "); }

const IMPACT_CLS = {
  high:   "bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/30",
  medium: "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30",
  low:    "bg-sky-500/15 text-sky-700 dark:text-sky-300 border-sky-500/30",
};

const COUNTRY_FLAG = {
  US: "🇺🇸", EU: "🇪🇺", UK: "🇬🇧", JP: "🇯🇵", CN: "🇨🇳", DE: "🇩🇪", FR: "🇫🇷", IT: "🇮🇹",
};

function fmtDate(iso, locale = "it-IT") {
  const d = new Date(iso);
  return {
    date: d.toLocaleDateString(locale, { weekday: "short", day: "numeric", month: "short" }),
    time: d.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" }),
    full: d,
  };
}

function relativeTime(d) {
  const diff = d.getTime() - Date.now();
  const abs = Math.abs(diff);
  const min = Math.round(diff / 60000);
  const hrs = Math.round(min / 60);
  const days = Math.round(hrs / 24);
  if (abs < 3600000) return min >= 0 ? `tra ${min} min` : `${-min} min fa`;
  if (abs < 86400000) return hrs >= 0 ? `tra ${hrs}h` : `${-hrs}h fa`;
  return days >= 0 ? `tra ${days}g` : `${-days}g fa`;
}

export default function CalendarPage() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [days, setDays] = useState(14);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/calendar/upcoming",
        { params: { days, include_earnings: true } });
      setEvents(data.events || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [days]);
  useEffect(() => { load(); }, [load]);

  // Group by date
  const grouped = {};
  for (const e of events) {
    const key = e.ts.slice(0, 10);
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(e);
  }

  return (
    <div className="space-y-6" data-testid="calendar-page">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Calendar className="h-6 w-6 text-sky-500"/> Calendario Economico
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Eventi macro ad alto impatto su Forex, Gold e indici. Schedule ricorrenti + earnings real-time.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}
                  className="px-3 py-2 rounded-md bg-background border border-border text-sm"
                  data-testid="calendar-days-select">
            <option value="7">Prossimi 7 giorni</option>
            <option value="14">Prossimi 14 giorni</option>
            <option value="30">Prossimi 30 giorni</option>
            <option value="60">Prossimi 60 giorni</option>
          </select>
          <button onClick={load} disabled={loading}
                  className="flex items-center gap-2 px-3 py-2 rounded-md border border-border text-sm hover:bg-secondary"
                  data-testid="calendar-refresh">
            <RefreshCcw className={classNames("h-3.5 w-3.5", loading && "animate-spin")}/>
            Aggiorna
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 flex items-start gap-3">
        <AlertCircle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0"/>
        <div className="text-sm text-amber-700 dark:text-amber-300">
          <div className="font-semibold mb-1">Filtro News attivo nell&apos;EA</div>
          L&apos;EA blocca automaticamente nuove entrate ±15 min da eventi <strong>high impact</strong>.
          Spread tipicamente esplodono durante NFP, CPI, FOMC.
        </div>
      </div>

      {Object.keys(grouped).length === 0 && !loading && (
        <div className="text-center py-12 text-muted-foreground border border-dashed border-border rounded-xl">
          Nessun evento programmato nei prossimi {days} giorni.
        </div>
      )}

      <div className="space-y-4">
        {Object.entries(grouped).map(([date, items]) => (
          <div key={date} className="rounded-xl border border-border bg-card overflow-hidden"
               data-testid={`calendar-day-${date}`}>
            <div className="px-4 py-2 bg-secondary/50 text-sm font-semibold flex items-center justify-between">
              <span>{fmtDate(date).date.replace(/^./, c => c.toUpperCase())}</span>
              <span className="text-xs text-muted-foreground font-normal">
                {items.length} {items.length === 1 ? "evento" : "eventi"}
              </span>
            </div>
            <div className="divide-y divide-border">
              {items.map((e) => {
                const t = fmtDate(e.ts);
                const high = e.impact === "high";
                return (
                  <div key={`${e.ts}-${e.title}`} className="px-4 py-3 grid grid-cols-12 gap-3 items-center hover:bg-secondary/20"
                       data-testid={`calendar-event-${e.title.slice(0,12)}`}>
                    <div className="col-span-2 sm:col-span-1 font-mono text-sm">
                      {t.time}
                    </div>
                    <div className="col-span-1 text-xl text-center">
                      {COUNTRY_FLAG[e.country] || "🌐"}
                    </div>
                    <div className="col-span-2 sm:col-span-1">
                      <span className={classNames("px-2 py-0.5 rounded text-[10px] font-bold border uppercase",
                        IMPACT_CLS[e.impact] || IMPACT_CLS.low)}>
                        {e.impact}
                      </span>
                    </div>
                    <div className="col-span-7 sm:col-span-7">
                      <div className={classNames("font-medium text-sm", high && "text-rose-700 dark:text-rose-300")}>
                        {e.title}
                      </div>
                      {e.note && (
                        <div className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{e.note}</div>
                      )}
                    </div>
                    <div className="col-span-12 sm:col-span-2 text-right">
                      <div className="text-xs text-muted-foreground">{relativeTime(t.full)}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
