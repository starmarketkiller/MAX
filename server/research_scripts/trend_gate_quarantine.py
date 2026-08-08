#!/usr/bin/env python3
"""
08/08 - TREND_GATE ("blindato" in trend_gate_core.py, verificato riprodurre
esatto PF 2.28/39 trade del prototipo) applicato SINGOLARMENTE a ogni
strategia NON ancora nel gruppo dei 9 validati, per vedere se qualcuna
"in quarantena" trova la sua dimensione sotto questo nuovo gate (breakout
rect_engine confermato + direzione concorde) invece di essere scartata a
priori. bidirezionale (buy_only_execution=False): lasciamo che sia il
gate stesso a decidere se una strategia ha edge BUY, SELL o nessuno dei
due sotto questo regime - testarla gia' BUY-only nasconderebbe un
eventuale lato short genuino.

Score reali letti da MQL5 dove esistono (vedi commenti); 70.0 uniforme
DICHIARATO per le RESEARCH_ONLY (nessuna controparte MQL5) e per le mie
varianti sperimentali (MALAYSIAN_SNR_BREAKOUT). Per le _v2 uso gli score
originali del file pastato dall'utente (SH_BMS_RTO_v2=78, SilverBullet_v2=80,
OTE_v2=76, OrderBlock_v2=75, FVG_v2=74).

Caveat dati: le strategie 1h/4h girano ancora su Yahoo a finestra corta (il
refetch Dukascopy e' a 140/300 giorni, non ancora sopra soglia) - stesso
avviso di tutta la sessione di oggi, non ripetuto per ogni riga.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trend_gate_core as tg

TF_MAP = {
    "ADX_RSI": "1h", "AMD_CONT": "4h", "AMD_REVERSAL": "4h", "BB_SQUEEZE": "4h",
    "BJORGUM": "4h", "BOLLINGER": "1d", "DISP_REBAL": "4h", "EMA_PULLBACK": "4h",
    "FVG_MIT": "1d", "ICHIMOKU": "1h", "IFVG": "1d", "JUDAS_SWING": "4h",
    "LDN_REVERSAL": "4h", "LONDON_BO": "4h", "MACD": "1h", "MALAYSIAN_SNR": "4h",
    "MALAYSIAN_SNR_BREAKOUT": "1h", "NY_REVERSAL": "1h", "OB_MIT": "1d",
    "ORDER_BLOCK": "1d", "OTE_CONT": "1h", "PO3": "4h", "RANGE_FADE": "1d",
    "RSI_DIV": "1h", "SCALP_BB_FADE": "1h", "SCALP_EMA": "1d",
    "SCALP_RANGE_BRK": "1d", "SCALP_RSI_SNAP": "4h", "SMS_BMS_RTO": "4h",
    "STRUCT_REACT": "1h", "THREE_BAR_DELIVERY_BREAK": "1d", "TURTLE_SOUP": "1d",
    "WEEKLY_EXP": "1h",
    "SH_BMS_RTO_V2": "1d", "SILVER_BULLET_V2": "4h", "OTE_CONT_V2": "1h",
    "ORDER_BLOCK_V2": "1d", "FVG_CONT_V2": "1d",
}

# score reale MQL5 dove trovato (grep su s.score= nei file NXS_Strategies*.mqh),
# 70.0 dichiarato altrove (RESEARCH_ONLY o variante sperimentale mia)
SCORES = {
    "ADX_RSI": 62.0, "AMD_CONT": 72.0, "AMD_REVERSAL": 75.0, "BB_SQUEEZE": 70.0,
    "BJORGUM": 68.0, "BOLLINGER": 62.0, "DISP_REBAL": 72.0, "EMA_PULLBACK": 64.0,
    "FVG_MIT": 70.0, "ICHIMOKU": 65.0, "IFVG": 73.0, "JUDAS_SWING": 75.0,
    "LDN_REVERSAL": 76.0, "LONDON_BO": 70.0, "MACD": 65.0, "MALAYSIAN_SNR": 68.0,
    "MALAYSIAN_SNR_BREAKOUT": 70.0, "NY_REVERSAL": 75.0, "OB_MIT": 70.0,
    "ORDER_BLOCK": 70.0, "OTE_CONT": 69.0, "PO3": 76.0, "RANGE_FADE": 62.0,
    "RSI_DIV": 68.0, "SCALP_BB_FADE": 70.0, "SCALP_EMA": 70.0,
    "SCALP_RANGE_BRK": 70.0, "SCALP_RSI_SNAP": 70.0, "SMS_BMS_RTO": 72.0,
    "STRUCT_REACT": 70.0, "THREE_BAR_DELIVERY_BREAK": 74.0, "TURTLE_SOUP": 70.0,
    "WEEKLY_EXP": 70.0,
    "SH_BMS_RTO_V2": 78.0, "SILVER_BULLET_V2": 80.0, "OTE_CONT_V2": 76.0,
    "ORDER_BLOCK_V2": 75.0, "FVG_CONT_V2": 74.0,
}

MIN_TRADES_MEANINGFUL = 15   # sotto questa soglia il PF non e' interpretabile


def main():
    results = []
    strats = sorted(TF_MAP)
    for idx, strat in enumerate(strats, 1):
        tf = TF_MAP[strat]
        try:
            r = tg.run_trend_gate([strat], tf, buy_only=set(),
                                   scores={strat: SCORES.get(strat, 70.0)},
                                   buy_only_execution=False)
            r["strat"] = strat
            r["tf"] = tf
            results.append(r)
            print(f"[{idx}/{len(strats)}] {strat} fatto (src={r['src']}, trades={r['trades']})", flush=True)
        except Exception as e:
            print(f"[{idx}/{len(strats)}] {strat} ERRORE: {str(e)[:150]}", flush=True)

    print("\n" + "=" * 130)
    print(f"{'Strategia':<26}{'TF':>3}{'Trade':>7}{'PF':>7}{'WR%':>7}{'NetPnL':>10}  {'BUY n/PF':<14}{'SELL n/PF':<14}")
    results.sort(key=lambda r: (r["pf"] is None, -(r["pf"] or 0)))
    for r in results:
        flag = "" if r["trades"] >= MIN_TRADES_MEANINGFUL else "  (campione troppo piccolo)"
        wr = r["wr"] if r["wr"] is not None else 0.0
        buy_s = f"{r['n_buy']}/{r['pf_buy']}"
        sell_s = f"{r['n_sell']}/{r['pf_sell']}"
        print(f"{r['strat']:<26}{r['tf']:>3}{r['trades']:>7}{str(r['pf']):>7}{wr:>7.1f}{r['net_pnl']:>10}  "
              f"{buy_s:<14}{sell_s:<14}{flag}")
    print("=" * 130)


if __name__ == "__main__":
    main()
