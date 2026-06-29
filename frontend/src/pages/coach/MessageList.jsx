import { useState } from "react";
import { Sparkles, Zap, Check, X, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import MarkdownLite from "@/pages/coach/MarkdownLite";
import { parseCoachActions, describeAction, actionTone } from "@/pages/coach/parseActions";

function cls(...c) { return c.filter(Boolean).join(" "); }

function TypingDots() {
  return (
    <div className="flex justify-start">
      <div className="bg-secondary rounded-2xl px-4 py-3 text-sm flex items-center gap-2">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "150ms" }} />
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "300ms" }} />
        <span className="text-muted-foreground ml-2 font-mono text-xs">Coach sta ragionando…</span>
      </div>
    </div>
  );
}

function EmptyState({ suggestions, onPick }) {
  return (
    <div className="text-center py-12 space-y-4 fade-in">
      <div className="inline-flex h-14 w-14 rounded-2xl bg-primary/10 ring-1 ring-primary/30 items-center justify-center shadow-[0_0_24px_-4px_hsl(var(--primary)/0.5)]">
        <Sparkles className="h-7 w-7 text-primary" />
      </div>
      <div className="text-muted-foreground">Inizia una conversazione col tuo Coach AI</div>
      <div className="flex flex-wrap justify-center gap-2 max-w-2xl mx-auto">
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="px-3 py-1.5 rounded-full bg-secondary hover:bg-secondary/80 border border-border hover:border-primary/40 text-xs transition-all"
            data-testid={`coach-suggestion-${s.slice(0, 12).replace(/\s/g, "_")}`}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function ActionCard({ action, onApplied }) {
  const [status, setStatus] = useState("idle"); // idle | applying | done | error
  const tone = actionTone(action);
  const apply = async () => {
    setStatus("applying");
    try {
      const { data } = await api.post("/coach/apply_action", {
        type: action.type,
        name: action.name,
        ...action.params,
      });
      setStatus("done");
      toast.success(`✓ ${data.applied || "Azione applicata"}`);
      onApplied?.(action);
    } catch (e) {
      setStatus("error");
      toast.error(`Errore: ${e?.response?.data?.detail || e.message}`);
    }
  };

  if (status === "done") {
    return (
      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 font-mono">
        <Check className="h-3 w-3" /> Applicato — {describeAction(action)}
      </div>
    );
  }
  return (
    <div className={cls(
      "flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[11px] border font-mono",
      tone === "warning"
        ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
        : "border-primary/30 bg-primary/10 text-primary"
    )}>
      {tone === "warning" ? <AlertTriangle className="h-3 w-3" /> : <Zap className="h-3 w-3" />}
      <span className="truncate">{describeAction(action)}</span>
      <button
        onClick={apply}
        disabled={status === "applying"}
        data-testid={`coach-apply-${action.type}`}
        className={cls(
          "ml-auto px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase transition-all active:scale-95",
          tone === "warning"
            ? "bg-amber-500/30 text-amber-200 hover:bg-amber-500/40"
            : "bg-primary/30 text-primary hover:bg-primary/50"
        )}
      >
        {status === "applying" ? "…" : "Apply"}
      </button>
      <button
        onClick={() => setStatus("done")}
        title="Ignora"
        className="opacity-60 hover:opacity-100"
        data-testid={`coach-dismiss-${action.type}`}
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}

function Message({ message }) {
  const isUser = message.role === "user";
  const parsed = isUser
    ? { cleanText: message.content, actions: [] }
    : parseCoachActions(message.content);

  return (
    <div className={cls("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        data-testid={`coach-msg-${message.role}`}
        className={cls(
          "max-w-[85%] rounded-2xl px-4 py-3 text-sm",
          isUser
            ? "bg-primary text-primary-foreground rounded-br-sm shadow-[0_0_16px_-6px_hsl(var(--primary)/0.6)]"
            : "bg-secondary text-foreground rounded-bl-sm border border-border"
        )}
      >
        {isUser
          ? <div className="whitespace-pre-wrap">{message.content}</div>
          : <MarkdownLite text={parsed.cleanText} />}
        {parsed.actions.length > 0 && (
          <div className="mt-3 pt-3 border-t border-border/60 flex flex-wrap gap-2">
            {parsed.actions.map((a, i) => (
              <ActionCard key={`${a.type}-${a.name || ""}-${i}`} action={a} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const MessageList = ({ scrollRef, messages, busy, suggestions, onPickSuggestion }) => (
  <div ref={scrollRef} className="flex-1 overflow-y-auto p-5 space-y-4">
    {messages.length === 0 && !busy && (
      <EmptyState suggestions={suggestions} onPick={onPickSuggestion} />
    )}
    {messages.map((m, i) => (
      <Message key={`msg-${m.ts || i}-${m.role}`} message={m} />
    ))}
    {busy && <TypingDots />}
  </div>
);

export default MessageList;
