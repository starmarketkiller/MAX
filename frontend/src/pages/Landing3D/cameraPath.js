// Un punto macchina per ognuna delle 6 sezioni (le 5 tappe + il finale): la
// camera gira intorno alla N (NexusLogo.jsx, ferma a [0, 2.1, -12]) restando
// sempre entro un angolo che la mantiene leggibile come lettera — la N è
// estrusa poco in profondità (1.35 unità contro 5.4 di altezza), un'orbita
// troppo larga o dall'alto la riduce a un pannello piatto irriconoscibile.
// Distanza e altezza variano invece parecchio: da lontano (tappa 0) fino a
// un avvicinamento ravvicinato al culmine (tappa 4, dove l'energia
// "lampeggia", impactTiming), poi un ritiro pulito per il finale — non un
// attraversamento vero, per non ritrovarsi a leggere una N specchiata
// proprio nel momento più importante (la call to action). Interpolato con
// uno smoothstep tra la tappa corrente e la successiva così ogni scroll,
// anche piccolo, produce un movimento reale — mai un tratto "morto".
const N_POS = [0, 2.1, -12];
export const CAMERA_WAYPOINTS = [
  { pos: [0, 3.4, 12], look: N_POS }, // 0 · Sempre attivo — vista d'insieme, da lontano
  { pos: [-6.5, 3.0, -3], look: [-0.3, 2.2, -11.3] }, // 1 · Si corregge da sé — orbita 3/4 a sinistra
  { pos: [6.5, 2.4, -3], look: [0.3, 2.1, -11.5] }, // 2 · Corsie separate — orbita 3/4 a destra
  { pos: [0, 4.0, -2.5], look: [0, 2.3, -11.5] }, // 3 · Sempre con te — leggero sopraelevo frontale
  { pos: [0, 1.1, -8.3], look: [0, 2.1, -12.5] }, // 4 · Validazione doppia — avvicinamento, culmine energia
  { pos: [0, 3.2, 8], look: [0, 2.05, -12] }, // 5 · finale — ritiro pulito, la N intera per la call to action
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
