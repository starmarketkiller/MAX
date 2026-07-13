import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { HUD_NODES } from "./content";

function labelTexture(text, color) {
  const c = document.createElement("canvas");
  c.width = 320;
  c.height = 96;
  const x = c.getContext("2d");
  x.clearRect(0, 0, 320, 96);
  x.font = "600 40px 'JetBrains Mono', ui-monospace, monospace";
  x.textAlign = "center";
  x.textBaseline = "middle";
  x.fillStyle = color;
  x.shadowColor = color;
  x.shadowBlur = 22;
  x.fillText(text, 160, 50);
  return new THREE.CanvasTexture(c);
}

function HoloNode({ pos, colorA, colorB, labels }) {
  const group = useRef();
  const ringOuter = useRef();
  const ringInner = useRef();
  const radar = useRef();
  const tex = useMemo(() => [labelTexture(labels[0], colorA), labelTexture(labels[1], colorB)], [labels, colorA, colorB]);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (ringOuter.current) ringOuter.current.rotation.z = t * 0.22;
    if (ringInner.current) ringInner.current.rotation.z = -t * 0.35;
    if (radar.current) radar.current.rotation.z = t * 0.9;
    if (group.current) group.current.rotation.y = Math.sin(t * 0.15) * 0.15;
  });

  return (
    <group position={pos} ref={group}>
      <mesh ref={ringOuter}>
        <torusGeometry args={[1.5, 0.014, 8, 64]} />
        <meshBasicMaterial color={colorA} transparent opacity={0.65} blending={THREE.AdditiveBlending} />
      </mesh>
      <mesh ref={ringInner} rotation={[0.3, 0, 0]}>
        <torusGeometry args={[1.08, 0.012, 8, 48]} />
        <meshBasicMaterial color={colorB} transparent opacity={0.55} blending={THREE.AdditiveBlending} />
      </mesh>
      {/* linea radar: un settore che spazza il cerchio, stile scanner HUD */}
      <mesh ref={radar}>
        <ringGeometry args={[0.15, 1.5, 32, 1, 0, Math.PI * 0.12]} />
        <meshBasicMaterial color={colorA} transparent opacity={0.16} blending={THREE.AdditiveBlending} side={THREE.DoubleSide} depthWrite={false} />
      </mesh>
      <sprite position={[0, 0.32, 0]} scale={[1.8, 0.54, 1]}>
        <spriteMaterial map={tex[0]} transparent opacity={0.95} depthWrite={false} blending={THREE.AdditiveBlending} />
      </sprite>
      <sprite position={[0, -0.32, 0]} scale={[1.8, 0.54, 1]}>
        <spriteMaterial map={tex[1]} transparent opacity={0.95} depthWrite={false} blending={THREE.AdditiveBlending} />
      </sprite>
    </group>
  );
}

/**
 * Interfacce HUD olografiche stile Iron Man: cerchi concentrici, una linea
 * radar che spazza, testo neon fluttuante — un nodo per tappa narrativa,
 * al posto delle vecchie glifi piatte.
 */
export default function HoloHUD() {
  return (
    <>
      {HUD_NODES.map((n, i) => (
        <HoloNode key={i} pos={n.pos} colorA={n.colorA} colorB={n.colorB} labels={n.labels} />
      ))}
    </>
  );
}
