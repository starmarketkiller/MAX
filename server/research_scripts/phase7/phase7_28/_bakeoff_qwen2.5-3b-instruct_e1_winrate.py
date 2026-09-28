def win_rate(trades):
    if not trades:
        return 0.0
    return sum(1 for trade in trades if trade['net_pnl'] > 0) / len(trades)
print(win_rate([{'net_pnl': 10.0}, {'net_pnl': -5.0}, {'net_pnl': 3.0}, {'net_pnl': -1.0}]))
