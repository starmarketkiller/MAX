#!/usr/bin/env python3
"""Phase 7.24 punto 1-2 - Funnel accounting: ogni conteggio (raw
event/generated/blocked/opened/closed/still-open) mappato allo stage
del funnel, con verifica ARITMETICA indipendente (non fidata dal solo
certificato) e adjudication del residuo 42 vs 43 vs 41."""
import os
import sys

PHASE724_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE724_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE724_DIR)
from nxs_liq_sweep_dataset_loader import (  # noqa: E402
    load_manifest, load_raw_rows, parse_certificate_funnel, pair_events, PHASE723_DIR)


def build():
    manifest, manifest_path = load_manifest()
    if manifest is None:
        return {"status": "NO_MANIFEST_FOUND"}

    rows = load_raw_rows(manifest)
    paired, unmatched_opens, opens_sorted, closes_sorted = pair_events(rows)

    cert_dest = manifest.get("certificate_dest")
    if cert_dest and not os.path.isabs(cert_dest):
        cert_dest = os.path.join(PHASE723_DIR, cert_dest)
    cert_funnel = parse_certificate_funnel(cert_dest) if cert_dest else None

    n_open_rows = len(opens_sorted)
    n_close_rows = len(closes_sorted)
    n_paired = len(paired)
    n_unmatched_opens = len(unmatched_opens)

    arithmetic_checks = {}
    if cert_funnel:
        g, b, oa, op, br = (cert_funnel["GENERATED"], cert_funnel["BLOCKED"],
                            cert_funnel["OPEN_ATTEMPT"], cert_funnel["OPENED"],
                            cert_funnel["BROKER_REJECT"])
        arithmetic_checks["generated_eq_blocked_plus_open_attempt"] = {
            "check": f"{g} == {b} + {oa}", "holds": g == b + oa}
        arithmetic_checks["open_attempt_eq_opened_plus_broker_reject"] = {
            "check": f"{oa} == {op} + {br}", "holds": oa == op + br}
        arithmetic_checks["certificate_opened_eq_csv_open_rows"] = {
            "check": f"{op} == {n_open_rows}", "holds": op == n_open_rows}
        arithmetic_checks["opened_eq_closed_plus_still_open"] = {
            "check": f"{op} == {n_close_rows} + {n_unmatched_opens}",
            "holds": op == n_close_rows + n_unmatched_opens}
    arithmetic_checks["close_rows_eq_paired_events"] = {
        "check": f"{n_close_rows} == {n_paired}", "holds": n_close_rows == n_paired}

    funnel_stages = [
        {"stage": "1_raw_event_generated", "count": cert_funnel["GENERATED"] if cert_funnel else None,
         "source": "certificato, riga --- Funnel ---, campo GENERATED",
         "meaning": "ogni barra D1 chiusa in cui il detector di sweep + filtro delivery-candle + "
                   "direzione producono un segnale valido (prima di qualunque gate applicativo)."},
        {"stage": "2_blocked_by_gate", "count": cert_funnel["BLOCKED"] if cert_funnel else None,
         "source": "certificato, campo BLOCKED (+ dettaglio gate_reasons)",
         "meaning": "segnale generato ma scartato da un gate del router (soprattutto "
                   "OPEN_POSITION: gia' una posizione LIQ_SWEEP aperta, dato che il selettore "
                   "7 e' single-position-at-a-time; in misura minore TF_GATE)."},
        {"stage": "3_open_attempt", "count": cert_funnel["OPEN_ATTEMPT"] if cert_funnel else None,
         "source": "certificato, campo OPEN_ATTEMPT",
         "meaning": "segnale passato tutti i gate, ordine di apertura tentato verso il broker "
                   "simulato del Tester."},
        {"stage": "4_broker_reject", "count": cert_funnel["BROKER_REJECT"] if cert_funnel else None,
         "source": "certificato, campo BROKER_REJECT",
         "meaning": "tentativo di apertura rifiutato dal broker simulato (fuori scope di questa "
                   "fase indagare il motivo specifico - non e' l'oggetto dell'adjudication "
                   "richiesta, nessuna anomalia dichiarata dal certificato su questo campo)."},
        {"stage": "5_opened", "count": n_open_rows,
         "source": "conteggio righe OPEN in NEXUS_trades.csv (strategy=LIQ_SWEEP) - "
                   "riconciliato 1:1 con il campo OPENED del certificato",
         "meaning": "posizione realmente aperta nel Tester - fonte di verita' riga-per-riga."},
        {"stage": "6_closed_within_window", "count": n_close_rows,
         "source": "conteggio righe CLOSE in NEXUS_trades.csv (strategy=LIQ_SWEEP)",
         "meaning": "posizione chiusa (SL/TP/altro) PRIMA della fine del periodo testato."},
        {"stage": "7_still_open_at_period_end", "count": n_unmatched_opens,
         "source": "OPEN senza CLOSE corrispondente dopo appaiamento FIFO cronologico corretto",
         "meaning": "posizione ancora aperta quando il Tester ha raggiunto period_end - MAI "
                   "chiusa nella finestra, quindi non ha e non potra' mai avere una riga CLOSE "
                   "in QUESTO run."},
        {"stage": "8_events_used_economically", "count": n_paired,
         "source": "appaiamento OPEN<->CLOSE cronologico (questa fase)",
         "meaning": "eventi con lifecycle completo (entry+exit+P&L reale) - il dataset primario "
                   "per qualunque futura edge validation."},
    ]

    residual_adjudication = [
        {
            "residual": "41 eventi appaiati (Phase 7.23) invece di 42 attesi (=n_close_rows)",
            "classification": "LOGGING_ACCOUNTING_GAP_ROOT_CAUSE_FOUND_AND_FIXED",
            "root_cause": "bug nell'harness (nxs_research_run_harness._detect_text_encoding, "
                "Phase 7.23): restituiva il codec esplicito 'utf-16-le'/'utf-16-be' invece del "
                "codec generico 'utf-16' - il primo NON rimuove il BOM dal testo decodificato, "
                "lasciando un carattere U+FEFF incollato al campo 'time' della PRIMISSIMA riga "
                "del file (il primo OPEN cronologico). U+FEFF (65279) ordina DOPO qualunque cifra "
                "ASCII in un confronto di stringhe, quindi quell'OPEN finiva in fondo alla lista "
                "ordinata invece che in testa, disallineando l'appaiamento FIFO e facendo fallire "
                "esattamente un confronto (l'ultimo, contro l'ultimo CLOSE cronologico).",
            "evidence": "decodifica con 'utf-16-le' -> primo campo time = "
                       "'\\ufeff2023.10.03 17:30:00' (verificato con repr() sui byte grezzi); "
                       "decodifica con 'utf-16' -> '2023.10.03 17:30:00' pulito, 42 eventi "
                       "appaiati correttamente, il singolo OPEN non appaiato rimasto e' quello "
                       "GENUINAMENTE piu' recente (2026.06.25), non quello piu' vecchio.",
            "fix_applied": "nxs_research_run_harness._detect_text_encoding ora ritorna 'utf-16' "
                "per qualunque BOM UTF-16 (LE o BE) - fix al research harness, nessuna modifica "
                "alla strategia. liq_sweep_diagnostic_run_v1.json (Phase 7.23) ricostruito con "
                "il fix: ora riporta 42 eventi, non piu' 41.",
            "status": "RISOLTO - non e' piu' un residuo da questa fase in poi.",
        },
        {
            "residual": "43 OPEN vs 42 CLOSE (scarto di 1, post-fix)",
            "classification": "EXPECTED_FUNNEL_DIFFERENCE",
            "root_cause": "l'unico OPEN senza CLOSE corrispondente e' il segnale cronologicamente "
                "PIU' RECENTE dell'intero campione (2026.06.25 01:15:00, SELL, "
                "Sweep_high_reversal:Asia-High, entry 4001.49, SL 4191.82, TP 3620.84) - aperto "
                "solo ~4.9 giorni prima della fine della finestra testata "
                "(period_end=2026.06.29 23:58:58 dal certificato). L'ultimo CLOSE osservato nel "
                "campione e' del giorno precedente (2026.06.24 15:25:03). Gli hold_sec osservati "
                "sui 42 eventi chiusi vanno da poche ore a >80 giorni (mediana su base "
                "empirica, TF D1 con SL/TP ad ampiezza ATR) - una posizione ancora aperta dopo "
                "solo 4.9 giorni e' pienamente compatibile con la distribuzione osservata, non "
                "un'anomalia.",
            "evidence": "verificato per costruzione: e' l'OPEN con timestamp massimo fra tutti "
                       "gli OPEN del campione, e la sua distanza dal period_end del certificato "
                       "e' positiva e piccola (4.9 giorni) - nessun'altra spiegazione compatibile "
                       "(non e' un evento duplicato, non manca un CLOSE altrove nel file: "
                       "verificato che nessun'altra riga CLOSE nel CSV grezzo referenzia un "
                       "timestamp/prezzo compatibile con questo OPEN).",
            "fix_applied": None,
            "status": "Non e' un difetto - e' l'esito atteso di qualunque backtest con una "
                     "finestra temporale finita e almeno una posizione ancora in corso alla "
                     "chiusura. Escluso per costruzione dal dataset economico canonico (nessun "
                     "P&L realizzato disponibile) - incluso nel dataset canonico come evento "
                     "OPEN_AT_PERIOD_END, non come evento chiuso.",
        },
    ]

    payload = {
        "run_id": manifest["run_id"], "run_isolation_manifest": manifest_path,
        "funnel_stages": funnel_stages,
        "arithmetic_checks": arithmetic_checks,
        "all_arithmetic_checks_hold": all(c["holds"] for c in arithmetic_checks.values()),
        "residual_adjudication": residual_adjudication,
        "final_counts": {
            "generated": cert_funnel["GENERATED"] if cert_funnel else None,
            "opened": n_open_rows, "closed_within_window": n_close_rows,
            "still_open_at_period_end": n_unmatched_opens,
            "events_used_economically": n_paired,
        },
        "no_reconciliation_forced": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE724_DIR, "funnel_accounting_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  all_arithmetic_checks_hold: {payload['all_arithmetic_checks_hold']}")
    print(f"  final_counts: {payload['final_counts']}")


if __name__ == "__main__":
    main()
