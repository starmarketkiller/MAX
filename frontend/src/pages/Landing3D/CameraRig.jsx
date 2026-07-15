import { useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { sampleCameraPath } from "./cameraPath";
import { impactBump } from "./impactTiming";

/**
 * Navigazione libera e profonda, a tappe: una posizione macchina dedicata
 * per ognuna delle 6 sezioni (cameraPath.js) — la camera gira intorno alla
 * N di NEXUS (NexusLogo) da angoli diversi e ci vola attraverso verso il
 * finale, non un'unica dolly generica sull'asse Z. Lo smoothing è sul
 * progresso stesso (non sulla posizione), così il movimento resta
 * continuo e fluido anche quando lo scroll è a scatti, ma ogni piccolo
 * scroll produce comunque uno spostamento visibile.
 *
 * `parallaxRef` (mouse+giroscopio, condiviso con NexusLogo tramite Scene)
 * aggiunge un micro-look-around indipendente dallo scroll — muovere il
 * mouse o inclinare il telefono sposta leggermente il punto di vista.
 *
 * Lo smoothing è una vera molla (posizione + velocità), non un semplice
 * decadimento esponenziale: appena la camera arriva a una tappa la
 * supera di un pelo e torna indietro da sola, un piccolo rimbalzo
 * elastico invece di fermarsi di colpo — sottosmorzata quel poco che
 * basta per sentirsi "fisica", non abbastanza da oscillare a lungo o
 * risultare fastidiosa.
 *
 * Al culmine dell'attraversamento della N (impactBump) fa vibrare il
 * telefono una sola volta (Navigator.vibrate) — un piccolo riscontro
 * fisico del passaggio.
 */
export default function CameraRig({ progressRef, parallaxRef }) {
  const { camera } = useThree();
  const smooth = useRef(0);
  const smoothVel = useRef(0);
  const tmpPos = useRef(new THREE.Vector3());
  const tmpLook = useRef(new THREE.Vector3());
  const vibrated = useRef(false);

  useFrame((state, delta) => {
    const dt = Math.min(delta, 0.1);
    const target = Math.min(Math.max(progressRef.current, 0), 1);
    const stiffness = 34;
    const damping = 9.6;
    const accel = (target - smooth.current) * stiffness - smoothVel.current * damping;
    smoothVel.current += accel * dt;
    smooth.current += smoothVel.current * dt;
    const { pos, look } = sampleCameraPath(smooth.current);
    const t = state.clock.elapsedTime;
    const px = parallaxRef ? parallaxRef.current.x : 0;
    const py = parallaxRef ? parallaxRef.current.y : 0;

    tmpPos.current.set(
      pos[0] + px * 0.55 + Math.sin(t * 0.1) * 0.1,
      pos[1] - py * 0.3,
      pos[2]
    );
    camera.position.lerp(tmpPos.current, 1);
    tmpLook.current.set(look[0] + px * 0.9, look[1] - py * 0.5, look[2]);
    camera.lookAt(tmpLook.current);

    const bump = impactBump(smooth.current);
    if (bump > 0.92 && !vibrated.current) {
      vibrated.current = true;
      if (typeof navigator !== "undefined" && navigator.vibrate) navigator.vibrate(50);
    } else if (bump < 0.4) {
      vibrated.current = false;
    }
  });

  return null;
}
