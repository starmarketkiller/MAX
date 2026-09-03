import json, statistics
from datetime import datetime

with open("emapb_deep_results.json", encoding="utf-8") as f:
    results = json.load(f)

for r in results:
    r["entry_time"] = datetime.fromisoformat(r["entry_time"])
    r["exit_time"] = datetime.fromisoformat(r["exit_time"])
    r["mfe_time"] = datetime.fromisoformat(r["mfe_time"])
    r["mae_time"] = datetime.fromisoformat(r["mae_time"])

wins = [r for r in results if r["pnl"] > 0]
losses = [r for r in results if r["pnl"] <= 0]

print(f"n trade totali = {len(results)}  vinti={len(wins)}  persi={len(losses)}")

# ---- winners: how efficiently did they capture their own peak? ----
print("\n=== VINCENTI: efficienza di cattura del picco (pnl / MFE) ===")
win_eff = []
for r in wins:
    if r["mfe_usd"] > 1:
        eff = r["pnl"] / r["mfe_usd"]
        win_eff.append(eff)
if win_eff:
    print(f"n={len(win_eff)}  media={statistics.mean(win_eff)*100:.0f}%  mediana={statistics.median(win_eff)*100:.0f}%")
    print(f"  catturano >80% del picco: {sum(1 for x in win_eff if x>0.8)}")
    print(f"  catturano 50-80%: {sum(1 for x in win_eff if 0.5<=x<=0.8)}")
    print(f"  catturano <50%: {sum(1 for x in win_eff if x<0.5)}")

# ---- losers: how many were floating in meaningful profit before reversing to a loss? ----
print("\n=== PERDENTI: quanti erano in profitto flottante prima di girare in perdita? ===")
loser_had_profit = [r for r in losses if r["mfe_usd"] > 10]
print(f"perdenti con MFE > $10 in un certo momento: {len(loser_had_profit)} / {len(losses)} "
      f"({len(loser_had_profit)/len(losses)*100:.0f}%)")
loser_had_profit_big = [r for r in losses if r["mfe_usd"] > 25]
print(f"perdenti con MFE > $25 (profitto flottante consistente) prima di girare in SL: {len(loser_had_profit_big)}")

tot_mfe_given_back_by_losers = sum(r["mfe_usd"] for r in loser_had_profit)
tot_actual_loss = sum(-r["pnl"] for r in loser_had_profit)
print(f"Somma MFE mai raggiunta da questi perdenti: ${tot_mfe_given_back_by_losers:.2f}")
print(f"Somma delle perdite finali di questi stessi trade: ${tot_actual_loss:.2f}")
print(f"-> se si fosse chiuso a meta' del picco MFE su questi trade, il PnL netto extra sarebbe stato circa "
      f"${sum(r['mfe_usd']*0.5 - r['pnl'] for r in loser_had_profit):.2f}")

print("\n--- dettaglio perdenti con MFE > $25 (persero un trade che stava per essere vincente) ---")
print(f"{'entry':17s} {'dir':4s} {'MFE$':>7s} {'ore a MFE':>10s} {'pnl finale':>11s} {'durata tot h':>13s}")
for r in sorted(loser_had_profit_big, key=lambda x: -x["mfe_usd"]):
    t_to_mfe_h = (r["mfe_time"] - r["entry_time"]).total_seconds()/3600
    dur_h = (r["exit_time"] - r["entry_time"]).total_seconds()/3600
    print(f"{r['entry_time'].strftime('%Y-%m-%d %H:%M'):17s} {'buy' if r['dir']==1 else 'sell':4s} "
          f"{r['mfe_usd']:7.2f} {t_to_mfe_h:10.1f} {r['pnl']:11.2f} {dur_h:13.1f}")

# ---- timing: how long after MFE peak until the trade actually closes? fast reversal vs slow bleed ----
print("\n=== Tempo dal picco (MFE) alla chiusura, per i perdenti con MFE>$25 ===")
for r in sorted(loser_had_profit_big, key=lambda x: -x["mfe_usd"]):
    time_after_peak_h = (r["exit_time"] - r["mfe_time"]).total_seconds()/3600
    print(f"{r['entry_time'].strftime('%Y-%m-%d %H:%M')}: picco {r['mfe_usd']:.2f}$ poi {time_after_peak_h:.1f}h fino alla chiusura a {r['pnl']:.2f}$")

# ---- direction bias: buy vs sell in the giveback pattern ----
print("\n=== Bias direzionale ===")
buy_losers_mfe = [r for r in loser_had_profit if r["dir"]==1]
sell_losers_mfe = [r for r in loser_had_profit if r["dir"]==-1]
print(f"perdenti-con-MFE: buy={len(buy_losers_mfe)}  sell={len(sell_losers_mfe)}")

# ---- how fast does MFE get reached (bars/hours) - fast spike vs slow build ----
print("\n=== Tempo per raggiungere il picco (tutti i trade con MFE>$15) ===")
big = [r for r in results if r["mfe_usd"] > 15]
fast = [r for r in big if (r["mfe_time"]-r["entry_time"]).total_seconds()/3600 < 4]
slow = [r for r in big if (r["mfe_time"]-r["entry_time"]).total_seconds()/3600 >= 4]
print(f"n totale con MFE>$15: {len(big)}")
print(f"picco raggiunto entro 4h dall'ingresso (spike rapido): {len(fast)}")
print(f"picco raggiunto dopo 4h (costruzione lenta): {len(slow)}")
def pnl_stats(group, label):
    if not group: return
    winners = sum(1 for r in group if r["pnl"]>0)
    print(f"  {label}: n={len(group)} vincenti={winners} ({winners/len(group)*100:.0f}%) pnl medio={statistics.mean(r['pnl'] for r in group):.2f}")
pnl_stats(fast, "spike rapido (<4h)")
pnl_stats(slow, "costruzione lenta (>=4h)")
