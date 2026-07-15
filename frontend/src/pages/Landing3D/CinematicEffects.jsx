import { useMemo } from "react";
import * as THREE from "three";
import { EffectComposer, Bloom, Vignette, DepthOfField } from "@react-three/postprocessing";
import { isLowEnd } from "./deviceTier";

// La N (NexusLogo) sta ferma in un unico punto del mondo per tutta la
// pagina — a differenza dei vecchi personaggi (l'arena a -34, il re a
// -19.5, ognuno a distanze diverse dalla camera a seconda della tappa),
// un target FISSO qui è affidabile: la profondità di campo che avevamo
// scartato in precedenza falliva proprio perché il soggetto da mettere a
// fuoco cambiava posizione/distanza ad ogni sezione, non perché l'idea
// in sé non funzionasse.
const FOCUS_TARGET = new THREE.Vector3(0, 2.1, -12);

/**
 * Bloom vero sopra il trucco "glow finto" già nei materiali (un bagliore
 * che risponde davvero alla luminosità della scena, non solo un piano
 * duplicato) + una vignettatura leggera per chiudere lo sguardo verso il
 * centro + una profondità di campo leggera con autofocus sulla N (sempre
 * ferma, vedi sopra): la N resta nitida, il pavimento riflettente e il
 * pulviscolo sullo sfondo si sfumano appena, un indizio di profondità in
 * più oltre al parallasse. Impostazioni volutamente contenute — la
 * versione precedente (su un soggetto che cambiava ad ogni sezione)
 * risultava troppo sfocata anche con valori bassi.
 *
 * Tutto disattivato sotto una certa soglia di schermo — il
 * post-processing è il costo più alto di tutta la scena, non ha senso
 * pagarlo su un telefono di fascia bassa.
 */
export default function CinematicEffects() {
  const target = useMemo(() => FOCUS_TARGET, []);
  if (isLowEnd) return null;

  return (
    <EffectComposer multisampling={0}>
      <DepthOfField target={target} focalLength={0.035} bokehScale={1.3} height={480} />
      <Bloom intensity={0.32} luminanceThreshold={0.62} luminanceSmoothing={0.2} mipmapBlur radius={0.5} />
      <Vignette eskil={false} offset={0.15} darkness={0.55} />
    </EffectComposer>
  );
}
