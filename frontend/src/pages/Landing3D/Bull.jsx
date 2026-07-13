import { useRef } from "react";
import { useFrame } from "@react-three/fiber";

/**
 * Il toro — stilizzato, procedurale (icosaedri sfaccettati, nessun asset
 * esterno), in metallo blu freddo con accenti mint (rialzista) sulle corna
 * e sugli occhi. Sfaccettato come il cristallo dell'hero, non liscio come
 * una sfera — altrimenti a grandezza piena legge come un palloncino
 * gonfiato, non un animale. Fluttua e ruota piano.
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

  const bodyMat = { color: "#a9c0e8", metalness: 0.65, roughness: 0.32, emissive: "#1c3a68", emissiveIntensity: 0.85, flatShading: true };
  const accentMat = { color: "#2ee88f", emissive: "#2ee88f", emissiveIntensity: 0.6, toneMapped: false, flatShading: true };

  return (
    <group ref={group} position={position} scale={scale} rotation={[0, -0.4, 0]}>
      {/* torso — allungato, non tondo: un icosaedro sfaccettato, non una sfera */}
      <mesh scale={[1.55, 0.68, 0.72]}>
        <icosahedronGeometry args={[0.9, 1]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      {/* testa */}
      <mesh position={[1.2, 0.3, 0]} scale={[0.7, 0.55, 0.55]}>
        <icosahedronGeometry args={[0.55, 1]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      {/* muso */}
      <mesh position={[1.68, 0.14, 0]} scale={[0.36, 0.26, 0.32]}>
        <icosahedronGeometry args={[0.4, 0]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      {/* corna — curvano verso l'alto e verso l'esterno, il segnale rialzista */}
      <mesh position={[1.28, 0.68, 0.3]} rotation={[0.3, 0, -0.7]}>
        <coneGeometry args={[0.08, 0.8, 6]} />
        <meshStandardMaterial {...accentMat} />
      </mesh>
      <mesh position={[1.28, 0.68, -0.3]} rotation={[-0.3, 0, -0.7]}>
        <coneGeometry args={[0.08, 0.8, 6]} />
        <meshStandardMaterial {...accentMat} />
      </mesh>
      {/* occhi */}
      <mesh position={[1.6, 0.38, 0.2]} scale={0.055}>
        <icosahedronGeometry args={[1, 0]} />
        <meshStandardMaterial {...accentMat} />
      </mesh>
      <mesh position={[1.6, 0.38, -0.2]} scale={0.055}>
        <icosahedronGeometry args={[1, 0]} />
        <meshStandardMaterial {...accentMat} />
      </mesh>
      {/* zampe anteriori — accennate, in posizione di carica, sfaccettate (6 lati) */}
      <mesh position={[0.5, -0.68, 0.36]} rotation={[0, 0, 0.15]}>
        <cylinderGeometry args={[0.12, 0.095, 0.62, 6]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      <mesh position={[0.5, -0.68, -0.36]} rotation={[0, 0, 0.15]}>
        <cylinderGeometry args={[0.12, 0.095, 0.62, 6]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      <mesh position={[-0.58, -0.64, 0.36]}>
        <cylinderGeometry args={[0.13, 0.1, 0.58, 6]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      <mesh position={[-0.58, -0.64, -0.36]}>
        <cylinderGeometry args={[0.13, 0.1, 0.58, 6]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
    </group>
  );
}
