import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { softDiscTexture } from "./textures";

// La camera viaggia con x tra circa -3 e 4: una stella generata per caso
// proprio lì, vicinissima al percorso, si ingrandisce a dismisura per via
// del sizeAttenuation (più vicina = sprite più grande) e appare come un
// unico blob bianco enorme invece che come un punto. minRadius tiene le
// stelle fuori da quel corridoio.
function makeLayer(count, spanZ, spreadXY, palette, minRadius = 9) {
  const positions = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    let x = (Math.random() - 0.5) * spreadXY;
    let y = (Math.random() - 0.5) * spreadXY * 0.6;
    const r = Math.hypot(x, y);
    if (r < minRadius) {
      const k = minRadius / Math.max(r, 0.001);
      x *= k;
      y *= k;
    }
    positions[i * 3] = x;
    positions[i * 3 + 1] = y;
    positions[i * 3 + 2] = Math.random() * -spanZ + 20;
    const col = palette[(Math.random() * palette.length) | 0];
    colors[i * 3] = col[0];
    colors[i * 3 + 1] = col[1];
    colors[i * 3 + 2] = col[2];
  }
  return { positions, colors };
}

const PALETTE = [
  [0.35, 0.65, 1.0],
  [0.13, 0.83, 0.97],
  [0.9, 0.95, 1.0],
  [0.4, 0.9, 0.75],
];

/**
 * Campo stellare procedurale a due strati di profondità, generato via canvas
 * texture (nessun asset esterno) — copre l'intero percorso della camera
 * (~260 unità) così le stelle non finiscono mai a ridosso della telecamera.
 * Lo strato vicino aggiunge una lieve parallasse guidata dal mouse.
 */
export default function Starfield({ mouseRef, starsFar = 2600, starsNear = 900 }) {
  const near = useRef();
  const far = useRef();
  const disc = useMemo(() => softDiscTexture(), []);
  const farData = useMemo(() => makeLayer(starsFar, 300, 140, PALETTE), [starsFar]);
  const nearData = useMemo(() => makeLayer(starsNear, 300, 70, PALETTE), [starsNear]);

  useFrame((_, delta) => {
    const dt = Math.min(delta, 0.1);
    const k = 1 - Math.exp(-dt * 3);
    const mx = mouseRef.current.x;
    const my = mouseRef.current.y;
    if (near.current) {
      near.current.position.x += (mx * 4 - near.current.position.x) * k;
      near.current.position.y += (-my * 2.4 - near.current.position.y) * k;
    }
    if (far.current) far.current.rotation.y += dt * 0.024;
  });

  return (
    <>
      <points ref={far}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" count={starsFar} array={farData.positions} itemSize={3} />
          <bufferAttribute attach="attributes-color" count={starsFar} array={farData.colors} itemSize={3} />
        </bufferGeometry>
        <pointsMaterial size={0.65} map={disc} vertexColors transparent depthWrite={false} blending={THREE.AdditiveBlending} sizeAttenuation />
      </points>
      <points ref={near}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" count={starsNear} array={nearData.positions} itemSize={3} />
          <bufferAttribute attach="attributes-color" count={starsNear} array={nearData.colors} itemSize={3} />
        </bufferGeometry>
        <pointsMaterial size={1.1} map={disc} vertexColors transparent depthWrite={false} blending={THREE.AdditiveBlending} sizeAttenuation />
      </points>
    </>
  );
}
