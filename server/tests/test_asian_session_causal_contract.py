"""NXLAB-AUDIT-ASIAN-LOOKAHEAD-001 — contratto causale su asian_hi/asian_lo.

_session_amd_series_raw calcolava asian_hi/asian_lo come valore FINALE della
sessione ASIAN (scansione sull'intero array) e lo assegnava anche alle barre
ancora dentro la sessione stessa - lookahead. Il fix impone che il livello
sia disponibile solo a sessione conclusa (asian_session_complete=True),
fedele a NXS_GetAMD (NXS_AMDModel.mqh: "if(asianEnd > TimeCurrent())
return r;"). Nessun dato reale in questo file: solo candele sintetiche.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import backtest  # noqa: E402

# V3 (P0): la cadenza non e' piu' dedotta dai dati - va dichiarata. Tutte le
# fixture di questo file sono orarie per costruzione (lo sa chi le scrive),
# non un'inferenza: e' esattamente il contratto point-in-time richiesto.
_H1 = 3600


def _c(time_str, o, h, l, c):
    return {"time": time_str, "open": o, "high": h, "low": l, "close": c}


def _synthetic_asian_spike_day(date="2026-01-05"):
    """Sessione ASIAN (ore 00-06) con lo spike che fissa il vero massimo
    SOLO all'ultima barra (06:00) - una barra precedente della stessa
    sessione non puo' conoscerlo causalmente."""
    candles = [
        _c(f"{date} 00:00", 100.0, 100.5, 99.5, 100.2),
        _c(f"{date} 01:00", 100.2, 100.8, 99.8, 100.4),
        _c(f"{date} 02:00", 100.4, 101.0, 100.0, 100.6),
        _c(f"{date} 03:00", 100.6, 101.2, 100.1, 100.8),
        _c(f"{date} 04:00", 100.8, 101.3, 100.2, 101.0),
        _c(f"{date} 05:00", 101.0, 101.5, 100.3, 101.2),
        _c(f"{date} 06:00", 101.2, 120.0, 101.0, 110.0),  # spike, fine sessione
    ]
    for h in range(7, 24):
        candles.append(_c(f"{date} {h:02d}:00", 110.0, 110.5, 109.5, 110.2))
    return candles


def test_asian_hi_lo_none_during_session():
    """Nessuna barra ASIAN deve ricevere un livello (nemmeno parziale) finche'
    la sessione non e' conclusa."""
    candles = _synthetic_asian_spike_day()
    sess = backtest._session_amd_series_raw(candles, declared_cadence_seconds=_H1)
    for i in range(0, 7):  # ore 00:00..06:00 = tutte ASIAN
        assert sess["session"][i] == "ASIAN"
        assert sess["asian_hi"][i] is None, f"asian_hi[{i}] doveva essere None durante la sessione"
        assert sess["asian_lo"][i] is None
        assert sess["asian_session_complete"][i] is False


def test_asian_hi_lo_available_and_correct_after_close():
    """Alla prima barra LONDON, il livello completo e corretto deve apparire."""
    candles = _synthetic_asian_spike_day()
    sess = backtest._session_amd_series_raw(candles, declared_cadence_seconds=_H1)
    i_london = 7
    assert sess["session"][i_london] == "LONDON"
    assert sess["asian_session_complete"][i_london] is True
    true_hi = max(c["high"] for c in candles[0:7])
    true_lo = min(c["low"] for c in candles[0:7])
    assert sess["asian_hi"][i_london] == true_hi == 120.0
    assert sess["asian_lo"][i_london] == true_lo == 99.5


def test_lookahead_regression_guard():
    """Guard esplicito: se qualcuno reintroduce il broadcast pre-fix, questo
    test deve fallire. Il massimo causale raggiungibile a i=2 (solo barre
    0..2) e' 101.0; il motore non deve MAI restituire un valore superiore
    a quella barra."""
    candles = _synthetic_asian_spike_day()
    sess = backtest._session_amd_series_raw(candles, declared_cadence_seconds=_H1)
    causal_hi_at_2 = max(c["high"] for c in candles[0:3])
    assert causal_hi_at_2 == 101.0
    assert sess["asian_hi"][2] is None, (
        "LOOKAHEAD REINTRODOTTO: asian_hi[2] non e' None - la sessione "
        "ASIAN non e' ancora conclusa a questa barra."
    )


def test_amd_phase_no_classification_during_session_then_correct_after():
    """amd_phase non deve classificare nessuna fase finche' la sessione non
    e' conclusa, e deve recuperare la fase corretta (contro il livello VERO,
    non quello lookahead) non appena la sessione chiude."""
    candles = _synthetic_asian_spike_day()
    # barra 02:00 rompe il massimo causale-finora (101.0) ma non il vero
    # massimo di sessione (120.0, formato solo alle 06:00)
    candles[2] = _c(candles[2]["time"], 100.4, 101.0, 100.0, 101.5)
    sess = backtest._session_amd_series_raw(candles, declared_cadence_seconds=_H1)
    for i in range(0, 7):
        assert sess["amd_phase"][i] is None, f"amd_phase[{i}] doveva restare None durante la sessione"
    # close=101.5 < vero massimo sessione (120.0) -> ACCUMULATION, non
    # MANIPULATION (comportamento pre-fix errato: si veda Decision Card §2 Passo 3)
    assert sess["amd_phase"][7] == ("ACCUMULATION", 0)


def test_session_amd_series_wrapper_propagates_fix():
    """Il percorso di produzione reale (riga ~605, _session_amd_series con
    intraday_ref) deve propagare gli stessi None/flag, non solo la _raw."""
    candles = _synthetic_asian_spike_day()
    outer = [candles[0], candles[4], candles[8], candles[12], candles[16], candles[20]]
    sess = backtest._session_amd_series(outer, intraday_ref=candles, declared_cadence_seconds=_H1)
    # outer[0] = ora 00:00, si proietta su una barra intraday ancora ASIAN
    assert sess["asian_hi"][0] is None
    assert sess["asian_session_complete"][0] is False
    # outer[4] = ora 16:00, ben dopo la chiusura ASIAN del giorno
    assert sess["asian_session_complete"][4] is True
    assert sess["asian_hi"][4] == 120.0


def test_confirmed_strategies_degrade_gracefully_during_session():
    """Le identita' CONFIRMED (PO3, LIQ_SWEEP via sig_liq_sweep_ext, CISD_TRUE)
    non devono mai lanciare eccezioni quando asian_hi/lo sono None - devono
    restituire 0 (nessun segnale), non un segnale basato su un livello futuro."""
    candles = _synthetic_asian_spike_day()
    sess = backtest._session_amd_series_raw(candles, declared_cadence_seconds=_H1)
    atr = [0.3] * len(candles)
    ind = {"sess": sess, "atr": atr, "choch_int": ([0] * len(candles), [True] * len(candles), [True] * len(candles)),
           "weekly_pwh": None, "weekly_pwl": None, "monthly_pmh": None, "monthly_pml": None}
    for i in range(0, 7):  # tutte barre ASIAN, asian_hi/lo=None
        assert backtest.sig_po3(candles, ind, i) == 0
        assert backtest.sig_liq_sweep_ext(candles, ind, i) == 0
        assert backtest.sig_cisd_true(candles, ind, i) == 0


def test_no_regression_post_session_strategies():
    """LONDON_BO, JUDAS_SWING, LDN_REVERSAL (NOT_AFFECTED, gated a barre
    post-sessione) devono produrre segnali BIT-A-BIT identici fra la logica
    pre-fix (broadcast su tutta la sessione) e quella post-fix, su ogni
    barra non-ASIAN - il fix non deve toccare il loro comportamento."""
    random.seed(20261015)
    multi = []
    px = 100.0
    for day in range(1, 11):
        for h in range(24):
            o = px
            px += random.uniform(-0.3, 0.3)
            hi = max(o, px) + random.uniform(0, 0.15)
            lo = min(o, px) - random.uniform(0, 0.15)
            multi.append(_c(f"2026-02-{day:02d} {h:02d}:00", o, hi, lo, px))

    sess_fixed = backtest._session_amd_series_raw(multi, declared_cadence_seconds=_H1)

    # Replica minima della logica PRE-fix, SOLO per il confronto di
    # non-regressione - non reintrodotta nel motore.
    def _old_buggy_asian(candles):
        n = len(candles)
        hour, date = [None] * n, [None] * n
        for i, cd in enumerate(candles):
            d, hm = cd["time"].split(" ")
            date[i], hour[i] = d, int(hm.split(":")[0])

        def _sess(h):
            if h is None:
                return None
            if 0 <= h < 7:
                return "ASIAN"
            if 7 <= h < 12:
                return "LONDON"
            if 12 <= h < 15:
                return "OVERLAP"
            if 15 <= h < 20:
                return "NY"
            return "AFTERNY"

        session = [_sess(h) for h in hour]
        hi_by_date, lo_by_date = {}, {}
        for i in range(n):
            if session[i] == "ASIAN":
                d = date[i]
                hi_by_date[d] = max(hi_by_date.get(d, -1e18), candles[i]["high"])
                lo_by_date[d] = min(lo_by_date.get(d, 1e18), candles[i]["low"])
        asian_hi = [hi_by_date.get(date[i]) for i in range(n)]
        asian_lo = [lo_by_date.get(date[i]) for i in range(n)]
        return session, asian_hi, asian_lo

    session_old, asian_hi_old, asian_lo_old = _old_buggy_asian(multi)
    sess_old = dict(sess_fixed)
    sess_old["asian_hi"], sess_old["asian_lo"], sess_old["session"] = asian_hi_old, asian_lo_old, session_old

    atr = [0.3] * len(multi)
    ema200 = [None] * len(multi)
    choch_int = ([0] * len(multi), [False] * len(multi), [True] * len(multi))

    def make_ind(sess):
        return {"sess": sess, "atr": atr, "ema200": ema200, "choch_int": choch_int,
                "weekly_pwh": None, "weekly_pwl": None, "monthly_pmh": None, "monthly_pml": None}

    ind_fixed, ind_old = make_ind(sess_fixed), make_ind(sess_old)
    checked = 0
    for i in range(20, len(multi)):
        if sess_fixed["session"][i] == "ASIAN":
            continue
        checked += 1
        for fn in (backtest.sig_london_bo, backtest.sig_judas_swing, backtest.sig_ldn_reversal):
            assert fn(multi, ind_old, i) == fn(multi, ind_fixed, i), (
                f"regressione in {fn.__name__} alla barra {i} ({multi[i]['time']})"
            )
    assert checked > 100  # garanzia che il test ha davvero esercitato barre post-sessione
