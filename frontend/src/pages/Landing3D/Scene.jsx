import { Suspense, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import CameraRig from "./CameraRig";
import Diorama from "./Diorama";
import Atmosphere from "./Atmosphere";
import ImpactSparks from "./ImpactSparks";
import Shockwave from "./Shockwave";
import CinematicEffects from "./CinematicEffects";
import useDeviceTilt from "./useDeviceTilt";

/**
 * Mouse (desktop) + giroscopio (mobile, useDeviceTilt) uniti in un unico
 * segnale smussato — la "vita" dello spazio 4D: ogni livello (Diorama)
 * applica la propria intensità, la camera il proprio micro-look-around.
 * Un solo smoothing condiviso invece di uno per consumatore, per non
 * avere jitter relativo tra camera e livelli.
 */
function ParallaxSync({ tilt, parallaxRef }) {
  const { pointer } = useThree();
  useFrame((state, delta) => {
    const k = 1 - Math.exp(-Math.min(delta, 0.1) * 5);
    const targetX = pointer.x + tilt.current.x;
    const targetY = pointer.y + tilt.current.y;
    parallaxRef.current.x += (targetX - parallaxRef.current.x) * k;
    parallaxRef.current.y += (targetY - parallaxRef.current.y) * k;
  });
  return null;
}

/**
 * Contenuto del Canvas R3F: spazio nero vero (non un fondale colorato),
 * dentro cui vivono elementi 3D reali — il toro, l'orso, il loro scontro,
 * il re, l'arena lontana (Diorama) — più pavimento riflettente, pulviscolo
 * e pilastri (Atmosphere), scintille d'impatto e onda d'urto per
 * l'impatto. Niente più video: solo luce, ombre e oggetti veri a
 * distanze diverse. Separato dalla UI HTML (overlay assoluto in
 * index.jsx) — comunicano solo via progressRef, letto ad ogni frame
 * senza mai forzare un re-render React.
 */
export default function Scene({ progressRef }) {
  const tilt = useDeviceTilt();
  const parallaxRef = useRef({ x: 0, y: 0 });

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
      <pointLight color="#4ade80" intensity={12} distance={14} position={[-5.6, 2, -9]} />
      <pointLight color="#f87171" intensity={12} distance={14} position={[5.6, 2, -9]} />
      <pointLight color="#fbbf24" intensity={16} distance={16} position={[0, 3, -18]} />

      <ParallaxSync tilt={tilt} parallaxRef={parallaxRef} />

      <Suspense fallback={null}>
        <Diorama progressRef={progressRef} parallaxRef={parallaxRef} />
      </Suspense>
      <Atmosphere />
      <ImpactSparks progressRef={progressRef} />
      <Shockwave progressRef={progressRef} />
      <CameraRig progressRef={progressRef} parallaxRef={parallaxRef} />
      <CinematicEffects />
    </>
  );
}
