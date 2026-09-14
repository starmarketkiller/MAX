"""
Causal Experiment 1 - analisi univariata + train/OOS + modello diagnostico
opzionale. Legge il dataset gia' costruito da
causal_experiment_1_wick_sweep_1r.py. Discovery, non ottimizzazione.
"""
import csv
import math
from collections import defaultdict, Counter

PATH = r"C:\Users\User\ClaudeWork\MAX\results\causal_experiment_1\wick_sweep_1r_dataset.csv"

with open(PATH, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

# escludi ambiguous/censored dall'analisi di esito (dichiarato, non imputato)
resolved = [r for r in rows if r["outcome"] in ("PLUS_1R_FIRST", "MINUS_1R_FIRST")]
resolved.sort(key=lambda r: r["timestamp"])
n_total = len(rows)
n_resolved = len(resolved)
print(f"Record totali: {n_total}, risolti: {n_resolved}, esclusi (ambiguous/censored): {n_total - n_resolved}")

base_hits = sum(1 for r in resolved if r["outcome"] == "PLUS_1R_FIRST")
base_rate = base_hits / n_resolved
print(f"\nBASE RATE incondizionato (+1R prima di -1R): {base_hits}/{n_resolved} = {base_rate:.3f}")


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((center - margin) / denom, (center + margin) / denom)


# --- split cronologico dichiarato PRIMA di guardare i risultati per-feature ---
# W1+W2 = train/discovery, W3 = OOS. Dichiarato nel report Phase E gia' come
# criterio di preferenza ("prime ~2/3 finestre -> train, ultima -> OOS").
train = [r for r in resolved if r["window_id"] in ("W1", "W2")]
oos = [r for r in resolved if r["window_id"] == "W3"]
print(f"\nTRAIN (W1+W2): n={len(train)}   OOS (W3): n={len(oos)}")
if len(oos) < 30:
    print("ATTENZIONE: OOS sotto la soglia minima di 30 campioni dichiarata nel report Phase E - "
          "qualunque confronto train/OOS su questo split va letto come indicativo, non conclusivo.")


def rate(subset):
    if not subset:
        return (0, 0, float("nan"))
    k = sum(1 for r in subset if r["outcome"] == "PLUS_1R_FIRST")
    return (k, len(subset), k / len(subset))


def report_bucket(name, subset_all, subset_train, subset_oos, base):
    k, n, p = rate(subset_all)
    kt, nt, pt = rate(subset_train)
    ko, no_, po = rate(subset_oos)
    lo, hi = wilson_ci(k, n) if n else (float("nan"), float("nan"))
    uplift = (p - base) if n else float("nan")
    same_dir = "n/a"
    if nt >= 5 and no_ >= 5 and not math.isnan(pt) and not math.isnan(po):
        dt = pt - base
        do_ = po - base
        same_dir = "SI" if (dt > 0) == (do_ > 0) else "NO"
    print(f"  {name:28s} n={n:4d} rate={p:.3f} uplift={uplift:+.3f} CI95=[{lo:.3f},{hi:.3f}]  "
          f"train(n={nt},rate={pt:.3f})  OOS(n={no_},rate={po:.3f})  stessa_direzione_train_oos={same_dir}")


def univariate(feature_name, bucket_fn, all_rows=resolved, base=base_rate):
    print(f"\n--- {feature_name} ---")
    buckets = defaultdict(list)
    for r in all_rows:
        buckets[bucket_fn(r)].append(r)
    for label in sorted(buckets.keys(), key=str):
        subset = buckets[label]
        subset_train = [r for r in subset if r["window_id"] in ("W1", "W2")]
        subset_oos = [r for r in subset if r["window_id"] == "W3"]
        report_bucket(str(label), subset, subset_train, subset_oos, base)


# direction
univariate("DIRECTION", lambda r: r["direction"])

# session
univariate("SESSION", lambda r: r["session_bucket"])

# day of week
univariate("DAY_OF_WEEK", lambda r: r["day_of_week"])

# hour (bucket semplice: notte/mattina/pomeriggio/sera)
def hour_bucket(r):
    h = int(r["hour"])
    if h < 6:
        return "00-06"
    if h < 12:
        return "06-12"
    if h < 18:
        return "12-18"
    return "18-24"
univariate("HOUR_BUCKET", hour_bucket)

# level age (mediana come soglia, dichiarata dopo aver visto la distribuzione,
# ma la SOGLIA e' l'unica cosa scelta sui dati - lo split binario stesso e'
# lo schema piu' semplice possibile, non un tuning di bucket multipli)
ages = sorted(float(r["level_age_seconds"]) for r in resolved if r["level_age_seconds"])
median_age = ages[len(ages) // 2]
print(f"\n(mediana level_age_seconds = {median_age:.0f}s = {median_age/3600:.1f}h, usata come soglia binaria sotto)")
def age_bucket(r):
    a = float(r["level_age_seconds"]) if r["level_age_seconds"] else 0
    return "YOUNG(<median)" if a < median_age else "OLD(>=median)"
univariate("LEVEL_AGE", age_bucket)

# touch count
tc_values = Counter(r["touch_count_before_sweep"] for r in resolved)
print(f"\n(distribuzione touch_count_before_sweep: {dict(tc_values)})")
univariate("TOUCH_COUNT", lambda r: f"touch={r['touch_count_before_sweep']}")

# penetration (mediana come soglia)
pens = sorted(float(r["penetration_pips"]) for r in resolved)
median_pen = pens[len(pens) // 2]
print(f"\n(mediana penetration_pips = {median_pen:.1f}, min={pens[0]:.1f}, max={pens[-1]:.1f})")
def pen_bucket(r):
    p = float(r["penetration_pips"])
    return "SHALLOW(<median)" if p < median_pen else "DEEP(>=median)"
univariate("PENETRATION", pen_bucket)

print("\n=== FINE ANALISI UNIVARIATA ===")
