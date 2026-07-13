import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { softDiscTexture } from "./textures";

const PALETTE = [
  [0.22, 0.9, 1],
  [0.55, 0.65, 1],
  [0.9, 0.95, 1],
];

/**
 * Il logo NEXUS (in HTML, sopra) appare da un'esplosione di particelle
 * luminose in 3D: i punti partono dal centro e si espandono verso un guscio
 * sferico irregolare in ~1.8s, poi restano a fluttuare/ruotare piano.
 * Sfuma quando lo scroll si allontana dalla sezione hero.
 */
export default function HeroBurst({ progressRef, count = 700 }) {
  const pointsRef = useRef();
  const matRef = useRef();
  const startT = useRef(null);
  const disc = useMemo(() => softDiscTexture(), []);
  const N = count;

  const { positions, targets, colors } = useMemo(() => {
    const positions = new Float32Array(N * 3);
    const targets = new Float32Array(N * 3);
    const colors = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      const dir = new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).normalize();
      const r = 2.2 + Math.random() * 3.4;
      targets[i * 3] = dir.x * r;
      targets[i * 3 + 1] = dir.y * r * 0.55 + 1.4;
      targets[i * 3 + 2] = dir.z * r * 0.5 + 1.5;
      const c = PALETTE[(Math.random() * PALETTE.length) | 0];
      colors[i * 3] = c[0];
      colors[i * 3 + 1] = c[1];
      colors[i * 3 + 2] = c[2];
    }
    return { positions, targets, colors };
  }, [N]);

  useFrame((state) => {
    if (startT.current === null) startT.current = state.clock.elapsedTime;
    const t = state.clock.elapsedTime - startT.current;
    const e = 1 - Math.pow(1 - Math.min(t / 1.8, 1), 3);
    const posAttr = pointsRef.current.geometry.attributes.position;
    for (let i = 0; i < N; i++) {
      posAttr.array[i * 3] = targets[i * 3] * e;
      posAttr.array[i * 3 + 1] = targets[i * 3 + 1] * e;
      posAttr.array[i * 3 + 2] = targets[i * 3 + 2] * e;
    }
    posAttr.needsUpdate = true;
    pointsRef.current.rotation.y = t * 0.07;
    const fadeP = progressRef.current;
    matRef.current.opacity = Math.max(0, 1 - fadeP * 4.5) * Math.min(1, t / 0.4);
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={N} array={positions} itemSize={3} />
        <bufferAttribute attach="attributes-color" count={N} array={colors} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial
        ref={matRef}
        size={0.22}
        map={disc}
        vertexColors
        transparent
        opacity={1}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
        sizeAttenuation
      />
    </points>
  );
}
