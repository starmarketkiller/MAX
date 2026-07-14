import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { impactBump } from "./impactTiming";

const N = 180;
const ORIGIN = new THREE.Vector3(0, 2.1, -10.5);

function softDiscTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.35, "rgba(255,255,255,.8)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}

/**
 * Scintille di collisione: al momento dell'impatto (impactTiming) esplode
 * una nube di particelle verdi/rosse verso l'utente (asse Z), con
 * gravità e attrito veri — non un semplice fade, un'esplosione con
 * fisica che si dissolve. Riparte da capo ogni volta che si torna sopra
 * la soglia (fronte di salita), così scrollando su e giù l'esplosione si
 * ripete invece di sparare tutte le particelle una volta sola.
 */
export default function ImpactSparks({ progressRef }) {
  const pointsRef = useRef();
  const wasBelow = useRef(true);
  const disc = useMemo(() => softDiscTexture(), []);

  const { positions, velocities, life, colors, maxLife } = useMemo(() => {
    const positions = new Float32Array(N * 3);
    const velocities = new Float32Array(N * 3);
    const life = new Float32Array(N).fill(0);
    const maxLife = new Float32Array(N);
    const colors = new Float32Array(N * 3);
    const green = new THREE.Color("#4ade80");
    const red = new THREE.Color("#f87171");
    for (let i = 0; i < N; i++) {
      const c = Math.random() < 0.5 ? green : red;
      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;
    }
    return { positions, velocities, life, colors, maxLife };
  }, []);

  const emit = () => {
    for (let i = 0; i < N; i++) {
      positions[i * 3] = ORIGIN.x + (Math.random() - 0.5) * 0.6;
      positions[i * 3 + 1] = ORIGIN.y + (Math.random() - 0.5) * 0.6;
      positions[i * 3 + 2] = ORIGIN.z;
      const spread = 3.2;
      velocities[i * 3] = (Math.random() - 0.5) * spread;
      velocities[i * 3 + 1] = Math.random() * 2.6;
      velocities[i * 3 + 2] = Math.random() * 4.5 + 1.5; // verso l'utente (+Z)
      life[i] = 1;
      maxLife[i] = 0.9 + Math.random() * 0.6;
    }
    if (pointsRef.current) {
      pointsRef.current.geometry.attributes.position.needsUpdate = true;
    }
  };

  useFrame((state, delta) => {
    const dt = Math.min(delta, 0.05);
    const raw = Math.min(Math.max(progressRef.current, 0), 1);
    const bump = impactBump(raw);
    const rising = bump > 0.5;
    if (rising && wasBelow.current) emit();
    wasBelow.current = !rising;

    // il PointsMaterial non ha un'opacità per-particella: quando una
    // scintilla esaurisce la vita la si parcheggia fuori dallo schermo
    // invece di provare a dissolverla via colore (che qui è fisso).
    let anyAlive = false;
    for (let i = 0; i < N; i++) {
      if (life[i] <= 0) continue;
      anyAlive = true;
      life[i] -= dt / maxLife[i];
      if (life[i] <= 0) {
        positions[i * 3 + 1] = -9999;
        continue;
      }
      velocities[i * 3 + 1] -= 3.2 * dt; // gravità
      velocities[i * 3] *= 1 - 0.6 * dt; // attrito
      velocities[i * 3 + 1] *= 1 - 0.15 * dt;
      velocities[i * 3 + 2] *= 1 - 0.6 * dt;
      positions[i * 3] += velocities[i * 3] * dt;
      positions[i * 3 + 1] += velocities[i * 3 + 1] * dt;
      positions[i * 3 + 2] += velocities[i * 3 + 2] * dt;
    }
    if (anyAlive && pointsRef.current) {
      pointsRef.current.geometry.attributes.position.needsUpdate = true;
      pointsRef.current.geometry.computeBoundingSphere();
    }
    if (pointsRef.current) {
      pointsRef.current.material.opacity = 0.85;
    }
  });

  return (
    <points ref={pointsRef} frustumCulled={false}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={N} array={positions} itemSize={3} />
        <bufferAttribute attach="attributes-color" count={N} array={colors} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial
        size={0.16}
        map={disc}
        vertexColors
        transparent
        opacity={0.85}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}
