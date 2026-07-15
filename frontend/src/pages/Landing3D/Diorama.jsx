import Cutout from "./Cutout";
import { convergeMap, impactBump } from "./impactTiming";

const IMG = (name) => `${process.env.PUBLIC_URL}/images/cutouts/${name}.webp`;

// Zoom continuo e lentissimo sull'arena per tutta la pagina — la camera
// "entra fisicamente" negli spalti, non è solo lo sfondo che sta fermo.
const arenaMap = (p) => p;

/**
 * La scena vera: elementi 3D reali (ritagli con alpha) a profondità
 * diverse in uno spazio nero. Tre livelli di parallasse rigorosi:
 * l'arena (sfondo, lentissima, con uno zoom continuo), toro e orso
 * (secondo piano, convergono l'uno verso l'altro caricandosi), lo
 * scontro/il re (primo piano, cresce nel momento dell'impatto). Lo
 * scroll pilota sia la camera (CameraRig, a tappe — una per sezione) sia
 * questi elementi stessi: toro e orso si muovono loro, non restano fermi
 * ad aspettare che la camera li scavalchi.
 *
 * `parallaxRef` (mouse + giroscopio, vedi useDeviceTilt) dà a ogni
 * livello una propria velocità di risposta al puntatore — lo sfondo si
 * sposta appena, il primo piano molto di più: è questo scarto, non lo
 * scroll, a far sembrare lo spazio vivo anche da fermi.
 */
export default function Diorama({ progressRef, parallaxRef, velocityRef }) {
  return (
    <group>
      {/* sfondo — lentissimo, con un leggero zoom "verso gli spalti".
          Largo e alto a sufficienza da coprire il frustum della camera anche
          ai bordi (aspect ratio larghi da telefono in orizzontale, o
          desktop): a fov=45 e questa distanza, sotto ~65 unità di larghezza
          si vedeva il nero oltre i bordi del piano, come una foto piccola
          incorniciata invece di un fondale a schermo intero. */}
      <Cutout
        url={IMG("arena")}
        width={92}
        height={78.9}
        position={[0, 9, -34]}
        progressRef={progressRef}
        mapProgress={arenaMap}
        convergeTo={[0, 9, -34]}
        convergeScale={1.07}
        parallaxRef={parallaxRef}
        parallaxStrength={0.35}
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
        parallaxRef={parallaxRef}
        parallaxStrength={0.9}
        glowColor="#4ade80"
        glowOpacity={0.5}
      />

      {/* l'orso, a destra, rosso — converge verso il re caricando */}
      <Cutout
        url={IMG("bear")}
        width={6.78}
        height={7.4}
        position={[5.6, 1.9, -9]}
        progressRef={progressRef}
        mapProgress={convergeMap}
        convergeTo={[1.5, 1.9, -17.5]}
        convergeScale={0.3}
        parallaxRef={parallaxRef}
        parallaxStrength={0.9}
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
        parallaxRef={parallaxRef}
        parallaxStrength={1.3}
        skewRef={velocityRef}
        skewStrength={1.4}
        additive
        pulse={false}
      />

      {/* il re dorato, in fondo — si rivela man mano che si vola dentro */}
      <Cutout
        url={IMG("king")}
        width={5.9}
        height={7.1}
        position={[0, 2.0, -19.5]}
        parallaxRef={parallaxRef}
        parallaxStrength={0.55}
        glowColor="#fbbf24"
        glowOpacity={0.42}
      />
    </group>
  );
}
