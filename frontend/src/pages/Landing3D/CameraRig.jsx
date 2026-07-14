import { useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

/**
 * Un movimento di camera lento e continuo lungo tutta la pagina — non un
 * percorso a tappe come nella versione precedente, solo un dolly-in +
 * lieve orbita che dà profondità reale allo schermo: si parte più
 * larghi/lontani, si arriva più stretti/vicini al finale. Smoothing in
 * tempo reale (non per-frame) cosi' resta fluido a qualunque framerate.
 */
export default function CameraRig({ progressRef }) {
  const { camera } = useThree();
  const smooth = useRef(0);
  const tmp = useRef(new THREE.Vector3());

  useFrame((state, delta) => {
    const dt = Math.min(delta, 0.1);
    const k = 1 - Math.exp(-dt * 3.5);
    smooth.current += (Math.min(Math.max(progressRef.current, 0), 1) - smooth.current) * k;
    const p = smooth.current;

    const angle = (p - 0.5) * 0.5; // orbita leggera, +-0.25 rad
    const radius = 11 - p * 3.5; // dolly-in: parte a 11, arriva a 7.5
    const height = 1.5 + Math.sin(p * Math.PI) * 0.6;

    tmp.current.set(Math.sin(angle) * radius, height, Math.cos(angle) * radius);
    camera.position.lerp(tmp.current, 1); // gia' smussato da `smooth`, applica diretto
    camera.lookAt(0, 1.5, 0);
  });

  return null;
}
