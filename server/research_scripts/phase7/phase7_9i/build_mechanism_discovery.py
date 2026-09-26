#!/usr/bin/env python3
"""Phase 7.9I - Mechanism Discovery. Sintetizza Edge Decomposition, Path
Anatomy e Natural Horizon per valutare categorie di meccanismo candidate,
ciascuna con evidenza a favore/contro, confidence e spiegazioni
alternative. Nessuna categoria assunta a priori come vincente.
"""
import os
import sys

PHASE79I_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402


def build():
    edge = load_json(os.path.join(PHASE79I_DIR, "breakout_acc_edge_decomposition_v1.json"))["payload"]
    path = load_json(os.path.join(PHASE79I_DIR, "breakout_acc_path_anatomy_v1.json"))["payload"]
    horizon = load_json(os.path.join(PHASE79I_DIR, "breakout_acc_natural_horizon_v1.json"))["payload"]

    by_dir = path["aggregate"]["by_direction"]
    buy = by_dir["BUY"]
    sell = by_dir["SELL"]
    htf = edge["decomposition"]["6_htf_context_causal_proxy_trend_aligned"]
    atr_tercile = edge["decomposition"]["7_volatility_regime_atr20_tercile"]
    mag_tercile = edge["decomposition"]["3_trigger_geometry_breakout_magnitude_price_units_tercile"]

    mechanisms = []

    mechanisms.append({
        "mechanism": "TREND_PERSISTENCE_DIRECTION_DEPENDENT",
        "description": "Il comportamento favorevole osservato e' concentrato quasi "
            "interamente sui BUY, coerente con GOLD in un trend rialzista secolare "
            "2019-2026 (~1280->~4500) - il segnale potrebbe catturare principalmente "
            "l'allineamento con un trend gia' in corso, non un edge di breakout simmetrico.",
        "evidence_for": [
            f"BUY: {buy['n_continuation']}/{buy['n']} continuation a 60 barre D1 "
                f"({round(100*buy['n_continuation']/buy['n'],1)}%) vs SELL: "
                f"{sell['n_continuation']}/{sell['n']} ({round(100*sell['n_continuation']/sell['n'],1)}%) "
                "- asimmetria molto ampia, non spiegabile da rumore campionario da sola.",
            f"BUY MFE mediano={buy['mfe']['median']} vs SELL MFE mediano={sell['mfe']['median']} "
                "- BUY sistematicamente piu' favorevole.",
            f"HTF proxy (EMA100 causale): {htf.get('True',{}).get('n','?')}/47 eventi OPENED "
                "sono trend-aligned (100%) - NESSUN evento e' stato eseguito contro il trend "
                "EMA100 causale, un pattern perfettamente confuso con la direzione.",
        ],
        "evidence_against": [
            "Il codice di NXS_Strat_BreakoutAcc() non contiene alcun filtro di trend/EMA "
                "esplicito (verificato su MQL5/Include/NEXUS_v1/NXS_Strategies.mqh) - il "
                "100% trend-alignment e' un fenomeno EMERGENTE del mercato in questo "
                "periodo, non una regola codificata.",
            "SELL n=11 e' piccolo - un singolo evento SELL anomalo potrebbe pesare "
                "sproporzionatamente sulla percentuale di continuation SELL.",
        ],
        "alternative_explanations": [
            "Il campione copre quasi esclusivamente un regime di mercato (bull market "
                "GOLD pluriennale) - un periodo con un regime opposto (bear/range) non e' "
                "rappresentato, quindi non si puo' escludere che il pattern si inverta in "
                "condizioni di mercato diverse.",
        ],
        "confidence": "MODERATE - pattern ampio e coerente su piu' analisi indipendenti "
            "(continuation rate, MFE/MAE, HTF proxy), ma confuso con un singolo regime di "
            "mercato osservato e con N(SELL)=11 piccolo.",
    })

    mechanisms.append({
        "mechanism": "CONTINUATION_SYMMETRIC_BREAKOUT",
        "description": "L'ipotesi originale/naive: il breakout (in ENTRAMBE le direzioni) "
            "tende a continuare nella direzione del segnale.",
        "evidence_for": [
            f"Aggregato (BUY+SELL): {path['aggregate']['continuation_vs_failure_at_60d1']['CONTINUATION']}"
                f"/{path['aggregate']['n_events']} continuation a 60 barre - maggioranza, "
                "ma non schiacciante.",
            "Natural Horizon: il ritorno medio close-to-close (aggregato, direction-"
                "adjusted) cresce in modo pressoche' monotono da barra 1 a barra 60, CI95% "
                "esclude lo zero per 43 barre consecutive (18-60).",
        ],
        "evidence_against": [
            "La sola vista aggregata NASCONDE l'asimmetria BUY/SELL massiccia (vedi "
                "TREND_PERSISTENCE_DIRECTION_DEPENDENT) - il 'continuation' aggregato e' "
                "trainato quasi interamente dai BUY.",
            f"SELL da solo mostra continuation solo {sell['n_continuation']}/{sell['n']} "
                f"({round(100*sell['n_continuation']/sell['n'],1)}%) - fortemente CONTRO "
                "una continuation simmetrica.",
        ],
        "alternative_explanations": ["Vedi TREND_PERSISTENCE_DIRECTION_DEPENDENT - la "
            "spiegazione piu' parsimoniosa per il pattern aggregato e' l'asimmetria "
            "direzionale, non un meccanismo di continuation universale."],
        "confidence": "LOW come meccanismo SIMMETRICO (fortemente contraddetto dalla "
            "scomposizione BUY/SELL) - MODERATE se ristretto alla sola direzione BUY.",
    })

    n_high_atr = atr_tercile.get("HIGH", {}).get("n", 0)
    mechanisms.append({
        "mechanism": "VOLATILITY_EXPANSION",
        "description": "I breakout che avvengono in regime di volatilita' (ATR20 causale) "
            "piu' alta mostrano un percorso post-evento migliore.",
        "evidence_for": [
            f"Terzile ATR20 HIGH (n={n_high_atr}): MFE mediano="
                f"{atr_tercile['HIGH']['mfe']['median']} vs LOW/MID "
                f"({atr_tercile['LOW']['mfe']['median']}/{atr_tercile['MID']['mfe']['median']}) "
                "- differenza sostanziale, stessa direzione del terzile di magnitudine "
                "del breakout (vedi sotto, i due sono probabilmente correlati).",
            f"Terzile magnitudine breakout HIGH: MFE mediano="
                f"{mag_tercile['HIGH']['mfe']['median']}, MAE mediano="
                f"{mag_tercile['HIGH']['mae']['median']} - il piu' favorevole rapporto "
                "MFE/MAE fra i 3 terzili.",
        ],
        "evidence_against": [
            "ATR20 causale e magnitudine del breakout sono probabilmente correlate fra "
                "loro (un range piu' ampio/volatile produce naturalmente breakout di "
                "magnitudine maggiore) - non e' chiaro se il volume regime sia un fattore "
                "indipendente o solo un proxy della stessa geometria del breakout.",
            "N per terzile (~15-16) e' piccolo - stime di mediana instabili.",
        ],
        "alternative_explanations": ["La magnitudine del breakout stesso (non la "
            "volatilita' generale) potrebbe essere il vero driver - i due terzili si "
            "sovrappongono parzialmente nel campione."],
        "confidence": "LOW-MODERATE - pattern presente ma confuso con la magnitudine del "
            "breakout, N per gruppo piccolo.",
    })

    mechanisms.append({
        "mechanism": "DELAYED_BREAKOUT_CONTINUATION",
        "description": "Il vantaggio informativo del segnale non si materializza "
            "immediatamente ma emerge con un ritardo (alcune barre dopo l'evento).",
        "evidence_for": [
            "Natural Horizon: il CI95% del ritorno medio NON esclude lo zero in modo "
                "stabile fino a circa barra 10-18, poi lo esclude establmente fino a barra "
                "60 - suggestivo di un vantaggio che si consolida con un ritardo, non "
                "immediato.",
            f"bars_to_mfe mediano (BUY)={buy['bars_to_mfe']['median']} barre D1 - il "
                "massimo movimento favorevole tipicamente arriva MOLTE barre dopo "
                "l'ingresso, non nell'immediato.",
        ],
        "evidence_against": [
            f"MAE viene raggiunto PRIMA di MFE nel {path['aggregate']['mae_reached_before_mfe']['pct']}% "
                "degli eventi (57.4%) - un'adverse excursion iniziale e' altrettanto "
                "comune di un ritardo puramente favorevole, coerente con un semplice "
                "shake-out iniziale piu' che un pattern di 'delayed continuation' pulito.",
        ],
        "alternative_explanations": ["Il ritardo osservato potrebbe semplicemente "
            "riflettere il tempo naturale di sviluppo di un trend gia' in corso "
            "(TREND_PERSISTENCE), non un meccanismo specifico di 'breakout ritardato'."],
        "confidence": "LOW-MODERATE - alcuni elementi di supporto (CI95 tardivo, bars_to_mfe "
            "alto) ma non distinguibile in modo netto da TREND_PERSISTENCE.",
    })

    mechanisms.append({
        "mechanism": "FALSE_BREAK_AVOIDANCE",
        "description": "Il gate di Acceptance (2 chiusure consecutive oltre il range di 20 "
            "barre) evita i falsi breakout, catturando solo breakout genuini.",
        "evidence_for": [
            "Per costruzione, l'Acceptance richiede 2 chiusure consecutive oltre il range "
                "(non 1 sola rottura intrabar) - un filtro strutturale contro whipsaw "
                "immediato.",
            f"MFE raggiunto prima di MAE solo nel {path['aggregate']['mfe_reached_before_mae']['pct']}% "
                "dei casi - MA quando succede, spesso precede movimenti favorevoli ampi.",
        ],
        "evidence_against": [
            f"{path['aggregate']['continuation_vs_failure_at_60d1']['FAILURE']}/"
                f"{path['aggregate']['n_events']} eventi sono comunque classificati FAILURE "
                "a 60 barre - il filtro Acceptance non elimina una quota sostanziale di "
                "esiti sfavorevoli, specialmente lato SELL.",
        ],
        "alternative_explanations": ["Il filtro Acceptance a 2 chiusure e' identico per "
            "BUY e SELL (nessuna asimmetria nel codice) - non spiega da solo l'asimmetria "
            "direzionale osservata."],
        "confidence": "LOW - plausibile per costruzione del gate, ma nessuna evidenza "
            "diretta specifica di questo dataset lo conferma oltre il design della regola "
            "stessa.",
    })

    mechanisms.append({
        "mechanism": "NO_STABLE_MECHANISM_NOISE_DRIVEN",
        "description": "I pattern osservati sono compatibili con rumore campionario su un "
            "N piccolo (47 eventi, 8 anni, 11 SELL).",
        "evidence_for": [
            "N totale piccolo, SELL n=11 particolarmente piccolo per conclusioni robuste.",
            "Distribuzione per anno molto irregolare (2019 n=3, 2026 n=1) - concentrazione "
                "temporale non uniforme.",
            "Il CI95% del Natural Horizon e' descrittivo, non corretto per test multipli "
                "su 60 barre - un falso positivo su una singola barra non sarebbe "
                "sorprendente.",
        ],
        "evidence_against": [
            "L'asimmetria BUY/SELL e' troppo ampia (66.7% vs 9.1% continuation) per essere "
                "spiegata solo da rumore su un singolo gruppo piccolo, in particolare "
                "perche' converge con un secondo segnale indipendente (HTF proxy causale "
                "100% trend-aligned).",
            "Il pattern di crescita monotona del ritorno medio nel Natural Horizon e' "
                "coerente su tutta la finestra di 60 barre, non un singolo picco isolato.",
        ],
        "alternative_explanations": [],
        "confidence": "LOW come spiegazione UNICA - alcuni elementi (dimensione campione, "
            "concentrazione temporale) restano validi caveat trasversali a tutte le altre "
            "categorie.",
    })

    return {
        "phase": "7.9I",
        "question": "Che cosa sta realmente catturando BREAKOUT_ACC?",
        "mechanisms_evaluated": mechanisms,
        "primary_finding": (
            "L'evidenza piu' forte e convergente (da 3 analisi indipendenti - continuation "
            "rate, MFE/MAE per direzione, HTF proxy causale) indica che il comportamento "
            "favorevole osservato e' fortemente DIREZIONE-DIPENDENTE (quasi tutto sui BUY) "
            "e coincide con un periodo di trend rialzista secolare di GOLD. Questo rende "
            "TREND_PERSISTENCE_DIRECTION_DEPENDENT la spiegazione singola piu' supportata, "
            "con CONTINUATION_SYMMETRIC_BREAKOUT esplicitamente CONTRADDETTA come "
            "meccanismo simmetrico universale."
        ),
        "no_optimization_no_rescue": True,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79I_DIR, "breakout_acc_mechanism_discovery_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(payload["primary_finding"])
    return doc


if __name__ == "__main__":
    main()
