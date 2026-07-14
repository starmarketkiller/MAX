import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { MeshReflectorMaterial } from "@react-three/drei";
import * as THREE from "three";

const isLowEnd = typeof window !== "undefined" && window.innerWidth < 820;

function softDiscTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.3, "rgba(255,255,255,.7)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}

const PYLON_COLORS = ["#38bdf8", "#8b6ff0", "#38bdf8", "#22d3ee", "#8b6ff0", "#38bdf8", "#22d3ee", "#8b6ff0"];

/**
 * Il pavimento che riceve ombre vere (profondità reale, non finta) + un
 * pulviscolo di particelle lente + un anello di pilastri luminosi intorno
 * all'arena — sono loro, scorrendo ai lati mentre la camera avanza, a dare
 * la parallasse più forte: elementi vicini che si muovono più in fretta di
 * quelli lontani è l'indizio di profondità che il cervello legge per primo.
 */
export default function Atmosphere() {
  const dustRef = useRef();
  const disc = useMemo(() => softDiscTexture(), []);
  const dust = useMemo(() => {
    const N = 260;
    const positions = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 22;
      positions[i * 3 + 1] = Math.random() * 10 - 2;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 14 + 2;
    }
    return positions;
  }, []);

  const pylons = useMemo(() => {
    // Il raggio della camera va da 5.5 (dentro) a 18 (fuori): i pilastri
    // stanno ben oltre 18 così la camera non ci passa mai vicino — altrimenti
    // a certi angoli di scroll uno di loro riempie tutto lo schermo.
    const N = 12;
    return Array.from({ length: N }, (_, i) => {
      const angle = (i / N) * Math.PI * 2;
      const radius = 25 + (i % 3) * 3.5;
      const height = 4.5 + (i % 3) * 1.6;
      return {
        pos: [Math.sin(angle) * radius, height / 2 - 2.4, Math.cos(angle) * radius],
        height,
        color: PYLON_COLORS[i % PYLON_COLORS.length],
      };
    });
  }, []);

  useFrame((state) => {
    if (dustRef.current) dustRef.current.rotation.y = state.clock.elapsedTime * 0.01;
  });

  return (
    <>
      {pylons.map((p, i) => (
        <mesh key={i} position={p.pos} castShadow>
          <boxGeometry args={[0.32, p.height, 0.32]} />
          <meshStandardMaterial color="#0a1830" emissive={p.color} emissiveIntensity={0.9} metalness={0.6} roughness={0.35} />
        </mesh>
      ))}
      {/* pavimento riflettente: le luci e lo schermo si specchiano — il
          singolo indizio piu' forte che lo spazio e' davvero tridimensionale,
          non un fondale piatto dietro il video. Risoluzione ridotta su
          schermi piccoli per non far scaldare i telefoni. */}
      <mesh position={[0, -2.4, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[60, 60]} />
        {isLowEnd ? (
          <meshStandardMaterial color="#050a16" metalness={0.6} roughness={0.4} />
        ) : (
          <MeshReflectorMaterial
            blur={[280, 100]}
            resolution={512}
            mixBlur={1}
            mixStrength={28}
            roughness={0.85}
            depthScale={1}
            minDepthThreshold={0.4}
            maxDepthThreshold={1.3}
            color="#050a16"
            metalness={0.65}
            mirror={0.35}
          />
        )}
      </mesh>
      <points ref={dustRef} position={[0, 0, 0]}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" count={260} array={dust} itemSize={3} />
        </bufferGeometry>
        <pointsMaterial size={0.06} map={disc} color="#8ea6cf" transparent opacity={0.5} depthWrite={false} blending={THREE.AdditiveBlending} />
      </points>
    </>
  );
}
