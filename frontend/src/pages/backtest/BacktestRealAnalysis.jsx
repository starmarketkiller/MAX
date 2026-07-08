import { useCallback, useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { Upload, Loader2, ClipboardPaste, FileText, CheckCircle2, XCircle, Ban, Clock, Activity } from "lucide-react";

const VERDICT = {
  FORTE:      { cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30", label: "FORTE" },
  OK:         { cls: "text-sky-400 bg-sky-500/10 border-sky-500/30", label: "OK" },
  DEBOLE:     { cls: "text-amber-400 bg-amber-500/10 border-amber-500/30", label: "DEBOLE" },
  CRITICA:    { cls: "text-rose-400 bg-rose-500/10 border-rose-500/30", label: "CRITICA" },
  BLOCCATA:   { cls: "text-violet-300 bg-violet-500/10 border-violet-500/30", label: "BLOCCATA" },
  POCHI_DATI: { cls: "text-muted-foreground bg-secondary/40 border-border", label: "POCHI DATI" },
  NO_SETUP:   { cls: "text-muted-foreground bg-secondary/20 border-border", label: "NO SETUP" },
};

function VBadge({ v }) {
  const s = VERDICT[v] || VERDICT.POCHI_DATI;
  return <span className={`px-2 py-0.5 rounded border text-[10px] font-bold font-mono ${s.cls}`}>{s.label}</span>;
}

function num(x, d = 2) { return (x ?? 0).toFixed(d); }

export default function BacktestRealAnalysis() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [minTrades, setMinTrades] = useState(10);
  const [showPaste, setShowPaste] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [srcName, setSrcName] = useState("");
  const fileRef = useRef(null);

  // Riapri l'ultima analisi salvata dal backend.
  useEffect(() => {
    (async () => {
      try {
        const { data: last } = await api.get("/backtest/analyze_csv/last");
        if (last && last.rows) { setData(last); setSrcName(last.name || ""); }
      } catch { /* noop */ }
    })();
  }, []);

  const analyze = useCallback(async (csv, name) => {
    if (!csv || !csv.trim()) { setError("CSV vuoto."); return; }
    setBusy(true); setError(""); setData(null);
    try {
      const { data: out } = await api.post("/backtest/analyze_csv", {
        csv, name: name || srcName, min_trades: Number(minTrades) || 10,
      });
      setData(out); setSrcName(out.name || name || "");
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || "Errore analisi");
    } finally { setBusy(false); }
  }, [minTrades, srcName]);

  const onFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => analyze(String(reader.result || ""), f.name);
    reader.readAsText(f);
  };

  // Journal LIVE: verdetti sui trade reali gia' sincronizzati dalla demo.
  const loadJournal = useCallback(async () => {
    setBusy(true); setError(""); setData(null);
    try {
      const { data: out } = await api.get(
        `/analytics/journal_verdict?min_trades=${Number(minTrades) || 10}`);
      if (!out.rows || out.rows.length === 0) {
        setError(out.note || "Nessun trade sincronizzato dalla demo da analizzare.");
      } else {
        setData(out); setSrcName("Journal live (demo)");
      }
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || "Errore journal");
    } finally { setBusy(false); }
  }, [minTrades]);

  // Diagnostica LIVE: verdetti + BLOCCHI dalle stat che l'EA pusha (perche' non apre).
  const loadDiagnostic = useCallback(async () => {
    setBusy(true); setError(""); setData(null);
    try {
      const { data: out } = await api.get(
        `/analytics/strategy_diagnostic_live?min_trades=${Number(minTrades) || 10}`);
      if (!out.rows || out.rows.length === 0) {
        setError(out.note || "Nessuna stat live: l'EA non ha ancora pushato.");
      } else {
        setData(out); setSrcName("Diagnostica live (blocchi)");
      }
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || "Errore diagnostica");
    } finally { setBusy(false); }
  }, [minTrades]);

  const counts = data?.summary?.counts || {};
  const rec = data?.recommendations || {};

  return (
    <div className="space-y-5" data-testid="bt-real-analysis">
      <div className="rounded-xl border border-border p-4">
        <div className="flex items-center gap-2 mb-1">
          <FileText className="h-5 w-5 text-sky-500" />
          <h2 className="text-lg font-bold">Analisi Reale (test MT5)</h2>
        </div>
        <p className="text-sm text-muted-foreground">
          Carica il CSV per-strategia di un test reale (il file <code>*_stats.csv</code> emesso
          dall&apos;EA) <b>oppure</b> premi <b>Journal live</b> per analizzare i trade reali già
          sincronizzati dalla demo. Ottieni il verdetto per strategia + le raccomandazioni:
          cosa tenere, cosa spegnere, quali chiudono troppo veloce, quali non aprono e perché.
        </p>

        <div className="flex flex-wrap items-center gap-2 mt-3">
          <input ref={fileRef} type="file" accept=".csv,text/csv" onChange={onFile} className="hidden" />
          <button onClick={() => fileRef.current?.click()} disabled={busy}
            data-testid="bt-ra-upload"
            className="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-sm inline-flex items-center gap-1.5 disabled:opacity-50">
            <Upload className="h-4 w-4" /> Carica CSV
          </button>
          <button onClick={() => setShowPaste((s) => !s)}
            className="px-3 py-1.5 rounded-lg border border-border hover:bg-secondary text-sm inline-flex items-center gap-1.5">
            <ClipboardPaste className="h-4 w-4" /> Incolla
          </button>
          <button onClick={loadJournal} disabled={busy}
            data-testid="bt-ra-journal"
            className="px-3 py-1.5 rounded-lg border border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10 text-sm inline-flex items-center gap-1.5 disabled:opacity-50">
            <Activity className="h-4 w-4" /> Journal live (demo)
          </button>
          <button onClick={loadDiagnostic} disabled={busy}
            data-testid="bt-ra-diagnostic"
            className="px-3 py-1.5 rounded-lg border border-violet-500/40 text-violet-300 hover:bg-violet-500/10 text-sm inline-flex items-center gap-1.5 disabled:opacity-50">
            <Ban className="h-4 w-4" /> Diagnostica live (blocchi)
          </button>
          <label className="text-xs text-muted-foreground inline-flex items-center gap-1.5 ml-auto">
            min trade
            <input type="number" min={1} value={minTrades}
              onChange={(e) => setMinTrades(e.target.value)}
              className="w-16 px-2 py-1 rounded border border-border bg-background text-sm" />
          </label>
        </div>

        {showPaste && (
          <div className="mt-3 space-y-2">
            <textarea value={pasteText} onChange={(e) => setPasteText(e.target.value)}
              placeholder="Incolla qui il contenuto del CSV (name;enabled;called;...)"
              className="w-full h-28 px-3 py-2 rounded-lg border border-border bg-background text-xs font-mono" />
            <button onClick={() => analyze(pasteText, "incollato")} disabled={busy}
              className="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-sm disabled:opacity-50">
              Analizza incollato
            </button>
          </div>
        )}

        {error && <div className="mt-3 text-sm text-rose-400">{error}</div>}
      </div>

      {busy && (
        <div className="rounded-xl border border-border p-10 text-center">
          <Loader2 className="h-8 w-8 mx-auto mb-2 animate-spin text-sky-500" />
          <div className="text-muted-foreground text-sm">Analizzo i verdetti...</div>
        </div>
      )}

      {data?.rows && !busy && (
        <>
          {/* Riepilogo + raccomandazioni */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="rounded-xl border border-border p-4">
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-2">
                Riepilogo {srcName && <span className="text-foreground">· {srcName}</span>}
              </div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(counts).map(([k, v]) => (
                  <div key={k} className="inline-flex items-center gap-1.5">
                    <VBadge v={k} /><span className="text-xs font-mono">{v}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-xl border border-border p-4 space-y-1.5 text-xs">
              {rec.keep?.length > 0 && (
                <div className="flex items-start gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                  <span><b className="text-emerald-400">Tieni:</b> {rec.keep.join(", ")}</span>
                </div>)}
              {rec.disable?.length > 0 && (
                <div className="flex items-start gap-1.5">
                  <XCircle className="h-4 w-4 text-rose-400 mt-0.5 flex-shrink-0" />
                  <span><b className="text-rose-400">Spegni (perdono):</b> {rec.disable.join(", ")}</span>
                </div>)}
              {rec.too_fast?.length > 0 && (
                <div className="flex items-start gap-1.5">
                  <Clock className="h-4 w-4 text-amber-400 mt-0.5 flex-shrink-0" />
                  <span><b className="text-amber-400">Chiudono troppo veloce (&lt;5m):</b> {rec.too_fast.join(", ")}</span>
                </div>)}
              {rec.blocked?.length > 0 && (
                <div className="flex items-start gap-1.5">
                  <Ban className="h-4 w-4 text-violet-300 mt-0.5 flex-shrink-0" />
                  <span><b className="text-violet-300">Non aprono:</b> {rec.blocked.map((b) => `${b.name} (${b.blocker})`).join(", ")}</span>
                </div>)}
              {!rec.keep?.length && !rec.disable?.length && !rec.blocked?.length && (
                <div className="text-muted-foreground">Nessun segnale netto: campione ancora piccolo.</div>)}
            </div>
          </div>

          {/* Tabella verdetti */}
          <div className="rounded-xl border border-border overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[10px] uppercase tracking-wide text-muted-foreground border-b border-border">
                  <th className="text-left px-3 py-2">Strategia</th>
                  <th className="text-left px-3 py-2">Verdetto</th>
                  <th className="text-right px-3 py-2">N</th>
                  <th className="text-right px-3 py-2">PF</th>
                  <th className="text-right px-3 py-2">Exp.R</th>
                  <th className="text-right px-3 py-2">WR%</th>
                  <th className="text-right px-3 py-2">Hold</th>
                  <th className="text-left px-3 py-2">Note</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((x) => (
                  <tr key={x.name} className="border-b border-border/50 hover:bg-secondary/30">
                    <td className="px-3 py-2 font-mono font-semibold">{x.name}</td>
                    <td className="px-3 py-2"><VBadge v={x.verdict} /></td>
                    <td className="px-3 py-2 text-right font-mono">{x.executed}</td>
                    <td className="px-3 py-2 text-right font-mono">{num(x.pf)}</td>
                    <td className={`px-3 py-2 text-right font-mono ${x.exp > 0 ? "text-emerald-400" : x.exp < 0 ? "text-rose-400" : ""}`}>{x.exp > 0 ? "+" : ""}{num(x.exp)}</td>
                    <td className="px-3 py-2 text-right font-mono">{num(x.wr, 0)}</td>
                    <td className="px-3 py-2 text-right font-mono text-muted-foreground">{x.hold_min > 0 ? `${num(x.hold_min, 0)}m` : "—"}</td>
                    <td className="px-3 py-2 text-[11px] text-muted-foreground">{x.why}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
