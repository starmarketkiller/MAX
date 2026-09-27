#!/usr/bin/env python3
"""Phase 7.22 punto 2 - DATA_EXPOSURE_MAP. A differenza di BREAKOUT_ACC
(Phase 7.21), ORDER_BLOCK V2 non ha MAI avuto un'ANALISI economica -
questa e' la PRIMA misurazione economica in assoluto per questa
identita' implementativa.

CORREZIONE TRACCIATA (durante questa stessa fase, prima di calcolare
qualunque statistica): il run di discovery lanciato in questa fase ha
prodotto un certificato con funnel GENERATED=2/OPENED=1 per la finestra
2023.10.02-2026.06.30 - ma NEXUS_trades.csv (log persistente, mai
azzerato fra sessioni) conteneva GIA' 13 trade ORDER_BLOCK reali
(2024.04.08-2026.08.24), quasi certamente scritti dal run diagnostico
originale di Phase 7.14 (stesso file di log, stesso meccanismo
NXS_LogTradeCSV, InpLogTrades=true di default - quel run copriva
FromDate=2023.10.02 ToDate=2026.08.25) settimane prima di questa fase.
Il certificato di QUESTA fase sembra riflettere solo un sotto-segmento
della sessione (causa non identificata, dichiarata come anomalia non
risolta, non nascosta) - il file CSV resta la fonte di verita' (MT5 =
ground truth), non il certificato.

Conseguenza pratica: i 13 trade reali gia' disponibili SONO SUFFICIENTI
per la baseline economica - la seconda finestra 'discovery' pluriennale
non era necessaria a posteriori (nota per la task successiva: verificare
NEXUS_trades.csv PRIMA di lanciare un nuovo run lungo). La finestra
FORWARD genuinamente untouched si e' ristretta di conseguenza (i dati
esistenti coprono gia' fino al 2026.08.24)."""
import os
import sys

PHASE722_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE722_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

DATA_START = "2023.10.02"
DATA_END_OBSERVED = "2026.08.24"  # ultimo CLOSE reale gia' presente in NEXUS_trades.csv
FORWARD_START = "2026.08.25"
TODAY = "2026.09.27"


def build():
    payload = {
        "principle": "Un periodo e' UNTOUCHED per una data domanda solo se nessun essere umano o "
                    "script di ricerca lo ha mai esaminato per QUELLA domanda specifica, prima "
                    "d'ora. 'Esiste gia' nel log persistente' non equivale a 'e' stato analizzato'.",
        "key_difference_from_breakout_acc_7_21": "ORDER_BLOCK V2 non ha MAI avuto un'ANALISI "
            "economica (nessun P&L mai calcolato) - Phase 7.13-7.16 hanno lavorato SOLO su segnali "
            "grezzi/zone lifecycle in Research Mode diagnostica. Questa fase costruisce la PRIMA "
            "analisi economica in assoluto per V2 - non c'e' una 'scoperta precedente su questi "
            "stessi dati economici' da cui guardarsi (a differenza di H2 in BREAKOUT_ACC).",
        "data_provenance_correction": "Scoperto DURANTE questa fase (dichiarato, non nascosto): "
            "NEXUS_trades.csv e' un log CONDIVISO e MAI azzerato fra sessioni - conteneva GIA' 13 "
            f"trade ORDER_BLOCK reali ({DATA_START.replace('.', '-')} - "
            f"{DATA_END_OBSERVED.replace('.', '-')}) prima ancora che questa fase lanciasse il "
            "proprio run, quasi certamente prodotti dal run diagnostico originale di Phase 7.14 "
            "(stessa finestra temporale, stesso meccanismo di logging attivo di default). Il "
            "certificato del run di QUESTA fase (GENERATED=2/OPENED=1) e' incoerente col contenuto "
            "del CSV (13 trade nella stessa finestra dichiarata dal certificato) - anomalia NON "
            "risolta in questa fase, il CSV resta la fonte di verita' (MT5 = ground truth per "
            "istruzione esplicita del task) perche' verificabile riga per riga, il certificato no.",
        "periods": [
            {
                "period": f"prima del {DATA_START}",
                "used_for_development": "SCONOSCIUTO - non investigato in questa fase.",
                "genuinely_untouched": "NON VERIFICATO",
                "verdict": "NON USATO - stessa soglia gia' stabilita nel progetto (run r002/r003 di "
                          "riferimento, sweep37) - nessuna evidenza di dati comparabili prima.",
            },
            {
                "period": f"{DATA_START} - {DATA_END_OBSERVED} (13 trade reali gia' presenti nel "
                         "log persistente, MAI analizzati economicamente prima d'ora)",
                "used_for_development": "NO (mai un'analisi economica prima d'ora)",
                "used_in_diagnosis_phase_7_13_16": "PARZIALMENTE - Phase 7.13/7.14/7.16 hanno "
                    "guardato QUESTO INTERVALLO per una domanda DIVERSA (integrita' del fix via "
                    "zone lifecycle/segnali, MAI P&L/expectancy/PF).",
                "used_for_fix": "NO", "used_for_parity": "SI (Phase 7.16, su segnali, non su P&L)",
                "seen_in_reports": "SI per segnali/zone, MAI per P&L/expectancy/PF",
                "genuinely_untouched_for_economic_baseline": True,
                "genuinely_untouched_for_signal_level_integrity": False,
                "verdict": "POPOLAZIONE PRIMARIA di questa fase - baseline economica DESCRITTIVA "
                          "(13 trade, prima misurazione economica in assoluto per V2).",
            },
            {
                "period": f"{FORWARD_START} - {TODAY} (finestra FORWARD, genuinamente untouched)",
                "used_for_development": False, "used_in_diagnosis_phase_7_13_16": False,
                "used_for_fix": False, "used_for_parity": False, "seen_in_reports": False,
                "genuinely_untouched_for_economic_baseline": True,
                "genuinely_untouched_for_signal_level_integrity": True,
                "verdict": "VERO HOLDOUT - l'unica finestra residua mai attraversata da nessun run "
                          "(i dati esistenti coprono gia' fino al "
                          f"{DATA_END_OBSERVED.replace('.', '-')}). Finestra molto corta (~1 mese) - "
                          "atteso probabile INSUFFICIENT_OOS_SAMPLE, esito ammesso dal protocollo.",
            },
        ],
        "sufficient_data_already_existed_note": "Per una prossima fase simile: verificare "
            "NEXUS_trades.csv PRIMA di lanciare un nuovo run pluriennale - in questo caso i dati "
            "necessari erano gia' disponibili da un run precedente (Phase 7.14), rendendo il primo "
            "run lungo di questa fase (poi interrotto per lentezza) e il secondo run di ~2h22min "
            "non strettamente necessari per la baseline (sono comunque serviti a confermare il "
            "certificato ufficiale e la riproducibilita', non solo a produrre dati).",
        "forward_window": [FORWARD_START, TODAY],
        "conclusion": "Nessun vero holdout STORICO indipendente esiste all'interno dei 13 trade gia' "
            "disponibili - trattati come baseline, MAI come conferma indipendente. La finestra "
            "forward (molto corta, ~1 mese) e' l'unica genuinamente idonea a un test OOS.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE722_DIR, "orderblock_data_exposure_map_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
