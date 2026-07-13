import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { QUANTUM_CORE_POSITION } from "./content";

const DISK_VS = `
  varying vec2 vPos;
  void main() {
    vPos = position.xy;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

// Disco di accrescimento procedurale: gradiente radiale ciano->violetto,
// una trama a spirale (angolo + raggio) che ruota, bordi che sfumano a zero
// sia verso il buco nero (interno) sia verso il bordo esterno.
const DISK_FS = `
  varying vec2 vPos;
  uniform float uT;
  void main() {
    float r = length(vPos) / 6.5;
    float rN = clamp((r - 0.31) / (1.0 - 0.31), 0.0, 1.0);
    float a = atan(vPos.y, vPos.x);
    float swirl = sin(a * 6.0 - uT * 2.2 + r * 9.0) * 0.5 + 0.5;
    float band = smoothstep(0.0, 0.18, rN) * (1.0 - smoothstep(0.55, 1.0, rN));
    vec3 col = mix(vec3(0.9, 0.98, 1.0), vec3(0.16, 0.86, 1.0), rN);
    col = mix(col, vec3(0.56, 0.36, 0.98), smoothstep(0.5, 1.0, rN));
    col += swirl * 0.4;
    float alpha = band * (0.65 + swirl * 0.5);
    gl_FragColor = vec4(col, alpha);
  }
`;

/**
 * Il finale: un "Core Quantico" — buco nero pulsante con disco di
 * accrescimento luminoso. La camera (in CameraRig) frena e si ferma davanti,
 * lungo l'ultimo tratto della curva.
 */
export default function QuantumCore() {
  const diskRef = useRef();
  const diskMatRef = useRef();
  const lightRef = useRef();
  const haloRef = useRef();

  useFrame((state, dt) => {
    const t = state.clock.elapsedTime;
    if (diskRef.current) diskRef.current.rotation.z += dt * 0.35;
    if (diskMatRef.current) diskMatRef.current.uniforms.uT.value += dt;
    if (lightRef.current) lightRef.current.intensity = 42 + Math.sin(t * 1.6) * 16;
    if (haloRef.current) haloRef.current.material.opacity = 0.14 + Math.sin(t * 1.2) * 0.05;
  });

  return (
    <group position={QUANTUM_CORE_POSITION}>
      <mesh>
        <sphereGeometry args={[1.5, 32, 32]} />
        <meshBasicMaterial color="#000005" />
      </mesh>
      <mesh ref={haloRef}>
        <sphereGeometry args={[1.64, 32, 32]} />
        <meshBasicMaterial color="#38e6ff" transparent opacity={0.18} blending={THREE.AdditiveBlending} side={THREE.BackSide} depthWrite={false} />
      </mesh>
      <mesh ref={diskRef} rotation={[Math.PI * 0.34, 0, 0.15]}>
        <ringGeometry args={[2.0, 6.5, 96]} />
        <shaderMaterial
          ref={diskMatRef}
          vertexShader={DISK_VS}
          fragmentShader={DISK_FS}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          side={THREE.DoubleSide}
          uniforms={{ uT: { value: 0 } }}
        />
      </mesh>
      <pointLight ref={lightRef} color="#38e6ff" intensity={55} distance={60} />
    </group>
  );
}
