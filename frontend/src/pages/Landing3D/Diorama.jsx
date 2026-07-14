import Cutout from "./Cutout";
import { N_SECTIONS } from "./content";

const IMG = (name) => `${process.env.PUBLIC_URL}/images/cutouts/${name}.webp`;

function smoothstep(t) {
  const c = Math.min(Math.max(t, 0), 1);
  return c * c * (3 - 2 * c);
}

// Il culmine (toro e orso che si scontrano) deve coincidere con la
// sezione "Sempre con te" (indice 3 su 6) — non con la fine della pagina.
// Mappa il progresso grezzo di pagina (0..1) su un progresso di
// convergenza che raggiunge 1 lì e resta 1 per il resto dello scroll.
const IMPACT_SECTION = 3.3;
function convergeMap(p) {
  const sectionP = p * (N_SECTIONS - 1);
  return smoothstep(sectionP / IMPACT_SECTION);
}
// Zoom continuo e lentissimo sull'arena per tutta la pagina — la camera
// "entra fisicamente" negli spalti, non è solo lo sfondo che sta fermo.
const arenaMap = (p) => p;
// Lo scontro non deve restare enorme per sempre una volta raggiunto il
// culmine — cresce fino all'impatto e poi rientra, un vero flash che
// esplode e si ritira, così non copre la scena nelle sezioni successive
// (dove camera e re devono tornare protagonisti).
const IMPACT_WIDTH = 1.15;
function impactBump(p) {
  const sectionP = p * (N_SECTIONS - 1);
  const t = Math.max(0, 1 - Math.abs(sectionP - IMPACT_SECTION) / IMPACT_WIDTH);
  return smoothstep(t);
}

/**
 * La scena vera: elementi 3D reali (ritagli con alpha) a profondità
 * diverse in uno spazio nero. Tre livelli di parallasse rigorosi:
 * l'arena (sfondo, lentissima, con uno zoom continuo), toro e orso
 * (secondo piano, convergono l'uno verso l'altro caricandosi), lo
 * scontro/il re (primo piano, cresce nel momento dell'impatto). Lo
 * scroll pilota sia la camera (CameraRig, a tappe — una per sezione) sia
 * questi elementi stessi: toro e orso si muovono loro, non restano fermi
 * ad aspettare che la camera li scavalchi.
 */
export default function Diorama({ progressRef }) {
  return (
    <group>
      {/* sfondo — lentissimo, con un leggero zoom "verso gli spalti" */}
      <Cutout
        url={IMG("arena")}
        width={30}
        height={25.7}
        position={[0, 9, -34]}
        progressRef={progressRef}
        mapProgress={arenaMap}
        convergeTo={[0, 9, -34]}
        convergeScale={1.07}
        billboard={false}
        pulse={false}
      />

      {/* il toro, a sinistra, verde — converge verso il re caricando */}
      <Cutout
        url={IMG("bull")}
        width={9.27}
        height={5.2}
        position={[-5.6, 1.1, -9]}
        progressRef={progressRef}
        mapProgress={convergeMap}
        convergeTo={[-1.5, 1.7, -17.5]}
        convergeScale={0.3}
        glowColor="#4ade80"
        glowOpacity={0.5}
      />

      {/* l'orso, a destra, rosso — converge verso il re caricando */}
      <Cutout
        url={IMG("bear")}
        width={4.45}
        height={5.7}
        position={[5.6, 1.5, -9]}
        progressRef={progressRef}
        mapProgress={convergeMap}
        convergeTo={[1.5, 1.9, -17.5]}
        convergeScale={0.3}
        glowColor="#f87171"
        glowOpacity={0.5}
      />

      {/* lo scontro di energia tra i due, additivo puro — cresce nel
          momento dell'impatto, primo piano rispetto a tutto il resto */}
      <Cutout
        url={IMG("clash")}
        width={8.2}
        height={5.1}
        position={[0, 2.1, -10.5]}
        progressRef={progressRef}
        mapProgress={impactBump}
        convergeTo={[0, 2.1, -10.5]}
        convergeScale={1.45}
        additive
        pulse={false}
      />

      {/* il re dorato, in fondo — si rivela man mano che si vola dentro */}
      <Cutout
        url={IMG("king")}
        width={5.9}
        height={7.1}
        position={[0, 2.0, -19.5]}
        glowColor="#fbbf24"
        glowOpacity={0.42}
      />
    </group>
  );
}
