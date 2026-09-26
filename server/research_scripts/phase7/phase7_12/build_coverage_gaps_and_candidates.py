#!/usr/bin/env python3
"""Phase 7.12 - Scansione statica MIRATA delle lacune di copertura
(punto 2 della task). Documenta esattamente cosa e' stato ricontrollato
in questa fase, cosa e' stato trovato, e cosa resta esplicitamente NON
verificato. Nessun DEFECT_CONFIRMED dichiarato senza evidenza diretta
sul codice."""
import os
import sys

PHASE712_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE712_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import save_json, wrap_with_provenance  # noqa: E402


def build():
    method = {
        "step_1": "Rilettura diretta di build_stateful_strategy_static_audit.py (Phase "
            "7.10) per estrarre la METODOLOGIA ESATTA usata: grep di struct globali "
            "che matchano il pattern '*State g_*' + variabili 'static' function-local "
            "nei 4 file NXS_Strategies*.mqh, poi lettura manuale del codice per "
            "ciascun candidato trovato cosi'.",
        "step_2": "Grep INDIPENDENTE e piu' ampio in questa fase su TUTTI e 4 i file "
            "(pattern: dichiarazioni globali che iniziano con un tipo struct o "
            "'datetime'/'int'/'double'/'bool' seguito da 'g_') - per trovare stato "
            "globale che NON segue la convenzione '*State' e sarebbe stato quindi "
            "escluso dal grep originale.",
        "step_3": "Per ogni variabile trovata NON gia' presente nei 20 candidati di "
            "Phase 7.10, lettura diretta del codice della funzione strategia "
            "corrispondente: TF usato (NXS_EffTF() dinamico vs hardcoded), presenza "
            "di una guardia TF prima della mutazione di stato, natura dello stato.",
        "step_4": "Verifica incrociata dei risultati contro il campo 'stateful' del "
            "census Phase 7.11, per trovare discrepanze fra quanto dichiarato e quanto "
            "verificato direttamente sul codice in questa fase.",
        "explicitly_not_done": (
            "NON e' stata eseguita una lettura riga-per-riga di ogni singola funzione "
            "NXS_Strat_* del progetto (71+ funzioni Python sig_*, 60+ funzioni MQL5) - "
            "la scansione si e' concentrata su (a) le identita' gia' segnalate come "
            "gap potenziali da Phase 7.11 (CRT, FVG_MIT_WINDOW, OB_MIT, motore NXR), e "
            "(b) un grep strutturale ampio ma non esaustivo su TUTTE le possibili "
            "convenzioni di naming per stato globale. Un residuo di lacuna NON "
            "verificata resta esplicitamente dichiarato sotto."
        ),
    }

    findings = [
        {
            "candidate": "FVG_MIT_WINDOW",
            "gap_type": "STATEFUL_FIELD_INCORRECT_IN_CENSUS + NOT_IN_PHASE_7_10_AUDIT",
            "verified_state": "g_fvgMitWBull[NXS_FVGMITW_MAX_ZONES] (pool di zone FVG), "
                "g_fvgMitWBear[...], g_fvgMitWBullCount, g_fvgMitWBearCount, "
                "g_fvgMitWLastBar - NXS_Strategies_SMC.mqh:260-310.",
            "why_missed_by_7_10": "Le variabili non seguono la convenzione di naming "
                "'*State g_*' (sono array con nomi 'g_fvgMitW*', non una struct "
                "'SomeState g_qualcosa') - il grep esaustivo di Phase 7.10 le ha "
                "strutturalmente saltate.",
            "mechanism_check": {
                "tf_source": "NXS_EffTF() (dinamico) - riga 280: "
                    "iTime(g_sym, NXS_EffTF(), 1)",
                "guard_before_mutation": "NESSUNA guardia sul TF attivo prima di "
                    "mutare g_fvgMitWBull/Bear - solo un gate 'nuova barra' "
                    "(tBar1==g_fvgMitWLastBar) che e' esso stesso derivato da "
                    "NXS_EffTF(), quindi soggetto allo stesso 'inseguimento' gia' "
                    "visto in BREAKOUT_ACC/BAR_UPDN pre-fix.",
                "state_nature": "pool di zone (creazione, invecchiamento/rimozione via "
                    "_fvgMitW_removeBull/Bear) - piu' vicino a una struttura dati "
                    "condivisa che a un semplice cooldown.",
            },
            "documentary_evidence": (
                "Commento del codice (righe 275-278): 'Aggiorna il registro UNA VOLTA "
                "per barra nuova... deve girare sempre, anche se il toggle e' spento in "
                "questo giro, altrimenti il registro perde barre e la finestra si "
                "sfasa rispetto al Python, che itera ogni candela senza saltarne mai "
                "una.' - suggerisce un modello mentale a SINGOLO timeframe (paragone "
                "esplicito con un cammino Python barra-per-barra), non un router "
                "multi-TF con piu' pass sullo stesso tick - la STESSA ambiguita' "
                "intento-vs-difetto risolta per BREAKOUT_ACC con adjudication "
                "documentale dedicata (Phase 7.9F, 6 fonti indipendenti)."
            ),
            "classification": "SUSPECT",
            "why_not_defect_confirmed": (
                "Manca l'adjudication documentale/empirica dedicata (tipo Phase 7.9F) "
                "che ha permesso di passare da SUSPECT a DEFECT_CONFIRMED per "
                "BREAKOUT_ACC - un solo commento, per quanto suggestivo, non e' "
                "sufficiente secondo lo stesso standard di rigore gia' applicato in "
                "questo progetto."
            ),
            "operational_relevance": "FVG_MIT_WINDOW e' default ENABLED "
                "(InpStrat_FVG_MIT_WINDOW=true) MA strutturalmente bloccata "
                "dall'UNKNOWN_STRATEGY_REGISTRY_GAP (Phase 7.11) - non puo' aprire "
                "trade oggi indipendentemente da questo secondo difetto. Se il gap di "
                "registry venisse corretto senza sapere di questo secondo problema, "
                "si attiverebbe silenziosamente un SECONDO difetto non testato.",
        },
        {
            "candidate": "OB_MIT",
            "gap_type": "STATEFUL_FIELD_INCORRECT_IN_CENSUS + NOT_IN_PHASE_7_10_AUDIT",
            "verified_state": "NESSUNO stato proprio - eredita g_obBuy/g_obSell di "
                "ORDER_BLOCK per chiamata diretta.",
            "why_missed_by_7_10": "Il grep di Phase 7.10 cercava DICHIARAZIONI di "
                "stato dentro le funzioni NXS_Strat_* - NXS_Strat_OB_Mitigation_"
                "Structural() non dichiara ne' usa direttamente alcuna variabile di "
                "stato, quindi non e' stata segnalata dal grep. La sua esposizione al "
                "difetto e' indiretta (via chiamata di funzione), non rilevabile da "
                "un grep lessicale.",
            "mechanism_check": {
                "call_graph": "NXS_Strat_OB_Mitigation_Structural() (NXS_Strategies_"
                    "SMC.mqh:355) chiama DIRETTAMENTE 'SNXSSignal raw = "
                    "NXS_Strat_OrderBlock();' e ne riusa il risultato - nessuna logica "
                    "propria oltre un floor sullo score.",
                "implication": "Ogni chiamata a OB_MIT ESEGUE la stessa mutazione di "
                    "stato (g_obBuy/g_obSell) gia' classificata DEFECT_CONFIRMED per "
                    "ORDER_BLOCK - non e' un'analogia strutturale, e' la STESSA "
                    "esecuzione di codice.",
            },
            "documentary_evidence": "Nessuna necessaria - la chiamata diretta e' "
                "evidenza sufficiente e diretta (non richiede adjudication su intento, "
                "e' un fatto del grafo delle chiamate).",
            "classification": "DEFECT_CONFIRMED",
            "why_confirmed_directly": (
                "A differenza degli altri 10 residui (evidenza STRUTTURALE per "
                "analogia, mai empiricamente misurata per la strategia specifica), "
                "qui l'evidenza e' un fatto diretto del codice: OB_MIT non ha una "
                "propria logica di stato, eredita quella di ORDER_BLOCK per "
                "costruzione. Resta comunque non empiricamente misurato (nessun "
                "esperimento diagnostico dedicato eseguito in questa fase)."
            ),
            "operational_relevance": "OB_MIT e' default DISABLED "
                "(InpStrat_OB_Mit=false) - selettore 20 (indipendente da ORDER_BLOCK, "
                "selettore 15). Se mai abilitata, contamina LO STESSO stato globale "
                "condiviso con ORDER_BLOCK (default ENABLED) - un canale di "
                "propagazione incrociata fra le due identita', distinto dalla "
                "contaminazione cross-TF di ciascuna singolarmente.",
        },
        {
            "candidate": "CRT",
            "gap_type": "VERIFIED_NO_GAP (controllo negativo)",
            "verified_state": "NESSUNO - NXS_Strat_CRT() e' interamente stateless "
                "(sweptHigh/sweptLow ricalcolati da zero a ogni chiamata da "
                "iHigh/iLow/iClose correnti, nessuna struct/static/globale).",
            "classification": "NOT_APPLICABLE",
            "note": "Verificato DIRETTAMENTE per escludere un falso positivo - CRT usa "
                "NXS_EffTF() per il PROPRIO calcolo (come ogni strategia multi-TF) ma "
                "non ha alcuno stato da contaminare fra chiamate. Resta soggetta a "
                "UNKNOWN_STRATEGY_REGISTRY_GAP (Phase 7.11), pattern DIVERSO e "
                "indipendente da questo.",
        },
        {
            "candidate": "NXR_* (motore NXS_ReusePerformancePack.mqh: IFVG/FVG_MIT/"
                "OB_MIT/MalaysianSNR)",
            "gap_type": "NOT_IN_PHASE_7_10_AUDIT_SCOPE (file diverso)",
            "note": "Phase 7.10 ha scansionato solo NXS_Strategies*.mqh (4 file) - "
                "NXS_ReusePerformancePack.mqh non e' fra questi, quindi nessuna "
                "funzione NXR_Strat_* e' stata controllata per questo pattern. Phase "
                "7.11 ha gia' verificato 0 call site per queste funzioni (codice morto "
                "irraggiungibile) - se davvero irraggiungibile, il gap e' "
                "NOT_APPLICABLE nella pratica, ma la verifica di irraggiungibilita' "
                "era per grep testuale, non per analisi statica del flusso di "
                "controllo completa - NON RIVERIFICATO in questa fase.",
            "classification": "NOT_ENOUGH_EVIDENCE",
        },
    ]

    residual_gap = {
        "description": (
            "Questa scansione ha verificato direttamente CRT, FVG_MIT_WINDOW, OB_MIT "
            "(le identita' gia' segnalate come sospette da Phase 7.11) piu' un grep "
            "strutturale piu' ampio sulle dichiarazioni globali nei 4 file "
            "NXS_Strategies*.mqh. NON ha ri-verificato riga-per-riga la logica INTERNA "
            "di ciascuna delle 71 funzioni Python sig_* ne' di tutte le 60+ funzioni "
            "MQL5 NXS_Strat_* per pattern DIVERSI da CROSS_TIMEFRAME_STATE_"
            "CONTAMINATION (es. altri tipi di bias look-ahead, altri bug di accounting) "
            "- questo resta un limite dichiarato, non un'affermazione di copertura "
            "esaustiva."
        ),
        "recommended_future_scan": (
            "Un grep dedicato per il pattern IDENTICO applicato qui (dichiarazioni "
            "globali NON-'*State*') esteso anche a file di strategia fuori da "
            "NXS_Strategies*.mqh (es. NXS_ReusePerformancePack.mqh per il motore NXR, "
            "se mai risultasse raggiungibile) sarebbe il prossimo passo di copertura "
            "naturale, non eseguito qui per restare nello scope richiesto."
        ),
    }

    return {
        "phase": "7.12",
        "scope": "Scansione statica MIRATA (punto 2 della richiesta) - non un nuovo "
            "census, non una ri-esecuzione dell'audit 7.10 completo.",
        "no_defect_confirmed_without_direct_evidence": True,
        "method": method,
        "findings": findings,
        "residual_coverage_gap_declared": residual_gap,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE712_DIR, "coverage_gaps_and_new_candidates_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"findings: {len(payload['findings'])}")
    return doc


if __name__ == "__main__":
    main()
