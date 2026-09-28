def win_rate(trades):
    if not trades:
        return 0.0
    win_count = sum(1 for t in trades if t['net_pnl'] > 0)
    return win_count / len(trades)
print(win_rate([{'net_pnl': 10.0}, {'net_pnl': -5.0}, {'net_pnl': 3.0}, {'net_pnl': -1.0}]))
