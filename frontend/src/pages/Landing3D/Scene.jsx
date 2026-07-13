import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import CameraRig from "./CameraRig";
import Starfield from "./Starfield";
import LightTrail from "./LightTrail";
import HoloHUD from "./HoloHUD";
import HeroBurst from "./HeroBurst";
import QuantumCore from "./QuantumCore";
import Candlesticks from "./Candlesticks";
import TradeObjects from "./TradeObjects";
import Effects from "./Effects";
import { QUALITY_PRESETS } from "./quality";

function CoreCrystal() {
  const core = useRef();
  const wire = useRef();
  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (core.current) {
      core.current.rotation.y = t * 0.3;
      core.current.rotation.x = t * 0.15;
    }
    if (wire.current) wire.current.rotation.copy(core.current.rotation);
  });
  return (
    <group position={[0, 1.4, 1.5]}>
      <mesh ref={core}>
        <icosahedronGeometry args={[1.7, 0]} />
        <meshStandardMaterial color="#2e6fd6" emissive="#0a3a7a" emissiveIntensity={0.75} metalness={0.6} roughness={0.25} flatShading />
      </mesh>
      <lineSegments ref={wire}>
        <edgesGeometry args={[new THREE.IcosahedronGeometry(1.74, 0)]} />
        <lineBasicMaterial color="#7ff0ff" transparent opacity={0.55} />
      </lineSegments>
    </group>
  );
}

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
 * .glb/.gltf — solo geometrie e shader procedurali.
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
      <CoreCrystal />
      <HeroBurst progressRef={progressRef} count={q.heroParticles} />
      <LightTrail />
      <Candlesticks count={q.candles} />
      <TradeObjects lights={quality !== "low"} />
      <HoloHUD />
      <QuantumCore />

      <CameraRig progressRef={progressRef} mouseRef={mouseRef} />
      <Effects bloom={q.bloom} bloomScale={q.bloomScale || 0.5} />
    </>
  );
}
