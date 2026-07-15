import { N_SECTIONS } from "./content";

function smoothstep(t) {
  const c = Math.min(Math.max(t, 0), 1);
  return c * c * (3 - 2 * c);
}

// Il culmine (la camera al punto di massimo avvicinamento alla N,
// cameraPath.js tappa 4) deve coincidere con "Validazione doppia" — non
// con la fine della pagina.
export const IMPACT_SECTION = 4.0;
export const IMPACT_WIDTH = 0.85;

// Progresso di convergenza: raggiunge 1 al culmine e resta 1 dopo.
export function convergeMap(p) {
  const sectionP = p * (N_SECTIONS - 1);
  return smoothstep(sectionP / IMPACT_SECTION);
}

// Impulso dell'attraversamento: cresce fino al culmine e poi rientra — un
// vero flash, non una crescita permanente. Usato per l'energia della N
// (NexusLogo) e la vibrazione (CameraRig).
export function impactBump(p) {
  const sectionP = p * (N_SECTIONS - 1);
  const t = Math.max(0, 1 - Math.abs(sectionP - IMPACT_SECTION) / IMPACT_WIDTH);
  return smoothstep(t);
}

export function sectionProgress(p) {
  return p * (N_SECTIONS - 1);
}
