// Un punto macchina per ognuna delle 6 sezioni (le 5 tappe + il finale):
// non un'unica dolly continua e generica, ma una tappa dedicata per
// elemento — si passa dalla vista d'insieme, al toro, all'orso, al punto
// dello scontro, all'impatto, fino a fermarsi davanti al re. Interpolato
// con uno smoothstep tra la tappa corrente e la successiva così ogni
// scroll, anche piccolo, produce un movimento reale verso il prossimo
// punto — mai un tratto "morto" dove la camera resta ferma.
export const CAMERA_WAYPOINTS = [
  { pos: [0, 2.6, 15], look: [0, 1.8, -9] }, // 0 · Sempre attivo — vista d'insieme
  { pos: [-3.6, 2.0, 7.2], look: [-4.4, 1.35, -8] }, // 1 · Si corregge da sé — verso il toro
  { pos: [3.6, 2.0, 4.4], look: [4.4, 1.55, -8.5] }, // 2 · Corsie separate — verso l'orso
  { pos: [0, 1.9, 0.2], look: [0, 1.95, -10.5] }, // 3 · Sempre con te — verso lo scontro
  { pos: [0, 1.85, -3.8], look: [0, 1.95, -16] }, // 4 · Validazione doppia — l'impatto/il re che emerge
  { pos: [0, 1.6, -13.6], look: [0, 1.85, -19.5] }, // 5 · finale — davanti al re
];

function smoothstep(t) {
  const c = Math.min(Math.max(t, 0), 1);
  return c * c * (3 - 2 * c);
}

// p: 0..1 sull'intera pagina. Restituisce {pos:[x,y,z], look:[x,y,z]}
// interpolati tra la tappa corrente e la successiva.
export function sampleCameraPath(p) {
  const n = CAMERA_WAYPOINTS.length;
  const scaled = Math.min(Math.max(p, 0), 1) * (n - 1);
  const i = Math.min(Math.floor(scaled), n - 2);
  const frac = smoothstep(scaled - i);
  const a = CAMERA_WAYPOINTS[i];
  const b = CAMERA_WAYPOINTS[i + 1];
  return {
    pos: [0, 1, 2].map((k) => a.pos[k] + (b.pos[k] - a.pos[k]) * frac),
    look: [0, 1, 2].map((k) => a.look[k] + (b.look[k] - a.look[k]) * frac),
  };
}
