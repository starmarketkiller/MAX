import { Suspense } from "react";
import CameraRig from "./CameraRig";
import Diorama from "./Diorama";
import Atmosphere from "./Atmosphere";

/**
 * Contenuto del Canvas R3F: spazio nero vero (non un fondale colorato),
 * dentro cui vivono elementi 3D reali — il toro, l'orso, il loro scontro,
 * il re, l'arena lontana (Diorama) — più pavimento riflettente, pulviscolo
 * e pilastri (Atmosphere) per profondità. Niente più video: solo luce,
 * ombre e oggetti veri a distanze diverse. Separato dalla UI HTML (overlay
 * assoluto in index.jsx) — comunicano solo via progressRef, letto ad ogni
 * frame senza mai forzare un re-render React.
 */
export default function Scene({ progressRef }) {
  return (
    <>
      <color attach="background" args={["#000000"]} />
      <fogExp2 attach="fog" args={["#010103", 0.016]} />

      <ambientLight color="#0c1830" intensity={0.55} />
      <directionalLight
        color="#9fd8ff"
        intensity={0.9}
        position={[6, 9, 4]}
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-camera-near={1}
        shadow-camera-far={40}
        shadow-camera-left={-16}
        shadow-camera-right={16}
        shadow-camera-top={16}
        shadow-camera-bottom={-16}
      />
      <directionalLight color="#8b6ff0" intensity={0.35} position={[-8, 3, -4]} />
      <pointLight color="#4ade80" intensity={12} distance={14} position={[-6.6, 2, -7]} />
      <pointLight color="#f87171" intensity={12} distance={14} position={[6.6, 2, -7]} />
      <pointLight color="#fbbf24" intensity={16} distance={16} position={[0, 3, -18]} />

      <Suspense fallback={null}>
        <Diorama progressRef={progressRef} />
      </Suspense>
      <Atmosphere />
      <CameraRig progressRef={progressRef} />
    </>
  );
}
