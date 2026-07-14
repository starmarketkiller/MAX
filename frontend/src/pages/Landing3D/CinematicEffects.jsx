import { EffectComposer, Bloom, Vignette } from "@react-three/postprocessing";
import { isLowEnd } from "./deviceTier";

/**
 * Bloom vero sopra il trucco "glow finto" già nei materiali (un bagliore
 * che risponde davvero alla luminosità della scena, non solo un piano
 * duplicato) + una vignettatura leggera per chiudere lo sguardo verso il
 * centro. Disattivato sotto una certa soglia di schermo — il
 * post-processing è il costo più alto di tutta la scena, non ha senso
 * pagarlo su un telefono di fascia bassa.
 *
 * La profondità di campo dinamica (autofocus sul target della camera)
 * è stata provata e scartata: con la nostra scala di scena (l'arena a
 * -34, il re a -19.5) il target non seguiva in modo affidabile la
 * camera tra le sezioni e in alcuni punti sfocava il soggetto principale
 * (il re, proprio al finale) invece dello sfondo — un rischio più grande
 * del beneficio estetico. Il parallasse (CameraRig, Diorama) resta la
 * fonte principale di percezione della profondità.
 */
export default function CinematicEffects() {
  if (isLowEnd) return null;

  return (
    <EffectComposer multisampling={0}>
      <Bloom intensity={0.32} luminanceThreshold={0.62} luminanceSmoothing={0.2} mipmapBlur radius={0.5} />
      <Vignette eskil={false} offset={0.15} darkness={0.55} />
    </EffectComposer>
  );
}
