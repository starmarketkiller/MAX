"""NXLAB-AUDIT-ASIAN-LOOKAHEAD-001 V3 — due finding della seconda review
indipendente di Codex sul branch fix/asian-lookahead-causal-contract
(HEAD revisionato: 7608483af421b26f1f1a624ff1a59dc2ede8b4d0).

P0: _detect_cadence_seconds (V2) deduceva la cadenza con la moda delle
differenze sull'INTERO array passato - non causale: aggiungere barre
future poteva cambiare la moda e quindi asian_session_complete per un
giorno PASSATO (prefix invariance violata). Fix: cadenza dichiarata
esplicitamente dal chiamante (declared_cadence_seconds), mai dedotta.
Senza dichiarazione, la completezza resta sempre non verificabile.

P1: il parser raw (_parse_bar_utc_fields) e il wrapper (_session_amd_series,
che usava ancora _epoch_utc) avevano due logiche diverse per lo stesso
input - raw normalizzava gli offset, il wrapper andava in eccezione su un
timestamp timezone-aware. Inoltre "+24:00" e "+00:99" (non orari validi)
passavano la vecchia regex. Fix: _bar_epoch_utc() unifica la logica per
entrambi; range check espliciti su ore/minuti dell'offset.

Nessun dato reale, nessun backtest economico, nessun holdout.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import backtest  # noqa: E402

_H1 = 3600
_M15 = 900


def _c(time_str, o, h, l, c):
    return {"time": time_str, "open": o, "high": h, "low": l, "close": c}


def _hourly_asian_day(date, spike_hour=6, spike_high=120.0):
    candles = []
    for h in range(0, 7):
        hi = spike_high if h == spike_hour else (101.0 + h * 0.1)
        candles.append(_c(f"{date} {h:02d}:00", 100 + h * 0.1, hi, 99 + h * 0.1, 100.5 + h * 0.1))
    for h in range(7, 24):
        candles.append(_c(f"{date} {h:02d}:00", 110.0, 110.5, 109.5, 110.2))
    return candles


# --------------------------------------------------------- P0: prefix invariance ----

def test_prefix_invariance_future_bars_do_not_change_past_completeness():
    """Riproduzione ESATTA del finding di Codex: calcolare asian_session_complete
    per un giorno (day1), poi ricalcolarlo con PIU' barre future aggiunte
    (day2, day3...) - il risultato per day1 deve essere IDENTICO bit-a-bit,
    mai cambiare retroattivamente."""
    day1 = _hourly_asian_day("2026-05-04")
    prefix_only = list(day1)
    sess_prefix = backtest._session_amd_series_raw(prefix_only, declared_cadence_seconds=_H1)

    day2 = _hourly_asian_day("2026-05-05")
    day3 = _hourly_asian_day("2026-05-06")
    extended = day1 + day2 + day3
    sess_extended = backtest._session_amd_series_raw(extended, declared_cadence_seconds=_H1)

    for i in range(len(day1)):
        assert sess_prefix["asian_session_complete"][i] == sess_extended["asian_session_complete"][i], (
            f"PREFIX INVARIANCE VIOLATA alla barra {i} ({day1[i]['time']}): "
            f"aggiungere barre future ha cambiato asian_session_complete di un giorno passato"
        )
        assert sess_prefix["asian_hi"][i] == sess_extended["asian_hi"][i]
        assert sess_prefix["asian_lo"][i] == sess_extended["asian_lo"][i]
        assert sess_prefix["amd_phase"][i] == sess_extended["amd_phase"][i]


def test_prefix_invariance_even_with_irregular_future_cadence():
    """Stesso principio, ma le barre future hanno una spaziatura DIVERSA
    (M15) da quelle passate (H1) - con una cadenza dichiarata fissa (H1),
    il giorno passato non deve accorgersene in nessun modo."""
    day1 = _hourly_asian_day("2026-05-11")
    sess_before = backtest._session_amd_series_raw(list(day1), declared_cadence_seconds=_H1)

    future_m15 = [_c(f"2026-05-12 00:{m:02d}", 100, 101, 99, 100.5) for m in range(0, 60, 15)]
    extended = day1 + future_m15
    sess_after = backtest._session_amd_series_raw(extended, declared_cadence_seconds=_H1)

    for i in range(len(day1)):
        assert sess_before["asian_session_complete"][i] == sess_after["asian_session_complete"][i]
        assert sess_before["asian_hi"][i] == sess_after["asian_hi"][i]


# --------------------------------------------------------- P0: cadenza dichiarata ----

def test_cadence_not_declared_means_never_complete():
    """Senza declared_cadence_seconds, nessuna sessione - per quanto
    perfettamente completa nei dati - puo' essere dichiarata completa.
    Fail-closed esplicito, non un default indovinato."""
    candles = _hourly_asian_day("2026-05-13")
    sess = backtest._session_amd_series_raw(candles)  # nessuna cadenza dichiarata
    for i in range(len(candles)):
        assert sess["asian_session_complete"][i] is False
        assert sess["asian_hi"][i] is None


def test_subsampled_input_does_not_borrow_a_different_cadence():
    """Input 'sottocampionato': dati realmente a cadenza M30 (barre ogni 30
    min) ma la copertura ASIAN risultante NON coincide con l'ipotesi H1
    dichiarata - deve risultare INCOMPLETA (il contratto dichiarato e'
    quello che conta, mai una cadenza dedotta dalla spaziatura reale dei
    dati, che qui e' diversa da quella dichiarata)."""
    candles = []
    for h in range(0, 7):
        for m in (0, 30):
            candles.append(_c(f"2026-05-14 {h:02d}:{m:02d}", 100, 101, 99, 100.5))
    for h in range(7, 9):
        candles.append(_c(f"2026-05-14 {h:02d}:00", 110, 110.5, 109.5, 110.2))
    # Dichiariamo H1 (cadenza SBAGLIATA rispetto ai dati reali, che sono M30)
    sess = backtest._session_amd_series_raw(candles, declared_cadence_seconds=_H1)
    i_post = len(candles) - 1
    assert sess["asian_session_complete"][i_post] is False, (
        "un input M30 non deve risultare 'completo' sotto un'ipotesi H1 dichiarata erroneamente"
    )
    # Con la cadenza dichiarata CORRETTA (M30=1800s), la stessa serie e' completa
    sess_m30 = backtest._session_amd_series_raw(candles, declared_cadence_seconds=1800)
    assert sess_m30["asian_session_complete"][i_post] is True


def test_irregular_session_with_known_calendar_is_flagged_incomplete_not_crashed():
    """Sessione irregolare (gap attorno 'a una festivita'' simulata) CON
    cadenza nota e dichiarata - deve risultare incompleta, senza eccezioni,
    senza assumere che il gap sia 'legittimo' o 'illegittimo' (non lo
    classifichiamo, lo rileviamo soltanto)."""
    candles = [_c(f"2026-05-18 {h:02d}:00", 100, 101, 99, 100.5) for h in (0, 1, 2)]
    # 3,4 mancanti (es. festivita' simulata)
    candles += [_c(f"2026-05-18 {h:02d}:00", 100, 101, 99, 100.5) for h in (5, 6)]
    candles.append(_c("2026-05-18 07:00", 110, 110.5, 109.5, 110.2))
    sess = backtest._session_amd_series_raw(candles, declared_cadence_seconds=_H1)
    assert sess["asian_session_complete"][-1] is False
    assert sess["asian_hi"][-1] is None


# --------------------------------------------------------- P1: parser unico ----

def test_offset_24_00_rejected():
    r = backtest._parse_bar_utc_fields("2026-03-29 07:00+24:00")
    assert r == (None, None, None), "+24:00 non e' un orario valido - deve fallire chiuso"


def test_offset_00_99_rejected():
    r = backtest._parse_bar_utc_fields("2026-03-29 07:00+00:99")
    assert r == (None, None, None), "+00:99 non e' un orario valido - deve fallire chiuso"


def test_offset_boundary_values_accepted():
    """Confini VALIDI (23:59 e 00:00) devono continuare a funzionare - la
    validazione deve rifiutare solo cio' che e' davvero impossibile."""
    assert backtest._parse_bar_utc_fields("2026-03-29 07:00+23:59")[0] is not None
    assert backtest._parse_bar_utc_fields("2026-03-29 07:00+00:00")[0] is not None
    assert backtest._parse_bar_utc_fields("2026-03-29 07:00-23:59")[0] is not None


def test_wrapper_no_longer_crashes_on_timezone_aware_timestamp_codex_repro():
    """Riproduzione ESATTA del finding di Codex: il wrapper
    _session_amd_series andava in eccezione su '2026-03-02 00:00+00:00'
    (via _epoch_utc, parser rigido) anche se la funzione raw gestiva gia'
    l'offset correttamente."""
    intraday = [_c(f"2026-03-02 {h:02d}:{m:02d}+00:00", 100, 101, 99, 100.5)
                for h in range(24) for m in (0, 15, 30, 45)]
    outer = [_c("2026-03-02 00:00+00:00", 100, 101, 99, 100.5),
             _c("2026-03-02 08:00+00:00", 110, 110.5, 109.5, 110.2)]
    # Non deve lanciare eccezioni (prima del fix: ValueError da _epoch_utc/strptime)
    sess = backtest._session_amd_series(outer, intraday_ref=intraday, declared_cadence_seconds=_M15)
    assert sess is not None


def test_raw_and_wrapper_agree_on_same_input():
    """raw e wrapper devono dare lo stesso esito sullo stesso input (quando
    intraday_ref e' assente o coincide con candles, il wrapper DELEGA
    interamente alla raw - stessa logica, non una duplicata)."""
    candles = _hourly_asian_day("2026-05-20")
    sess_raw = backtest._session_amd_series_raw(candles, declared_cadence_seconds=_H1)
    sess_wrap_none = backtest._session_amd_series(candles, intraday_ref=None, declared_cadence_seconds=_H1)
    sess_wrap_same = backtest._session_amd_series(candles, intraday_ref=candles, declared_cadence_seconds=_H1)
    for key in ("asian_hi", "asian_lo", "asian_session_complete", "session", "date", "hour"):
        assert sess_raw[key] == sess_wrap_none[key] == sess_wrap_same[key], f"divergenza su {key}"


def test_raw_and_wrapper_agree_with_real_intraday_projection():
    """Con una vera proiezione intraday->esterno (il percorso di produzione
    reale), il wrapper deve produrre valori coerenti con cio' che la raw
    calcola sulla serie intraday stessa - stessa logica di parsing, stessa
    regola di completezza, solo progettata su un indice diverso."""
    intraday = _hourly_asian_day("2026-05-21")
    sess_raw_fine = backtest._session_amd_series_raw(intraday, declared_cadence_seconds=_H1)
    outer = [intraday[0], intraday[4], intraday[8], intraday[12], intraday[16], intraday[20]]
    sess_wrap = backtest._session_amd_series(outer, intraday_ref=intraday, declared_cadence_seconds=_H1)
    # outer[2] = ora 08:00 (indice intraday 8, post-sessione) - stesso esito della raw a quell'indice
    assert sess_wrap["asian_session_complete"][2] == sess_raw_fine["asian_session_complete"][8]
    assert sess_wrap["asian_hi"][2] == sess_raw_fine["asian_hi"][8]


# --------------------------------------------------------- non-regressione ----

def test_no_regression_nine_confirmed_consumers_with_declared_cadence():
    """Le 9 identita' CONFIRMED continuano a degradare correttamente a
    'nessun segnale' durante la sessione, ora con cadenza dichiarata
    esplicitamente (non piu' dedotta) - stesso esito di V1/V2."""
    candles = _hourly_asian_day("2026-05-22")
    sess = backtest._session_amd_series_raw(candles, declared_cadence_seconds=_H1)
    atr = [0.3] * len(candles)
    ind = {"sess": sess, "atr": atr,
           "choch_int": ([0] * len(candles), [True] * len(candles), [True] * len(candles)),
           "weekly_pwh": None, "weekly_pwl": None, "monthly_pmh": None, "monthly_pml": None}
    for i in range(0, 7):
        assert backtest.sig_po3(candles, ind, i) == 0
        assert backtest.sig_liq_sweep_ext(candles, ind, i) == 0
        assert backtest.sig_cisd_true(candles, ind, i) == 0


def test_no_regression_london_bo_judas_swing_ldn_reversal_with_declared_cadence():
    """LONDON_BO/JUDAS_SWING/LDN_REVERSAL su sessioni complete con cadenza
    DICHIARATA (non dedotta) devono continuare a funzionare esattamente
    come prima - nessuna eccezione, nessun cambio di comportamento sulle
    barre post-sessione."""
    import random
    random.seed(20261017)
    multi = []
    px = 100.0
    for day in range(1, 6):
        for h in range(24):
            o = px
            px += random.uniform(-0.3, 0.3)
            hi = max(o, px) + random.uniform(0, 0.15)
            lo = min(o, px) - random.uniform(0, 0.15)
            multi.append(_c(f"2026-06-{day:02d} {h:02d}:00", o, hi, lo, px))

    sess = backtest._session_amd_series_raw(multi, declared_cadence_seconds=_H1)
    atr = [0.3] * len(multi)
    ema200 = [None] * len(multi)
    choch_int = ([0] * len(multi), [False] * len(multi), [True] * len(multi))
    ind = {"sess": sess, "atr": atr, "ema200": ema200, "choch_int": choch_int,
           "weekly_pwh": None, "weekly_pwl": None, "monthly_pmh": None, "monthly_pml": None}
    checked = 0
    for i in range(20, len(multi)):
        if sess["session"][i] == "ASIAN":
            continue
        assert sess["asian_session_complete"][i] is True, (
            f"falso negativo con cadenza dichiarata corretta alla barra {i}"
        )
        checked += 1
        for fn in (backtest.sig_london_bo, backtest.sig_judas_swing, backtest.sig_ldn_reversal):
            fn(multi, ind, i)
    assert checked > 50
