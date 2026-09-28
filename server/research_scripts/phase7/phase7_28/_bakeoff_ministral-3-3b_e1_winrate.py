def win_rate(trades):
    return sum(1 for trade in trades if trade['net_pnl'] > 0) / len(trades) if trades else 0.0
print(win_rate([{'net_pnl': 10.0}, {'net_pnl': -5.0}, {'net_pnl': 3.0}, {'net_pnl': -1.0}]))
