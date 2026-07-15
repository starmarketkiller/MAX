import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { MeshReflectorMaterial } from "@react-three/drei";
import * as THREE from "three";
import { isLowEnd } from "./deviceTier";

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

const PYLON_COLORS = ["#38bdf8", "#8b6ff0", "#22d3ee", "#8b6ff0"];
const FLIGHT_CENTER_Z = -10;

/**
 * Il pavimento che riceve ombre vere (profondità reale, non finta) + un
 * pulviscolo di particelle lente (con linee sottili tra i punti vicini,
 * un effetto "costellazione/rete" calcolato una sola volta al mount, non
 * ad ogni frame) + un anello di pilastri luminosi intorno al percorso di
 * volo — sono loro, scorrendo ai lati mentre la camera avanza, a dare la
 * parallasse più forte: elementi vicini che si muovono più in fretta di
 * quelli lontani è l'indizio di profondità che il cervello legge per
 * primo.
 */
export default function Atmosphere() {
  const dustRef = useRef();
  const disc = useMemo(() => softDiscTexture(), []);
  const { dust, constellation } = useMemo(() => {
    const N = 280;
    const positions = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 26;
      positions[i * 3 + 1] = Math.random() * 10 - 2;
      positions[i * 3 + 2] = FLIGHT_CENTER_Z + (Math.random() - 0.5) * 40;
    }
    // linee tra punti vicini — "costellazione", non una rete neurale
    // ricalcolata ogni frame: le posizioni sono fisse (il gruppo ruota
    // tutto insieme, i punti non si muovono l'uno rispetto all'altro), il
    // confronto tra le coppie si fa una sola volta qui al mount, non nel
    // render loop.
    const maxDist = 3.4;
    const maxDist2 = maxDist * maxDist;
    const lineVerts = [];
    for (let i = 0; i < N; i++) {
      let linked = 0;
      for (let j = i + 1; j < N && linked < 2; j++) {
        const dx = positions[i * 3] - positions[j * 3];
        const dy = positions[i * 3 + 1] - positions[j * 3 + 1];
        const dz = positions[i * 3 + 2] - positions[j * 3 + 2];
        if (dx * dx + dy * dy + dz * dz < maxDist2) {
          lineVerts.push(
            positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2],
            positions[j * 3], positions[j * 3 + 1], positions[j * 3 + 2]
          );
          linked++;
        }
      }
    }
    return { dust: positions, constellation: new Float32Array(lineVerts) };
  }, []);

  const pylons = useMemo(() => {
    // La camera vola quasi in linea retta lungo z (x resta vicino a 0): un
    // anello di pilastri centrato sullo stesso asse la incrocerebbe in due
    // punti esatti. Sfasare gli angoli di mezzo passo e tenere il raggio
    // largo garantisce che il pilastro più vicino resti comunque a
    // distanza di sicurezza (~10 unità) anche nel punto di incrocio.
    const N = 8;
    return Array.from({ length: N }, (_, i) => {
      const angle = ((i + 0.5) / N) * Math.PI * 2;
      const radius = 26 + (i % 3) * 3;
      const height = 5 + (i % 3) * 1.8;
      return {
        pos: [Math.sin(angle) * radius, height / 2 - 2.4, FLIGHT_CENTER_Z + Math.cos(angle) * radius],
        height,
        color: PYLON_COLORS[i % PYLON_COLORS.length],
      };
    });
  }, []);

  useFrame((state) => {
    if (dustRef.current) dustRef.current.rotation.y = state.clock.elapsedTime * 0.008;
  });

  return (
    <>
      {pylons.map((p, i) => (
        <mesh key={i} position={p.pos} castShadow>
          <boxGeometry args={[0.32, p.height, 0.32]} />
          <meshStandardMaterial color="#060d1c" emissive={p.color} emissiveIntensity={0.9} metalness={0.6} roughness={0.35} />
        </mesh>
      ))}
      {/* pavimento riflettente: le luci e i personaggi si specchiano — il
          singolo indizio piu' forte che lo spazio e' davvero tridimensionale.
          Risoluzione ridotta su schermi piccoli per non far scaldare i telefoni. */}
      <mesh position={[0, -2.4, FLIGHT_CENTER_Z]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[70, 70]} />
        {isLowEnd ? (
          <meshStandardMaterial color="#020306" metalness={0.6} roughness={0.4} />
        ) : (
          <MeshReflectorMaterial
            blur={[280, 100]}
            resolution={512}
            mixBlur={1}
            mixStrength={22}
            roughness={0.9}
            depthScale={1}
            minDepthThreshold={0.4}
            maxDepthThreshold={1.3}
            color="#020306"
            metalness={0.6}
            mirror={0.25}
          />
        )}
      </mesh>
      <group ref={dustRef}>
        <points>
          <bufferGeometry>
            <bufferAttribute attach="attributes-position" count={280} array={dust} itemSize={3} />
          </bufferGeometry>
          <pointsMaterial size={0.06} map={disc} color="#8ea6cf" transparent opacity={0.45} depthWrite={false} blending={THREE.AdditiveBlending} />
        </points>
        <lineSegments>
          <bufferGeometry>
            <bufferAttribute attach="attributes-position" count={constellation.length / 3} array={constellation} itemSize={3} />
          </bufferGeometry>
          <lineBasicMaterial color="#4a6f9e" transparent opacity={0.14} depthWrite={false} blending={THREE.AdditiveBlending} />
        </lineSegments>
      </group>
    </>
  );
}
