const present = (value) => value !== null && value !== undefined && value !== "";

export function matchesKnowledgeFilters(row, filters) {
  const q = filters.q.trim().toLowerCase();
  const haystack = [row.title, row.source, row.category, row.strategy, row.verdict, row.snippet].filter(present).join(" ").toLowerCase();
  return (!q || haystack.includes(q)) && (!filters.category || row.category === filters.category)
    && (!filters.strategy || row.strategy === filters.strategy) && (!filters.phase || row.phase === filters.phase)
    && (!filters.kind || row.kind === filters.kind) && (!filters.verdict || row.verdict === filters.verdict)
    && (!filters.date || row.date === filters.date);
}
