import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { impactBump } from "./impactTiming";

const BAR_W = 1.0;
const BAR_H = 5.4;
const DEPTH = 1.35;
const HALF_GAP = 1.55; // distanza dal centro delle due barre verticali
const BEVEL = 0.06;

function barGeometry(w, h, d) {
  const shape = new THREE.Shape();
  const hw = w / 2;
  const hh = h / 2;
  shape.moveTo(-hw, -hh);
  shape.lineTo(hw, -hh);
  shape.lineTo(hw, hh);
  shape.lineTo(-hw, hh);
  shape.lineTo(-hw, -hh);
  return new THREE.ExtrudeGeometry(shape, {
    depth: d,
    bevelEnabled: true,
    bevelThickness: BEVEL,
    bevelSize: BEVEL,
    bevelSegments: 3,
    curveSegments: 1,
  });
}

/**
 * La "N" di NEXUS come unico vero protagonista visivo della scena — non un
 * disegno, tre barre 3D vere (due verticali, una diagonale che le
 * collega, ruotata via trigonometria non stimata a occhio) in un
 * materiale che si illumina davvero (emissive + Bloom), non un'immagine
 * piatta con un trucco di luce finta sopra.
 *
 * Si inclina con il mouse/giroscopio (parallaxRef) — "il logo che si
 * muove con il mouse" richiesto esplicitamente — più una minima
 * oscillazione residua per restare viva anche da ferma. Niente rotazione
 * costante e indipendente dallo scroll: la camera segue un percorso
 * scelto apposta per tenere la N sempre leggibile (cameraPath.js), e una
 * N che gira per conto suo con velocità legata al tempo trascorso — non
 * alla posizione di scroll — la porterebbe a un angolo imprevedibile a
 * ogni ricarica, vanificando quella scelta.
 *
 * L'emissive lampeggia (via `impactBump`, letto da progressRef) nel
 * momento di massimo avvicinamento della camera (cameraPath.js, tappa 4)
 * — "energia che si accende quando ci si avvicina", sincronizzata con la
 * stessa vibrazione del telefono in CameraRig.
 */
export default function NexusLogo({ progressRef, parallaxRef }) {
  const groupRef = useRef();
  const matRefs = useRef([]);
  const flash = useRef(0);
  const setMatRef = (i) => (el) => {
    matRefs.current[i] = el;
  };

  const diagGeom = useMemo(() => {
    const dx = HALF_GAP * 2;
    const dy = BAR_H;
    const len = Math.hypot(dx, dy);
    return { geom: barGeometry(BAR_W * 1.08, len, DEPTH), len, angle: Math.atan2(dx, dy) };
  }, []);

  const leftGeom = useMemo(() => barGeometry(BAR_W, BAR_H, DEPTH), []);
  const rightGeom = useMemo(() => barGeometry(BAR_W, BAR_H, DEPTH), []);

  useFrame((state, delta) => {
    const t = state.clock.elapsedTime;
    if (groupRef.current) {
      const px = parallaxRef ? parallaxRef.current.x : 0;
      const py = parallaxRef ? parallaxRef.current.y : 0;
      groupRef.current.rotation.y = px * 0.5;
      groupRef.current.rotation.x = Math.sin(t * 0.17) * 0.035 - py * 0.28;
      groupRef.current.rotation.z = Math.sin(t * 0.11) * 0.015;
    }
    const dt = Math.min(delta, 0.1);
    const k = 1 - Math.exp(-dt * 6);
    const raw = Math.min(Math.max(progressRef ? progressRef.current : 0, 0), 1);
    const target = impactBump(raw);
    flash.current += (target - flash.current) * k;
    matRefs.current.forEach((m, i) => {
      if (m) m.emissiveIntensity = (i === 2 ? 2.1 : 1.9) + flash.current * 3.2;
    });
  });

  return (
    <group ref={groupRef} position={[0, 2.1, -12]}>
      <mesh geometry={leftGeom} position={[-HALF_GAP, 0, -DEPTH / 2]} castShadow>
        <meshPhysicalMaterial
          ref={setMatRef(0)}
          color="#061020"
          emissive="#38bdf8"
          emissiveIntensity={1.9}
          metalness={0.35}
          roughness={0.22}
          clearcoat={0.6}
          clearcoatRoughness={0.2}
          toneMapped={false}
        />
      </mesh>
      <mesh geometry={rightGeom} position={[HALF_GAP, 0, -DEPTH / 2]} castShadow>
        <meshPhysicalMaterial
          ref={setMatRef(1)}
          color="#061020"
          emissive="#38bdf8"
          emissiveIntensity={1.9}
          metalness={0.35}
          roughness={0.22}
          clearcoat={0.6}
          clearcoatRoughness={0.2}
          toneMapped={false}
        />
      </mesh>
      <mesh
        geometry={diagGeom.geom}
        position={[0, 0, -DEPTH / 2]}
        rotation={[0, 0, -diagGeom.angle]}
        castShadow
      >
        <meshPhysicalMaterial
          ref={setMatRef(2)}
          color="#061020"
          emissive="#22d3ee"
          emissiveIntensity={2.1}
          metalness={0.35}
          roughness={0.2}
          clearcoat={0.6}
          clearcoatRoughness={0.2}
          toneMapped={false}
        />
      </mesh>
    </group>
  );
}
