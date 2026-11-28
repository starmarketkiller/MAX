import React from "react";
import { createRoot } from "react-dom/client";
import { act } from "react-dom/test-utils";
import DiscoveryPanel from "./DiscoveryPanel";
import { pivotKindFromAnchor, formatSpan } from "@/lib/geometry/useDiscovery";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const T0 = 1760000000;
const ev = (over = {}) => ({
  event_id: "E1", name: "Inversione A", revision: 3, outcome: "REVERSAL", classification: "MAJOR_REVERSAL", size_class: "UNCLASSIFIED", symbol: "GOLD", timeframe_observation: "H4",
  dataset_id: "DS", source: "XM", clock_basis: "TERMINAL_CLOCK (x)", discovered_at: T0, author: "u", author_verified: true, imported_by: null,
  epistemic_mode: "RETROSPECTIVE_DISCOVERY", validation_status: "NOT_VALIDATED", units: { pip_size: 0.1, point: null, tick_size: null },
  pivot: { t: T0, price: 3900, kind: "HIGH", ref: { kind: "CANDLE", field: "high" } }, origin: { t: T0 - 86400, price: 3800, ref: { kind: "FREE" } }, destination: null,
  derived: { prior_direction: "UP", next_direction: "DOWN", prior_leg: { direction: "UP", amplitude_price: 100, amplitude_pips: 1000, duration_s: 86400 }, next_leg: null },
  geometries: [{ id: "L1", geometry_id: "G1", timing: "BEFORE_EVENT_OBSERVABLE", causal_knowledge: "NOT_ESTABLISHED", geometry: { type: "trendline", semantic_class: "DIAG_SELL" } }],
  structures: [{ id: "S1", kind: "IMPULSE", scale: "MAJOR", parent_id: null, derived: { direction: "UP", amplitude_price: 100, amplitude_pips: 1000, duration_s: 86400 } },
    { id: "S2", kind: "CORRECTION", scale: "MINOR", parent_id: "S1", derived: { direction: "DOWN", amplitude_price: 20, amplitude_pips: 200, duration_s: 3600 } }],
  annotations: [{ id: "A1", text: "spike" }], hypotheses: [{ id: "H1", text: "esaurimento", status: "OPEN" }], evidence_for: [], evidence_against: [], analog_links: [], status: "ACTIVE", ...over,
});

let host, root;
beforeEach(() => { host = document.createElement("div"); document.body.appendChild(host); root = createRoot(host); });
afterEach(() => { act(() => root.unmount()); host.remove(); });

const props = (over = {}) => ({
  events: [ev()], selectedEventId: "E1", setSelectedEventId: jest.fn(), draft: {}, setDraft: jest.fn(), tool: "select", setTool: jest.fn(), units: { pip_size: 0.1 }, symbol: "GOLD",
  createFromDraft: jest.fn(() => Promise.resolve()), update: jest.fn(() => Promise.resolve()), archive: jest.fn(() => Promise.resolve()), nav: { goTo: jest.fn(), openMultiscale: jest.fn(), back: jest.fn(), forward: jest.fn() },
  geoms: [{ geometry_id: "G1" }], selectedGeomId: "G1", structForm: { kind: "IMPULSE", scale: "MAJOR", parent_id: null }, setStructForm: jest.fn(), compare: jest.fn(),
  status: { state: "idle", error: null }, note: null, setNote: jest.fn(), ...over,
});
const q = (id) => host.querySelector(`[data-testid="${id}"]`);

test("banner epistemico: retrospettiva, DISCOVERY_ONLY, nessuna validazione ne' segnale", () => {
  act(() => root.render(<DiscoveryPanel {...props()} />));
  const t = q("lab-mode-banner").textContent;
  expect(t).toMatch(/RETROSPECTIVE_DISCOVERY/); expect(t).toMatch(/nessuna validazione/); expect(t).toMatch(/nessun segnale/); expect(t).toMatch(/≠ edge predittivo/);
});

test("scheda: grandezze derivate in prezzo e pip, validazione NOT_VALIDATED, modalita' immutabile, nessun pulsante di validazione", () => {
  act(() => root.render(<DiscoveryPanel {...props()} />));
  expect(q("lab-card-prior").textContent).toMatch(/100 = 1000 pip/);
  expect(q("lab-card-validation").textContent).toBe("NOT_VALIDATED");
  expect(q("lab-card-facts").textContent).toMatch(/RETROSPECTIVE_DISCOVERY.*immutabile/);
  expect(host.textContent).not.toMatch(/\bValida\b|Approva|Esegui|Ordine|Apri posizione|Segnale operativo/);   // nessuna azione di validazione o di trading (le etichette manuali DIAG_BUY/SELL sono solo classificazioni)
  expect(host.querySelectorAll("button").length).toBeGreaterThan(5);
  expect([...host.querySelectorAll("button")].some((b) => /valida|ordine|esegui/i.test(b.textContent))).toBe(false);
});

test("geometria collegata: conoscenza causale NOT_ESTABLISHED e avviso che presente nel grafico != conoscibile prima", () => {
  act(() => root.render(<DiscoveryPanel {...props()} />));
  expect(q("lab-geom-G1").textContent).toMatch(/NOT_ESTABLISHED/);
  expect(host.textContent).toMatch(/non si retrodata/);
});

test("strutture: gerarchia padre-figlio indentata; scale come classificazione, non timeframe", () => {
  act(() => root.render(<DiscoveryPanel {...props()} />));
  expect(q("lab-struct-S2").style.paddingLeft).toBe("10px");
  expect(q("lab-struct-S1").style.paddingLeft).toBe("0px");
  expect(host.textContent).toMatch(/non timeframe fissi né teorie d'onda/);
});

test("creazione disabilitata finche' non e' scelto il pivot; poi invia nome ed esito", async () => {
  const p = props({ events: [], selectedEventId: null });
  act(() => root.render(<DiscoveryPanel {...p} />));
  expect(q("lab-create").disabled).toBe(true);
  act(() => root.render(<DiscoveryPanel {...p} draft={{ pivot: { t: T0, price: 3900, ref: { kind: "CANDLE", field: "high" } }, kind: "HIGH", tf: "H4" }} />));
  expect(q("lab-create").disabled).toBe(false);
  await act(async () => { q("lab-create").click(); });
  expect(p.createFromDraft).toHaveBeenCalledWith({ name: "", outcome: "REVERSAL" });
});

test("import: autore dichiarato non autenticato quando l'importatore e' diverso", () => {
  act(() => root.render(<DiscoveryPanel {...props({ events: [ev({ author_verified: false, imported_by: "bob", author: "alice" })] })} />));
  expect(q("lab-card-facts").textContent).toMatch(/autore alice \(dichiarato; importato da bob\)/);
});

test("utility: tipo di pivot dedotto dal campo della candela e durate leggibili", () => {
  expect(pivotKindFromAnchor({ price: 5, ref: { field: "high" } })).toBe("HIGH");
  expect(pivotKindFromAnchor({ price: 5, ref: { field: "low" } })).toBe("LOW");
  expect(pivotKindFromAnchor({ price: 9, ref: { field: "close" } }, { high: 10, low: 2 })).toBe("HIGH");
  expect(pivotKindFromAnchor({ price: 3, ref: { field: "open" } }, { high: 10, low: 2 })).toBe("LOW");
  expect(formatSpan(14400)).toBe("4h 0m"); expect(formatSpan(90000)).toBe("1g 1h 0m");
});
