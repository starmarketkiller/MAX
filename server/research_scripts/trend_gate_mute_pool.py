#!/usr/bin/env python3
"""
08/08 - test di gruppo sulle 18 strategie "mute" (0 trade singolarmente sotto
TREND_GATE). Versione CORRETTA rispetto alla prima bozza: quella forzava
tutte e 18 sullo stesso TF (4h) anche per strategie native 1d/1h - stesso
tipo di bug gia' trovato altrove oggi (OTE_CONT su TF sbagliato). Qui 3 pool
separati, ciascuno sul TF nativo delle sue strategie (TF_MAP di oggi).

Risultato (08/08): il pool 4h (8 strategie) si sblocca a 14 trade/PF 1.03,
ma e' quasi tutto BUY (9 trade PF 4.06) - il SELL (5 trade) crolla a PF 0.02.
I pool 1d e 1h restano muti. L'ipotesi "solitudine statistica" non regge:
il pool non crea edge nuovo, fa solo riemergere lo stesso bias BUY visto
ovunque oggi.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trend_gate_core as tg

GROUPS = {
    "1d": ["BOLLINGER", "FVG_MIT", "IFVG", "OB_MIT", "ORDER_BLOCK", "RANGE_FADE"],
    "4h": ["BJORGUM", "DISP_REBAL", "EMA_PULLBACK", "JUDAS_SWING", "LDN_REVERSAL",
           "MALAYSIAN_SNR", "AMD_REVERSAL", "BB_SQUEEZE"],
    "1h": ["RSI_DIV", "OTE_CONT", "NY_REVERSAL", "SCALP_BB_FADE"],
}


def main():
    for tf, grp in GROUPS.items():
        scores = {s: 70.0 for s in grp}   # nessuno score reale noto per queste - uniforme dichiarato
        r = tg.run_trend_gate(strats=grp, tf=tf, buy_only=set(), scores=scores, buy_only_execution=False)
        print(f"\n{'=' * 60}\nPOOL {tf} ({len(grp)} strategie: {', '.join(grp)})\n{'=' * 60}")
        print(f"  Sorgente dati: {r['src']}")
        print(f"  Trade totali:  {r['trades']}")
        print(f"  Profit Factor: {r['pf']}")
        print(f"  Win Rate:      {r['wr']}%")
        print(f"  Net P&L:       {r['net_pnl']}")
        print(f"  Buy (n / PF):  {r['n_buy']} / {r['pf_buy']}")
        print(f"  Sell (n / PF): {r['n_sell']} / {r['pf_sell']}")


if __name__ == "__main__":
    main()
