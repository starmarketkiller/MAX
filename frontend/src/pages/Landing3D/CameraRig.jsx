import { useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { CAMERA_WAYPOINTS } from "./content";

// Lineare fino all'85%, poi ease-out cubica: la camera "frena" solo
// nell'ultimo tratto, davanti al Core Quantico — non durante tutto il viaggio.
const approach = (p) => {
  if (p < 0.85) return (p / 0.85) * 0.85;
  const t = (p - 0.85) / 0.15;
  return 0.85 + (1 - Math.pow(1 - t, 3)) * 0.15;
};

/**
 * Camera "legata" allo scroll: `progressRef.current` è aggiornato da un
 * GSAP ScrollTrigger nel componente padre (index.jsx), fuori dal Canvas.
 * Qui, ad ogni frame, la posizione/lookAt vengono interpolate lungo la
 * curva della camera in base a quel valore — nessun re-render React coinvolto.
 */
export default function CameraRig({ progressRef, mouseRef }) {
  const { camera } = useThree();
  const camPath = useMemo(
    () => new THREE.CatmullRomCurve3(CAMERA_WAYPOINTS.map((w) => new THREE.Vector3(...w.pos))),
    []
  );
  const lookPath = useMemo(
    () => new THREE.CatmullRomCurve3(CAMERA_WAYPOINTS.map((w) => new THREE.Vector3(...w.look))),
    []
  );
  const prog = useRef(0);
  const cmx = useRef(0);
  const cmy = useRef(0);
  const tmpPos = useMemo(() => new THREE.Vector3(), []);
  const tmpLook = useMemo(() => new THREE.Vector3(), []);

  useFrame((_, delta) => {
    // Smoothing esponenziale in tempo reale (non per-frame): a basso
    // framerate un fattore fisso per-frame farebbe inseguire la camera per
    // secondi interi invece che in una frazione di secondo percepita.
    const dt = Math.min(delta, 0.1);
    const kProg = 1 - Math.exp(-dt * 5.5);
    const kMouse = 1 - Math.exp(-dt * 4.5);
    const target = progressRef.current;
    prog.current += (target - prog.current) * kProg;
    const mx = mouseRef.current.x;
    const my = mouseRef.current.y;
    cmx.current += (mx - cmx.current) * kMouse;
    cmy.current += (my - cmy.current) * kMouse;

    const p = approach(Math.min(Math.max(prog.current, 0), 1));
    camPath.getPointAt(p, tmpPos);
    lookPath.getPointAt(Math.min(p + 0.02, 1), tmpLook);
    camera.position.set(tmpPos.x + cmx.current * 5, tmpPos.y - cmy.current * 3.5, tmpPos.z);
    camera.lookAt(tmpLook.x + cmx.current * 2, tmpLook.y - cmy.current * 1.5, tmpLook.z);
  });

  return null;
}
