const STYLES = {
  LIVE: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  RESEARCH: "border-violet-500/30 bg-violet-500/10 text-violet-700 dark:text-violet-300",
  DERIVED: "border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-400",
  CACHED: "border-cyan-500/25 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300",
  DEMO: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  UNAVAILABLE: "border-border bg-secondary/50 text-muted-foreground",
};

export const DATA_PROVENANCE = Object.freeze(Object.keys(STYLES));

export function normalizeDataProvenance(source) {
  const value = String(source || "").toUpperCase();
  if (DATA_PROVENANCE.includes(value)) return value;
  if (value.includes("RESEARCH")) return "RESEARCH";
  if (value.includes("DEMO") || value.includes("SYNTHETIC")) return "DEMO";
  if (value.includes("CACHE") || value.includes("STALE")) return "CACHED";
  if (value.includes("DERIVED") || value.includes("LEDGER") || value.includes("RECONSTRUCTED")) return "DERIVED";
  if (value.includes("LIVE") || value.includes("OBSERVED") || value === "EA_PUSH") return "LIVE";
  return "UNAVAILABLE";
}

export default function DataProvenanceBadge({ source, label, className = "", title, testId }) {
  const normalized = normalizeDataProvenance(source);
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full border px-2 py-1 font-mono text-[9px] font-bold tracking-wider ${STYLES[normalized]} ${className}`}
      title={title || `Data provenance: ${normalized}`}
      data-testid={testId || `provenance-${normalized.toLowerCase()}`}
    >
      {label || normalized}
    </span>
  );
}
