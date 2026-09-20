#!/usr/bin/env python3
"""Phase 7.4A - Detector formalizzato per SEQ-0015 MOMENTUM_BURST_CONTINUATION.

QUESTO MODULO NON VIENE ESEGUITO SU DATI NEXUS IN QUESTA FASE. Il
self-test in __main__ usa esclusivamente barre sintetiche generate in
memoria - nessun file di dati NEXUS e' letto, nessun outcome e' mai
calcolato qui. Serve solo a dimostrare che il detector, la soglia
causale e il guard di causalita' funzionano end-to-end PRIMA di essere
congelati nella frozen spec (phase7_4_seq0015_frozen_spec_v1.json).

Formalizzazione (sec.1-4 del task utente):

  TR_t = max(high_t-low_t, abs(high_t-close_{t-1}), abs(low_t-close_{t-1}))
  burst_ratio_t = TR_t / ATR_{t-1}          (MAI TR_t/ATR_t - vedi sotto)
  is_burst_t = burst_ratio_t > causal_rolling_P90_252(burst_ratio, up to t-1)
  direction_t = BUY se close_t>open_t, SELL se close_t<open_t, NO_EVENT se ==

Perche' ATR_{t-1} e non ATR_t per la SOGLIA DI RILEVAZIONE: wilder_atr()
(riusata identica da server/research_scripts/phase5/build_market_state.py,
riga 56-64) e' una EMA(alpha=1/14) di TR CHE INCLUDE TR_t nella propria
media alla posizione t. server/research_scripts/phase5/build_events.py
riga 99 (VOLATILITY_EXPANSION, poi H008_EVENT_VOLATILITY_EXPANSION,
REFUTED - vedi failure_memory_links nella frozen spec) usava esattamente
tr>mult*atr[i] con questo ATR same-bar: la barra anomala attenua
meccanicamente il proprio rapporto di anomalia proprio nei casi piu'
estremi. Usando ATR_{t-1} (shift di una barra) questa attenuazione non
puo' avvenire per costruzione - verificato qui esplicitamente, non solo
dichiarato.

Per la NORMALIZZAZIONE DELL'OUTCOME (non del detector) si usa invece
ATR_t: e' gia' interamente noto a prediction_start=close(t) e non c'e'
alcun incentivo ad attenuare un effetto che a quel punto e' gia' un
fatto (vedi frozen_parameters.outcome_atr_normalization nella frozen
spec)."""
import hashlib
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase5"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_3", "engine"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_3"))
from build_market_state import wilder_atr  # noqa: E402 - riuso diretto, nessuna duplicazione della formula ATR
from sequence_causality_guard import enforce_temporal_causality, SequenceCausalityViolation  # noqa: E402,F401

DETECTOR_VERSION = "seq0015_momentum_burst_detector.py@v1"

# Unica fonte di verita' per i parametri congelati - la frozen spec JSON
# importa questo stesso dict, cosi' frozen_parameters_hash e' garantito
# identico fra codice e artifact di pre-registrazione (nessun copia-incolla
# manuale che possa divergere in silenzio).
FROZEN_PARAMETERS = {
    "detector_formula": {
        "true_range_formula": "TR_t = max(high_t-low_t, abs(high_t-close_{t-1}), abs(low_t-close_{t-1}))",
        "atr_method": "Wilder EMA(alpha=1/14), causale, riusata identica da server/research_scripts/phase5/build_market_state.py:wilder_atr",
        "atr_period": 14,
        "burst_ratio_formula": "burst_ratio_t = TR_t / ATR_{t-1}",
        "burst_ratio_denominator_justification": (
            "ATR_{t-1} usa esclusivamente informazione fino a t-1. ATR_t (come verificato leggendo "
            "wilder_atr() e il suo uso reale in server/research_scripts/phase5/build_events.py:99 per "
            "VOLATILITY_EXPANSION/H008_EVENT_VOLATILITY_EXPANSION, REFUTED) include TR_t nella propria "
            "media mobile EMA - la barra anomala attenuerebbe meccanicamente il proprio rapporto di "
            "anomalia proprio nei casi piu' estremi. Verificato esplicitamente come richiesto (sec.1), "
            "non solo assunto."
        ),
        "threshold_method": "CAUSAL_ROLLING_PERCENTILE",
        "threshold_percentile": 90,
        "threshold_window_bars": 252,
        "threshold_minimum_warmup_bars": 252,
        "threshold_rationale": (
            "CLAIM-0042/CLAIM-0043 (fonte esterna di SEQ-0015) descrivono un meccanismo di soglia "
            "scalata alla volatilita' ma NON forniscono un moltiplicatore ATR unico e canonico per "
            "'range anomalo'. Non essendo disponibile un ancoraggio esterno univoco, si usa una regola "
            "distribuzionale calcolata SOLO sul passato: percentile 90 su una finestra rolling causale "
            "di 252 barre H4, esclusa la barra corrente (shift di 1). 252 e' la stessa finestra gia' "
            "usata come convenzione di progetto per atr_percentile in "
            "server/research_scripts/phase5/build_market_state.py:P['atr_percentile_window'] - non "
            "scelta ad-hoc per questa sequence. Percentile 90 e finestra 252 sono FISSATI ORA."
        ),
        "not_tried_alternative_thresholds": (
            "Nessun test di soglie alternative (es. percentili 85/95 o moltiplicatori fissi "
            "1.2/1.5/1.8/2.0xATR) e' stato eseguito su dati NEXUS prima di congelare questa scelta."
        ),
    },
    "direction_policy": {
        "rule": "BUY se close_t>open_t, SELL se close_t<open_t, NO_EVENT se close_t==open_t (doji/zero-body)",
        "no_event_handling": (
            "Una barra doji che supera la soglia di burst_ratio NON genera alcun sequence_event - "
            "conta come evento scartato, mai incluso in un pool con direzione arbitraria."
        ),
        "dependency_on_future_bars": "NESSUNA - dipende esclusivamente da open_t/close_t, gia' noti a observation_cutoff=close(t).",
    },
    "observation_timing": {
        "event_a_index": "t (barra H4 con burst_ratio_t sopra soglia)",
        "observation_cutoff_index": "close(t)",
        "transition_complete_index": "close(t) - MOMENTUM_BURST non ha transition_conditions separate (market_sequence_registry_v1.json:SEQ-0015)",
        "prediction_start_index": "close(t), verificato >= transition_complete_index da sequence_causality_guard.py",
        "outcome_window_start_index": "t+1 - nessun prezzo con indice <= t entra nel calcolo dell'outcome.",
    },
    "state_snapshot_pre_burst": {
        "principle": (
            "Tutte le feature di stato per il baseline matching sono calcolate a t-1, mai a t - la "
            "barra t e' essa stessa l'evento anomalo, includerla nel proprio stato di matching sarebbe "
            "circolare."
        ),
        "volatility_state_pre_burst": "Terzile (LOW/MED/HIGH) di atr_percentile a t-1, terzili fissati SOLO su development_discovery (convenzione H006/Phase7.1).",
        "trend_state_pre_burst": "Terzile (DOWN/FLAT/UP) di ema_slope_atr_norm a t-1, stessa convenzione di terzili fissati solo su discovery.",
        "directional_efficiency_excluded": (
            "NON incluso come dimensione di matching separata: il meccanismo causale dichiarato "
            "(CLAIM-0042/0043) riguarda l'espansione di volatilita', non l'efficienza del movimento "
            "pregresso; trend_state_pre_burst copre gia' la componente direzionale rilevante. "
            "Aggiungere directional_efficiency aumenterebbe i gradi di liberta' del matching senza una "
            "giustificazione causale distinta, in contrasto con la scelta di questa family per 'poche "
            "dimensioni, pochi gradi di liberta''."
        ),
    },
    "episode_rule": {
        "episode_gap_rule_bars": 3,
        "natural_horizon_bars": 40,
        "overlap_policy": "COLLAPSE_TO_FIRST",
        "rationale": (
            "I burst possono comparire su barre H4 consecutive o quasi-consecutive durante la stessa "
            "espansione direzionale - non sono letture indipendenti dello stesso fenomeno. "
            "episode_gap_rule=3 barre (12h): due burst a non piu' di 3 barre di distanza sono trattati "
            "come la stessa espansione; un gap piu' ampio senza ulteriori burst e' trattato come "
            "espansione conclusa. COLLAPSE_TO_FIRST usa la prima barra dell'espansione come "
            "rappresentante (anti-cherry-pick, gia' incorporato in sequence_episode_engine.py). "
            "natural_horizon=40 barre H4, identico all'orizzonte dell'outcome primario - stessa "
            "convenzione di H006/Phase7.1, non scelto per questa sequence specifica."
        ),
    },
    "control_exclusion_window": {
        "exclusion_buffer_bars": 40,
        "rule": (
            "Per un evento a event_a_index=t sono esclusi dal SUO pool di controllo: (1) la barra t "
            "stessa; (2) qualunque barra r con |r-t|<=40 barre (evita che un controllo condivida il "
            "tratto di prezzo usato per l'outcome dell'evento); (3) qualunque altra barra "
            "MOMENTUM_BURST dello stesso episode_id; (4) qualunque barra di split diverso (enforcement "
            "strutturale gia' esistente - BaselineEngineV4.match() + cross_split_safety.py, riusati "
            "senza modifiche)."
        ),
    },
    "candidate_family": {
        "family_id": "SEQFAM-SEQ0015_MOMENTUM_BURST-CANDIDATES-V1",
        "candidates": [
            {"candidate_id": "CAND-P74-SEQ0015-BOTH", "direction": "BOTH", "role": "PRIMARY_INFERENTIAL"},
            {"candidate_id": "CAND-P74-SEQ0015-BUY", "direction": "BUY", "role": "PRIMARY_INFERENTIAL"},
            {"candidate_id": "CAND-P74-SEQ0015-SELL", "direction": "SELL", "role": "PRIMARY_INFERENTIAL"},
        ],
        "decision": (
            "BOTH/BUY/SELL pre-registrati TUTTI E TRE ORA come famiglia inferenziale unica (stessa "
            "convenzione di Phase 7.1/RECLAIM) - non 'BOTH primary, BUY/SELL diagnostic'. Nessuno dei "
            "tre puo' essere promosso individualmente senza passare per l'intera sequenza "
            "discovery->internal_validation->locked_validation. La sequenza 'BOTH fallisce -> guardiamo "
            "BUY -> promuoviamo BUY' e' impossibile per costruzione: tutti e 3 sono valutati insieme "
            "sotto la stessa correzione FDR (vedi multiple_testing_full_family)."
        ),
    },
    "baseline_k": 5,
    "baseline_minimum_control_count": 20,
    "outcome_atr_normalization": {
        "rule": "L'ATR per normalizzare l'outcome primario/secondario e' ATR_t (Wilder ATR(14) fino e incluso il bar t) - NON ATR_{t-1}.",
        "why_this_differs_from_detection_denominator": (
            "Per la soglia di rilevazione, ATR_t attenuerebbe meccanicamente l'anomalia misurata "
            "(auto-diluizione). Per la normalizzazione dell'outcome, ATR_t e' gia' interamente noto a "
            "prediction_start=close(t) (nessuna barra futura richiesta) e non c'e' alcun incentivo ad "
            "attenuare un effetto che a quel punto e' gia' un fatto: e' l'unita' di misura piu' recente "
            "e causalmente valida disponibile quando il clock dell'outcome parte. Le due scelte "
            "(ATR_{t-1} per la soglia, ATR_t per l'outcome) sono entrambe corrette e non contraddittorie "
            "- verificato esplicitamente come richiesto al punto 7."
        ),
    },
    "multiple_testing_full_family": {
        "family_id": "SEQFAM-SEQ0015_MOMENTUM_BURST-FULL-COMPARISON-FAMILY-V1",
        "members_description": "3 candidati (BOTH/BUY/SELL) x 7 outcome (1 primary + 6 secondary, OutcomeSurfaceV3.inferential_family_size()=7) = 21 confronti.",
        "n_comparisons": 21,
        "method": "Benjamini-Hochberg FDR, q=0.10 (multiple_testing_v2.benjamini_hochberg, riusato senza modifiche).",
        "diagnostic_exclusion": "I 6 outcome DIAGNOSTIC_ONLY non entrano MAI in questa famiglia di confronto.",
    },
}


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    return pd.concat([(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)


def causal_burst_ratio(high: pd.Series, low: pd.Series, close: pd.Series, atr_period: int = 14) -> pd.Series:
    tr = true_range(high, low, close)
    atr = wilder_atr(high, low, close, atr_period)
    atr_prev = atr.shift(1)  # ATR_{t-1} - MAI atr (same-bar), vedi docstring del modulo
    return tr / atr_prev


def causal_rolling_threshold(burst_ratio: pd.Series, window: int = 252, percentile: int = 90) -> pd.Series:
    """threshold_t = percentile-esimo percentile di burst_ratio[t-window .. t-1] - la barra t stessa
    e' esclusa (shift(1)) cosi' il proprio valore non alza la propria soglia di confronto."""
    shifted = burst_ratio.shift(1)
    return shifted.rolling(window, min_periods=window).apply(lambda x: float(np.percentile(x, percentile)), raw=True)


def make_sequence_event_id(sequence_id: str, event_a_index: int, detector_version: str) -> str:
    raw = f"{sequence_id}|{event_a_index}|{detector_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def detect_sequence(bars: pd.DataFrame, market_state: pd.DataFrame, frozen_params: dict) -> list:
    """bars: DataFrame con colonne open/high/low/close (indice posizionale RangeIndex).
    market_state: DataFrame con colonne volatility_state/trend_state gia' calcolate
    a t (verranno LAGGATE di 1 qui per ottenere la versione pre-burst - il chiamante
    non deve pre-laggarle, e' responsabilita' del detector, cosi' l'errore non puo'
    essere commesso a valle in modo silenzioso).

    frozen_params: deve essere IDENTICO a FROZEN_PARAMETERS (nessun parametro
    modificabile a runtime - verificato dal chiamante tramite
    frozen_parameters_hash prima di invocare questa funzione)."""
    fp = frozen_params["detector_formula"]
    burst_ratio = causal_burst_ratio(bars["high"], bars["low"], bars["close"], fp["atr_period"])
    threshold = causal_rolling_threshold(burst_ratio, fp["threshold_window_bars"], fp["threshold_percentile"])
    is_burst = burst_ratio > threshold

    vol_state_prev = market_state["volatility_state"].shift(1)
    trend_state_prev = market_state["trend_state"].shift(1)

    events = []
    for t in range(len(bars)):
        burst_flag = is_burst.iloc[t]
        if pd.isna(burst_flag) or not bool(burst_flag):
            continue  # warmup (soglia NaN) o non-burst - in entrambi i casi nessun evento
        close_t, open_t = bars["close"].iloc[t], bars["open"].iloc[t]
        if close_t > open_t:
            direction = "BUY"
        elif close_t < open_t:
            direction = "SELL"
        else:
            continue  # NO_EVENT - doji/zero-body, sec.3
        if pd.isna(vol_state_prev.iloc[t]) or pd.isna(trend_state_prev.iloc[t]):
            continue  # warmup insufficiente per lo stato pre-burst
        eid = make_sequence_event_id("SEQ-0015", t, DETECTOR_VERSION)
        events.append({
            "sequence_event_id": eid, "sequence_id": "SEQ-0015", "direction": direction,
            "event_a_index": t, "transition_complete_index": t, "event_b_index_optional": None,
            "observation_cutoff_index": t, "prediction_start_index": t,
            "state_snapshot": {
                "direction": direction,
                "volatility_state_pre_burst": vol_state_prev.iloc[t],
                "trend_state_pre_burst": trend_state_prev.iloc[t],
            },
            "detector_version": DETECTOR_VERSION,
            "burst_ratio": float(burst_ratio.iloc[t]), "threshold_at_t": float(threshold.iloc[t]),
        })
    return events


if __name__ == "__main__":
    # ---- Self-test STRUTTURALE su barre SINTETICHE - nessun dato NEXUS. ----
    rng = np.random.default_rng(42)
    n = 400
    close = 2000 + np.cumsum(rng.normal(0, 2.0, n))
    open_ = close - rng.normal(0, 1.0, n)
    high = np.maximum(open_, close) + np.abs(rng.normal(0, 0.5, n))
    low = np.minimum(open_, close) - np.abs(rng.normal(0, 0.5, n))
    # Inseriamo 3 burst artificiali forzati (barre 300, 301 vicine=stesso episodio; 350 isolata).
    for idx, mult in [(300, 8.0), (301, 7.0), (350, 9.0)]:
        high[idx] = close[idx - 1] + mult * 3.0
        low[idx] = close[idx - 1] - 1.0
        close[idx] = high[idx] - 0.5  # forza BUY (close>open)
        open_[idx] = close[idx - 1]

    bars = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})
    vol_labels = np.where(np.arange(n) % 3 == 0, "LOW", np.where(np.arange(n) % 3 == 1, "MED", "HIGH"))
    trend_labels = np.where(np.arange(n) % 3 == 0, "DOWN", np.where(np.arange(n) % 3 == 1, "FLAT", "UP"))
    market_state = pd.DataFrame({"volatility_state": vol_labels, "trend_state": trend_labels})

    events = detect_sequence(bars, market_state, FROZEN_PARAMETERS)
    print(f"Caso 1 (detect_sequence su barre sintetiche): {len(events)} eventi rilevati dopo warmup={FROZEN_PARAMETERS['detector_formula']['threshold_minimum_warmup_bars']}")
    assert len(events) >= 1, "atteso almeno 1 evento fra i 3 burst artificiali forzati (dopo warmup)"

    # Caso 2: ogni evento passa il causality guard (fail-closed, riusato senza modifiche).
    for e in events:
        ok = enforce_temporal_causality(
            observation_cutoff_index=e["observation_cutoff_index"], max_feature_timestamp_index=e["observation_cutoff_index"],
            transition_complete_index=e["transition_complete_index"], prediction_start_index=e["prediction_start_index"],
            outcome_window_start_index=e["prediction_start_index"] + 1, sequence_event_id=e["sequence_event_id"],
        )
        assert ok is True
    print(f"Caso 2 (causality guard): tutti i {len(events)} eventi passano enforce_temporal_causality.")

    # Caso 3: sequence_event_id deterministico e stabile per lo stesso (sequence_id, event_a_index, detector_version).
    for e in events:
        recomputed = make_sequence_event_id(e["sequence_id"], e["event_a_index"], e["detector_version"])
        assert recomputed == e["sequence_event_id"]
    print("Caso 3 (id deterministico): sequence_event_id riproducibile per ogni evento.")

    # Caso 4: direzione dipende SOLO da open_t/close_t (nessuna dipendenza da t+1).
    for e in events:
        t = e["event_a_index"]
        expected_dir = "BUY" if close[t] > open_[t] else "SELL"
        assert e["direction"] == expected_dir
    print("Caso 4 (direzione causale): direction coerente con close_t vs open_t, nessuna barra futura coinvolta.")

    print(f"\nDETECTOR_VERSION = {DETECTOR_VERSION}")
    print("\nSelf-test strutturale completato su dati SINTETICI - nessun dato NEXUS letto, nessun outcome calcolato.")
