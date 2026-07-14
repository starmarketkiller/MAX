import CameraRig from "./CameraRig";
import VideoScreen from "./VideoScreen";
import Atmosphere from "./Atmosphere";

/**
 * Contenuto del Canvas R3F: il video vive dentro uno spazio 3D vero (luci,
 * ombre, pavimento, camera che si muove) invece che come sfondo piatto.
 * Separato dalla UI HTML (overlay assoluto in index.jsx) — comunicano solo
 * via progressRef, letto ad ogni frame senza mai forzare un re-render React.
 */
export default function Scene({ progressRef }) {
  return (
    <>
      <color attach="background" args={["#040611"]} />
      <fogExp2 attach="fog" args={["#050a16", 0.028]} />

      <ambientLight color="#1c3a68" intensity={0.9} />
      <directionalLight
        color="#9fd8ff"
        intensity={1.6}
        position={[6, 9, 4]}
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-camera-near={1}
        shadow-camera-far={30}
        shadow-camera-left={-12}
        shadow-camera-right={12}
        shadow-camera-top={12}
        shadow-camera-bottom={-12}
      />
      <directionalLight color="#8b6ff0" intensity={0.5} position={[-8, 3, -4]} />

      <VideoScreen progressRef={progressRef} />
      <Atmosphere />
      <CameraRig progressRef={progressRef} />
    </>
  );
}
