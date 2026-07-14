import Cutout from "./Cutout";

const IMG = (name) => `${process.env.PUBLIC_URL}/images/cutouts/${name}.webp`;

/**
 * La scena vera: non più un video, elementi 3D reali (ritagli con alpha)
 * piazzati a profondità diverse in uno spazio nero — toro e orso si
 * affrontano, lo scontro di energia tra loro, l'arena come fondale
 * lontano, il re dorato rivelato in fondo. Lo scroll pilota la camera
 * (CameraRig) che vola attraverso questo spazio, non un punto fermo che
 * guarda uno schermo: si passa TRA il toro e l'orso, si attraversa lo
 * scontro, si arriva davanti al re.
 */
export default function Diorama() {
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

      {/* il toro, a sinistra, verde */}
      <Cutout
        url={IMG("bull")}
        width={9.18}
        height={5.2}
        position={[-6.6, 1.1, -9]}
        glowColor="#4ade80"
        glowOpacity={0.5}
      />

      {/* l'orso, a destra, rosso */}
      <Cutout
        url={IMG("bear")}
        width={4.7}
        height={5.7}
        position={[6.6, 1.5, -9]}
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
