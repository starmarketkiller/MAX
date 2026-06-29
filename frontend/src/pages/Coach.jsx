import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Sparkles, RefreshCcw, Trash2, LineChart } from "lucide-react";
import api from "@/lib/api";
import MessageList from "@/pages/coach/MessageList";
import InputBar from "@/pages/coach/InputBar";
import { DailyBrief, InsightChip } from "@/pages/coach/Banners";
import CoachMemoryPanel from "@/pages/coach/CoachMemoryPanel";

const SUGGESTIONS = [
  "Analizza i miei ultimi trade e dammi 3 azioni concrete",
  "Quale strategia performa peggio e perché?",
  "Sto rischiando troppo? Controlla il drawdown",
  "Dammi un piano per la prossima settimana",
];

function newSessionId() {
  return "coach-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8);
}

function appendMessage(messages, role, content) {
  return [...messages, { role, content, ts: new Date().toISOString() }];
}

export default function CoachPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [insights, setInsights] = useState([]);
  const [dailyBrief, setDailyBrief] = useState(null);
  const scrollRef = useRef(null);
  // Session id lives in React state only (in-memory). Refreshing the page
  // intentionally starts a new conversation; the previous session is still
  // queryable from the backend via /coach/history.
  const [sessionId] = useState(newSessionId);
  // Pre-loaded chart context (from Live Chart widget link)
  const [searchParams, setSearchParams] = useSearchParams();
  const chartSymbol = searchParams.get("symbol");
  const chartTf     = searchParams.get("tf");
  const chartContext = chartSymbol && chartTf
    ? { symbol: chartSymbol, tf: chartTf } : null;

  const loadHistory = useCallback(async () => {
    try {
      const { data } = await api.get("/coach/history", { params: { session_id: sessionId } });
      setMessages(data.messages || []);
    } catch (e) { console.warn("coach loadHistory failed", e); }
  }, [sessionId]);

  const loadInsights = useCallback(async () => {
    try {
      const { data } = await api.get("/coach/quick_insights");
      setInsights(data.insights || []);
    } catch (e) { console.warn("coach loadInsights failed", e); }
  }, []);

  const loadDailyBrief = useCallback(async () => {
    try {
      const { data } = await api.get("/coach/daily_brief");
      if (data?.brief && !data.brief.read) setDailyBrief(data.brief);
    } catch (e) { console.warn("coach loadDailyBrief failed", e); }
  }, []);

  useEffect(() => {
    loadHistory(); loadInsights(); loadDailyBrief();
  }, [loadHistory, loadInsights, loadDailyBrief]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages.length, busy]);

  const dismissBrief = async () => {
    if (!dailyBrief) return;
    try { await api.post(`/coach/notifications/${dailyBrief.id}/read`); }
    catch (e) { console.warn("coach dismissBrief failed", e); }
    setDailyBrief(null);
  };

  const send = async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || busy) return;
    setInput("");
    setMessages((m) => appendMessage(m, "user", msg));
    setBusy(true);
    try {
      // Include chart context (symbol/timeframe) so Claude can ground its answer.
      const payload = { session_id: sessionId, message: msg };
      if (chartContext) {
        payload.chart_context = chartContext;
      }
      const { data } = await api.post("/coach/chat", payload);
      setMessages((m) => appendMessage(m, "assistant", data.reply));
    } catch {
      setMessages((m) => appendMessage(m, "assistant",
        "⚠️ Impossibile contattare il coach. Verifica EMERGENT_LLM_KEY in backend/.env."));
    } finally {
      setBusy(false);
    }
  };

  // Auto-prime: when arriving from the Live Chart, drop a starter message into
  // the input so the user only has to press send (or edit it).
  useEffect(() => {
    if (chartContext && messages.length === 0 && !input) {
      setInput(`Sto guardando ${chartContext.symbol} ${chartContext.tf}. ` +
               `Cosa pensi del setup attuale (HTF bias, regime, zone vicine, blocker)?`);
    }
  }, [chartContext, messages.length, input]);

  const reset = async () => {
    if (!confirm("Azzerare la conversazione con il Coach?")) return;
    await api.delete(`/coach/session/${sessionId}`);
    setMessages([]);
  };

  return (
    <div className="space-y-6" data-testid="coach-page">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-sky-500" /> AI Trade Coach
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Analizza i tuoi trade con AI. Powered by Claude Sonnet 4.5 via Emergent.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={loadInsights} title="Refresh insights"
                  className="p-2 rounded-md border border-border hover:bg-secondary"
                  data-testid="coach-refresh-insights">
            <RefreshCcw className="h-4 w-4" />
          </button>
          <button onClick={reset}
                  className="flex items-center gap-1 px-3 py-2 rounded-md border border-border text-sm hover:bg-secondary text-rose-600"
                  data-testid="coach-clear-btn">
            <Trash2 className="h-3.5 w-3.5" /> Reset
          </button>
        </div>
      </div>

      {dailyBrief && <DailyBrief brief={dailyBrief} onClose={dismissBrief} />}

      {chartContext && (
        <div
          data-testid="coach-chart-context-banner"
          className="rounded-lg border border-cyan-500/30 bg-cyan-500/5 px-4 py-2.5 flex items-center gap-3"
        >
          <LineChart className="h-4 w-4 text-cyan-400 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="text-xs text-muted-foreground">
              Contesto live dal grafico
            </div>
            <div className="text-sm font-mono font-bold tracking-tight">
              {chartContext.symbol} <span className="text-muted-foreground">·</span> {chartContext.tf}
            </div>
          </div>
          <button
            onClick={() => setSearchParams({})}
            data-testid="coach-chart-context-clear"
            className="text-[10px] uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors px-2 py-1 rounded border border-border"
          >
            Rimuovi
          </button>
        </div>
      )}

      <CoachMemoryPanel />

      {insights.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3" data-testid="coach-insights">
          {insights.slice(0, 6).map((ins) => (
            <InsightChip key={`${ins.type}-${ins.title}`} ins={ins} />
          ))}
        </div>
      )}

      <div className="rounded-xl border border-border bg-card overflow-hidden flex flex-col"
           style={{ height: "min(680px, 70vh)" }}>
        <MessageList
          scrollRef={scrollRef}
          messages={messages}
          busy={busy}
          suggestions={SUGGESTIONS}
          onPickSuggestion={send}
        />
        <InputBar
          value={input}
          onChange={setInput}
          onSubmit={send}
          disabled={busy}
        />
      </div>
    </div>
  );
}
