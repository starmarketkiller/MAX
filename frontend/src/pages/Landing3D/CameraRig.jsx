import { useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

/**
 * Il volo dentro l'arena: si scrolla giù e si entra, si torna su e si esce.
 * Non un percorso a tappe, un unico arco continuo — si parte larghi e alti
 * (vista d'insieme, fuori dall'arena), si scende dentro stringendo molto
 * l'inquadratura verso il basso, quasi tra il pubblico. Il raggio cambia
 * tanto apposta: più la camera si muove, più i pilastri ai lati e il
 * pavimento scorrono veloci in primo piano — quella parallasse è l'indizio
 * di profondità più diretto che esista.
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

    const angle = (p - 0.5) * 1.3; // orbita ampia, +-0.65 rad (~75 gradi totali)
    const radius = 18 - p * 12.5; // si entra davvero: da 18 (fuori) a 5.5 (dentro)
    const height = 3.1 - p * 2.0 + Math.sin(p * Math.PI) * 0.35;
    const lookY = 1.7 - p * 0.5;

    tmp.current.set(
      Math.sin(angle) * radius + pointer.x * 0.5,
      height - pointer.y * 0.3,
      Math.cos(angle) * radius
    );
    camera.position.lerp(tmp.current, 1); // gia' smussato da `smooth`, applica diretto
    camera.lookAt(0, lookY, 0);
  });

  return null;
}
