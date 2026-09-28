import json
from datetime import datetime
from collections import defaultdict

def _dt(s):
    return datetime.strptime(s, '%Y.%m.%d %H:%M:%S')

#!/usr/bin/env python3
"""Funzione che calcola i dati per ogni anno basandosi sulle transazioni con profitto"""
import os
import sys
from collections import defaultdict

PHASE725_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE725_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE725_DIR)
from nxs_liq_sweep_edge_dataset_loader import (  # noqa: E402
    load_closed_events, net_pnl, split_by_direction, entry_time, _dt)


def compute_temporal_concentration(events):
    by_year = defaultdict(list)
    for e in events:
        by_year[_dt(e['entry_time']).year].append(e)

    per_year = {str(y): {"n_trades": len(v), "net_pnl_sum": sum(v),
                         "win_rate": sum(1 for p in v if p['net_pnl'] > 0) / len(v)}
                for y, v in sorted(by_year.items())}
    years_positive = sum(1 for v in per_year.values() if v["net_pnl_sum"] > 0)

    years_with_positive_net = years_positive
    years_total_with_at_least_1_trade = sum(1 for v in per_year.values() if v["n_trades"] > 0)

    return {
        'years_with_positive_net': years_with_positive_net,
        'years_total_with_at_least_1_trade': years_total_with_at_least_1_trade,
        'years_data': per_year
    }

events = [{"entry_time": "2019.06.05 17:30:00", "net_pnl": -16.06}, {"entry_time": "2019.06.21 05:30:00", "net_pnl": -16.76}, {"entry_time": "2019.08.07 17:00:00", "net_pnl": -26.66}, {"entry_time": "2020.01.06 01:45:00", "net_pnl": -11.75}, {"entry_time": "2020.02.21 18:00:00", "net_pnl": -17.05}, {"entry_time": "2020.04.14 12:30:00", "net_pnl": -43.910000000000004}, {"entry_time": "2020.06.24 16:15:00", "net_pnl": 86.0}, {"entry_time": "2020.07.23 17:00:00", "net_pnl": 83.0}, {"entry_time": "2020.11.09 14:15:00", "net_pnl": -26.7}, {"entry_time": "2020.12.21 12:00:00", "net_pnl": -26.97}, {"entry_time": "2021.01.06 14:45:00", "net_pnl": -25.24}, {"entry_time": "2021.02.19 17:00:00", "net_pnl": -25.48}, {"entry_time": "2021.03.02 18:00:00", "net_pnl": -26.09}, {"entry_time": "2021.05.10 17:00:00", "net_pnl": -24.5}, {"entry_time": "2021.05.19 13:30:00", "net_pnl": -48.83}, {"entry_time": "2021.06.18 15:30:00", "net_pnl": -26.05}, {"entry_time": "2021.08.11 18:00:00", "net_pnl": -23.71}, {"entry_time": "2021.09.30 17:30:00", "net_pnl": -22.67}, {"entry_time": "2021.11.10 16:30:00", "net_pnl": -31.659999999999997}, {"entry_time": "2022.02.15 16:45:00", "net_pnl": 87.13999999999999}, {"entry_time": "2022.05.16 11:00:00", "net_pnl": -29.7}, {"entry_time": "2022.07.07 17:15:00", "net_pnl": -17.69}, {"entry_time": "2022.09.02 17:15:00", "net_pnl": -18.2}, {"entry_time": "2022.09.19 17:45:00", "net_pnl": -20.49}, {"entry_time": "2022.12.05 17:15:00", "net_pnl": 63.93000000000001}, {"entry_time": "2023.01.17 17:00:00", "net_pnl": -40.64}, {"entry_time": "2023.03.15 11:45:00", "net_pnl": 100.5}, {"entry_time": "2023.04.06 16:45:00", "net_pnl": -73.15}, {"entry_time": "2023.07.20 17:15:00", "net_pnl": -21.29}, {"entry_time": "2023.09.28 18:15:00", "net_pnl": -15.07}, {"entry_time": "2023.10.20 17:00:00", "net_pnl": -27.13}, {"entry_time": "2023.11.30 17:15:00", "net_pnl": 93.26}, {"entry_time": "2024.03.05 16:00:00", "net_pnl": 67.96}, {"entry_time": "2024.04.02 15:30:00", "net_pnl": 124.03999999999999}, {"entry_time": "2024.07.15 18:00:00", "net_pnl": -34.0}, {"entry_time": "2024.08.20 11:00:00", "net_pnl": -46.61}, {"entry_time": "2024.09.16 17:30:00", "net_pnl": -31.389999999999997}, {"entry_time": "2024.09.24 10:30:00", "net_pnl": 113.8}, {"entry_time": "2024.10.31 15:15:00", "net_pnl": -29.36}, {"entry_time": "2025.01.20 16:00:00", "net_pnl": 117.58999999999999}, {"entry_time": "2025.02.12 03:45:00", "net_pnl": -54.84}, {"entry_time": "2025.03.17 14:45:00", "net_pnl": 169.14999999999998}, {"entry_time": "2025.07.23 04:15:00", "net_pnl": -42.72}, {"entry_time": "2025.09.01 01:45:00", "net_pnl": 147.56}, {"entry_time": "2025.09.09 06:15:00", "net_pnl": 191.51999999999998}, {"entry_time": "2025.10.01 01:30:00", "net_pnl": 226.03}, {"entry_time": "2026.06.09 04:30:00", "net_pnl": -86.97999999999999}]
print(json.dumps(compute_temporal_concentration(events)))
