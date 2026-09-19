#!/usr/bin/env python3
"""Phase 7.2 sec.7 - Normalizza i 115 claim grezzi in market_mechanism_registry_v1.json.
Il mapping claim_id -> mechanism_id e' stato costruito leggendo claimed_mechanism/
event_sequence di ogni claim (non generato a priori) - vedi phase7_2_research_journal_v1.jsonl
per la nota di metodo. Un claim puo' supportare piu' di un mechanism (candidate_mechanism_ids
e' un array)."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
PHASE72_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_2")
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

# mechanism_id -> (name, definition, [claim_ids])
MECHANISMS = {
    "MECH-01": ("TREND_PERSISTENCE", "Un movimento direzionale sostenuto tende a continuare nel breve/medio termine.",
                ["CLAIM-0001", "CLAIM-0091"]),
    "MECH-02": ("MOMENTUM_DECAY_TO_MEAN_REVERSION", "Dopo una fase iniziale trend-following, il momentum decade e parte dell'effetto si inverte a orizzonti piu' lunghi.",
                ["CLAIM-0002"]),
    "MECH-03": ("SESSION_TIME_OF_DAY_SEASONALITY", "Ritorni realizzati, volatilita' e spread mostrano pattern ricorrenti legati all'ora del giorno/apertura-chiusura sessione.",
                ["CLAIM-0003", "CLAIM-0004", "CLAIM-0013", "CLAIM-0018", "CLAIM-0096", "CLAIM-0097", "CLAIM-0098", "CLAIM-0099"]),
    "MECH-04": ("ILLIQUIDITY_RISK_PREMIUM", "Premio di rischio richiesto per il costo di impatto di prezzo in condizioni meno liquide - fattore strutturale, non un sequence di trading.",
                ["CLAIM-0005"]),
    "MECH-05": ("LIQUIDITY_SHOCK_VOLATILITY_FEEDBACK", "Uno shock di liquidita' deprime il prezzo in tempo reale e coincide con volatilita' elevata.",
                ["CLAIM-0006"]),
    "MECH-06": ("BREAKOUT_ACCEPTANCE_CONTINUATION", "Un breakout di un livello/range viene accettato (chiusure successive lo confermano) e il movimento continua nella direzione della rottura.",
                ["CLAIM-0007", "CLAIM-0009", "CLAIM-0027", "CLAIM-0031", "CLAIM-0036", "CLAIM-0042",
                 "CLAIM-0048", "CLAIM-0068", "CLAIM-0070", "CLAIM-0071", "CLAIM-0083", "CLAIM-0085",
                 "CLAIM-0086", "CLAIM-0090", "CLAIM-0106", "CLAIM-0107", "CLAIM-0112", "CLAIM-0113"]),
    "MECH-07": ("BREAKOUT_CONDITIONAL_ON_PARTICIPATION", "La continuazione di un breakout e' condizionata a liquidita'/partecipazione/volume concorrenti, non e' universale.",
                ["CLAIM-0008", "CLAIM-0010", "CLAIM-0028", "CLAIM-0049", "CLAIM-0060", "CLAIM-0073"]),
    "MECH-08": ("BREAKOUT_FAILURE", "Un breakout di un livello/range fallisce a mantenersi, il prezzo rientra nel range precedente.",
                ["CLAIM-0023", "CLAIM-0033", "CLAIM-0044", "CLAIM-0045", "CLAIM-0064"]),
    "MECH-09": ("SIGNAL_OVERFITTING_METHODOLOGICAL_CAUTION", "Segnali OHLCV semplici, backtest senza costi/OOS, e liste di asset scelte con survivorship bias sovrastimano sistematicamente l'edge apparente - non un fenomeno di mercato, ma un avvertimento metodologico ricorrente nel corpus.",
                ["CLAIM-0024", "CLAIM-0038", "CLAIM-0068", "CLAIM-0090"]),
    "MECH-10": ("VOLATILITY_COMPRESSION_TO_EXPANSION", "Una contrazione misurabile della volatilita' rispetto alla propria storia recente precede una fase di espansione.",
                ["CLAIM-0025", "CLAIM-0072", "CLAIM-0073", "CLAIM-0082"]),
    "MECH-11": ("VOLATILITY_REGIME_DIRECTION_DECOUPLING", "Le transizioni di regime di volatilita' possono essere scollegate dalla direzione dei ritorni.",
                ["CLAIM-0026"]),
    "MECH-12": ("CALENDAR_SCHEDULED_EVENT_DRIFT", "Il prezzo deriva in una direzione prima di un evento macro schedulato e dateable (es. riunione di politica monetaria), indipendentemente dall'esito atteso.",
                ["CLAIM-0011", "CLAIM-0012"]),
    "MECH-13": ("GOLD_CALENDAR_DEMAND_SHOCK", "Eventi culturali/calendariali ricorrenti generano una pressione di acquisto anticipata specifica per l'oro.",
                ["CLAIM-0021", "CLAIM-0022"]),
    "MECH-14": ("TERM_STRUCTURE_ROLL_YIELD", "La forma della curva future condiziona il ritorno di rollover atteso - fattore strutturale sui futures, indipendente dal timing intraday.",
                ["CLAIM-0019", "CLAIM-0020"]),
    "MECH-15": ("VOLATILITY_CLUSTERING", "L'ampiezza delle variazioni di prezzo e' persistente anche quando il segno non lo e'.",
                ["CLAIM-0014"]),
    "MECH-16": ("FAT_TAIL_VOL_RETURN_ASYMMETRY", "Codate spesse e correlazione negativa ritorno-volatilita': i drawdown ampi coincidono con impennate di volatilita'.",
                ["CLAIM-0015"]),
    "MECH-17": ("SESSION_SIGN_REVERSAL", "Il segno di un premio/anomalia guadagnato in una sessione tende a invertirsi nella sessione successiva.",
                ["CLAIM-0016", "CLAIM-0017"]),
    "MECH-18": ("LIQUIDITY_SWEEP", "Il prezzo eccede brevemente un livello di riferimento (swing, sessione, giorno/settimana precedente) senza necessariamente chiudere oltre - evento base, agnostico rispetto all'esito successivo.",
                ["CLAIM-0032", "CLAIM-0033", "CLAIM-0034", "CLAIM-0054", "CLAIM-0058", "CLAIM-0062", "CLAIM-0065",
                 "CLAIM-0102", "CLAIM-0103"]),
    "MECH-19": ("LEVEL_RECLAIM_REVERSAL",
                "Dopo un LIQUIDITY_SWEEP, il prezzo richiude oltre il livello nella direzione opposta allo sweep e questo viene interpretato come inversione - ATTENZIONE: questo e' strutturalmente il mechanism generico gia' testato e REFUTED_AT_DISCOVERY in Phase 7.1 (RECLAIM). Vedi failure_memory_relation per ogni claim/sequence che usa questo mechanism.",
                ["CLAIM-0035", "CLAIM-0050", "CLAIM-0052", "CLAIM-0108", "CLAIM-0109", "CLAIM-0110", "CLAIM-0111"]),
    "MECH-20": ("SWEEP_WITHOUT_RECLAIM_CONTINUATION",
                "Il prezzo eccede un livello (sweep) MA NON richiude oltre nella direzione opposta ('run', non reversal) - la continuazione nella direzione dello sweep viene interpretata come il vero movimento. CONTRADDICE direttamente MECH-19 sullo stesso evento visibile - vedi contradiction_registry_v1.json.",
                ["CLAIM-0051", "CLAIM-0056", "CLAIM-0059", "CLAIM-0114"]),
    "MECH-21": ("GAP_IMBALANCE_FVG_RESPONSE", "Un gap fra candele consecutive (imbalance/fair value gap) viene rivisitato e la probabilita' di essere riempito prima della scadenza varia sistematicamente.",
                ["CLAIM-0057", "CLAIM-0080", "CLAIM-0081"]),
    "MECH-22": ("GRID_MARTINGALE_MEAN_REVERSION_ASSUMPTION", "La redditivita' di un sistema a griglia dipende dall'assunzione implicita che il prezzo rivisiti entrambi i lati del punto di partenza (mean-reversion strutturale) - logica di money-management che nasconde un'assunzione di mercato, non un mechanism di prezzo puro.",
                ["CLAIM-0037", "CLAIM-0038"]),
    "MECH-23": ("TREND_CHOP_REGIME_CLASSIFICATION", "Il rapporto fra volatilita' e deriva direzionale (o misure equivalenti come l'efficiency ratio) distingue un regime di trend pulito da uno choppy/laterale.",
                ["CLAIM-0039", "CLAIM-0040", "CLAIM-0076", "CLAIM-0077"]),
    "MECH-24": ("POSITION_HOLDING_TIME_RISK_GROWTH", "La varianza di equity in condizioni drift-dominant cresce con il tempo trascorso in posizione, motivando un limite di tempo fisso - principio di risk management derivato da un'assunzione di mercato, non un mechanism osservabile di per se'.",
                ["CLAIM-0041", "CLAIM-0084"]),
    "MECH-25": ("MOMENTUM_BURST_CONTINUATION", "Un range giornaliero ampio riflette uno spostamento genuino di partecipazione/momentum che tende a proseguire.",
                ["CLAIM-0042", "CLAIM-0043"]),
    "MECH-26": ("MEAN_REVERSION_BAND_TOUCH_REGIME_DEPENDENT", "Il tocco di una banda di volatilita' (es. Bollinger) implica un'aspettativa di reversione verso la media, ma l'affidabilita' e' regime-dipendente e sistematicamente instabile.",
                ["CLAIM-0046", "CLAIM-0047", "CLAIM-0063", "CLAIM-0093", "CLAIM-0115"]),
    "MECH-27": ("HTF_TREND_FILTER_ALIGNMENT", "Lo stato di trend/direzione su un timeframe o mercato di riferimento piu' ampio (HTF, indice cross-asset) e' usato come filtro per un evento osservato su un timeframe/mercato piu' locale.",
                ["CLAIM-0031", "CLAIM-0048", "CLAIM-0055", "CLAIM-0067", "CLAIM-0069", "CLAIM-0075",
                 "CLAIM-0089", "CLAIM-0104"]),
    "MECH-28": ("VALUE_AREA_ACCEPTANCE_REJECTION", "Il prezzo che rientra ed e' accettato (chiusure, non solo wick) dentro/fuori la value area di un profilo di volume definisce continuazione vs rigetto.",
                ["CLAIM-0078", "CLAIM-0079"]),
    "MECH-29": ("VWAP_ACCEPTANCE_REJECTION", "Il prezzo che torna al VWAP di sessione durante un trend attrae flusso difensivo istituzionale (accettazione) oppure viene respinto, mantenendo la direzione precedente.",
                ["CLAIM-0074", "CLAIM-0075", "CLAIM-0092", "CLAIM-0093"]),
    "MECH-30": ("SESSION_TRANSITION_LIQUIDITY_SHIFT", "La transizione fra sessioni (Tokyo->Londra->NY) sposta la composizione di partecipanti e liquidita', cambiando il comportamento strutturale del prezzo.",
                ["CLAIM-0029", "CLAIM-0030", "CLAIM-0053", "CLAIM-0061", "CLAIM-0066", "CLAIM-0085",
                 "CLAIM-0094", "CLAIM-0095", "CLAIM-0100", "CLAIM-0101"]),
    "MECH-31": ("DXY_REAL_YIELDS_GOLD_VALUATION", "Il prezzo dell'oro e' influenzato da relazioni cross-asset (DXY, tassi reali) come driver di valutazione di medio periodo, con possibili rotture temporanee in fasi di flight-to-safety.",
                ["CLAIM-0104", "CLAIM-0105"]),
    "MECH-32": ("PAIRS_COINTEGRATION_MEAN_REVERSION", "Due strumenti cointegrati condividono un equilibrio di lungo periodo; deviazioni dello spread tendono a rientrare.",
                ["CLAIM-0087"]),
    "MECH-33": ("DUAL_MOVING_AVERAGE_MOMENTUM", "Il momentum derivato dalla differenza fra una media mobile corta e una lunga del midpoint di barra segnala continuazione.",
                ["CLAIM-0088"]),
}

CLAIM_TO_MECH = {}
for mech_id, (name, definition, claim_ids) in MECHANISMS.items():
    for cid in claim_ids:
        CLAIM_TO_MECH.setdefault(cid, []).append(mech_id)


def main():
    corpus_path = os.path.join(PHASE72_DIR, "external_hypothesis_corpus_v1.json")
    with open(corpus_path, encoding="utf-8") as f:
        corpus_doc = json.load(f)
    claims = corpus_doc["payload"]["claims"]

    unmapped = []
    for c in claims:
        mech_ids = CLAIM_TO_MECH.get(c["claim_id"], [])
        c["candidate_mechanism_ids"] = mech_ids
        if not mech_ids:
            unmapped.append(c["claim_id"])

    save_json(corpus_path, wrap_with_provenance(corpus_doc["payload"], "phase7/phase7_2/build_mechanism_registry.py (claim tagging pass)"))

    mechanism_entries = []
    for mech_id, (name, definition, claim_ids) in MECHANISMS.items():
        source_types = set()
        for cid in claim_ids:
            claim = next((c for c in claims if c["claim_id"] == cid), None)
            if claim:
                source_types.add(claim["source_type"])
        mechanism_entries.append({
            "mechanism_id": mech_id,
            "name": name,
            "definition": definition,
            "supporting_claim_ids": claim_ids,
            "n_supporting_claims": len(claim_ids),
            "n_distinct_source_types": len(source_types),
            "source_types": sorted(source_types),
        })

    registry_payload = {
        "n_mechanisms": len(mechanism_entries),
        "n_claims_mapped": len(claims) - len(unmapped),
        "n_claims_unmapped": len(unmapped),
        "unmapped_claim_ids": unmapped,
        "mechanisms": mechanism_entries,
    }
    save_json(os.path.join(PHASE72_DIR, "market_mechanism_registry_v1.json"),
              wrap_with_provenance(registry_payload, "phase7/phase7_2/build_mechanism_registry.py"))

    print(f"n_mechanisms={len(mechanism_entries)} n_claims_mapped={len(claims)-len(unmapped)} n_unmapped={len(unmapped)}")
    if unmapped:
        print("UNMAPPED:", unmapped)
    print("written: external_hypothesis_corpus_v1.json (candidate_mechanism_ids aggiornati)")
    print("written: market_mechanism_registry_v1.json")


if __name__ == "__main__":
    main()
