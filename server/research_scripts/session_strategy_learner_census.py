#!/usr/bin/env python3
"""
13/08 - Censimento sessione x strategia per popolare NEXUS\\auto_disable.csv,
la fonte dati che manca al Learner (#13 SESSION x STRATEGY AUTO-LEARNER,
NXS_EdgeAdaptive.mqh): NXS_EA_Learner_Load() carica quel CSV all'avvio, ma
(a) nulla lo ha mai scritto e (b) NXS_EA_Learner_IsDisabled() non e' mai
chiamato nel gate di esecuzione - funzionalita' completa all'80%, mai
finita. Vedi vault "NEXUS EA - Incidente Sicurezza e Setup Desktop (13-08)".

A differenza dei filtri di regime gia' fatti a mano uno alla volta (MACD
10/08, famiglia SCALP_* 11/08), qui si copre sistematicamente tutto il
nucleo attuale (16 strategie) a grana sessione (ASIAN/LONDON/OVERLAP/NY/
AFTERNY - riusa `session_filter`, gia' presente in run_backtest, mai usato
per un censimento completo prima d'ora).

Disciplina identica al resto della sessione: una sessione va in
auto_disable.csv SOLO se OOS pf<1.0 CON campione minimo E la debolezza
regge sulla maggioranza delle finestre walk-forward (non solo
sull'aggregato) - lo stesso principio per cui il breakeven da solo su CRT
sembrava neutro ma era dannoso solo abbinato al trailing, o per cui TSI in
un singolo giro sembra "buono" ma il campione e' troppo sottile per
fidarsene. Solo ricerca: NON tocca NXS_EA_Learner_IsDisabled() ne' il gate
di esecuzione - quello resta un secondo passo, solo dopo conferma esplicita.
"""
import sys
import os
import csv

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL = "XAUUSD"
BARS = 110000
IS_RANGE, OOS_RANGE = (0.0, 0.6), (0.6, 1.0)
N_WINDOWS = 5

# Le 16 del nucleo demo (NXS_Profile_Enabled=true), col TF di profilo reale
# (NXS_Profile_TF in NXS_StrategyProfiles.mqh) - stesso motore, stesso TF
# che l'EA usa davvero, non un TF di comodo.
NUCLEUS = {
    "ADX_RSI":         "D1",
    "AMD_CONT":        "30m",
    "AMD_REVERSAL":    "15m",
    "BREAKOUT_ACC":    "D1",
    "CRT":             "30m",
    "EMA_PULLBACK":    "1h",
    "FVG_CONT":        "4h",
    "FVG_MIT_WINDOW":  "4h",
    "LDN_REVERSAL":    "15m",
    "LIQ_SWEEP":       "D1",
    "LONDON_BO":       "4h",
    "MACD":            "4h",
    "SAR":             "4h",
    "TSI":             "D1",
    "TURTLE_SOUP":     "1h",
}

# Codici sessione ENUM_NXS_SESSION (NXS_Defines.mqh) - NECESSARI per un
# auto_disable.csv che il loader MQL5 sappia leggere. SESS_NONE=0 escluso
# (non e' una sessione osservabile).
SESSION_CODE = {"ASIAN": 1, "LONDON": 2, "OVERLAP": 3, "NY": 4, "AFTERNY": 5}

MIN_OOS_TRADES = 20   # sessione singola = 1/5 del campione totale circa - soglia piu' bassa dei test whole-TF
MIN_WF_MAJORITY = 3   # su 5 finestre, quante devono essere <1.0 per contare "confermato"


def call(tf, strat, bar_range, session):
    return bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                            risk_pct=1.0, bars=BARS, bar_range=bar_range,
                            session_filter={session})


def walk_forward(tf, strat, session):
    out = []
    for w in range(N_WINDOWS):
        br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
        r = call(tf, strat, br, session)
        out.append((r.get("profit_factor"), r.get("trades")))
    return out


def main():
    print("NEXUS - Censimento Learner: sessione x strategia (nucleo, 15 vive)", flush=True)
    flagged = []
    for strat, tf in NUCLEUS.items():
        print(f"\n{'='*72}\n{strat} @ {tf}\n{'='*72}", flush=True)
        base_oos = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat,
                                    strategies=[strat], risk_pct=1.0, bars=BARS,
                                    bar_range=OOS_RANGE)
        print(f"  baseline (nessun filtro sessione) OOS: pf={base_oos.get('profit_factor')} "
              f"n={base_oos.get('trades')} dd={base_oos.get('max_dd_pct')}%", flush=True)

        for session in SESSION_CODE:
            oos = call(tf, strat, OOS_RANGE, session)
            pf_oos, n_oos = oos.get("profit_factor"), oos.get("trades", 0)
            if n_oos < MIN_OOS_TRADES:
                print(f"    {session:<8} OOS pf={pf_oos} n={n_oos} -- campione troppo sottile, scartata", flush=True)
                continue
            marker = ""
            if pf_oos is not None and pf_oos < 1.0:
                wf = walk_forward(tf, strat, session)
                neg_windows = sum(1 for pf, n in wf if pf is not None and n >= 5 and pf < 1.0)
                confirmed = neg_windows >= MIN_WF_MAJORITY
                marker = f"  <-- {'CONFERMATA' if confirmed else 'debole ma non confermata'} " \
                         f"(wf negative: {neg_windows}/5, {['%.2f/%d' % (pf, n) for pf, n in wf]})"
                if confirmed:
                    flagged.append({
                        "strategy": strat, "session": session, "session_code": SESSION_CODE[session],
                        "oos_pf": pf_oos, "oos_n": n_oos, "oos_dd": oos.get("max_dd_pct"),
                        "neg_windows": neg_windows,
                        "reason": f"OOS_PF_{pf_oos:.2f}_WF_{neg_windows}of5",
                    })
            print(f"    {session:<8} OOS pf={pf_oos} n={n_oos} dd={oos.get('max_dd_pct')}%{marker}", flush=True)

    print(f"\n{'='*72}\nSessioni CONFERMATE deboli (OOS pf<1.0 + maggioranza walk-forward negativa): "
          f"{len(flagged)}\n{'='*72}", flush=True)
    for f in flagged:
        print(f"  {f['strategy']:<16} {f['session']:<8} OOS pf={f['oos_pf']:.2f} n={f['oos_n']} "
              f"wf_neg={f['neg_windows']}/5", flush=True)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "session_strategy_learner_census.csv")
    with open(out_path, "w", encoding="utf-8") as f:
        json_rows = flagged
        import json
        json.dump(json_rows, f, indent=2)
    print(f"\nDettaglio completo (JSON): {out_path}")

    # auto_disable.csv nella STESSA cartella dello script, NON copiato nella
    # cartella dati MT5 - e' un artefatto di ricerca, il deploy sul vero
    # MQL5\Files\NEXUS\ resta un passo manuale/separato dopo revisione.
    auto_disable_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "auto_disable.csv")
    with open(auto_disable_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["strategy", "session", "reason"])
        for row in flagged:
            w.writerow([row["strategy"], row["session_code"], row["reason"]])
    print(f"auto_disable.csv (bozza, formato compatibile col loader MQL5): {auto_disable_path}")
    print("NON ancora copiato in MQL5\\Files\\NEXUS\\ e NXS_EA_Learner_IsDisabled() "
          "NON e' collegato al gate di esecuzione - entrambi passi separati, solo dopo revisione.")


if __name__ == "__main__":
    main()
