import { useRef } from "react";
import { useFrame } from "@react-three/fiber";

/**
 * L'orso — stilizzato, procedurale, stesso metallo blu freddo del toro con
 * accenti corallo (ribassista) su occhi e artigli. Sfaccettato come il
 * cristallo dell'hero (icosaedri, non sfere lisce) — altrimenti a
 * grandezza piena legge come un palloncino gonfiato, non un animale.
 * Una zampa alzata in atto di colpire verso il basso — il movimento
 * ribassista.
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

  const bodyMat = { color: "#a9c0e8", metalness: 0.62, roughness: 0.34, emissive: "#241825", emissiveIntensity: 0.85, flatShading: true };
  const accentMat = { color: "#fb7185", emissive: "#fb7185", emissiveIntensity: 0.6, toneMapped: false, flatShading: true };

  return (
    <group ref={group} position={position} scale={scale} rotation={[0, 0.5, 0]}>
      {/* torso, più tozzo del toro ma comunque sfaccettato, non tondo */}
      <mesh scale={[1.0, 0.82, 0.8]}>
        <icosahedronGeometry args={[0.95, 1]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      {/* gobba */}
      <mesh position={[-0.35, 0.62, 0]} scale={[0.5, 0.32, 0.5]}>
        <icosahedronGeometry args={[0.55, 0]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      {/* testa */}
      <mesh position={[1.05, 0.4, 0]} scale={[0.58, 0.5, 0.5]}>
        <icosahedronGeometry args={[0.55, 1]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      {/* muso */}
      <mesh position={[1.48, 0.26, 0]} scale={[0.3, 0.22, 0.26]}>
        <icosahedronGeometry args={[0.4, 0]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      {/* orecchie */}
      <mesh position={[0.76, 0.78, 0.3]} scale={0.15}>
        <icosahedronGeometry args={[1, 0]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      <mesh position={[0.76, 0.78, -0.3]} scale={0.15}>
        <icosahedronGeometry args={[1, 0]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      {/* occhi */}
      <mesh position={[1.4, 0.46, 0.18]} scale={0.052}>
        <icosahedronGeometry args={[1, 0]} />
        <meshStandardMaterial {...accentMat} />
      </mesh>
      <mesh position={[1.4, 0.46, -0.18]} scale={0.052}>
        <icosahedronGeometry args={[1, 0]} />
        <meshStandardMaterial {...accentMat} />
      </mesh>
      {/* zampa alzata, in atto di colpire verso il basso — il movimento ribassista */}
      <group ref={paw} position={[0.66, 0.0, 0.48]}>
        <mesh rotation={[0, 0, -0.3]}>
          <cylinderGeometry args={[0.14, 0.11, 0.78, 6]} />
          <meshStandardMaterial {...bodyMat} />
        </mesh>
        <mesh position={[0.26, -0.44, 0]} scale={[0.18, 0.12, 0.2]}>
          <icosahedronGeometry args={[1, 0]} />
          <meshStandardMaterial {...bodyMat} />
        </mesh>
        {[-0.08, 0, 0.08].map((dz, i) => (
          <mesh key={i} position={[0.37, -0.5, dz]} rotation={[0, 0, -0.3]}>
            <coneGeometry args={[0.03, 0.14, 5]} />
            <meshStandardMaterial {...accentMat} />
          </mesh>
        ))}
      </group>
      {/* zampe d'appoggio, sfaccettate (6 lati) */}
      <mesh position={[-0.48, -0.72, 0.34]}>
        <cylinderGeometry args={[0.15, 0.12, 0.56, 6]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      <mesh position={[-0.48, -0.72, -0.34]}>
        <cylinderGeometry args={[0.15, 0.12, 0.56, 6]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
      <mesh position={[0.44, -0.76, -0.38]}>
        <cylinderGeometry args={[0.14, 0.11, 0.5, 6]} />
        <meshStandardMaterial {...bodyMat} />
      </mesh>
    </group>
  );
}
