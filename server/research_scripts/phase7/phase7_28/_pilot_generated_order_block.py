import json
from datetime import datetime
from collections import defaultdict

def _dt(s):
    return datetime.strptime(s, '%Y.%m.%d %H:%M:%S')

def compute_temporal_concentration(events):
    by_year = defaultdict(list)
    for e in events:
        by_year[_dt(entry_time(e)).year].append(net_pnl(e))

    per_year = {}
    for y, v in sorted(by_year.items()):
        per_year[str(y)] = {
            'n_trades': len(v),
            'net_pnl_sum': sum(v),
            'win_rate': sum(1 for p in v if p > 0) / len(v)
        }

    years_positive = sum(1 for v in per_year.values() if v['net_pnl_sum'] > 0)
    years_total_with_at_least_1_trade = len(per_year)

    per_year['years_with_positive_net'] = years_positive
    per_year['years_total_with_at_least_1_trade'] = years_total_with_at_least_1_trade

    return per_year


# Data di input
events = [
    {"entry_time": "2024.04.08 17:15:00", "net_pnl": 97.0},
    {"entry_time": "2024.05.15 17:00:00", "net_pnl": -49.4},
    {"entry_time": "2024.10.02 18:00:00", "net_pnl": -40.2},
    {"entry_time": "2024.12.12 16:15:00", "net_pnl": -40.6},
    {"entry_time": "2025.03.19 11:45:00", "net_pnl": 107.2},
    {"entry_time": "2025.04.09 02:30:00", "net_pnl": 158.8},
    {"entry_time": "2025.05.20 05:00:00", "net_pnl": -77.6},
    {"entry_time": "2025.06.10 04:15:00", "net_pnl": 168.3},
    {"entry_time": "2025.09.04 01:15:01", "net_pnl": -39.5},
    {"entry_time": "2026.01.07 04:00:00", "net_pnl": 259.7},
    {"entry_time": "2026.03.30 04:00:00", "net_pnl": -244.7},
    {"entry_time": "2026.07.24 11:00:00", "net_pnl": -86.3},
    {"entry_time": "2026.08.17 15:45:00", "net_pnl": 284.7}
]

print(json.dumps(compute_temporal_concentration(events)))

events = [{"entry_time": "2024.04.08 17:15:00", "net_pnl": 97.0}, {"entry_time": "2024.05.15 17:00:00", "net_pnl": -49.4}, {"entry_time": "2024.10.02 18:00:00", "net_pnl": -40.2}, {"entry_time": "2024.12.12 16:15:00", "net_pnl": -40.6}, {"entry_time": "2025.03.19 11:45:00", "net_pnl": 107.2}, {"entry_time": "2025.04.09 02:30:00", "net_pnl": 158.8}, {"entry_time": "2025.05.20 05:00:00", "net_pnl": -77.6}, {"entry_time": "2025.06.10 04:15:00", "net_pnl": 168.3}, {"entry_time": "2025.09.04 01:15:01", "net_pnl": -39.5}, {"entry_time": "2026.01.07 04:00:00", "net_pnl": 259.7}, {"entry_time": "2026.03.30 04:00:00", "net_pnl": -244.7}, {"entry_time": "2026.07.24 11:00:00", "net_pnl": -86.3}, {"entry_time": "2026.08.17 15:45:00", "net_pnl": 284.7}]
print(json.dumps(compute_temporal_concentration(events)))
