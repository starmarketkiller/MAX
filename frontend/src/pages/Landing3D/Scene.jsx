import CameraRig from "./CameraRig";
import ArenaBackdrop from "./ArenaBackdrop";
import Atmosphere from "./Atmosphere";

/**
 * Contenuto del Canvas R3F: l'arena riempie tutto lo schermo come sfondo
 * (ArenaBackdrop, agganciato alla camera), mentre pavimento riflettente,
 * pulviscolo e pilastri luminosi (Atmosphere) vivono nello spazio 3D vero
 * davanti a lei e si muovono con parallasse mentre la camera avanza dentro
 * l'arena scrollando. Separato dalla UI HTML (overlay assoluto in
 * index.jsx) — comunicano solo via progressRef, letto ad ogni frame senza
 * mai forzare un re-render React.
 */
export default function Scene({ progressRef }) {
  return (
    <>
      <color attach="background" args={["#040611"]} />
      <fogExp2 attach="fog" args={["#050a16", 0.024]} />

      <ambientLight color="#1c3a68" intensity={0.9} />
      <directionalLight
        color="#9fd8ff"
        intensity={1.6}
        position={[6, 9, 4]}
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-camera-near={1}
        shadow-camera-far={30}
        shadow-camera-left={-16}
        shadow-camera-right={16}
        shadow-camera-top={16}
        shadow-camera-bottom={-16}
      />
      <directionalLight color="#8b6ff0" intensity={0.5} position={[-8, 3, -4]} />

      <ArenaBackdrop progressRef={progressRef} />
      <Atmosphere />
      <CameraRig progressRef={progressRef} />
    </>
  );
}
