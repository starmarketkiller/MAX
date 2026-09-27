#!/usr/bin/env python3
"""Phase 7.19 punto 9 - FIDELITY_FRAMEWORK_V1: misura ESCLUSIVAMENTE
quanto e' fedele la ricostruzione del contesto reale, MAI un voto sulla
strategia. Criteri precisi (non solo descrittivi) per i 4 livelli."""
import os
import sys

PHASE719_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE719_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def build():
    payload = {
        "framework_name": "FIDELITY_FRAMEWORK_V1",
        "principle": "La fedelta' misura la ricostruzione, non la strategia. Un Visual Audit "
                    "con fidelity bassa (C/D) non puo' sostenere conclusioni forti - "
                    "un'analisi che ignora questo vincolo e' invalida per costruzione.",
        "tiers": {
            "A": {
                "label": "Fidelity A - massima",
                "criteria_all_required": [
                    "same_broker_feed: stesso broker/feed del trade reale",
                    "tick_or_m1_available: dati tick o M1 disponibili per il periodo",
                    "real_fill: fill REALE (non stimato) noto (actual_fill_price.is_proxy=false)",
                    "real_state_snapshot: state_before/state_after catturati LIVE "
                    "(capture_method=LIVE_EA_INSTRUMENTATION), non ricostruiti offline",
                    "runtime_identity_verified: RUNTIME_IDENTITY_MANIFEST_V1 disponibile e "
                    "corrispondente",
                    "timezone_verified: timezone/DST del timestamp verificati "
                    "(confidence=VERIFIED su tutti i timestamp rilevanti)",
                ],
                "example_from_this_project": "Trace EA reale ORDER_BLOCK/TSI (Phase 7.14/7.18) "
                                            "SOLO se accoppiato a un fill reale e a un manifest "
                                            "di identita' runtime - nessun esempio in questo "
                                            "progetto soddisfa OGGI tutti i criteri (manca il "
                                            "manifest, non ancora implementato)",
            },
            "B": {
                "label": "Fidelity B - alta",
                "criteria_all_required": [
                    "same_ohlc_feed: stesso feed OHLC (non necessariamente tick)",
                    "limited_lower_granularity: granularita' inferiore limitata ma presente "
                    "(es. M15 quando servirebbe M1)",
                    "state_partially_reconstructed: stato ricostruito da un trace reale "
                    "dell'EA (anche se non ogni campo e' catturato)",
                ],
                "example_from_this_project": "Trace EA reale ORDER_BLOCK (Phase 7.14, tick "
                                            "reali MT5, stato zona catturato live, ma fill "
                                            "reale/manifest non ancora integrati in un unico "
                                            "packet)",
            },
            "C": {
                "label": "Fidelity C - moderata",
                "criteria_any_present": [
                    "different_feed: feed diverso da quello del trade originale (es. serie "
                    "ricampionata M15->D1)",
                    "fill_proxy: fill stimato/proxy, non reale (actual_fill_price.is_proxy=true)",
                    "state_reconstructed: stato interamente ricostruito offline "
                    "(capture_method=RECONSTRUCTED_OFFLINE)",
                    "incomplete_intraday: dati intraday incompleti per il periodo",
                ],
                "example_from_this_project": "Ricostruzione Python TF-scoped di ORDER_BLOCK/TSI "
                                            "(Phase 7.13/7.17) su serie M15 ricampionata - "
                                            "PARTIAL_STRUCTURAL_MODEL, non validata come parity "
                                            "evento-per-evento (Phase 7.16)",
            },
            "D": {
                "label": "Fidelity D - illustrativa",
                "criteria_any_present": [
                    "illustrative_only: ricostruzione a scopo puramente illustrativo",
                    "insufficient_data: dati insufficienti per un giudizio scientifico",
                    "structural_only_no_runtime_trace: SOLO informazioni strutturali "
                    "(funzione, stato dichiarato, TF canonico) senza alcun trace di runtime "
                    "reale per l'evento specifico",
                ],
                "example_from_this_project": "Un packet costruito per una strategia SENZA "
                                            "trace reale disponibile, usando solo la sua "
                                            "identita' statica (census/registry) - vedi "
                                            "l'esempio SH_BMS_RTO in questa fase",
                "explicit_limitation": "NESSUNA conclusione economica o di edge puo' essere "
                                      "tratta da un audit a fidelity D - solo verifica "
                                      "strutturale che lo schema riesca a rappresentare la "
                                      "strategia.",
            },
        },
        "determination_rule": "Il tier e' determinato dal criterio PIU' BASSO soddisfatto fra "
                             "tutti i componenti del packet (prezzo, stato, timestamp) - un "
                             "packet con fill reale ma stato ricostruito offline non puo' "
                             "dichiararsi Fidelity A, al massimo B/C a seconda degli altri "
                             "criteri.",
        "downstream_constraint": "Un VISUAL_AUDIT_RESULT_V1 con fidelity_of_this_audit in "
                                "{C, D} DEVE essere etichettato come OBSERVATION o HYPOTHESIS, "
                                "MAI come VALIDATED_RESULT (vedi ANTI_BIAS_RULES_V1).",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE719_DIR, "fidelity_framework_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
