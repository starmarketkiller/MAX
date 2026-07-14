import { useEffect, useRef } from "react";
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
 */
export default function Cutout({
  url,
  width,
  height,
  position,
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

  useEffect(() => {
    if ("colorSpace" in texture) texture.colorSpace = THREE.SRGBColorSpace;
    texture.anisotropy = 4;
  }, [texture]);

  useFrame((state) => {
    if (glowRef.current && pulse) {
      const t = state.clock.elapsedTime;
      glowRef.current.material.opacity = glowOpacity * (0.8 + Math.sin(t * 1.6 + position[0]) * 0.2);
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

  if (!billboard) {
    return <group position={position}>{content}</group>;
  }
  return (
    <Billboard position={position} follow>
      {content}
    </Billboard>
  );
}
