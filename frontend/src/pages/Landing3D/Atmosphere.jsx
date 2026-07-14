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

/**
 * Il pavimento che riceve l'ombra dello schermo (profondità vera, non
 * finta) + un pulviscolo di particelle lente — l'atmosfera che rende lo
 * spazio 3D leggibile come spazio, non solo lo schermo sospeso nel vuoto.
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

  useFrame((state) => {
    if (dustRef.current) dustRef.current.rotation.y = state.clock.elapsedTime * 0.01;
  });

  return (
    <>
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
