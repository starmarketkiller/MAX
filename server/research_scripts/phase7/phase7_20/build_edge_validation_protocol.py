#!/usr/bin/env python3
"""Phase 7.20 punto 6 - proposta di protocollo unico EDGE_VALIDATION_V1,
applicabile a qualunque strategia READY_FOR_EDGE_VALIDATION di questa o
future shortlist. Solo SPECIFICA in questa fase - nessuna esecuzione,
nessun parameter sweep, nessun risk sizing."""
import os
import sys

PHASE720_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE720_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def build():
    payload = {
        "protocol_name": "EDGE_VALIDATION_V1",
        "principle": "Ogni stadio e' un CANCELLO (gate) sequenziale - non si passa allo stadio "
                    "successivo se quello precedente non e' superato. Nessuno stadio usa optimization, "
                    "risk sizing aggressivo, compounding o portfolio testing (fuori scope, blocco "
                    "successivo dichiarato dall'utente).",
        "stages": {
            "0_preregistration": {
                "what": "Prima di guardare QUALUNQUE risultato del nuovo campione/periodo: dichiarare "
                       "per iscritto (preregistration, stesso schema gia' usato in Phase 7 per TSI/"
                       "ORDER_BLOCK) l'ipotesi esatta, la metrica di successo, il periodo di holdout, la "
                       "soglia minima di campione, e i costi da includere. Hash del documento salvato "
                       "PRIMA del run.",
                "gate_to_pass": "Documento di preregistrazione esiste e ha un hash verificabile "
                               "precedente a qualunque dato di outcome.",
            },
            "1_baseline_edge": {
                "what": "Misurare il comportamento grezzo (MFE/MAE/win-rate/PF) sul campione di scoperta "
                       "gia' esistente (o un primo run se non esiste, vedi shortlist), SENZA costi, SENZA "
                       "filtri aggiuntivi, confrontato con un benchmark esplicito (random entry o "
                       "buy-and-hold sullo stesso periodo/simbolo/direzione) - non un numero isolato.",
                "gate_to_pass": "Il comportamento e' misurabilmente diverso dal benchmark su questo "
                               "campione (qualunque direzione) - se NON lo e', si ferma qui, "
                               "GENUINE_NO_EDGE_CANDIDATE, nessun ulteriore stadio.",
            },
            "2_costs": {
                "what": "Applicare spread reale + slippage (segnale->fill, gia' misurato se disponibile) "
                       "+ commissione + swap/overnight al risultato dello stadio 1. Riportare il "
                       "risultato CON e SENZA costi fianco a fianco, mai solo il numero netto.",
                "gate_to_pass": "Il vantaggio misurato allo stadio 1 sopravvive (anche ridotto) "
                               "all'applicazione dei costi reali - se i costi lo cancellano "
                               "completamente, fermarsi qui.",
            },
            "3_oos": {
                "what": "Testare lo stesso comportamento su un campione temporalmente SUCCESSIVO e "
                       "indipendente da quello di scoperta (mai uno split retroattivo dello stesso "
                       "campione senza un vero confine temporale) - preregistrato allo stadio 0.",
                "gate_to_pass": "Il comportamento (direzione dell'effetto, non necessariamente la "
                               "magnitudo esatta) e' presente anche nell'OOS.",
            },
            "4_execution_realism": {
                "what": "Verificare che il segnale sia eseguibile nell'ordine causale corretto (nessun "
                       "look-ahead), con fill realistici (non solo teorici) - riusa "
                       "ANTI_LEAKAGE_SPECIFICATION_V1 e SOURCE_OF_TRUTH_HIERARCHY_V1 (Phase 7.19).",
                "gate_to_pass": "Nessuna violazione di causalita' trovata; fill realistici disponibili "
                               "per almeno un sottoinsieme rappresentativo del campione.",
            },
            "5_minimum_viable_capital": {
                "what": "Solo DOPO aver superato 1-4: stimare (non ancora impostare) il capitale minimo "
                       "sotto cui lo SL tipico in valuta/lotto minimo consumerebbe una frazione eccessiva "
                       "del conto (soglia da definire separatamente, non in questa fase) - nessun "
                       "position sizing proposto qui, solo la domanda 'e' verificabile con 300/500/1000 "
                       "euro?' preparata per il blocco successivo.",
                "gate_to_pass": "N/A - stadio di preparazione per il blocco successivo dichiarato "
                               "dall'utente (baseline edge -> costi -> OOS -> execution -> minimum "
                               "viable capital -> demo forward), non un gate finale di questo protocollo.",
            },
            "6_demo_forward_readiness": {
                "what": "Solo dopo 1-5 superati: la strategia e' idonea per un forward test in demo (non "
                       "ancora proposto qui, ne' autorizzato in questa fase).",
                "gate_to_pass": "N/A - fuori scope di questa fase.",
            },
        },
        "explicit_exclusions_this_protocol_never_does": [
            "parameter sweep / TP-SL optimization (qualunque forma)",
            "risk sizing aggressivo o compounding",
            "portfolio testing (piu' strategie insieme)",
            "promozione a live/demo automatica al superamento degli stadi",
            "uso del PF storico da solo per decidere l'esito di uno stadio",
        ],
        "reuses_from_phase_7_19": ["EVENT_AUDIT_PACKET_V1 (cattura evento)", "FIDELITY_FRAMEWORK_V1 "
                                  "(livello di fiducia dei dati usati)", "ANTI_LEAKAGE_SPECIFICATION_V1 "
                                  "(stadio 4)", "SOURCE_OF_TRUTH_HIERARCHY_V1 (mai Python come fonte "
                                  "primaria per una decisione economica)"],
        "not_executed_in_this_phase": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE720_DIR, "edge_validation_protocol_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
