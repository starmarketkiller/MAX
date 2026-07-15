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
 * post-processing dedicata al glow, questo trucco costa quasi nulla e
 * rende i bordi al neon (fulmini verdi/rossi, oro) davvero luminosi.
 *
 * `progressRef` + `convergeTo`/`convergeScale` (opzionali): se passati,
 * l'elemento non resta fermo nel mondo mentre la camera lo scavalca — si
 * sposta lui stesso verso `convergeTo` e scala fino a `convergeScale`,
 * seguendo lo scroll. `mapProgress` trasforma il progresso grezzo prima
 * di applicarlo (per far coincidere un culmine con una sezione precisa,
 * o per un impulso invece di una rampa lineare).
 *
 * `parallaxRef` + `parallaxStrength` (opzionali): un piccolo scarto di
 * posizione, indipendente dallo scroll, che segue mouse/giroscopio
 * (useDeviceTilt) — ogni livello ha una propria intensità, così lo
 * spazio risponde come vivo anche senza scrollare.
 *
 * `skewRef` + `skewStrength` (opzionali): una leggerissima torsione
 * (rotation.z) proporzionale alla velocità di scroll — dà peso/inerzia
 * all'energia dello scontro quando si scrolla veloce, si assesta da sola
 * quando lo scroll si ferma.
 *
 * `normalMapUrl` (opzionale): niente modelli 3D veri, ma la pittura di luci
 * e ombre già presente nel ritaglio (muscoli, pieghe dell'armatura) diventa
 * un vero rilievo — normal map generata offline dalla luminanza
 * dell'immagine stessa (Sobel su un'immagine "riempita" oltre il bordo
 * alpha, per non avere un dislivello finto proprio sul contorno). Con
 * MeshStandardMaterial al posto di MeshBasicMaterial, le luci della scena
 * — compresa MouseLight, che segue il mouse — creano riflessi e ombre
 * dinamiche reali sopra il ritaglio piatto. `emissiveMap` mantiene la
 * stessa resa "sempre visibile" di prima come base, la luce vera si
 * aggiunge sopra invece di sostituirla — zero rischio di un'immagine che
 * si spegne se la luce è debole o mal posizionata.
 */
export default function Cutout({
  url,
  normalMapUrl,
  normalScale = 0.65,
  width,
  height,
  position,
  progressRef,
  mapProgress,
  convergeTo,
  convergeScale = 1,
  parallaxRef,
  parallaxStrength = 0,
  skewRef,
  skewStrength = 1,
  flipX = false,
  glowColor,
  glowOpacity = 0.4,
  glowScale = 1.22,
  additive = false,
  pulse = true,
  billboard = true,
}) {
  const texture = useLoader(THREE.TextureLoader, url);
  const normalMap = useLoader(THREE.TextureLoader, normalMapUrl || url);
  const glowRef = useRef();
  const groupRef = useRef();
  const smooth = useRef(0);
  const basePos = useRef(new THREE.Vector3(...position));
  const finalPos = useRef(new THREE.Vector3(...position));
  const rotZ = useRef(0);
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

    if (!groupRef.current) return;

    if (progressRef && endVec) {
      const dt = Math.min(delta, 0.1);
      const k = 1 - Math.exp(-dt * 2.0); // più lento = convergenza più sostenuta
      const raw = Math.min(Math.max(progressRef.current, 0), 1);
      const mapped = mapProgress ? mapProgress(raw) : raw;
      smooth.current += (mapped - smooth.current) * k;
      const p = smooth.current;
      basePos.current.lerpVectors(startVec, endVec, p);
      groupRef.current.scale.setScalar(THREE.MathUtils.lerp(1, convergeScale, p));
    }

    finalPos.current.copy(basePos.current);
    if (parallaxRef && parallaxStrength) {
      finalPos.current.x += parallaxRef.current.x * parallaxStrength;
      finalPos.current.y += -parallaxRef.current.y * parallaxStrength * 0.6;
    }
    groupRef.current.position.copy(finalPos.current);

    if (skewRef) {
      const dt2 = Math.min(delta, 0.1);
      const k2 = 1 - Math.exp(-dt2 * 6);
      const target = THREE.MathUtils.clamp(-skewRef.current * 0.0015 * skewStrength, -0.12, 0.12);
      rotZ.current += (target - rotZ.current) * k2;
      groupRef.current.rotation.z = rotZ.current;
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
        {normalMapUrl ? (
          <meshStandardMaterial
            map={texture}
            normalMap={normalMap}
            normalScale={new THREE.Vector2(normalScale, normalScale)}
            emissiveMap={texture}
            emissive="#ffffff"
            emissiveIntensity={0.82}
            roughness={0.5}
            metalness={0.08}
            transparent
            alphaTest={0.12}
            depthWrite={!additive}
            blending={additive ? THREE.AdditiveBlending : THREE.NormalBlending}
            toneMapped={false}
          />
        ) : (
          <meshBasicMaterial
            map={texture}
            transparent
            alphaTest={0.12}
            depthWrite={!additive}
            blending={additive ? THREE.AdditiveBlending : THREE.NormalBlending}
            toneMapped={false}
          />
        )}
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
