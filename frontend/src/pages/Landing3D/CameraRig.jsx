import { useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

/**
 * Navigazione libera e profonda: la camera vola in linea (quasi) retta
 * dentro la scena, da fuori (toro e orso di fronte, l'arena dietro) fino
 * a dentro (attraverso lo scontro di energia, in mezzo a loro, fino a
 * fermarsi davanti al re dorato). Non un punto fermo che guarda uno
 * schermo — uno spostamento vero nello spazio 3D, con toro/orso/scontro/
 * re/pilastri che scorrono tutti a velocità diverse (parallasse) perché
 * sono oggetti reali a profondità diverse, non un'unica immagine piatta.
 *
 * Scroll giù = si entra (z decresce), scroll su = si esce (z torna su) —
 * bidirezionale, con un leggero dondolio laterale e un parallasse sul
 * mouse per non sembrare mai un binario rigido.
 */
export default function CameraRig({ progressRef }) {
  const { camera, pointer } = useThree();
  const smooth = useRef(0);
  const tmp = useRef(new THREE.Vector3());

  useFrame((state, delta) => {
    const dt = Math.min(delta, 0.1);
    const k = 1 - Math.exp(-dt * 3.5);
    smooth.current += (Math.min(Math.max(progressRef.current, 0), 1) - smooth.current) * k;
    const p = smooth.current;
    const t = state.clock.elapsedTime;

    const camZ = 15 - p * 30; // da +15 (fuori, vista d'insieme) a -15 (oltre il re)
    const camY = 2.4 - p * 0.7 + Math.sin(p * Math.PI) * 0.3;
    const sway = Math.sin(p * Math.PI * 1.4) * 1.6; // dondolio laterale, non un binario dritto
    const lookZ = camZ - 10.5;
    const lookY = 1.7 - p * 0.35;

    tmp.current.set(
      sway + pointer.x * 0.6 + Math.sin(t * 0.08) * 0.15,
      camY - pointer.y * 0.3,
      camZ
    );
    camera.position.lerp(tmp.current, 1); // gia' smussato da `smooth`, applica diretto
    camera.lookAt(sway * 0.4, lookY, lookZ);
  });

  return null;
}
