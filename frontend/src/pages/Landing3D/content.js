// Contenuto narrativo della landing — le 5 tappe. Niente coordinate 3D qui:
// la scena (la N di NEXUS) è la stessa per tutte le sezioni, cambia solo
// l'angolo da cui la camera la guarda (cameraPath.js).

// 6 sezioni nella rail: le 5 tappe + il finale (NEXUS).
export const N_SECTIONS = 6;

// Ordine invertito su richiesta esplicita: l'ultima tappa diventa la prima
// (e così via a cascata) — la sezione finale con NEXUS e la call to action
// resta com'era, in fondo alla pagina.
export const STEPS = [
  {
    badge: "Validazione doppia",
    title: "Non ci fidiamo di un solo test.",
    desc: "Ogni risultato viene messo alla prova su periodi diversi prima di essere considerato affidabile. Se non regge ovunque, non lo chiamiamo un vantaggio.",
  },
  {
    badge: "Sempre con te",
    title: "Non sei solo davanti ai numeri.",
    desc: "Un assistente personale che legge i tuoi trade, ti avvisa se stai rischiando troppo e ti spiega cosa sta succedendo — in linguaggio umano, non in tabelle.",
  },
  {
    badge: "Mai tutto su un solo binario",
    title: "Le posizioni corrono su corsie separate.",
    desc: "Se una parte del motore rallenta, le altre continuano per conto loro. Il rischio non si concentra mai in un unico punto.",
  },
  {
    badge: "Si corregge da sé",
    title: "Un motore che si rimette sempre alla prova.",
    desc: "Ogni ciclo lo testa di nuovo. Quando una parte non funziona più, il sistema la rivede — senza aspettare che sia tu ad accorgertene.",
  },
  {
    badge: "Sempre attivo",
    title: "L'intelligenza artificiale non dorme mai.",
    desc: "Mentre tu vivi la tua vita, il motore resta sveglio: sorveglia il mercato senza pause, senza distrazioni, senza un momento di stanchezza.",
  },
];
