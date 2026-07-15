import { Suspense, useEffect, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
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
const BASE_FOV = 45;
const REF_ASPECT = 1.85;
const HALF_BASE_FOV_TAN = Math.tan((BASE_FOV * Math.PI) / 360);
// tan(metà del fov orizzontale) alla aspect di riferimento — resta fisso,
// è il "tetto" di larghezza inquadrata che non vogliamo mai superare.
const HALF_REF_HFOV_TAN = HALF_BASE_FOV_TAN * REF_ASPECT;

/**
 * three.js fissa il fov VERTICALE e lascia che quello orizzontale cresca con
 * l'aspect ratio — su un telefono ruotato in orizzontale (aspect > 2) questo
 * apre un campo visivo orizzontale enorme, molto più largo di quanto i
 * fondali/elementi della scena siano stati pensati per coprire: il risultato
 * è il nero visibile ai lati anche se il canvas stesso è a schermo intero.
 * Oltre REF_ASPECT (più largo di un 16:9 desktop) si riduce il fov verticale
 * quel poco che serve a tenere il fov orizzontale sotto lo stesso tetto che
 * già vale su desktop — sotto quella soglia il comportamento resta
 * identico a prima (fov=45 fisso, nessuna delle inquadrature già tarate
 * cambia).
 */
function ResponsiveFov() {
  const { camera, size } = useThree();
  useEffect(() => {
    if (!size.height) return;
    const aspect = size.width / size.height;
    let fov = BASE_FOV;
    if (aspect > REF_ASPECT) {
      fov = (2 * Math.atan(HALF_REF_HFOV_TAN / aspect) * 180) / Math.PI;
    }
    camera.fov = fov;
    camera.aspect = aspect;
    camera.updateProjectionMatrix();
  }, [size, camera]);
  return null;
}

/**
 * La "fonte di luce virtuale legata al mouse" per le normal map (Cutout con
 * `normalMapUrl`): non è ferma nel mondo — sta sempre a distanza fissa
 * davanti alla camera, spostata a sinistra/destra/su/giù dal mouse, come
 * una torcia tenuta leggermente scostata dall'occhio. Così muscoli e
 * armatura reagiscono con ombre e riflessi reali indipendentemente da dove
 * si trova la camera lungo il percorso — non serve una luce diversa per
 * ogni tappa.
 */
function MouseLight({ parallaxRef }) {
  const ref = useRef();
  const { camera } = useThree();
  const tmp = useRef(new THREE.Vector3());

  useFrame(() => {
    if (!ref.current) return;
    const px = parallaxRef.current.x;
    const py = parallaxRef.current.y;
    tmp.current.set(px * 5.5, -py * 3.5 + 1.4, -3.2);
    tmp.current.applyMatrix4(camera.matrixWorld);
    ref.current.position.copy(tmp.current);
  });

  return <pointLight ref={ref} color="#dbe8ff" intensity={26} distance={24} decay={2} />;
}

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
export default function Scene({ progressRef, velocityRef }) {
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

      <ResponsiveFov />
      <ParallaxSync tilt={tilt} parallaxRef={parallaxRef} />
      <MouseLight parallaxRef={parallaxRef} />

      <Suspense fallback={null}>
        <Diorama progressRef={progressRef} parallaxRef={parallaxRef} velocityRef={velocityRef} />
      </Suspense>
      <Atmosphere />
      <ImpactSparks progressRef={progressRef} />
      <Shockwave progressRef={progressRef} />
      <CameraRig progressRef={progressRef} parallaxRef={parallaxRef} />
      <CinematicEffects />
    </>
  );
}
