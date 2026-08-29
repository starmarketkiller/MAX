#!/usr/bin/env python3
"""29/08 - motore di esecuzione "come MT5 vero", non un backtest astratto.

Porta in Python, formula per formula, i pezzi del motore MQL5 reale che il
vecchio backtest.py NON modellava affatto (confermato stanotte: zero
occorrenze di lotto minimo/volume_step in tutto backtest.py):

1. NXS_CalcLotRisk (NXS_Risk.mqh) - dimensionamento a rischio%, floor al
   lotto minimo broker, rifiuto RISK_SIZE se anche il minimo rischia troppo
   (o esecuzione "a rischio maggiorato" se sotto il tetto configurato).
2. Spread REALE per ora del giorno (server time), da un profilo estratto
   dai tick reali di GOLD su questo broker (nxs_spread_profile_gold.csv,
   10 mesi, Nov 2025-Ago 2026, milioni di tick via CopyTicksRange - non un
   parser del formato .tkc, dati ufficiali del terminale). Niente replay
   tick-per-tick: un istogramma per ora basta per un'esecuzione realistica,
   verificato stanotte che i segnali delle strategie valutano comunque
   sempre su barre chiuse, mai su singoli tick.
3. NXS_Profile_Enabled - lo stesso terzo cancello (whitelist indipendente
   da "voglio provarla") trovato stanotte, che bloccava silenziosamente
   tutte e 6 le strategie nuove nonostante il loro toggle fosse true.

Specifiche simbolo GOLD confermate dai log reali di stanotte (non assunte):
tick_size=0.01, tick_value=$1.00/lotto (derivato da un rifiuto RISK_SIZE
reale: slDist=133.42, ticksInSL=13342 -> tick_size=133.42/13342=0.01;
riskAtMin=133.42 per minLot=0.01 -> tick_value=133.42/(13342*0.01)=1.00).
"""
import os
import csv
import random
import math

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- Specifiche simbolo GOLD (XM Global, confermate dai log reali) ----
TICK_SIZE = 0.01
TICK_VALUE_PER_LOT = 1.00     # $ per tick (0.01 di prezzo) per 1.0 lotto
VOLUME_MIN = 0.01
VOLUME_STEP = 0.01
VOLUME_MAX_CAP = 5.0          # InpMaxLot (NXS_Inputs.mqh)

# ---- Gate RISK_SIZE (NXS_Risk.mqh, InpMaxRiskAtMinLotPct) ----
MAX_RISK_AT_MINLOT_PCT = 8.0

# ---- NXS_Profile_Enabled: whitelist reale (NXS_StrategyProfiles.mqh) ----
# NB: elenco delle strategie ATTIVE nel nucleo v3.0 + le 6 nuove da
# TradingView. Se una strategia manca qui, nel motore vero non aprirebbe
# MAI un trade (bug trovato stanotte) - va tenuto sincronizzato a mano con
# NXS_Profile_Enabled() quando si aggiunge/rimuove qualcosa la' dentro.
PROFILE_ENABLED = {
    "BREAKOUT_ACC": True, "MACD": True, "LONDON_BO": True, "LIQ_SWEEP": True,
    "AMD_CONT": True, "FVG_CONT": True, "TSI": True, "ADX_RSI": True,
    "SAR": True, "EMA_PULLBACK": True, "THREE_BAR_DELIVERY_BREAK": True,
    "LDN_REVERSAL": True, "AMD_REVERSAL": True, "TURTLE_SOUP": False,
    "FVG_MIT_WINDOW": False, "CRT": False, "SH_BMS_RTO_V2": False,
    "BB_SQUEEZE": False, "STRUCT_REACT": False, "DISP_REBAL": False,
    "OTE_CONT": False, "ICHIMOKU": False,
    "BAR_UPDN": True, "PMAX": True, "MACD_SMA200": True,
    "RSI_DIV_PINE": True, "ICHIMOKU_HULL_MACD": True, "3COMMAS_BOT": True,
}


def profile_enabled(strat_name):
    """Replica NXS_Profile_Enabled: default False (non elencata = mai aperta)."""
    return PROFILE_ENABLED.get(strat_name, False)


# ---- Spread reale per ora del giorno ----
_spread_hist = {}   # hour -> list of (bin_upper_pts, count) per campionamento


def load_spread_profile(path=None):
    global _spread_hist
    path = path or os.path.join(HERE, "nxs_spread_profile_gold.csv")
    _spread_hist = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            h = int(row["hour"])
            # Ricostruiamo una distribuzione campionabile dai percentili
            # (non abbiamo l'istogramma completo qui, solo i percentili
            # scritti da MQL5): pesi uniformi sui bucket p10/p25/p50/p75/
            # p90/p95/p99 + coda oltre p99 fino a un cap ragionevole.
            pts = [
                (0.10, int(row["p10"])), (0.25, int(row["p25"])),
                (0.50, int(row["p50"])), (0.75, int(row["p75"])),
                (0.90, int(row["p90"])), (0.95, int(row["p95"])),
                (0.99, int(row["p99"])),
            ]
            _spread_hist[h] = pts
    return _spread_hist


def sample_spread_points(hour, rng=random):
    """Campiona uno spread realistico (in punti) per l'ora indicata,
    interpolando tra i percentili reali estratti dai tick di stanotte."""
    if not _spread_hist:
        load_spread_profile()
    pts = _spread_hist.get(hour) or _spread_hist.get(hour % 24)
    if not pts:
        return 55  # fallback: mediana tipica osservata nelle ore normali
    u = rng.random()
    # Interpolazione lineare tra i punti percentile noti (0->p10 come base).
    xs = [0.0] + [p[0] for p in pts]
    ys = [pts[0][1] * 0.6] + [p[1] for p in pts]   # stima sotto p10, prudente
    if u >= xs[-1]:
        # coda oltre p99: usa lo stesso passo dell'ultimo intervallo noto
        step = ys[-1] - ys[-2] if len(ys) > 1 else 10
        extra = (u - xs[-1]) / (1.0 - xs[-1])
        return max(1, int(ys[-1] + extra * max(step, 5) * 5))
    for i in range(1, len(xs)):
        if u <= xs[i]:
            frac = (u - xs[i-1]) / max(xs[i] - xs[i-1], 1e-9)
            return max(1, int(ys[i-1] + frac * (ys[i] - ys[i-1])))
    return ys[-1]


def spread_price(hour, rng=random):
    return sample_spread_points(hour, rng) * TICK_SIZE


# ---- NXS_SpreadOK (NXS_MTFSpreadVol.mqh) - gate GLOBALE, chiamato in
# OnTick PRIMA di qualunque dispatch di strategia (NEXUS_EA_v2.mq5:1033):
# se lo spread e' troppo largo, quel tick non apre NESSUNA nuova posizione
# per NESSUNA strategia. La variante "adattiva" (NXR_SpreadOK) esiste nel
# codice ma InpNXR_Enable e' hardcoded false (non e' nemmeno un input) -
# morta per costruzione (stessa scoperta fatta per IFVG/FVG_Mit il 25/08),
# quindi il gate VIVO e' sempre la versione semplice sotto.
MAX_SPREAD_POINTS_GOLD = 80       # g_profile.maxSpreadPts per XAUUSD
MAX_SPREAD_ATR_PCT = 8.0          # InpMaxSpreadAtrPct


def spread_ok(spread_pts, atr):
    """True se il tick sarebbe passato NXS_SpreadOK(). atr: ATR corrente
    (M15, e' l'ultimo calcolato al momento del check globale in OnTick,
    prima che il loop multi-TF lo sovrascriva per-strategia)."""
    if spread_pts > MAX_SPREAD_POINTS_GOLD:
        return False
    if atr and atr > 0:
        pct_of_atr = (spread_pts * TICK_SIZE / atr) * 100.0
        if pct_of_atr > MAX_SPREAD_ATR_PCT:
            return False
    return True


# ---- NXS_CalcLotRisk, porting fedele (NXS_Risk.mqh righe 49-128) ----
def calc_lot_risk(sl_price_dist, risk_pct, balance, strat_name="",
                   anti_bleed_mult=1.0, account_lot_mult=1.0, streak_mult=1.0,
                   max_lot=VOLUME_MAX_CAP):
    """Ritorna (lots, reason). lots<=0 significa "non aprire" (reason spiega perche').
    anti_bleed_mult/account_lot_mult/streak_mult di default 1.0 (=off, come
    InpUseAntiBleed=false/InpUseStreakSizing di default nel motore vero)."""
    risk = balance * risk_pct / 100.0
    risk *= anti_bleed_mult
    risk *= account_lot_mult
    risk *= streak_mult
    if risk <= 0:
        return 0.0, "risk<=0"

    if TICK_VALUE_PER_LOT <= 0 or TICK_SIZE <= 0 or sl_price_dist <= 0:
        return 0.0, "metadati_non_validi"

    ticks_in_sl = sl_price_dist / TICK_SIZE
    if ticks_in_sl <= 0:
        return 0.0, "ticks_in_sl<=0"
    lots = risk / (ticks_in_sl * TICK_VALUE_PER_LOT)

    max_lot_eff = min(max_lot, VOLUME_MAX_CAP)
    lots = min(max_lot_eff, lots)
    lots = math.floor(lots / VOLUME_STEP) * VOLUME_STEP
    lots = round(lots, 2)

    if lots < VOLUME_MIN:
        risk_at_min = ticks_in_sl * TICK_VALUE_PER_LOT * VOLUME_MIN
        if risk_at_min > risk * 1.0000001:
            ceiling_money = balance * MAX_RISK_AT_MINLOT_PCT / 100.0
            if MAX_RISK_AT_MINLOT_PCT > 0 and risk_at_min <= ceiling_money:
                return VOLUME_MIN, "rischio_maggiorato"
            return 0.0, "ordine_rifiutato_risk_size"
        lots = VOLUME_MIN
    return lots, "ok"


if __name__ == "__main__":
    load_spread_profile()
    print("Profilo spread caricato, ore campione:")
    for h in (0, 1, 8, 14, 20):
        vals = [sample_spread_points(h) for _ in range(5)]
        print(f"  ora {h:02d}: campioni spread(pt) = {vals}")

    print("\nEsempio RISK_SIZE su conto $500 e $1000, stop $38 (WEEKLY_EXP nativo):")
    for bal in (500, 1000):
        lots, reason = calc_lot_risk(38.0, 1.0, bal, "WEEKLY_EXP")
        print(f"  balance=${bal}: lots={lots} reason={reason}")
