import { useEffect, useMemo, useRef } from "react";
import { useLoader, useFrame } from "@react-three/fiber";
import { Billboard } from "@react-three/drei";
import * as THREE from "three";

/**
 * Un elemento vero della scena — non un video, un ritaglio con canale
 * alpha reale (toro, orso, re, impatto) proiettato su un piano che guarda
 * sempre la camera (Billboard di drei): mentre si vola nella scena
 * scrollando, ogni elemento resta leggibile da qualunque angolo, come un
 * ologramma, invece di rivelarsi piatto quando la camera lo aggira.
 *
 * Un secondo piano più grande, additivo e leggermente pulsante dietro
 * l'immagine vera simula un bloom/glow — non abbiamo una pipeline di
 * post-processing, questo trucco costa quasi nulla e rende i bordi al
 * neon (fulmini verdi/rossi, oro) davvero luminosi.
 *
 * `progressRef` + `convergeTo`/`convergeScale` (opzionali): se passati,
 * l'elemento non resta fermo nel mondo mentre la camera lo scavalca — si
 * sposta lui stesso verso `convergeTo` e scala fino a `convergeScale`,
 * seguendo lo scroll. `mapProgress` trasforma il progresso grezzo (0..1
 * sull'intera pagina) prima di applicarlo: usato per far coincidere il
 * culmine (toro e orso che si scontrano) con una sezione precisa invece
 * che con la fine della pagina, o per far "respirare" lo scontro con un
 * impulso invece di una semplice interpolazione lineare.
 */
export default function Cutout({
  url,
  width,
  height,
  position,
  progressRef,
  mapProgress,
  convergeTo,
  convergeScale = 1,
  flipX = false,
  glowColor,
  glowOpacity = 0.4,
  glowScale = 1.22,
  additive = false,
  pulse = true,
  billboard = true,
}) {
  const texture = useLoader(THREE.TextureLoader, url);
  const glowRef = useRef();
  const groupRef = useRef();
  const smooth = useRef(0);
  const tmp = useRef(new THREE.Vector3());
  const startVec = useMemo(() => new THREE.Vector3(...position), [position]);
  const endVec = useMemo(() => (convergeTo ? new THREE.Vector3(...convergeTo) : null), [convergeTo]);

  useEffect(() => {
    if ("colorSpace" in texture) texture.colorSpace = THREE.SRGBColorSpace;
    texture.anisotropy = 4;
  }, [texture]);

  useFrame((state, delta) => {
    if (glowRef.current && pulse) {
      const t = state.clock.elapsedTime;
      glowRef.current.material.opacity = glowOpacity * (0.8 + Math.sin(t * 1.6 + position[0]) * 0.2);
    }
    if (groupRef.current && progressRef && endVec) {
      const dt = Math.min(delta, 0.1);
      const k = 1 - Math.exp(-dt * 3.5);
      const raw = Math.min(Math.max(progressRef.current, 0), 1);
      const mapped = mapProgress ? mapProgress(raw) : raw;
      smooth.current += (mapped - smooth.current) * k;
      const p = smooth.current;
      tmp.current.lerpVectors(startVec, endVec, p);
      groupRef.current.position.copy(tmp.current);
      groupRef.current.scale.setScalar(THREE.MathUtils.lerp(1, convergeScale, p));
    }
  });

  const content = (
    <group scale={[flipX ? -1 : 1, 1, 1]}>
      {glowColor && (
        <mesh ref={glowRef} scale={[glowScale, glowScale, 1]} renderOrder={1}>
          <planeGeometry args={[width, height]} />
          <meshBasicMaterial
            map={texture}
            color={glowColor}
            transparent
            opacity={glowOpacity}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
            toneMapped={false}
          />
        </mesh>
      )}
      <mesh renderOrder={2} castShadow>
        <planeGeometry args={[width, height]} />
        <meshBasicMaterial
          map={texture}
          transparent
          alphaTest={0.12}
          depthWrite={!additive}
          blending={additive ? THREE.AdditiveBlending : THREE.NormalBlending}
          toneMapped={false}
        />
      </mesh>
    </group>
  );

  const inner = billboard ? <Billboard follow>{content}</Billboard> : content;

  return (
    <group ref={groupRef} position={position}>
      {inner}
    </group>
  );
}
