import Bull from "./Bull";
import Bear from "./Bear";
import VolumeHistogram from "./VolumeHistogram";
import { TRADE_OBJECT_ZS } from "./content";

/**
 * Il toro, l'orso e un istogramma di volumi in coppia per ogni tappa —
 * oggetti veri del mondo trading, non solo nella prima sezione.
 * Alternano lato per non ripetersi sempre uguali lungo il corridoio.
 *
 * `lights=false` (fascia bassa) salta le 10 luci puntiformi dedicate: ogni
 * luce reale nella scena ha un costo che si moltiplica su ogni frammento
 * illuminato, indipendentemente da quanto è vicina — sul mobile debole pesa
 * più delle geometrie stesse. Toro e orso restano illuminati dalla luce
 * ambientale/direzionale della scena, solo un po' più cupi.
 */
export default function TradeObjects({ lights = true }) {
  return (
    <>
      {TRADE_OBJECT_ZS.map((z, i) => {
        const side = i % 2 === 0 ? 1 : -1;
        return (
          <group key={z}>
            <Bull position={[7 * side, 1.4 + (i % 3) * 0.5, z]} scale={0.9} />
            {lights && <pointLight color="#eaf2ff" intensity={12} distance={8} position={[7 * side, 2, z]} />}
            <Bear position={[-7 * side, 2.6 + (i % 2) * 0.9, z - 14]} scale={0.9} />
            {lights && <pointLight color="#eaf2ff" intensity={12} distance={8} position={[-7 * side, 3, z - 14]} />}
            <VolumeHistogram position={[1.6 * side, -2.6, z]} seed={i + 2} />
          </group>
        );
      })}
    </>
  );
}
