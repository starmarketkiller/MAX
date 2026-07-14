import Cutout from "./Cutout";

const IMG = (name) => `${process.env.PUBLIC_URL}/images/cutouts/${name}.webp`;

/**
 * La scena vera: non più un video, elementi 3D reali (ritagli con alpha)
 * piazzati a profondità diverse in uno spazio nero — toro e orso si
 * affrontano, lo scontro di energia tra loro, l'arena come fondale
 * lontano, il re dorato rivelato in fondo. Lo scroll pilota sia la camera
 * (CameraRig) che vola attraverso questo spazio, sia toro e orso stessi:
 * invece di restare fermi ai lati (dove su schermi stretti come un
 * telefono un campo visivo più stretto li taglia fuori), si avvicinano
 * al re rimpicciolendo mentre si scrolla — restano sempre dentro
 * l'inquadratura, ovunque.
 */
export default function Diorama({ progressRef }) {
  return (
    <group>
      {/* fondale dell'arena, lontano e fisso — non billboard: resta
          ancorato al mondo, dà il contesto senza mai essere l'elemento
          principale */}
      <Cutout
        url={IMG("arena")}
        width={30}
        height={25.7}
        position={[0, 9, -34]}
        billboard={false}
        pulse={false}
      />

      {/* il toro, a sinistra, verde — converge verso il re rimpicciolendo */}
      <Cutout
        url={IMG("bull")}
        width={9.18}
        height={5.2}
        position={[-5.6, 1.1, -9]}
        progressRef={progressRef}
        convergeTo={[-1.5, 1.7, -17.5]}
        convergeScale={0.3}
        glowColor="#4ade80"
        glowOpacity={0.5}
      />

      {/* l'orso, a destra, rosso — converge verso il re rimpicciolendo */}
      <Cutout
        url={IMG("bear")}
        width={4.7}
        height={5.7}
        position={[5.6, 1.5, -9]}
        progressRef={progressRef}
        convergeTo={[1.5, 1.9, -17.5]}
        convergeScale={0.3}
        glowColor="#f87171"
        glowOpacity={0.5}
      />

      {/* lo scontro di energia tra i due, additivo puro — cosi' qualunque
          imperfezione nel ritaglio del fondale scompare (il nero non
          somma nulla), resta solo la luce */}
      <Cutout
        url={IMG("clash")}
        width={8.2}
        height={5.1}
        position={[0, 2.1, -10.5]}
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
