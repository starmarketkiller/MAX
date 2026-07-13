import { useRef } from "react";
import { useFrame } from "@react-three/fiber";

/**
 * L'orso — stilizzato, procedurale, stesso metallo blu freddo del toro con
 * accenti corallo (ribassista) su occhi e artigli. Una zampa alzata in
 * atto di colpire verso il basso — il movimento ribassista.
 */
export default function Bear({ position = [0, 0, 0], scale = 1 }) {
  const group = useRef();
  const paw = useRef();
  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (group.current) {
      group.current.rotation.y = Math.sin(t * 0.16 + 2) * 0.5 + 0.3;
      group.current.position.y = position[1] + Math.sin(t * 0.55 + 1.5) * 0.16;
    }
    if (paw.current) paw.current.rotation.z = -0.6 + Math.sin(t * 0.9) * 0.12;
  });

  const bodyMat = { color: "#a9c0e8", metalness: 0.68, roughness: 0.3, emissive: "#241825", emissiveIntensity: 0.85 };
  const accentMat = { color: "#fb7185", emissive: "#fb7185", emissiveIntensity: 0.6, toneMapped: false };

  return (
    <group ref={group} position={position} scale={scale} rotation={[0, 0.5, 0]}>
      {/* torso, più tozzo e arrotondato del toro */}
      <mesh scale={[1.1, 1.0, 0.95]}>
        <sphereGeometry args={[0.95, 20, 16]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      {/* gobba */}
      <mesh position={[-0.35, 0.75, 0]} scale={[0.55, 0.4, 0.55]}>
        <sphereGeometry args={[0.55, 14, 10]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      {/* testa */}
      <mesh position={[1.05, 0.5, 0]} scale={[0.62, 0.58, 0.58]}>
        <sphereGeometry args={[0.55, 18, 14]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      {/* muso */}
      <mesh position={[1.5, 0.32, 0]} scale={[0.32, 0.26, 0.3]}>
        <sphereGeometry args={[0.4, 12, 10]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      {/* orecchie tonde */}
      <mesh position={[0.78, 0.98, 0.32]} scale={0.16}>
        <sphereGeometry args={[1, 10, 10]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      <mesh position={[0.78, 0.98, -0.32]} scale={0.16}>
        <sphereGeometry args={[1, 10, 10]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      {/* occhi */}
      <mesh position={[1.42, 0.58, 0.2]} scale={0.055}>
        <sphereGeometry args={[1, 8, 8]} />
        <meshStandardMaterial {...accentMat} />
      </mesh>
      <mesh position={[1.42, 0.58, -0.2]} scale={0.055}>
        <sphereGeometry args={[1, 8, 8]} />
        <meshStandardMaterial {...accentMat} />
      </mesh>
      {/* zampa alzata, in atto di colpire verso il basso — il movimento ribassista */}
      <group ref={paw} position={[0.7, 0.1, 0.55]}>
        <mesh rotation={[0, 0, -0.3]}>
          <cylinderGeometry args={[0.16, 0.13, 0.9, 8]} />
          <meshStandardMaterial {...bodyMat} />
        </mesh>
        <mesh position={[0.3, -0.5, 0]} scale={[0.2, 0.14, 0.22]}>
          <sphereGeometry args={[1, 10, 8]} />
          <meshStandardMaterial {...bodyMat} />
        </mesh>
        {[-0.08, 0, 0.08].map((dz, i) => (
          <mesh key={i} position={[0.42, -0.58, dz]} rotation={[0, 0, -0.3]}>
            <coneGeometry args={[0.03, 0.16, 6]} />
            <meshStandardMaterial {...accentMat} />
          </mesh>
        ))}
      </group>
      {/* zampe d'appoggio */}
      <mesh position={[-0.55, -0.85, 0.4]}>
        <cylinderGeometry args={[0.17, 0.14, 0.65, 8]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      <mesh position={[-0.55, -0.85, -0.4]}>
        <cylinderGeometry args={[0.17, 0.14, 0.65, 8]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      <mesh position={[0.5, -0.9, -0.45]}>
        <cylinderGeometry args={[0.16, 0.13, 0.6, 8]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
    </group>
  );
}
