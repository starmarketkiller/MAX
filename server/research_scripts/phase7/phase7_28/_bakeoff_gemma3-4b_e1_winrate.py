def win_rate(trades):
    """
    Calcola la frazione di trade con net_pnl > 0.

    Args:
        trades: Lista di dict con chiave 'net_pnl' (float).

    Returns:
        La frazione (float fra 0 e 1) di trade con net_pnl > 0.
        Se la lista e' vuota, ritorna 0.0.
    """
    if not trades:
        return 0.0

    wins = sum(1 for trade in trades if trade['net_pnl'] > 0)
    return float(wins) / len(trades)
print(win_rate([{'net_pnl': 10.0}, {'net_pnl': -5.0}, {'net_pnl': 3.0}, {'net_pnl': -1.0}]))
