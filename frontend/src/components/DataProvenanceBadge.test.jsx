import { normalizeDataProvenance } from "./DataProvenanceBadge";

test("normalizes backend provenance without inventing a source", () => {
  expect(normalizeDataProvenance("OBSERVED_EA_TELEMETRY")).toBe("LIVE");
  expect(normalizeDataProvenance("SYNTHETIC_DATA")).toBe("DEMO");
  expect(normalizeDataProvenance("DERIVED_ANALYTICS")).toBe("DERIVED");
  expect(normalizeDataProvenance(undefined)).toBe("UNAVAILABLE");
});

test("normalizes research certificates", () => {
  expect(normalizeDataProvenance("RESEARCH_CERTIFICATE")).toBe("RESEARCH");
});
