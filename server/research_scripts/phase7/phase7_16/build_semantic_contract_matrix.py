#!/usr/bin/env python3
"""Phase 7.16 punto 1 - semantic contract matrix: confronto diretto sul
codice (non assunto) fra il contratto reale dell'EA MT5 post-fix
(NXS_Strat_OrderBlock/NXS_OB_UpdateSide, MQL5/Include/NEXUS_v1/
NXS_Strategies.mqh righe 2077-2172) e la ricostruzione Python
(server/research_scripts/phase7/phase7_13/nxs_order_block_replica.py +
build_ab_simulation.py), dimensione per dimensione.
"""
import os
import sys

PHASE716_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE716_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

MATRIX = [
    {
        "dimension": "Frequenza e ordine delle valutazioni",
        "mt5_ea": "NXS_Strat_OrderBlock() e' chiamata ad OGNI TICK durante il passaggio D1 del "
                 "loop multi-TF del router (che gira anch'esso ad ogni tick, ciclando tutti i "
                 "passaggi TF ad ogni tick) - post-fix, la guardia rende la chiamata un no-op "
                 "immediato per i passaggi non-D1, ma il passaggio D1 stesso viene comunque "
                 "raggiunto molte volte al giorno (una volta per ogni tick in cui il ciclo del "
                 "router arriva alla posizione D1 nell'array passes[]).",
        "python_reconstruction": "ob_update_side() e' chiamata UNA VOLTA per indice di barra D1 "
                                 "(build_ab_simulation.py, loop su tf_bars['D1']) - una "
                                 "valutazione per barra, non per tick.",
        "verdict": "DIVERSO - granularita' temporale della valutazione fondamentalmente diversa "
                  "(continua/per-tick vs discreta/per-barra)",
    },
    {
        "dimension": "Tick/Bid reali vs proxy",
        "mt5_ea": "Il test 'touched' usa `SymbolInfoDouble(g_sym, SYMBOL_BID)` - il prezzo BID "
                 "LIVE del tick corrente, durante la formazione della barra oggi (shift 0, non "
                 "ancora chiusa).",
        "python_reconstruction": "Il test 'touched' usa il range [low,high] di `bars[i]` - "
                                 "**la barra appena CHIUSA (shift 1, IERI)**, non la barra in "
                                 "formazione (shift 0, oggi) durante la quale il bid live "
                                 "dell'EA si muoverebbe davvero.",
        "verdict": "DIVERSO - E' L'ERRORE DI ALLINEAMENTO IDENTIFICATO IN QUESTA FASE (vedi "
                  "punto 2): il proxy usa la barra sbagliata per 'touched', non solo una "
                  "granularita' diversa da quella tick-by-tick.",
    },
    {
        "dimension": "Timeframe effettivamente usato",
        "mt5_ea": "PERIOD_D1 (post-fix, guardia NXS_Profile_TF('ORDER_BLOCK')==D1) su barre D1 "
                 "REALI del broker (convenzione di bar-open del broker, sconosciuta esattamente "
                 "in questa fase).",
        "python_reconstruction": "Serie D1 RICAMPIONATA deterministicamente da una serie M15 "
                                 "locale (fonte: nxs_m15_gold_extended.csv), con un confine "
                                 "giorno dedotto EMPIRICAMENTE (01:00, valido nel 91.6% dei "
                                 "giorni della serie M15) - NON verificato uguale alla "
                                 "convenzione D1 nativa del broker.",
        "verdict": "DIVERSO - stessa etichetta 'D1' ma fonte e convenzione di bar-boundary "
                  "diverse e non verificate identiche",
    },
    {
        "dimension": "ATR / disponibilita' temporale",
        "mt5_ea": "g_atr e' un indicatore iATR nativo MT5 (Wilder, periodo InpATR_Period=14) "
                 "calcolato sulla history REALE disponibile al terminale, che tipicamente include "
                 "un lookback PRIMA della data di inizio del test (il Tester carica storia "
                 "sufficiente per il warm-up degli indicatori) - la sua traiettoria a qualunque "
                 "data riflette anni di storia precedente.",
        "python_reconstruction": "ATR di Wilder(14) calcolato SOLO sulle barre della serie locale "
                                 "(a partire da 2023-10-02, l'inizio della fonte M15) - NESSUNA "
                                 "storia precedente disponibile, quindi warm-up parte da zero "
                                 "in quel punto, non da anni di storia reale.",
        "verdict": "DIVERSO - valori di soglia (1.2*ATR) calcolati su basi storiche "
                  "sistematicamente diverse per l'INTERO periodo, non solo nelle prime barre",
    },
    {
        "dimension": "Warmup e stato iniziale",
        "mt5_ea": "g_obBuy/g_obSell iniziano a zero-value (SNXSOBState default) all'avvio del "
                 "test (FromDate=2023.10.02, stesso ancoraggio nominale della fonte Python).",
        "python_reconstruction": "OBState() iniziano anch'essi a zero-value, stesso ancoraggio "
                                 "nominale 2023-10-02.",
        "verdict": "COERENTE (punto di partenza nominale condiviso) - ma la storia dell'ATR "
                  "PRIMA di questo punto e' comunque diversa (vedi sopra), quindi anche le "
                  "primissime soglie non sono identiche fra le due implementazioni",
    },
    {
        "dimension": "Creazione zona (displacement + BOS + origine)",
        "mt5_ea": "Ricerca su shift 3..10, soglia body>=1.2*atr, BOS su iHighest/iLowest a 15 "
                 "barre da shift+1, origine su shift+1..shift+6 (righe 2087-2112).",
        "python_reconstruction": "Stessa logica, stessa soglia, stesso lookback, stesso range di "
                                 "ricerca - porting verificato fedele riga per riga in Phase "
                                 "7.13/7.14.",
        "verdict": "STRUTTURALMENTE IDENTICO (controllo di flusso) - mai in dubbio in questa "
                  "fase - le differenze numeriche derivano dai dati/ATR in ingresso, non dalla "
                  "logica",
    },
    {
        "dimension": "Aggiornamento/scadenza/invalidazione zona",
        "mt5_ea": "barsWaited++ e invalidazione su shift-1 (c1=iClose(tf,1)) ad ogni newBar; "
                 "scadenza se barsWaited>InpOB_MaxWaitBars(20) (righe 2117-2124).",
        "python_reconstruction": "Stessa logica, stesso shift-1, stessa soglia 20 - porting "
                                 "verificato fedele.",
        "verdict": "STRUTTURALMENTE IDENTICO",
    },
    {
        "dimension": "Consumo della zona (retest one-shot)",
        "mt5_ea": "touched (bid live, shift 0) + rejection (shift-1 O/C) -> st.active=false, "
                 "one-shot (righe 2125-2137).",
        "python_reconstruction": "touched (shift-1 L/H, NON shift 0) + rejection (shift-1 O/C) -> "
                                 "state.active=False, one-shot.",
        "verdict": "PARZIALMENTE DIVERSO - il consumo ONE-SHOT e' identico (una volta soddisfatte "
                  "le condizioni, la zona si disattiva in entrambi), ma QUANDO le condizioni "
                  "risultano soddisfatte differisce per l'errore di allineamento di 'touched' "
                  "sopra",
    },
    {
        "dimension": "Filtri/gate H1 e SMC",
        "mt5_ea": "Applicati DOPO NXS_OB_UpdateSide(), dentro NXS_Strat_OrderBlock(): "
                 "g_structH1.trend (righe 2158-2159) e NXS_SMCReactionOK se "
                 "InpUseSMCReactionGate (righe 2163-2167).",
        "python_reconstruction": "NON REPLICATI - dichiarato esplicitamente fuori scope in Phase "
                                 "7.13/7.14 ('gates_not_modeled_declared').",
        "verdict": "DIVERSO MA IRRILEVANTE PER IL CONFRONTO GIA' FATTO - vedi prossima riga: sia "
                  "il conteggio EA che quello Python sono presi PRIMA di questi gate, quindi "
                  "sono comparabili fra loro anche se nessuno dei due rappresenta il segnale "
                  "finale post-gate",
    },
    {
        "dimension": "Momento esatto in cui si conta un 'segnale'",
        "mt5_ea": "Il trace diagnostico di Phase 7.14 (NXS_OB_DiagWrite) e' posizionato DENTRO "
                 "NXS_OB_UpdateSide(), al momento 'RETEST_SIGNAL_FIRED' - PRIMA che "
                 "NXS_Strat_OrderBlock() applichi i gate H1/SMC. Verificato: il conteggio EA di "
                 "Phase 7.14 (8 post-fix) e' quindi un RAW TRIGGER pre-gate.",
        "python_reconstruction": "ab_simulation.py conta 'generated_a/generated_b' allo stesso "
                                 "punto (uscita di ob_update_side con segnale != None), anch'esso "
                                 "un RAW TRIGGER pre-gate.",
        "verdict": "STESSO LIVELLO DEL FUNNEL - CONFERMATO (non un'assunzione): sia 8 (EA) che 7 "
                  "(Python) sono raw trigger pre-gate H1/SMC, pre-esecuzione. Il confronto "
                  "numerico Phase 7.14/7.15 era corretto su QUESTO punto specifico.",
    },
    {
        "dimension": "Semplificazioni intenzionali dichiarate nel modulo Python",
        "mt5_ea": "N/A",
        "python_reconstruction": "Il docstring di nxs_order_block_replica.py dichiara: 'touched e "
                                 "rejection valutati sulla STESSA barra appena chiusa (bar i), "
                                 "non per-tick, data la granularita' disponibile' - **questa "
                                 "descrizione e' IMPRECISA**: non si limita a sostituire il "
                                 "tick-by-tick con una barra discreta (approssimazione "
                                 "accettabile e dichiarata), ma usa la barra SBAGLIATA (shift 1, "
                                 "ieri) invece della barra che retrospettivamente corrisponde a "
                                 "'durante la formazione della barra corrente' (shift 0 al "
                                 "momento della valutazione, cioe' bars[i+1] nell'array "
                                 "storico completo disponibile offline).",
        "verdict": "ERRORE DI IMPLEMENTAZIONE NELLA RICOSTRUZIONE PYTHON, NON SOLO UNA "
                  "SEMPLIFICAZIONE DICHIARATA - vedi punto 2 per la dimostrazione e la "
                  "quantificazione dell'impatto",
    },
]


def build():
    n_identical = sum(1 for m in MATRIX if "IDENTICO" in m["verdict"] and "PARZIALMENTE" not in m["verdict"])
    n_different = sum(1 for m in MATRIX if "DIVERSO" in m["verdict"])
    payload = {
        "source_files_read_directly": [
            "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh righe 2069-2172 (NXS_Strat_OrderBlock, "
            "NXS_OB_UpdateSide - post-fix, guardia inclusa)",
            "server/research_scripts/phase7/phase7_13/nxs_order_block_replica.py",
            "server/research_scripts/phase7/phase7_13/build_ab_simulation.py",
            "server/research_scripts/phase7/phase7_14/nxs_ob_diag_instrumentation_snapshot.mqh.txt "
            "(punto esatto del conteggio 'segnale' nel trace EA reale)",
        ],
        "matrix": MATRIX,
        "n_dimensions_checked": len(MATRIX),
        "n_structurally_identical": n_identical,
        "n_different_or_partially_different": n_different,
        "key_finding": "L'assunzione 'i segnali contati da EA e Python sono allo stesso livello "
                      "del funnel' e' CONFERMATA (non un'assunzione non verificata) - entrambi "
                      "sono raw trigger pre-gate H1/SMC. La causa della divergenza NON e' un "
                      "mismatch di livello del funnel, ma un errore di allineamento temporale "
                      "nel test 'touched' della ricostruzione Python (usa la barra shift-1 "
                      "invece della barra shift-0/forming) - vedi punto 2.",
        "no_assumption_that_8_and_7_are_same_funnel_level": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE716_DIR, "semantic_contract_matrix_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  dimensioni verificate: {payload['n_dimensions_checked']}")
    print(f"  identiche: {payload['n_structurally_identical']} | diverse: {payload['n_different_or_partially_different']}")


if __name__ == "__main__":
    main()
