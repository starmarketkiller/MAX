import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Billboard } from "@react-three/drei";
import * as THREE from "three";
import { impactBump } from "./impactTiming";

const VERTEX = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const FRAGMENT = /* glsl */ `
  uniform float uProgress;
  uniform vec3 uColor;
  varying vec2 vUv;
  void main() {
    vec2 c = vUv - 0.5;
    float d = length(c) * 2.0;
    float radius = uProgress * 1.05;
    float width = 0.1 + uProgress * 0.08;
    float ring = smoothstep(radius - width, radius, d) * (1.0 - smoothstep(radius, radius + width, d));
    // a radius~0 il "ring" collassa in un disco pieno al centro (d=0):
    // senza questo fattore, a riposo (uProgress=0) l'onda d'urto sarebbe
    // comunque un cerchio bianco opaco piazzato esattamente davanti al re.
    float appear = smoothstep(0.0, 0.05, uProgress);
    float fade = 1.0 - smoothstep(0.55, 1.0, uProgress);
    gl_FragColor = vec4(uColor, ring * appear * fade * 0.9);
  }
`;

/**
 * L'onda d'urto al momento dell'impatto: un anello che si espande dal
 * punto dello scontro e si dissolve — non una vera distorsione dello
 * schermo (richiederebbe una pipeline di post-processing a parte), ma
 * un effetto shader autonomo, leggero, che legge lo stesso impulso
 * (impactTiming) di scontro/scintille/vibrazione, quindi resta sempre
 * sincronizzato con loro.
 */
export default function Shockwave({ progressRef }) {
  const matRef = useRef();
  const smooth = useRef(0);

  const uniforms = useMemo(
    () => ({
      uProgress: { value: 0 },
      uColor: { value: new THREE.Color("#eafcff") },
    }),
    []
  );

  useFrame((state, delta) => {
    const dt = Math.min(delta, 0.1);
    const k = 1 - Math.exp(-dt * 6);
    const raw = Math.min(Math.max(progressRef.current, 0), 1);
    const target = impactBump(raw);
    smooth.current += (target - smooth.current) * k;
    if (matRef.current) matRef.current.uniforms.uProgress.value = smooth.current;
  });

  return (
    <Billboard position={[0, 2.1, -10.5]}>
      <mesh renderOrder={5}>
        <planeGeometry args={[16, 16]} />
        <shaderMaterial
          ref={matRef}
          vertexShader={VERTEX}
          fragmentShader={FRAGMENT}
          uniforms={uniforms}
          transparent
          depthWrite={false}
          depthTest
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </Billboard>
  );
}
