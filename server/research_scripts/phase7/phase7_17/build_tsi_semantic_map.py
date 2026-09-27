#!/usr/bin/env python3
"""Phase 7.17 punto 1 - congela l'identita' TSI: funzione MQL5
canonica, selector/profile, TF canonico, stato persistente, struttura
del doppio smoothing EMA, ordine delle chiamate, punti di mutazione,
gate a valle, implementazioni Python/proxy storici. Distingue
esplicitamente strategia intesa, implementazione attuale, proxy
storici.
"""
import os
import sys

PHASE717_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE717_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def build():
    payload = {
        "canonical_function": {
            "file": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh",
            "function": "NXS_Strat_TSI()",
            "lines": "1354-1414 (struct SNXSTSIState + funzione)",
            "call_site": "MQL5/Experts/NEXUS_EA_v2.mq5:525, out[n++] = NXS_Strat_TSI(); - "
                        "blocco 'Classic 16', chiamata INCONDIZIONATA (nessun if di "
                        "selettore al call site, il gate vive dentro la funzione)",
            "wrappers_or_reuse": "NESSUNO trovato (grep esaustivo su g_tsiState/"
                                 "NXS_Strat_TSI in tutto MQL5/) - a differenza di ORDER_BLOCK/"
                                 "OB_MIT, TSI non ha un'identita' gemella che ne riusi il "
                                 "codice",
        },
        "selector_and_profile": {
            "enable_flag": "InpStrat_TSI (default true)",
            "selector": 5,
            "gate_code": "if(!InpStrat_TSI || !NXS_SelectorAllows(5)) return s; (riga 1368) - "
                        "UNICO controllo di ammissibilita', nessuna guardia TF",
            "canonical_tf": "PERIOD_D1 (NXS_Profile_TF('TSI'), NXS_StrategyProfiles.mqh:283)",
            "tf_guard_present": False,
            "tf_guard_note": "NESSUNA guardia `if(tf != NXS_Profile_TF('TSI')) return s;` "
                            "presente - stessa forma di difetto strutturale di BREAKOUT_ACC "
                            "(pre-fix) e ORDER_BLOCK (pre-fix)",
        },
        "persistent_state": {
            "struct": "SNXSTSIState g_tsiState (riga 1354-1364) - UN SOLO struct globale "
                     "(non due come g_obBuy/g_obSell di ORDER_BLOCK)",
            "fields": {
                "init": "bool, se lo stato e' stato inizializzato",
                "lastBarTime": "datetime, ultima barra 'chiusa' vista - CONDIVISO fra tutti i "
                              "passaggi TF, stesso meccanismo di corruzione gia' visto in "
                              "BREAKOUT_ACC/ORDER_BLOCK",
                "sm1, sm1Abs": "doppio EMA (primo stadio) di priceChange e |priceChange|",
                "sm2, sm2Abs": "doppio EMA (secondo stadio, applicato a sm1/sm1Abs) - QUESTI "
                              "sono i valori usati per calcolare il TSI vero e proprio",
                "signal": "EMA(TSI, InpTSI_SignalPeriod) - la signal line per il cross",
                "tsiPrev, signalPrev": "valori PRIMA dell'aggiornamento della barra corrente, "
                                      "usati per rilevare il cross",
                "prevClose": "chiusura precedente, per calcolare priceChange",
                "barsSeen": "contatore di aggiornamenti - usato per il warmup "
                           "(InpTSI_LongPeriod*3 = 75 aggiornamenti richiesti)",
            },
            "key_structural_difference_from_order_block": "ORDER_BLOCK ha uno stato "
                "DISCRETO/a fasi (idle/attiva/consumata) che puo' essere 'ricreato' - una "
                "contaminazione puo' essere sanata dalla successiva ricerca di zona. TSI ha "
                "un FILTRO RICORSIVO CONTINUO (IIR, doppio EMA) la cui memoria non si "
                "'ricrea' mai - ogni aggiornamento, anche contaminato, resta nella memoria "
                "del filtro per sempre con peso esponenzialmente decrescente ma MAI nullo. "
                "Vedi build_tsi_mechanism_formalization.py per la formalizzazione "
                "matematica.",
        },
        "double_ema_structure": {
            "stage_1": "sm1 = pc*aLong + sm1_prev*(1-aLong); sm1Abs = |pc|*aLong + "
                      "sm1Abs_prev*(1-aLong); aLong = 2/(InpTSI_LongPeriod+1) = 2/26",
            "stage_2": "sm2 = sm1*aShort + sm2_prev*(1-aShort); sm2Abs = sm1Abs*aShort + "
                      "sm2Abs_prev*(1-aShort); aShort = 2/(InpTSI_ShortPeriod+1) = 2/14",
            "tsi_value": "100 * sm2 / sm2Abs (se sm2Abs>0, altrimenti 0)",
            "signal_line": "signal = tsi_now*aSig + signal_prev*(1-aSig); aSig = "
                          "2/(InpTSI_SignalPeriod+1) = 2/8",
            "default_periods": {"InpTSI_LongPeriod": 25, "InpTSI_ShortPeriod": 13,
                               "InpTSI_SignalPeriod": 7},
        },
        "call_order_and_mutation_points": {
            "order": [
                "1. NXS_CollectRaw() chiama NXS_Strat_TSI() ad ogni passaggio multi-TF "
                "(nessun gate di selettore al call site)",
                "2. Dentro NXS_Strat_TSI(): se InpStrat_TSI/selettore falliscono, ritorna "
                "SUBITO (nessuna mutazione)",
                "3. tf = NXS_EffTF() (TF del passaggio CORRENTE, non necessariamente D1)",
                "4. curBar0 = iTime(tf, 0) - dipende dal TF del passaggio",
                "5. Se g_tsiState.lastBarTime != curBar0 (vero ad ogni cambio di passaggio "
                "TF che produce un curBar0 diverso, non solo ad ogni vera nuova barra D1): "
                "MUTAZIONE del filtro ricorsivo (sm1/sm1Abs/sm2/sm2Abs/signal/prevClose/"
                "lastBarTime/barsSeen) usando c1 = iClose(tf,1) DEL TF DEL PASSAGGIO",
                "6. Warmup: se barsSeen < 75, nessun segnale (ma la mutazione al punto 5 e' "
                "gia' avvenuta comunque)",
                "7. Cross TSI/signal -> segnale BUY/SELL",
            ],
            "mutation_point": "riga 1377-1397, dentro `if(g_tsiState.lastBarTime != curBar0)`",
        },
        "downstream_gates": "NESSUNO oltre a NXS_DefaultSLTP(s) (righe 1412) - a differenza "
                           "di ORDER_BLOCK (gate H1 trend + SMC reaction), TSI non ha filtri "
                           "post-segnale nell'EA reale - il segnale del trace diagnostico "
                           "sara' quindi GIA' il segnale finale pre-esecuzione, non solo un "
                           "raw trigger pre-gate.",
        "python_implementations": {
            "sig_tsi": {
                "file": "server/backtest.py:1088-1108",
                "description": "Cross puro TSI/signal-line, dichiarato 'fedele riga-per-riga' "
                              "in un commento del 04/08 - calcola il TSI vero (tsi_series(), "
                              "righe 1136-1162) su una SOLA serie di prezzi (single-TF, nessun "
                              "loop multi-pass) - strutturalmente EQUIVALENTE a Stream B "
                              "TF-scoped (analogo a quanto trovato per sig_order_block/"
                              "_ob_series in Phase 7.13).",
                "seeding_difference": "tsi_series()/_ema() inizializza l'EMA con il PRIMO "
                                     "valore della serie (out[seed_i]=vals[seed_i]); MQL5 "
                                     "inizializza g_tsiState a zero (default di struct) - il "
                                     "primissimo aggiornamento in MQL5 e' quindi "
                                     "sistematicamente diverso da Python (attenuato "
                                     "dell'alpha invece di partire dal valore pieno) - "
                                     "differenza di WARM-UP, non di meccanismo, si dissolve "
                                     "esponenzialmente dopo poche decine di barre - non e' il "
                                     "difetto sotto indagine in questa fase.",
            },
            "sig_tsi_extreme": {
                "file": "server/backtest.py:1111-1133",
                "description": "Variante SPERIMENTALE (richiede TSI in zona estrema prima del "
                              "cross, soglia=15) - dichiarata esplicitamente 'non un'ipotesi "
                              "di fedelta', MQL5 non ha questo filtro' - NON e' un proxy "
                              "dell'identita' canonica TSI, e' un'identita' diversa "
                              "(TSI_EXTREME), fuori scope per questa diagnosi.",
            },
        },
        "distinction_strategy_intended_vs_implemented_vs_proxy": {
            "strategia_intesa": "True Strength Index (William Blau): doppio smoothing EMA "
                               "del momentum su UN SOLO timeframe, confrontato con una "
                               "signal line - un indicatore di momentum a singolo TF per "
                               "definizione matematica standard.",
            "implementazione_attuale_mql5": "NXS_Strat_TSI() - matematicamente corretta "
                                           "(doppio EMA vero, non un proxy RSI come una "
                                           "versione precedente, vedi commento riga 1348) MA "
                                           "eseguita nel loop multi-TF del router SENZA "
                                           "guardia TF - lo stato del filtro viene aggiornato "
                                           "da passaggi non canonici.",
            "proxy_storico_python": "server/backtest.py::sig_tsi/tsi_series - fedele alla "
                                   "MATEMATICA del doppio EMA a singolo TF (l'intento), ma "
                                   "NON riproduce il comportamento multi-TF del router live "
                                   "(ne' la versione contaminata ne', necessariamente, quella "
                                   "corretta - va verificato, vedi punto 5).",
        },
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE717_DIR, "tsi_semantic_map_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
