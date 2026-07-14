import { useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { sampleCameraPath } from "./cameraPath";

/**
 * Navigazione libera e profonda, a tappe: una posizione macchina dedicata
 * per ognuna delle 6 sezioni (cameraPath.js) — ad ogni scroll ci si
 * avvicina davvero al prossimo elemento (il toro, poi l'orso, poi lo
 * scontro, poi il re), non un'unica dolly generica sull'asse Z. Lo
 * smoothing è sul progresso stesso (non sulla posizione), così il
 * movimento resta continuo e fluido anche quando lo scroll è a scatti,
 * ma ogni piccolo scroll produce comunque uno spostamento visibile.
 *
 * Aggiunge un lieve parallasse sul mouse e un piccolo dondolio organico
 * indipendente dal tempo, per non sembrare mai un binario rigido.
 */
export default function CameraRig({ progressRef }) {
  const { camera, pointer } = useThree();
  const smooth = useRef(0);
  const tmpPos = useRef(new THREE.Vector3());
  const tmpLook = useRef(new THREE.Vector3());

  useFrame((state, delta) => {
    const dt = Math.min(delta, 0.1);
    const k = 1 - Math.exp(-dt * 4.2);
    smooth.current += (Math.min(Math.max(progressRef.current, 0), 1) - smooth.current) * k;
    const { pos, look } = sampleCameraPath(smooth.current);
    const t = state.clock.elapsedTime;

    tmpPos.current.set(
      pos[0] + pointer.x * 0.5 + Math.sin(t * 0.1) * 0.1,
      pos[1] - pointer.y * 0.28,
      pos[2]
    );
    camera.position.lerp(tmpPos.current, 1);
    tmpLook.current.set(look[0], look[1], look[2]);
    camera.lookAt(tmpLook.current);
  });

  return null;
}
