#!/usr/bin/env python3
"""
04/08 (17) - Fase 0: Execution Audit, richiesta esplicitamente dall'utente
dopo aver letto il riferimento di esecuzione delle 37 strategie: "il
problema non e' solo la strategia, e' l'esecuzione della strategia".

Non sostituisce il protocollo NQROS v3.1 (Fase 1-10) - lo PRECEDE. Prima
di fidarsi di qualunque PF/trade-count, questo script misura quanto
segnale grezzo viene davvero convertito in un trade, e perche' no, per
UNA strategia alla volta (stesso motore di run_backtest, stessa logica
di filtri/posizione, ma con ogni barra di segnale grezzo classificata
invece di essere silenziosamente scartata).

Copre dalla checklist proposta dall'utente cio' che e' onestamente
misurabile con questo motore (bar-close, nessun dato tick):

  MISURATO qui:
  - Opportunity Loss % (segnali teorici vs trade aperti) + motivo del
    mancato ingresso (gia' in posizione / cooldown / confirm_bars /
    htf_filter / session_filter) - voci 5+8 della checklist.
  - Entry Quality: non "l'avrei aperto guardando il grafico" (richiede
    giudizio umano/visivo, non automatizzabile in modo rigoroso con
    questo motore) ma un proxy oggettivo su MFE/MAE - stesso principio
    gia' usato nei deep-dive Fase 2 (AMD_CONT/SILVER_BULLET/TURTLE_SOUP:
    "perdite segnale-sbagliato" MFE<0.3R vs "quasi-vincenti" MFE>=0.5R),
    qui esteso a un punteggio 1-5 stelle per OGNI trade, non solo i
    perdenti.
  - Fedelta' SL/TP: dedotta da STRATEGY_SLTP_ALWAYS/STRATEGY_TARGETS_ALWAYS
    (strutturale = fedele, generico = approssimazione ATR).

  DICHIARATO ma NON misurato (limite architetturale, non pigrizia):
  - Trigger/ritardo tick-by-tick: il motore valuta SOLO barre chiuse,
    mai singoli tick - non c'e' dato per misurare un ritardo in secondi
    o "barre" rispetto a un ipotetico ingresso intrabarra reale, tranne
    per le strategie con un "touch" che nel vero MQL5 e' su bid live
    (SILVER_BULLET/ORDER_BLOCK/SH_BMS_RTO) - per quelle il rischio di
    ritardo e' flaggato qualitativamente, non quantificato in barre.
  - "Lo avrei aperto guardando il grafico?": richiede giudizio visivo
    umano; il proxy MFE/MAE sopra e' la migliore approssimazione
    oggettiva disponibile, non un sostituto equivalente.

Uso: python3 server/research_scripts/execution_audit.py STRATEGY [TF...]
"""
import sys
from collections import Counter

sys.path.insert(0, "server")
import backtest as bt


def execution_audit(strategy, timeframe, symbol="XAUUSD", bars=2500,
                     cost_preset="retail_standard", htf_filter=False, trend_period=50,
                     confirm_bars=0, cooldown_bars=0, loss_cooldown_bars=0,
                     session_filter=None, risk_pct=1.0, atr_sl=1.5, atr_tp=3.0,
                     max_hold=40):
    candles, src = bt._fetch_real(symbol, timeframe, bars)
    ind = bt._prep(candles)
    closes = [c["close"] for c in candles]

    def _sma(idx, p):
        if idx < p - 1:
            return None
        return sum(closes[idx - p + 1: idx + 1]) / p

    reasons = Counter()
    entries = []   # dettaglio per ogni trade aperto: quality score
    equity = 10000.0
    pos = None
    last_close_i = -10 ** 9
    last_loss_i = -10 ** 9
    fn = bt.STRATEGIES[strategy]

    for i in range(2, len(candles)):
        px = candles[i]["close"]
        if pos:
            hi, lo = candles[i]["high"], candles[i]["low"]
            risk_dist = pos["risk_dist"]
            if risk_dist > 0:
                adverse = (pos["entry"] - lo) if pos["dir"] == 1 else (hi - pos["entry"])
                favorable = (hi - pos["entry"]) if pos["dir"] == 1 else (pos["entry"] - lo)
                pos["mae_r"] = max(pos["mae_r"], adverse / risk_dist)
                pos["mfe_r"] = max(pos["mfe_r"], favorable / risk_dist)
            hit = None
            if pos["dir"] == 1:
                if lo <= pos["sl"]:
                    hit = ("SL", pos["sl"])
                elif hi >= pos["tp"]:
                    hit = ("TP", pos["tp"])
            else:
                if hi >= pos["sl"]:
                    hit = ("SL", pos["sl"])
                elif lo <= pos["tp"]:
                    hit = ("TP", pos["tp"])
            if not hit and (i - pos["open_i"]) >= max_hold:
                hit = ("TIME", px)
            if hit:
                reason, exitpx = hit
                rd = pos["risk_dist"] if pos["risk_dist"] > 0 else 1e-9
                r_mult = ((exitpx - pos["entry"]) / rd) if pos["dir"] == 1 \
                    else ((pos["entry"] - exitpx) / rd)
                pnl = r_mult * pos["risk_money"]
                equity += pnl
                # --- Entry Quality (proxy oggettivo MFE/MAE, non giudizio
                # visivo - vedi nota in cima al file) ---
                mfe, mae = pos["mfe_r"], pos["mae_r"]
                if reason == "TP":
                    stars = 5 if mae < 0.3 else (4 if mae < 0.6 else 3)
                elif reason == "TIME":
                    stars = 3 if mfe >= 0.5 else 2
                else:  # SL
                    stars = 1 if mfe < 0.3 else (2 if mfe < 0.7 else 3)
                entries.append({"open_i": pos["open_i"], "dir": pos["dir"], "reason": reason,
                                 "r": round(r_mult, 2), "mfe_r": round(mfe, 2), "mae_r": round(mae, 2),
                                 "stars": stars})
                pos = None
                last_close_i = i
                if pnl < 0:
                    last_loss_i = i
            else:
                # Posizione ancora aperta su questa barra - controlla
                # comunque se sarebbe scattato un segnale, per contare
                # correttamente l'opportunity loss "gia' in posizione"
                # (altrimenti il segnale grezzo non viene MAI valutato
                # su queste barre e questa voce risulta sempre 0 - bug
                # trovato e corretto prima di fidarsi del report).
                atr_chk = ind["atr"][i]
                if atr_chk and atr_chk > 0 and fn(candles, ind, i) != 0:
                    reasons["ALREADY_IN_POSITION"] += 1
            continue

        atr = ind["atr"][i]
        if not atr or atr <= 0:
            continue
        v = fn(candles, ind, i)
        if v == 0:
            continue   # nessun segnale grezzo su questa barra - non conta per l'opportunity loss

        # Da qui: c'e' un segnale grezzo. Classifica cosa gli succede,
        # stesso ORDINE di controllo di run_backtest.
        if cooldown_bars > 0 and (i - last_close_i) < cooldown_bars:
            reasons["COOLDOWN"] += 1
            continue
        if loss_cooldown_bars > 0 and (i - last_loss_i) < loss_cooldown_bars:
            reasons["LOSS_COOLDOWN"] += 1
            continue
        if confirm_bars > 0:
            ok = all(i - k >= 0 and fn(candles, ind, i - k) == v for k in range(1, confirm_bars + 1))
            if not ok:
                reasons["CONFIRM_BARS"] += 1
                continue
        sig = v
        if htf_filter:
            sma = _sma(i, int(trend_period))
            if sma is not None and ((sig == 1 and px < sma) or (sig == -1 and px > sma)):
                reasons["HTF_FILTER"] += 1
                continue
        if session_filter is not None and ind["sess"]["session"][i] not in session_filter:
            reasons["SESSION_FILTER"] += 1
            continue

        # Segnale accettato -> apre un trade (stessa logica SL/TP di run_backtest)
        reasons["TRADE_OPENED"] += 1
        sl = px - sig * atr * atr_sl
        tp = px + sig * atr * atr_tp
        sltp_fn = bt.STRATEGY_SLTP_ALWAYS.get(strategy)
        if sltp_fn:
            dyn = sltp_fn(candles, ind, i, sig, px, atr)
            if dyn is not None:
                sl, tp = dyn
        target_fn = bt.STRATEGY_TARGETS_ALWAYS.get(strategy)
        if target_fn and not sltp_fn:
            dyn_tp = target_fn(candles, ind, i, sig, px, atr, sl_mult=atr_sl, pick="nearest")
            if dyn_tp is not None:
                tp = dyn_tp
        risk_dist = abs(px - sl)
        pos = {"dir": sig, "entry": px, "sl": sl, "tp": tp, "open_i": i,
               "risk_money": equity * (risk_pct / 100.0), "risk_dist": risk_dist,
               "mae_r": 0.0, "mfe_r": 0.0}

    theoretical = sum(reasons.values())
    opened = reasons.get("TRADE_OPENED", 0)
    opp_loss_pct = round((1 - opened / theoretical) * 100, 1) if theoretical else 0.0

    star_avg = round(sum(e["stars"] for e in entries) / len(entries), 2) if entries else 0.0
    sltp_kind = ("strutturale" if strategy in bt.STRATEGY_SLTP_ALWAYS
                 else ("TP strutturale/SL generico" if strategy in bt.STRATEGY_TARGETS_ALWAYS
                       else "generico (ATR)"))

    return {
        "strategy": strategy, "tf": timeframe, "bars": len(candles), "src": src,
        "theoretical_signals": theoretical, "trades_opened": opened,
        "opportunity_loss_pct": opp_loss_pct,
        "reasons": dict(reasons),
        "sltp_kind": sltp_kind,
        "entry_quality_avg_stars": star_avg,
        "entry_quality_dist": Counter(e["stars"] for e in entries),
        "entries": entries,
    }


def print_report(r):
    print(f"\n=== {r['strategy']} ({r['tf']}, {r['bars']} barre, {r['src']}) ===")
    print(f"  Segnali teorici: {r['theoretical_signals']}")
    print(f"  Trade aperti:    {r['trades_opened']}")
    print(f"  Opportunity Loss: {r['opportunity_loss_pct']}%")
    print(f"  Motivi scarto:")
    for k, v in sorted(r["reasons"].items(), key=lambda x: -x[1]):
        if k != "TRADE_OPENED":
            print(f"    {k}: {v}")
    print(f"  SL/TP: {r['sltp_kind']}")
    print(f"  Entry Quality media: {r['entry_quality_avg_stars']} stelle "
          f"(distribuzione {dict(sorted(r['entry_quality_dist'].items()))})")


if __name__ == "__main__":
    strat = sys.argv[1] if len(sys.argv) > 1 else "TURTLE_SOUP"
    tfs = sys.argv[2:] or ["4h", "1h", "1d"]
    for tf in tfs:
        r = execution_audit(strat, tf)
        print_report(r)
