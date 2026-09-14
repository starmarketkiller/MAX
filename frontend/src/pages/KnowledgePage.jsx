import { Fragment, useEffect, useMemo, useState } from "react";
import { BookOpen, ChevronLeft, FileText, Filter, Search, X } from "lucide-react";
import api from "@/lib/api";
import DataProvenanceBadge from "@/components/DataProvenanceBadge";
import { Card, cls } from "@/pages/dashboard/shared";
import { matchesKnowledgeFilters } from "@/lib/knowledgeFilters";

const present = (value) => value !== null && value !== undefined && value !== "";
const show = (value) => present(value) ? String(value) : "—";

function inline(text) {
  return String(text).split(/(`[^`]+`)/g).map((part, index) => part.startsWith("`") && part.endsWith("`")
    ? <code key={index} className="rounded bg-secondary px-1 py-0.5 font-mono text-[0.9em] text-sky-600 dark:text-sky-300">{part.slice(1, -1)}</code>
    : <Fragment key={index}>{part}</Fragment>);
}

function MarkdownViewer({ content }) {
  const blocks = useMemo(() => {
    const lines = String(content || "").replace(/\r\n/g, "\n").split("\n");
    const output = [];
    let index = 0;
    while (index < lines.length) {
      const line = lines[index];
      if (line.startsWith("```")) {
        const language = line.slice(3).trim();
        const code = [];
        index += 1;
        while (index < lines.length && !lines[index].startsWith("```")) code.push(lines[index++]);
        output.push({ type: "code", language, value: code.join("\n") });
      } else if (/^#{1,6}\s/.test(line)) {
        const level = line.match(/^#+/)[0].length;
        output.push({ type: "heading", level, value: line.replace(/^#{1,6}\s+/, "") });
      } else if (line.includes("|") && index + 1 < lines.length && /^\s*\|?\s*:?-+/.test(lines[index + 1])) {
        const rows = [line]; index += 2;
        while (index < lines.length && lines[index].includes("|")) rows.push(lines[index++]);
        output.push({ type: "table", rows: rows.map((row) => row.replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim())) });
        index -= 1;
      } else if (/^\s*[-*+]\s+/.test(line)) {
        const items = [];
        while (index < lines.length && /^\s*[-*+]\s+/.test(lines[index])) items.push(lines[index++].replace(/^\s*[-*+]\s+/, ""));
        output.push({ type: "list", ordered: false, items }); index -= 1;
      } else if (/^\s*\d+\.\s+/.test(line)) {
        const items = [];
        while (index < lines.length && /^\s*\d+\.\s+/.test(lines[index])) items.push(lines[index++].replace(/^\s*\d+\.\s+/, ""));
        output.push({ type: "list", ordered: true, items }); index -= 1;
      } else if (line.trim()) {
        const paragraph = [line.trim()];
        while (index + 1 < lines.length && lines[index + 1].trim() && !/^(#{1,6}\s|```|\s*[-*+]\s+|\s*\d+\.\s+)/.test(lines[index + 1])) paragraph.push(lines[++index].trim());
        output.push({ type: "paragraph", value: paragraph.join(" ") });
      }
      index += 1;
    }
    return output;
  }, [content]);

  return (
    <div className="min-w-0 space-y-3 break-words text-sm leading-6 text-foreground" data-testid="knowledge-markdown">
      {blocks.map((block, index) => {
        if (block.type === "heading") {
          const Tag = `h${Math.min(block.level + 1, 6)}`;
          return <Tag key={index} className={cls("font-semibold tracking-tight", block.level <= 2 ? "mt-6 text-lg" : "mt-4 text-base")}>{inline(block.value)}</Tag>;
        }
        if (block.type === "code") return <pre key={index} className="max-w-full overflow-x-auto rounded-lg border border-border bg-background p-3 text-xs"><code>{block.value}</code></pre>;
        if (block.type === "table") return <div key={index} className="max-w-full overflow-x-auto rounded-lg border border-border"><table className="min-w-full text-left text-xs"><thead className="bg-secondary/50"><tr>{block.rows[0].map((cell, ci) => <th key={ci} className="whitespace-nowrap px-3 py-2 font-semibold">{inline(cell)}</th>)}</tr></thead><tbody>{block.rows.slice(1).map((row, ri) => <tr key={ri} className="border-t border-border">{row.map((cell, ci) => <td key={ci} className="px-3 py-2 align-top">{inline(cell)}</td>)}</tr>)}</tbody></table></div>;
        if (block.type === "list") {
          const Tag = block.ordered ? "ol" : "ul";
          return <Tag key={index} className={cls("space-y-1 pl-5", block.ordered ? "list-decimal" : "list-disc")}>{block.items.map((item, ii) => <li key={ii}>{inline(item)}</li>)}</Tag>;
        }
        return <p key={index}>{inline(block.value)}</p>;
      })}
    </div>
  );
}

function StrategyDetail({ entry }) {
  const data = entry.strategy_data || {};
  const sweep = data.ultimo_sweep || {};
  const fields = [
    ["Status", data.stato], ["Implemented", data.implementata],
    ["Evidence level", data.affidabilita_dati], ["Decision", data.decisione_corrente],
    ["Profit factor", sweep.profit_factor ?? data.PF], ["Win rate", present(sweep.winrate_pct ?? data.WR_pct) ? `${sweep.winrate_pct ?? data.WR_pct}%` : null],
    ["Expectancy R", sweep.expectancy_R ?? data.expectancy_R], ["Trades", sweep.trade_eseguiti ?? data.trade],
    ["Notes", data.note],
  ];
  return <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">{fields.map(([label, value]) => <div key={label} className="rounded-lg border border-border bg-secondary/20 p-3"><div className="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</div><div className="mt-1 break-words font-mono text-xs">{show(value)}</div></div>)}</div>;
}

function DocumentRow({ item, selected, onSelect }) {
  return (
    <button type="button" onClick={() => onSelect(item.id)} className={cls("w-full rounded-lg border p-3 text-left transition-colors", selected ? "border-sky-500/40 bg-sky-500/5" : "border-border bg-card hover:bg-secondary/40")}>
      <div className="flex items-start justify-between gap-2"><span className="line-clamp-2 text-sm font-semibold">{item.title}</span><DataProvenanceBadge source={item.provenance} className="px-1.5 py-0.5 text-[8px]" /></div>
      <div className="mt-2 flex flex-wrap gap-1.5 font-mono text-[9px] text-muted-foreground"><span>{item.category}</span>{item.strategy ? <span>· {item.strategy}</span> : null}{item.date ? <span>· {item.date}</span> : null}</div>
      {item.snippet ? <p className="mt-2 line-clamp-2 text-[11px] leading-4 text-muted-foreground">{item.snippet}</p> : null}
    </button>
  );
}

export default function KnowledgePage() {
  const [index, setIndex] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [filters, setFilters] = useState({ q: "", category: "", strategy: "", phase: "", kind: "", verdict: "", date: "" });

  useEffect(() => {
    let active = true;
    api.get("/knowledge").then(({ data }) => { if (active) setIndex(data); })
      .catch(() => { if (active) setError("Knowledge index unavailable"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const documents = useMemo(() => index?.documents || [], [index]);
  const options = (key) => [...new Set(documents.map((row) => row[key]).filter(present))].sort();
  const filtered = useMemo(() => documents.filter((row) => matchesKnowledgeFilters(row, filters)), [documents, filters]);

  const select = async (id) => {
    setSelectedId(id); setDetail(null); setDetailLoading(true); setError("");
    try { const { data } = await api.get(`/knowledge/${encodeURIComponent(id)}`); setDetail(data); }
    catch { setError("Knowledge entry unavailable"); }
    finally { setDetailLoading(false); }
  };
  const related = detail ? documents.filter((row) => row.id !== detail.id && ((detail.strategy && row.strategy === detail.strategy) || (detail.phase && row.phase === detail.phase))).slice(0, 6) : [];
  const setFilter = (key, value) => setFilters((current) => ({ ...current, [key]: value }));
  const clearFilters = () => setFilters({ q: "", category: "", strategy: "", phase: "", kind: "", verdict: "", date: "" });

  return (
    <div className="space-y-4 fade-in" data-testid="knowledge-page">
      <div className="flex flex-wrap items-end justify-between gap-3"><div><div className="flex items-center gap-2"><BookOpen className="h-5 w-5 text-sky-500"/><h1 className="text-2xl font-semibold tracking-tight">Research Knowledge</h1><DataProvenanceBadge source={index ? "CACHED" : "UNAVAILABLE"} /></div><p className="mt-1 text-xs text-muted-foreground">Versioned audits, research, decisions, protocols and strategy evidence.</p></div><div className="font-mono text-[10px] text-muted-foreground">{loading ? "Loading…" : `${filtered.length} / ${documents.length} entries`}</div></div>

      {index?.strategy_database?.warning ? <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-700 dark:text-amber-300"><b>Strategy evidence scope:</b> {index.strategy_database.warning}</div> : null}
      <Card className="p-3">
        <div className="flex gap-2"><label className="relative min-w-0 flex-1"><Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground"/><input aria-label="Search knowledge" value={filters.q} onChange={(event) => setFilter("q", event.target.value)} placeholder="Search title, source, strategy, verdict or text…" className="h-9 w-full rounded-lg border border-border bg-background pl-9 pr-3 text-sm"/></label><button type="button" onClick={() => setFiltersOpen((value) => !value)} className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border px-3 text-xs"><Filter size={13}/>Filters</button>{Object.values(filters).some(Boolean) ? <button type="button" onClick={clearFilters} className="h-9 rounded-lg border border-border px-2" aria-label="Clear filters"><X size={14}/></button> : null}</div>
        {filtersOpen ? <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">{[["category","Category"],["strategy","Strategy"],["phase","Phase"],["kind","Type"],["verdict","Verdict"],["date","Date"]].map(([key,label]) => <label key={key} className="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">{label}<select value={filters[key]} onChange={(event) => setFilter(key, event.target.value)} className="mt-1 h-9 w-full rounded-md border border-border bg-background px-2 text-xs normal-case"><option value="">All</option>{options(key).map((value) => <option key={value} value={value}>{value}</option>)}</select></label>)}</div> : null}
      </Card>

      {error ? <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-600 dark:text-rose-400">{error}</div> : null}
      <div className="grid min-w-0 grid-cols-1 gap-4 lg:grid-cols-[minmax(280px,0.8fr)_minmax(0,1.8fr)]">
        <div className={cls("space-y-2", selectedId && "hidden lg:block")}>
          {loading ? <Card className="p-8 text-center text-sm text-muted-foreground">Loading knowledge index…</Card> : filtered.length ? filtered.map((item) => <DocumentRow key={item.id} item={item} selected={item.id === selectedId} onSelect={select}/>) : <Card className="p-8 text-center text-sm text-muted-foreground">No knowledge entries match these filters.</Card>}
        </div>
        <Card className={cls("min-w-0 p-4 sm:p-6", !selectedId && "hidden lg:block")}>
          {selectedId ? <button type="button" onClick={() => { setSelectedId(null); setDetail(null); }} className="mb-4 inline-flex items-center gap-1 text-xs text-muted-foreground lg:hidden"><ChevronLeft size={14}/>Back to results</button> : null}
          {detailLoading ? <div className="py-16 text-center text-sm text-muted-foreground">Loading entry…</div> : detail ? <div className="min-w-0"><div className="border-b border-border pb-4"><div className="flex flex-wrap items-center gap-2"><DataProvenanceBadge source={detail.provenance}/><span className="rounded border border-border px-2 py-0.5 font-mono text-[9px] text-muted-foreground">{detail.category}</span></div><h2 className="mt-3 text-xl font-semibold tracking-tight">{detail.title}</h2><div className="mt-2 break-all font-mono text-[10px] text-muted-foreground">{detail.source_path}</div></div><div className="mt-5">{detail.content_type === "strategy" ? <StrategyDetail entry={detail}/> : <MarkdownViewer content={detail.content}/>}</div>{detail.truncated ? <div className="mt-4 rounded border border-amber-500/30 p-2 text-xs text-amber-600">Document truncated at the safe response limit.</div> : null}{related.length ? <div className="mt-8 border-t border-border pt-4"><h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Related by exact strategy or phase</h3><div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">{related.map((item) => <DocumentRow key={item.id} item={item} selected={false} onSelect={select}/>)}</div></div> : null}</div> : <div className="flex min-h-[320px] flex-col items-center justify-center text-center text-muted-foreground"><FileText className="h-8 w-8 opacity-40"/><div className="mt-3 text-sm">Select a document or strategy record.</div></div>}
        </Card>
      </div>
    </div>
  );
}
