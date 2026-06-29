import { useEffect, useState } from "react";
import { BookOpenCheck, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";

// Compact, collapsible "Coach Memory" — durable notes that the rich-context
// bundle injects into every conversation. Use them for behavioural patterns
// you want the Coach to never forget (e.g. "I tend to revenge-trade after 3 losses").

export default function CoachMemoryPanel() {
  const [items, setItems] = useState([]);
  const [adding, setAdding] = useState("");
  const [open, setOpen] = useState(false);

  const load = async () => {
    try {
      const { data } = await api.get("/coach/memory");
      setItems(data.items || []);
    } catch (e) {
      console.warn("[CoachMemoryPanel] load failed", e?.message || e);
    }
  };
  useEffect(() => { load(); }, []);

  const add = async () => {
    const v = adding.trim();
    if (!v) return;
    try {
      await api.post("/coach/memory", { note: v });
      setAdding("");
      toast.success("Memoria salvata");
      load();
    } catch (e) {
      toast.error(`Errore: ${e?.response?.data?.detail || e.message}`);
    }
  };

  const remove = async (id) => {
    try {
      await api.delete(`/coach/memory/${id}`);
      load();
    } catch (e) {
      toast.error(`Errore: ${e?.response?.data?.detail || e.message}`);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-card/60 backdrop-blur-sm" data-testid="coach-memory-panel">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2.5 px-4 py-3 text-left hover:bg-secondary/40 transition-colors rounded-xl"
        data-testid="coach-memory-toggle"
      >
        <BookOpenCheck className="h-4 w-4 text-primary" />
        <div className="flex-1">
          <div className="text-sm font-semibold">Memoria del Coach</div>
          <div className="text-[11px] text-muted-foreground font-mono">
            {items.length} appunti persistenti · iniettati in ogni conversazione
          </div>
        </div>
        <span className={`text-xs text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`}>▾</span>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-2 fade-in">
          <div className="flex gap-2 mb-3">
            <input
              value={adding}
              onChange={(e) => setAdding(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && add()}
              placeholder="Es: 'Perdo di più durante l'overlap NY'"
              data-testid="coach-memory-input"
              className="flex-1 h-9 px-3 rounded-lg bg-background border border-border text-xs font-mono focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/40"
            />
            <button
              onClick={add}
              disabled={!adding.trim()}
              data-testid="coach-memory-add"
              className="h-9 px-3 rounded-lg bg-primary text-primary-foreground text-xs font-semibold disabled:opacity-50 hover:brightness-110 active:scale-95 transition-all inline-flex items-center gap-1.5 shadow-[0_0_12px_-4px_hsl(var(--primary)/0.5)]"
            >
              <Plus className="h-3 w-3" /> Aggiungi
            </button>
          </div>
          {items.length === 0 && (
            <div className="text-center py-6 text-xs text-muted-foreground">
              Nessuna memoria. Aggiungi pattern del tuo trading che il Coach deve ricordare sempre.
            </div>
          )}
          {items.map((m) => (
            <div
              key={m.id}
              data-testid={`coach-memory-item-${m.id}`}
              className="flex items-start gap-2 px-3 py-2 rounded-lg border border-border/60 bg-secondary/30 group hover:bg-secondary/60 transition-colors"
            >
              <div className="flex-1 text-xs">{m.note}</div>
              <button
                onClick={() => remove(m.id)}
                className="opacity-30 group-hover:opacity-100 transition-opacity text-rose-400 hover:text-rose-300"
                title="Elimina"
                data-testid={`coach-memory-delete-${m.id}`}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
