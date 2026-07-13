// Livello di qualità della scena 3D, deciso una volta all'avvio in base al
// dispositivo — non un semplice "è mobile?": un iPad recente resta "high",
// un telefono di fascia bassa (poca CPU/RAM, o l'utente ha chiesto meno
// movimento) scende a "low" e rinuncia al bloom multi-pass e a gran parte
// delle particelle, che sono il costo GPU più alto della scena.
export function detectQuality() {
  if (typeof window === "undefined") return "high";
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) return "low";

  const coarse = window.matchMedia("(pointer: coarse)").matches;
  const small = window.innerWidth < 820;
  const cores = navigator.hardwareConcurrency || 8;
  const mem = navigator.deviceMemory || 8; // Chrome/Android only, undefined altrove

  if (coarse && small && (cores <= 4 || mem <= 4)) return "low";
  if (coarse && small) return "medium";
  return "high";
}

// Parametri per livello: conteggi di particelle/candele/luci e se il bloom
// multi-pass è attivo. "high" è la baseline già collaudata su desktop (gli
// stessi numeri testati finora, non aumentati). "medium" tiene il bloom
// (è ciò che rende leggibile la scia e i pannelli olografici) ma con meno
// oggetti; "low" lo spegne del tutto — è il costo GPU più alto della scena.
export const QUALITY_PRESETS = {
  high: { dpr: [1, 2], bloom: true, starsFar: 2600, starsNear: 900, heroParticles: 700, candles: 90, bloomScale: 0.5 },
  medium: { dpr: [1, 1.5], bloom: true, starsFar: 1600, starsNear: 550, heroParticles: 420, candles: 55, bloomScale: 0.4 },
  low: { dpr: [1, 1], bloom: false, starsFar: 900, starsNear: 300, heroParticles: 220, candles: 32, bloomScale: 0 },
};
