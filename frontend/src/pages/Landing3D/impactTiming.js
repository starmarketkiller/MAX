import { N_SECTIONS } from "./content";

function smoothstep(t) {
  const c = Math.min(Math.max(t, 0), 1);
  return c * c * (3 - 2 * c);
}

// Il culmine (toro e orso che si scontrano) deve coincidere con la
// sezione "Sempre con te" (indice 3 su 6) — non con la fine della pagina.
export const IMPACT_SECTION = 3.3;
export const IMPACT_WIDTH = 1.15;

// Progresso di convergenza: raggiunge 1 al culmine e resta 1 dopo (toro e
// orso restano vicini al re per il resto della pagina).
export function convergeMap(p) {
  const sectionP = p * (N_SECTIONS - 1);
  return smoothstep(sectionP / IMPACT_SECTION);
}

// Impulso dell'impatto: cresce fino al culmine e poi rientra — un vero
// flash, non una crescita permanente. Usato per lo scontro, l'onda
// d'urto, le scintille e la vibrazione.
export function impactBump(p) {
  const sectionP = p * (N_SECTIONS - 1);
  const t = Math.max(0, 1 - Math.abs(sectionP - IMPACT_SECTION) / IMPACT_WIDTH);
  return smoothstep(t);
}

export function sectionProgress(p) {
  return p * (N_SECTIONS - 1);
}
