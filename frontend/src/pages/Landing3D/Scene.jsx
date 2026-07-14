import CameraRig from "./CameraRig";
import Starfield from "./Starfield";
import LightTrail from "./LightTrail";
import HoloHUD from "./HoloHUD";
import QuantumCore from "./QuantumCore";
import Candlesticks from "./Candlesticks";
import Effects from "./Effects";
import { QUALITY_PRESETS } from "./quality";

function ReflectiveFloor() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -7, 0]}>
      <planeGeometry args={[260, 260]} />
      <meshStandardMaterial color="#060a16" metalness={0.9} roughness={0.18} />
    </mesh>
  );
}

/**
 * Contenuto del Canvas R3F: separato dalla UI HTML (overlay assoluto in
 * index.jsx). Spazio profondo #050510, luci ciano/violetto, nessun asset
 * .glb/.gltf — solo geometrie e shader procedurali. Parte gia' dentro il
 * corridoio: l'hero (cristallo + esplosione di particelle) non esiste piu',
 * sostituito dall'arena video-scrub prima di questa scena.
 */
export default function Scene({ progressRef, mouseRef, quality = "high" }) {
  const q = QUALITY_PRESETS[quality] || QUALITY_PRESETS.high;
  return (
    <>
      <color attach="background" args={["#050510"]} />
      <fogExp2 attach="fog" args={["#05070f", 0.0062]} />

      <ambientLight color="#22406a" intensity={1.1} />
      <directionalLight color="#9fd8ff" intensity={1.4} position={[5, 10, 6]} />
      <directionalLight color="#8b6ff0" intensity={0.6} position={[-8, 2, -4]} />
      <pointLight color="#38bdf8" intensity={60} distance={60} position={[0, 1, 2]} />

      <Starfield mouseRef={mouseRef} starsFar={q.starsFar} starsNear={q.starsNear} />
      <ReflectiveFloor />
      <LightTrail />
      <Candlesticks count={q.candles} />
      <HoloHUD />
      <QuantumCore />

      <CameraRig progressRef={progressRef} mouseRef={mouseRef} />
      <Effects bloom={q.bloom} bloomScale={q.bloomScale || 0.5} />
    </>
  );
}
