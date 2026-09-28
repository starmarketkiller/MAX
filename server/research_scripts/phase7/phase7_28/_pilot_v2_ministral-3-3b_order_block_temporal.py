import json

def compute_temporal_concentration(events):
    anno_dict = {}

    for e in events:
        anno = e['entry_time'][:4]
        if anno not in anno_dict:
            anno_dict[anno] = {'n_trades': 0, 'net_pnl_sum': 0.0, 'positive_trades': 0}

        anno_dict[anno]['n_trades'] += 1
        anno_dict[anno]['net_pnl_sum'] += e['net_pnl']
        if e['net_pnl'] > 0:
            anno_dict[anno]['positive_trades'] += 1

    result = {}

    for anno, data in anno_dict.items():
        result[anno] = {
            'n_trades': data['n_trades'],
            'net_pnl_sum': data['net_pnl_sum'],
            'win_rate': data['positive_trades'] / data['n_trades']
        }

    result['years_with_positive_net'] = sum(1 for anno in anno_dict if anno_dict[anno]['net_pnl_sum'] > 0)
    result['years_total_with_at_least_1_trade'] = len(anno_dict)

    return result
events = [{"entry_time": "2024.04.08 17:15:00", "net_pnl": 97.0, "entry_price": 2320.43, "exit_price": 2422.66, "entry_tp": 2422.65, "direction": 1}, {"entry_time": "2024.05.15 17:00:00", "net_pnl": -49.4, "entry_price": 2358.39, "exit_price": 2323.79, "entry_tp": 2462.2, "direction": 1}, {"entry_time": "2024.10.02 18:00:00", "net_pnl": -40.2, "entry_price": 2648.34, "exit_price": 2613.34, "entry_tp": 2752.33, "direction": 1}, {"entry_time": "2024.12.12 16:15:00", "net_pnl": -40.6, "entry_price": 2690.69, "exit_price": 2650.93, "entry_tp": 2809.85, "direction": 1}, {"entry_time": "2025.03.19 11:45:00", "net_pnl": 107.2, "entry_price": 3030.23, "exit_price": 3148.73, "entry_tp": 3148.72, "direction": 1}, {"entry_time": "2025.04.09 02:30:00", "net_pnl": 158.8, "entry_price": 2981.32, "exit_price": 3142.69, "entry_tp": 3142.65, "direction": 1}, {"entry_time": "2025.05.20 05:00:00", "net_pnl": -77.6, "entry_price": 3221.37, "exit_price": 3253.71, "entry_tp": 3480.18, "direction": 1}, {"entry_time": "2025.06.10 04:15:00", "net_pnl": 168.3, "entry_price": 3313.68, "exit_price": 3480.2, "entry_tp": 3493.59, "direction": 1}, {"entry_time": "2025.09.04 01:15:01", "net_pnl": -39.5, "entry_price": 3560.43, "exit_price": 3520.94, "entry_tp": 3678.75, "direction": 1}, {"entry_time": "2026.01.07 04:00:00", "net_pnl": 259.7, "entry_price": 4465.93, "exit_price": 4736.94, "entry_tp": 4736.93, "direction": 1}, {"entry_time": "2026.03.30 04:00:00", "net_pnl": -244.7, "entry_price": 4432.6, "exit_price": 4249.71, "entry_tp": 4980.9, "direction": 1}, {"entry_time": "2026.07.24 11:00:00", "net_pnl": -86.3, "entry_price": 4048.27, "exit_price": 4136.51, "entry_tp": 3783.54, "direction": -1}, {"entry_time": "2026.08.17 15:45:00", "net_pnl": 284.7, "entry_price": 4378.67, "exit_price": 4669.48, "entry_tp": 4669.41, "direction": 1}]
print(json.dumps(compute_temporal_concentration(events)))
