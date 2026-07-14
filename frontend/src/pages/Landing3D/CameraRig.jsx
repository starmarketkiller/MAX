import { useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

/**
 * Un movimento di camera lento e continuo lungo tutta la pagina — non un
 * percorso a tappe come nella versione precedente, solo un dolly-in +
 * orbita ampia che dà profondità reale allo schermo: si parte larghi e
 * lontani (si vede il pavimento e lo spazio intorno), si arriva stretti
 * e vicini al finale. L'orbita è ampia apposta — è il movimento laterale
 * della camera, insieme allo spessore del box-schermo, a far percepire lo
 * spazio come davvero tridimensionale invece che un fondale piatto.
 *
 * Aggiunge anche un lieve parallasse sul mouse: la scena reagisce al
 * puntatore, un altro indizio di profondità che uno sfondo piatto non da'.
 * Smoothing in tempo reale (non per-frame) cosi' resta fluido a qualunque
 * framerate.
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

    const angle = (p - 0.5) * 1.1; // orbita ampia, +-0.55 rad (~63 gradi totali)
    const radius = 16 - p * 7; // dolly-in: parte largo a 16, arriva stretto a 9
    const height = 1.7 + Math.sin(p * Math.PI) * 1.1;

    tmp.current.set(
      Math.sin(angle) * radius + pointer.x * 0.5,
      height - pointer.y * 0.3,
      Math.cos(angle) * radius
    );
    camera.position.lerp(tmp.current, 1); // gia' smussato da `smooth`, applica diretto
    camera.lookAt(0, 1.7, 0);
  });

  return null;
}
