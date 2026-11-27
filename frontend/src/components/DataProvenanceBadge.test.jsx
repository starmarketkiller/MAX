import { normalizeDataProvenance } from "./DataProvenanceBadge";

test("normalizes backend provenance without inventing a source", () => {
  expect(normalizeDataProvenance("OBSERVED_EA_TELEMETRY")).toBe("LIVE");
  expect(normalizeDataProvenance("SYNTHETIC_DATA")).toBe("DEMO");
  expect(normalizeDataProvenance("DERIVED_ANALYTICS")).toBe("DERIVED");
  expect(normalizeDataProvenance(undefined)).toBe("UNAVAILABLE");
});

test("real historical datasets are labelled HISTORICAL, never LIVE or DEMO", () => {
  expect(normalizeDataProvenance("REAL_HISTORICAL")).toBe("HISTORICAL");
  expect(normalizeDataProvenance("AVAILABLE_OFFLINE")).toBe("UNAVAILABLE");
});

test("normalizes research certificates", () => {
  expect(normalizeDataProvenance("RESEARCH_CERTIFICATE")).toBe("RESEARCH");
});
