import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { CAMERA_WAYPOINTS } from "./content";

const VS = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

// vUv.x corre lungo il percorso (TubeGeometry), vUv.y intorno alla
// circonferenza — un impulso di energia scorre lungo la fibra verso il Core.
const FS = `
  varying vec2 vUv;
  uniform float uT;
  uniform vec3 uColorA;
  uniform vec3 uColorB;
  void main() {
    float flow = fract(vUv.x * 5.0 - uT * 0.55);
    float pulse = smoothstep(0.0, 0.18, flow) * smoothstep(0.55, 0.18, flow);
    vec3 base = mix(uColorA, uColorB, vUv.x);
    float edge = pow(sin(vUv.y * 3.14159), 1.6);
    vec3 col = base * (0.4 + edge * 0.6) + vec3(pulse) * 0.9;
    gl_FragColor = vec4(col, 0.55 + pulse * 0.4);
  }
`;

function offsetCurve(basePts, dx, dy, samples = 120) {
  const curve = new THREE.CatmullRomCurve3(basePts);
  const pts = [];
  for (let i = 0; i <= samples; i++) {
    const p = curve.getPointAt(i / samples);
    pts.push(new THREE.Vector3(p.x + dx, p.y + dy, p.z));
  }
  return new THREE.CatmullRomCurve3(pts);
}

/**
 * Il nastro olografico che guida la telecamera — sostituisce la vecchia
 * corridoio di candlestick. Una fibra centrale luminosa (shader procedurale,
 * impulso che scorre) + un alone volumetrico + due corsie parallele
 * (verde/viola) che mantengono il motivo "corsie separate / hedge".
 */
export default function LightTrail() {
  const matRef = useRef();

  const { spineGeo, sheathGeo, laneAGeo, laneBGeo } = useMemo(() => {
    const basePts = CAMERA_WAYPOINTS.map((w) => new THREE.Vector3(w.pos[0] * 0.5, w.pos[1] - 2.4, w.pos[2]));
    const spine = new THREE.CatmullRomCurve3(basePts);
    const spineGeo = new THREE.TubeGeometry(spine, 300, 0.09, 12, false);
    const sheathGeo = new THREE.TubeGeometry(spine, 300, 0.3, 12, false);
    const laneA = offsetCurve(basePts, -1.7, -0.25);
    const laneB = offsetCurve(basePts, 1.7, 0.35);
    const laneAGeo = new THREE.TubeGeometry(laneA, 160, 0.045, 8, false);
    const laneBGeo = new THREE.TubeGeometry(laneB, 160, 0.045, 8, false);
    return { spineGeo, sheathGeo, laneAGeo, laneBGeo };
  }, []);

  useFrame((_, dt) => {
    if (matRef.current) matRef.current.uniforms.uT.value += dt;
  });

  return (
    <group>
      <mesh geometry={spineGeo}>
        <shaderMaterial
          ref={matRef}
          vertexShader={VS}
          fragmentShader={FS}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          uniforms={{
            uT: { value: 0 },
            uColorA: { value: new THREE.Color("#38e6ff") },
            uColorB: { value: new THREE.Color("#8b6ff0") },
          }}
        />
      </mesh>
      <mesh geometry={sheathGeo}>
        <meshBasicMaterial
          color="#38bdf8"
          transparent
          opacity={0.07}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          side={THREE.DoubleSide}
        />
      </mesh>
      <mesh geometry={laneAGeo}>
        <meshBasicMaterial color="#2ee88f" transparent opacity={0.6} blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
      <mesh geometry={laneBGeo}>
        <meshBasicMaterial color="#8b6ff0" transparent opacity={0.6} blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
    </group>
  );
}
