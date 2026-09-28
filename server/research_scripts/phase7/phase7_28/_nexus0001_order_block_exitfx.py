import json

def compute_exit_efficiency(events):
    ratios = []
    skipped_zero = 0
    for event in events:
        direction = event['direction']
        entry_price = event['entry_price']
        exit_price = event['exit_price']
        entry_tp = event['entry_tp']

        if direction == 1:
            captured = exit_price - entry_price
            available = entry_tp - entry_price
        elif direction == -1:
            captured = entry_price - exit_price
            available = entry_price - entry_tp
        else:
            continue

        if available == 0:
            skipped_zero += 1
            continue

        ratio = captured / available
        ratios.append(ratio)

    mean_ratio = sum(ratios) / len(ratios) if ratios else 0.0
    return {
        'mean_exit_efficiency_ratio': mean_ratio,
        'n_events_used': len(ratios),
        'n_events_skipped_zero_available': skipped_zero
    }

events = [{"entry_time": "2024.04.08 17:15:00", "net_pnl": 97.0, "entry_price": 2320.43, "exit_price": 2422.66, "entry_tp": 2422.65, "direction": 1}, {"entry_time": "2024.05.15 17:00:00", "net_pnl": -49.4, "entry_price": 2358.39, "exit_price": 2323.79, "entry_tp": 2462.2, "direction": 1}, {"entry_time": "2024.10.02 18:00:00", "net_pnl": -40.2, "entry_price": 2648.34, "exit_price": 2613.34, "entry_tp": 2752.33, "direction": 1}, {"entry_time": "2024.12.12 16:15:00", "net_pnl": -40.6, "entry_price": 2690.69, "exit_price": 2650.93, "entry_tp": 2809.85, "direction": 1}, {"entry_time": "2025.03.19 11:45:00", "net_pnl": 107.2, "entry_price": 3030.23, "exit_price": 3148.73, "entry_tp": 3148.72, "direction": 1}, {"entry_time": "2025.04.09 02:30:00", "net_pnl": 158.8, "entry_price": 2981.32, "exit_price": 3142.69, "entry_tp": 3142.65, "direction": 1}, {"entry_time": "2025.05.20 05:00:00", "net_pnl": -77.6, "entry_price": 3221.37, "exit_price": 3253.71, "entry_tp": 3480.18, "direction": 1}, {"entry_time": "2025.06.10 04:15:00", "net_pnl": 168.3, "entry_price": 3313.68, "exit_price": 3480.2, "entry_tp": 3493.59, "direction": 1}, {"entry_time": "2025.09.04 01:15:01", "net_pnl": -39.5, "entry_price": 3560.43, "exit_price": 3520.94, "entry_tp": 3678.75, "direction": 1}, {"entry_time": "2026.01.07 04:00:00", "net_pnl": 259.7, "entry_price": 4465.93, "exit_price": 4736.94, "entry_tp": 4736.93, "direction": 1}, {"entry_time": "2026.03.30 04:00:00", "net_pnl": -244.7, "entry_price": 4432.6, "exit_price": 4249.71, "entry_tp": 4980.9, "direction": 1}, {"entry_time": "2026.07.24 11:00:00", "net_pnl": -86.3, "entry_price": 4048.27, "exit_price": 4136.51, "entry_tp": 3783.54, "direction": -1}, {"entry_time": "2026.08.17 15:45:00", "net_pnl": 284.7, "entry_price": 4378.67, "exit_price": 4669.48, "entry_tp": 4669.41, "direction": 1}]
print(json.dumps(compute_exit_efficiency(events)))
