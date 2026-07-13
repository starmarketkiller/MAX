import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const BARS = 12;

/**
 * Un istogramma di volumi — barre verticali di altezza variabile, come sotto
 * un grafico a candele reale. Pulsano piano, indipendenti l'una dall'altra.
 */
export default function VolumeHistogram({ position = [0, 0, 0], seed = 1 }) {
  const group = useRef();
  const heights = useMemo(() => {
    let s = seed * 7919;
    const rnd = () => {
      s = (s * 9301 + 49297) % 233280;
      return s / 233280;
    };
    return Array.from({ length: BARS }, () => 0.3 + rnd() * 1.9);
  }, [seed]);

  useFrame((state) => {
    if (!group.current) return;
    const t = state.clock.elapsedTime;
    group.current.children.forEach((bar, i) => {
      const s = 0.85 + Math.sin(t * 0.8 + i * 0.7) * 0.15;
      bar.scale.y = s;
    });
  });

  return (
    <group position={position}>
      <group ref={group}>
        {heights.map((h, i) => (
          <mesh key={i} position={[(i - BARS / 2) * 0.34, h / 2, 0]}>
            <boxGeometry args={[0.22, h, 0.22]} />
            <meshStandardMaterial
              color="#38bdf8"
              emissive="#0d3a5a"
              emissiveIntensity={0.5 + (h / 2.2) * 0.6}
              metalness={0.4}
              roughness={0.4}
              transparent
              opacity={0.85}
            />
          </mesh>
        ))}
      </group>
      <mesh position={[0, -0.02, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[BARS * 0.34 + 0.3, 0.02]} />
        <meshBasicMaterial color="#38bdf8" transparent opacity={0.4} blending={THREE.AdditiveBlending} />
      </mesh>
    </group>
  );
}
