import { matchesKnowledgeFilters } from "../lib/knowledgeFilters";

const empty = { q: "", category: "", strategy: "", phase: "", kind: "", verdict: "", date: "" };
const row = {
  title: "ADX RSI validation", source: "vault/report.md", category: "Validation",
  strategy: "ADX_RSI", phase: "4", kind: "document", verdict: "PASS",
  date: "2026-09-14", snippet: "controlled research run",
};

test("searches across metadata and snippet", () => {
  expect(matchesKnowledgeFilters(row, { ...empty, q: "controlled" })).toBe(true);
  expect(matchesKnowledgeFilters(row, { ...empty, q: "bollinger" })).toBe(false);
});

test("combines exact metadata filters", () => {
  expect(matchesKnowledgeFilters(row, { ...empty, category: "Validation", strategy: "ADX_RSI", verdict: "PASS" })).toBe(true);
  expect(matchesKnowledgeFilters(row, { ...empty, verdict: "FAIL" })).toBe(false);
});
