// Contenuto e geometria narrativa condivisi tra la scena 3D e la UI HTML —
// un'unica fonte per il percorso camera, i nodi HUD e le tappe testuali.

export const N_SECTIONS = 7;

// 7 stazioni: hero, 5 tappe, finale. Camera e HUD leggono lo stesso indice.
export const CAMERA_WAYPOINTS = [
  { pos: [0, 3, 15], look: [0, 1, 0] }, // 0 hero
  { pos: [4, 4, -20], look: [0, 2.4, -38] }, // 1 l'AI non dorme
  { pos: [-3, 5.5, -58], look: [0, 3.8, -76] }, // 2 si corregge da sé
  { pos: [4, 7, -96], look: [0, 5.2, -114] }, // 3 corsie separate
  { pos: [-3, 9, -134], look: [0, 6.6, -152] }, // 4 l'assistente
  { pos: [3, 11, -172], look: [0, 8, -190] }, // 5 validazione doppia
  { pos: [0, 9, -206], look: [0, 9, -234] }, // 6 finale — il core quantico
];

export const QUANTUM_CORE_POSITION = [0, 9, -238];

// Un nodo HUD olografico per tappa: cerchi concentrici + testo neon rotante,
// posizionato accanto al percorso, mai sopra al testo o alla scia.
export const HUD_NODES = [
  { pos: [-5, 3.4, -30], colorA: "#38e6ff", colorB: "#2ee88f", labels: ["BUY", "SELL"] },
  { pos: [5, 6.2, -68], colorA: "#38e6ff", colorB: "#8b6ff0", labels: ["SELF-CHECK", "ITERATE"] },
  { pos: [-5, 7.6, -106], colorA: "#2ee88f", colorB: "#8b6ff0", labels: ["LANE A", "LANE B"] },
  { pos: [5, 8.8, -144], colorA: "#38e6ff", colorB: "#eaf2ff", labels: ["COACH", "ALERT"] },
  { pos: [-5, 10.8, -182], colorA: "#eaf2ff", colorB: "#38e6ff", labels: ["3M", "3Y"] },
];

// Profondità (z) di ogni tappa: il toro, l'orso e i volumi si affiancano in
// coppia al nodo HUD della stessa sezione — stesso ritmo, un elemento in più
// del mondo trading per ogni slide, non solo per la prima.
export const TRADE_OBJECT_ZS = [-30, -68, -106, -144, -182];

export const STEPS = [
  {
    badge: "Sempre attivo",
    title: "L'intelligenza artificiale non dorme mai.",
    desc: "Mentre tu vivi la tua vita, il motore resta sveglio: sorveglia il mercato senza pause, senza distrazioni, senza un momento di stanchezza.",
  },
  {
    badge: "Si corregge da sé",
    title: "Un motore che si rimette sempre alla prova.",
    desc: "Ogni ciclo lo testa di nuovo. Quando una parte non funziona più, il sistema la rivede — senza aspettare che sia tu ad accorgertene.",
  },
  {
    badge: "Mai tutto su un solo binario",
    title: "Le posizioni corrono su corsie separate.",
    desc: "Se una parte del motore rallenta, le altre continuano per conto loro. Il rischio non si concentra mai in un unico punto.",
  },
  {
    badge: "Sempre con te",
    title: "Non sei solo davanti ai numeri.",
    desc: "Un assistente personale che legge i tuoi trade, ti avvisa se stai rischiando troppo e ti spiega cosa sta succedendo — in linguaggio umano, non in tabelle.",
  },
  {
    badge: "Validazione doppia",
    title: "Non ci fidiamo di un solo test.",
    desc: "Ogni risultato viene messo alla prova su periodi diversi prima di essere considerato affidabile. Se non regge ovunque, non lo chiamiamo un vantaggio.",
  },
];
