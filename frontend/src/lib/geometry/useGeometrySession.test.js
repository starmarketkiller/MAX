import { diffPatch, errText } from "./useGeometrySession";

const base = { anchors: [{ t: 1, price: 2 }], style: { color: "#000000", width: 2, locked: false }, name: "a", description: "", semantic: { class: "NONE" } };

test("diffPatch: solo i campi cambiati; per lo stile solo le chiavi cambiate", () => {
  expect(diffPatch(base, { ...base })).toEqual({});
  expect(diffPatch(base, { ...base, name: "b" })).toEqual({ name: "b" });
  expect(diffPatch(base, { ...base, style: { ...base.style, locked: true } })).toEqual({ style: { locked: true } });
  expect(diffPatch(base, { ...base, anchors: [{ t: 1, price: 3 }], style: { ...base.style, width: 4 } })).toEqual({ anchors: [{ t: 1, price: 3 }], style: { width: 4 } });
});

test("diffPatch: lo sblocco (redo/undo di un oggetto bloccato) non rimanda lo stile intero", () => {
  const locked = { ...base, style: { ...base.style, locked: true } };
  const patch = diffPatch(locked, base);
  expect(Object.keys(patch)).toEqual(["style"]);
  expect(patch.style).toEqual({ locked: false });
});

test("errText: codice e messaggio dal backend, altrimenti testo generico", () => {
  expect(errText({ response: { data: { detail: { code: "OBJECT_LOCKED", message: "bloccato" } } } })).toBe("OBJECT_LOCKED: bloccato");
  expect(errText({ response: { data: { detail: "x" } } })).toBe("x");
  expect(errText(new Error("rete"))).toBe("rete");
});
