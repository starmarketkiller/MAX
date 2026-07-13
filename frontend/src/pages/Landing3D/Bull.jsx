import { useRef } from "react";
import { useFrame } from "@react-three/fiber";

/**
 * Il toro — stilizzato, procedurale (sfere/coni, nessun asset esterno),
 * in metallo blu freddo con accenti mint (rialzista) sulle corna e sugli
 * occhi. Fluttua e ruota piano, come gli altri oggetti-simbolo della scena.
 */
export default function Bull({ position = [0, 0, 0], scale = 1 }) {
  const group = useRef();
  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (group.current) {
      group.current.rotation.y = Math.sin(t * 0.18) * 0.5 - 0.3;
      group.current.position.y = position[1] + Math.sin(t * 0.6) * 0.18;
    }
  });

  const bodyMat = { color: "#a9c0e8", metalness: 0.7, roughness: 0.28, emissive: "#1c3a68", emissiveIntensity: 0.85 };
  const accentMat = { color: "#2ee88f", emissive: "#2ee88f", emissiveIntensity: 0.6, toneMapped: false };

  return (
    <group ref={group} position={position} scale={scale} rotation={[0, -0.4, 0]}>
      {/* torso */}
      <mesh scale={[1.35, 0.85, 0.9]}>
        <sphereGeometry args={[0.9, 20, 16]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      {/* testa */}
      <mesh position={[1.15, 0.35, 0]} scale={[0.75, 0.65, 0.65]}>
        <sphereGeometry args={[0.55, 18, 14]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      {/* muso */}
      <mesh position={[1.62, 0.18, 0]} scale={[0.4, 0.32, 0.4]}>
        <sphereGeometry args={[0.4, 14, 10]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      {/* corna — curvano verso l'alto e verso l'esterno, il segnale rialzista */}
      <mesh position={[1.25, 0.75, 0.32]} rotation={[0.3, 0, -0.7]}>
        <coneGeometry args={[0.09, 0.85, 8]} />
        <meshStandardMaterial {...accentMat} />
      </mesh>
      <mesh position={[1.25, 0.75, -0.32]} rotation={[-0.3, 0, -0.7]}>
        <coneGeometry args={[0.09, 0.85, 8]} />
        <meshStandardMaterial {...accentMat} />
      </mesh>
      {/* occhi */}
      <mesh position={[1.55, 0.45, 0.22]} scale={0.06}>
        <sphereGeometry args={[1, 8, 8]} />
        <meshStandardMaterial {...accentMat} />
      </mesh>
      <mesh position={[1.55, 0.45, -0.22]} scale={0.06}>
        <sphereGeometry args={[1, 8, 8]} />
        <meshStandardMaterial {...accentMat} />
      </mesh>
      {/* zampe anteriori — accennate, in posizione di carica */}
      <mesh position={[0.55, -0.85, 0.4]} rotation={[0, 0, 0.15]}>
        <cylinderGeometry args={[0.14, 0.11, 0.75, 8]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      <mesh position={[0.55, -0.85, -0.4]} rotation={[0, 0, 0.15]}>
        <cylinderGeometry args={[0.14, 0.11, 0.75, 8]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      <mesh position={[-0.65, -0.8, 0.4]}>
        <cylinderGeometry args={[0.15, 0.12, 0.7, 8]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      <mesh position={[-0.65, -0.8, -0.4]}>
        <cylinderGeometry args={[0.15, 0.12, 0.7, 8]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
    </group>
  );
}
