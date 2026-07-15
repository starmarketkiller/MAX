import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { impactBump } from "./impactTiming";

const BAR_W = 1.0;
const BAR_H = 5.4;
const DEPTH = 1.35;
const HALF_GAP = 1.55; // distanza dal centro delle due barre verticali
const BEVEL = 0.07;
const GLOW_SCALE = 1.16;

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
    bevelSegments: 6,
    curveSegments: 1,
  });
}

// Texture procedurale (un canvas disegnato una volta sola, non ogni frame):
// linee da circuito stampato incise nel metallo — dettaglio vero sulla
// superficie invece di un colore piatto, senza il costo di una vera mappa
// scaricata o di uno shader dedicato. Sfondo chiaro (non nero) perché è
// usata come emissiveMap: un fondo scuro spegneva quasi tutta la
// superficie tranne le linee, facendo leggere l'insieme come troppo buio.
function circuitTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#2c5f95";
  ctx.fillRect(0, 0, 256, 256);
  ctx.strokeStyle = "rgba(200, 235, 255, 0.75)";
  ctx.lineWidth = 2;
  const lines = [
    [20, 0, 20, 90], [20, 90, 60, 130], [60, 130, 60, 256],
    [236, 0, 236, 70], [236, 70, 190, 116], [190, 116, 190, 256],
    [0, 40, 100, 40], [156, 40, 256, 40],
    [0, 210, 90, 210], [90, 210, 130, 175], [130, 175, 256, 175],
  ];
  lines.forEach(([x1, y1, x2, y2]) => {
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
  });
  ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
  [[20, 90], [60, 130], [236, 70], [190, 116], [90, 210], [130, 175]].forEach(([x, y]) => {
    ctx.beginPath();
    ctx.arc(x, y, 3.5, 0, Math.PI * 2);
    ctx.fill();
  });
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(1, 2.4);
  return tex;
}

/**
 * La "N" di NEXUS come unico vero protagonista visivo della scena — non un
 * disegno, tre barre 3D vere (due verticali, una diagonale che le
 * collega, ruotata via trigonometria) in un materiale che si illumina
 * davvero (emissive + Bloom), non un'immagine piatta con un trucco di
 * luce finta sopra. Una texture da circuito stampato (generata una sola
 * volta, non un file scaricato) incisa nella superficie dà dettaglio
 * reale da vicino invece di restare un blocco piatto; due anelli sottili
 * che le orbitano intorno lentamente rinforzano visivamente il tema "la
 * camera le gira intorno".
 *
 * Ogni barra ha anche un doppio leggermente più grande dietro di sé,
 * additivo e pulsante — lo stesso trucco usato per il "glow" dei vecchi
 * ritagli PNG (bull/bear/king, ora rimossi): dà alla N una luce propria
 * percepita, non solo riflessi dalle luci della scena, e la pulsazione
 * aggiunge sensazione di movimento anche da ferma.
 *
 * Si inclina con il mouse/giroscopio (parallaxRef) — "il logo che si
 * muove con il mouse" — più una minima oscillazione residua. Niente
 * rotazione costante e indipendente dallo scroll sulla N stessa: la
 * camera segue un percorso scelto apposta per tenerla sempre leggibile
 * (cameraPath.js), e una N che gira per conto suo la porterebbe a un
 * angolo imprevedibile a ogni ricarica, vanificando quella scelta.
 *
 * L'emissive lampeggia (via `impactBump`, letto da progressRef) nel
 * momento di massimo avvicinamento della camera (cameraPath.js, tappa 4).
 */
export default function NexusLogo({ progressRef, parallaxRef }) {
  const groupRef = useRef();
  const matRefs = useRef([]);
  const glowRefs = useRef([]);
  const ring1Ref = useRef();
  const ring2Ref = useRef();
  const flash = useRef(0);
  const setMatRef = (i) => (el) => {
    matRefs.current[i] = el;
  };
  const setGlowRef = (i) => (el) => {
    glowRefs.current[i] = el;
  };

  const texture = useMemo(() => circuitTexture(), []);

  const diagGeom = useMemo(() => {
    const dx = HALF_GAP * 2;
    const dy = BAR_H;
    const len = Math.hypot(dx, dy);
    return { geom: barGeometry(BAR_W * 1.08, len, DEPTH), len, angle: Math.atan2(dx, dy) };
  }, []);

  const leftGeom = useMemo(() => barGeometry(BAR_W, BAR_H, DEPTH), []);
  const rightGeom = useMemo(() => barGeometry(BAR_W, BAR_H, DEPTH), []);
  const ringGeom = useMemo(() => new THREE.TorusGeometry(4.6, 0.03, 8, 64), []);
  const ringGeom2 = useMemo(() => new THREE.TorusGeometry(5.6, 0.025, 8, 64), []);

  const BASE = [2.3, 2.3, 2.6];

  useFrame((state, delta) => {
    const t = state.clock.elapsedTime;
    if (groupRef.current) {
      const px = parallaxRef ? parallaxRef.current.x : 0;
      const py = parallaxRef ? parallaxRef.current.y : 0;
      groupRef.current.rotation.y = px * 0.5;
      groupRef.current.rotation.x = Math.sin(t * 0.17) * 0.035 - py * 0.28;
      groupRef.current.rotation.z = Math.sin(t * 0.11) * 0.015;
    }
    if (ring1Ref.current) {
      ring1Ref.current.rotation.z = t * 0.05;
      ring1Ref.current.rotation.x = 1.2 + Math.sin(t * 0.08) * 0.06;
    }
    if (ring2Ref.current) {
      ring2Ref.current.rotation.z = -t * 0.035;
      ring2Ref.current.rotation.x = -1.05 + Math.sin(t * 0.06) * 0.05;
    }

    const dt = Math.min(delta, 0.1);
    const k = 1 - Math.exp(-dt * 6);
    const raw = Math.min(Math.max(progressRef ? progressRef.current : 0, 0), 1);
    const target = impactBump(raw);
    flash.current += (target - flash.current) * k;

    matRefs.current.forEach((m, i) => {
      if (m) m.emissiveIntensity = BASE[i] + flash.current * 3.4;
    });

    const pulse = 0.85 + Math.sin(t * 1.4) * 0.15;
    glowRefs.current.forEach((g) => {
      if (g) g.opacity = (0.22 + flash.current * 0.35) * pulse;
    });
  });

  return (
    <group ref={groupRef} position={[0, 2.1, -12]}>
      <mesh geometry={leftGeom} position={[-HALF_GAP, 0, -DEPTH / 2]} castShadow>
        <meshPhysicalMaterial
          ref={setMatRef(0)}
          color="#123055"
          emissiveMap={texture}
          emissive="#38bdf8"
          emissiveIntensity={BASE[0]}
          metalness={0.22}
          roughness={0.3}
          clearcoat={0.6}
          clearcoatRoughness={0.2}
          toneMapped={false}
        />
      </mesh>
      <mesh scale={[GLOW_SCALE, GLOW_SCALE, 1]} geometry={leftGeom} position={[-HALF_GAP, 0, -DEPTH / 2]} renderOrder={0}>
        <meshBasicMaterial
          ref={setGlowRef(0)}
          color="#38bdf8"
          transparent
          opacity={0.22}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      <mesh geometry={rightGeom} position={[HALF_GAP, 0, -DEPTH / 2]} castShadow>
        <meshPhysicalMaterial
          ref={setMatRef(1)}
          color="#123055"
          emissiveMap={texture}
          emissive="#38bdf8"
          emissiveIntensity={BASE[1]}
          metalness={0.22}
          roughness={0.3}
          clearcoat={0.6}
          clearcoatRoughness={0.2}
          toneMapped={false}
        />
      </mesh>
      <mesh scale={[GLOW_SCALE, GLOW_SCALE, 1]} geometry={rightGeom} position={[HALF_GAP, 0, -DEPTH / 2]} renderOrder={0}>
        <meshBasicMaterial
          ref={setGlowRef(1)}
          color="#38bdf8"
          transparent
          opacity={0.22}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      <mesh
        geometry={diagGeom.geom}
        position={[0, 0, -DEPTH / 2]}
        rotation={[0, 0, diagGeom.angle]}
        castShadow
      >
        <meshPhysicalMaterial
          ref={setMatRef(2)}
          color="#123055"
          emissiveMap={texture}
          emissive="#22d3ee"
          emissiveIntensity={BASE[2]}
          metalness={0.22}
          roughness={0.26}
          clearcoat={0.6}
          clearcoatRoughness={0.2}
          toneMapped={false}
        />
      </mesh>
      <mesh
        scale={[GLOW_SCALE, GLOW_SCALE, 1]}
        geometry={diagGeom.geom}
        position={[0, 0, -DEPTH / 2]}
        rotation={[0, 0, diagGeom.angle]}
        renderOrder={0}
      >
        <meshBasicMaterial
          ref={setGlowRef(2)}
          color="#22d3ee"
          transparent
          opacity={0.24}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      {/* due anelli sottili che orbitano a velocità e assi diversi — un
          accento "tech", non decorativo a caso, che richiama visivamente
          l'orbita della camera intorno alla N */}
      <mesh ref={ring1Ref} geometry={ringGeom} rotation={[1.2, 0, 0]}>
        <meshBasicMaterial color="#38bdf8" transparent opacity={0.28} toneMapped={false} />
      </mesh>
      <mesh ref={ring2Ref} geometry={ringGeom2} rotation={[-1.05, 0, 0]}>
        <meshBasicMaterial color="#22d3ee" transparent opacity={0.18} toneMapped={false} />
      </mesh>
    </group>
  );
}
