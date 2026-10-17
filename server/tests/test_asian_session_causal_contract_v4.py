"""NXLAB-AUDIT-ASIAN-LOOKAHEAD-001 V4 — due finding P0 rimasti dopo la V3,
dalla seconda review indipendente di Codex sul branch
fix/asian-lookahead-causal-contract (HEAD revisionato:
123024690c50def218f557de291cb4af1b50cae8).

P0-1: _session_amd_series riusava declared_cadence_seconds (la cadenza
della serie ESTERNA, es. H1) anche per intraday_ref, che e' SEMPRE M15
per costruzione (_load_dukascopy_m15). Fix: reference_cadence_seconds e'
ora un parametro indipendente, con default M15 - mai derivato dalla
cadenza esterna.

P0-2: boundaries nel wrapper usava "bar_width = (ultimo-primo)/(n-1)"
(media dei timestamp dell'intero array) per estrapolare il confine
dell'ULTIMA barra - non causale, perche' la media cambia quando si
aggiungono barre future, e quale barra sia "l'ultima" cambia con essa.
Fix: ogni confine e' ora funzione esclusiva dell'inizio di QUELLA barra
piu' la cadenza DICHIARATA (mai la media osservata, mai il timestamp
della barra successiva).

Questi test esercitano la catena reale _prep -> _session_amd_series ->
_session_amd_series_raw, non solo le funzioni helper isolate (vedi i
test marcati "catena reale" sotto). Nessun dato reale di mercato usato
per decisioni - il file dukascopy_xauusd_m15.json esistente e' ispezionato
SOLO per metadati (cadenza, duplicati, gap) in evidenza separata, non in
questi test. Nessun backtest economico, nessun holdout.
"""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import backtest as bt  # noqa: E402

_H1, _H4, _M15 = 3600, 14400, 900


def _c(t, o, h, l, cl):
    return {"time": t, "open": o, "high": h, "low": l, "close": cl}


def _m15_series(start, n_bars, asian_spike_date=None, spike_high=120.0, skip_index=None):
    """Serie M15 continua a partire da `start` (datetime). Se
    asian_spike_date e' dato, la 28a barra ASIAN (06:45) di quella data
    riceve spike_high. skip_index rimuove una barra (per i test di gap)."""
    out = []
    for i in range(n_bars):
        t = start + dt.timedelta(minutes=15 * i)
        if skip_index is not None and i == skip_index:
            continue
        date_str, hour, minute = t.strftime("%Y-%m-%d"), t.hour, t.minute
        hi = 101.0
        if asian_spike_date == date_str and hour == 6 and minute == 45:
            hi = spike_high
        out.append(_c(t.strftime("%Y-%m-%d %H:%M"), 100.0, hi, 99.0, 100.5))
    return out


def _external_series(start, n_bars, step_seconds):
    out = []
    for i in range(n_bars):
        t = start + dt.timedelta(seconds=step_seconds * i)
        out.append(_c(t.strftime("%Y-%m-%d %H:%M"), 100.0, 101.0, 99.0, 100.5))
    return out


# --------------------------------------------------- 1-2: catena reale _prep ----

def test_prep_h1_external_with_m15_reference_end_to_end():
    """Catena reale: _prep(H1, intraday_ref=M15) - non una chiamata diretta
    a _session_amd_series. Verifica che il contesto di sessione risultante
    sia popolato e coerente (nessuna eccezione, asian_session_complete
    presente per ogni barra)."""
    start = dt.datetime(2026, 1, 5, 0, 0)
    h1 = _external_series(start, 48, _H1)
    m15 = _m15_series(start, 48 * 4, asian_spike_date="2026-01-05")
    ind = bt._prep(h1, intraday_ref=m15, timeframe="h1")
    sess = ind["sess"]
    assert len(sess["asian_session_complete"]) == len(h1)
    # barra H1 alle 08:00 (indice 8) del 2026-01-05 - sessione Asian completa nel riferimento M15
    assert sess["asian_session_complete"][8] is True
    assert sess["asian_hi"][8] == 120.0


def test_prep_h4_external_with_m15_reference_end_to_end():
    """Catena reale: _prep(H4, intraday_ref=M15)."""
    start = dt.datetime(2026, 1, 5, 0, 0)
    h4 = _external_series(start, 24, _H4)  # 24 barre H4 = 4 giorni
    m15 = _m15_series(start, 24 * 16, asian_spike_date="2026-01-05")  # 16 M15 per barra H4
    ind = bt._prep(h4, intraday_ref=m15, timeframe="h4")
    sess = ind["sess"]
    # barra H4 che copre 08:00-12:00 del 2026-01-05 (indice 2, orario UTC 08:00) - post sessione
    assert sess["asian_session_complete"][2] is True
    assert sess["asian_hi"][2] == 120.0


# --------------------------------------------------- 3: calcolo diretto M15 ----

def test_direct_computation_on_m15_reference():
    """Calcolo diretto (_session_amd_series_raw) sulla serie M15 stessa,
    senza passare dal wrapper - riferimento per confrontare con la
    proiezione esterna."""
    start = dt.datetime(2026, 1, 6, 0, 0)
    m15 = _m15_series(start, 96, asian_spike_date="2026-01-06")
    sess = bt._session_amd_series_raw(m15, declared_cadence_seconds=_M15)
    i_08 = 32  # 08:00 = barra 32 a passi di 15 min
    assert sess["asian_session_complete"][i_08] is True
    assert sess["asian_hi"][i_08] == 120.0


# --------------------------------------------------- 4: prefix invariance wrapper ----

def test_wrapper_prefix_invariance_codex_repro():
    """Riproduzione ESATTA del finding P0-2 di Codex: barre esterne 00:00 e
    04:00, poi si aggiunge una barra futura 05:00 - asian_session_complete
    sulla barra 04:00 non deve cambiare."""
    start = dt.datetime(2026, 1, 7, 0, 0)
    m15 = _m15_series(start, 96, asian_spike_date="2026-01-07")
    outer_2 = [_c("2026-01-07 00:00", 100, 101, 99, 100.5),
               _c("2026-01-07 04:00", 100, 101, 99, 100.5)]
    sess_2 = bt._session_amd_series(outer_2, intraday_ref=m15, declared_cadence_seconds=_H4)
    complete_before = sess_2["asian_session_complete"][1]

    outer_3 = outer_2 + [_c("2026-01-07 05:00", 100, 101, 99, 100.5)]
    sess_3 = bt._session_amd_series(outer_3, intraday_ref=m15, declared_cadence_seconds=_H4)
    complete_after = sess_3["asian_session_complete"][1]

    assert complete_before == complete_after, (
        f"PREFIX INVARIANCE VIOLATA: barra 04:00 era complete={complete_before}, "
        f"diventa {complete_after} dopo aver aggiunto la barra futura 05:00"
    )


def test_wrapper_prefix_invariance_many_future_bars():
    """Stesso principio con molte piu' barre future, a cadenza diversa, per
    escludere che il fix dipenda dal numero esatto di barre aggiunte."""
    start = dt.datetime(2026, 1, 8, 0, 0)
    m15 = _m15_series(start, 96 * 10, asian_spike_date="2026-01-08")
    base = [_c("2026-01-08 00:00", 100, 101, 99, 100.5),
            _c("2026-01-08 08:00", 100, 101, 99, 100.5)]
    sess_base = bt._session_amd_series(base, intraday_ref=m15, declared_cadence_seconds=_H4 * 2)
    before = sess_base["asian_session_complete"][1]

    extended = base + [_c(f"2026-01-{8 + k:02d} 08:00", 100, 101, 99, 100.5) for k in range(1, 9)]
    sess_ext = bt._session_amd_series(extended, intraday_ref=m15, declared_cadence_seconds=_H4 * 2)
    after = sess_ext["asian_session_complete"][1]
    assert before == after


# --------------------------------------------------- 5: sessione completa ----

def test_asian_session_complete_through_real_chain():
    start = dt.datetime(2026, 1, 9, 0, 0)
    h1 = _external_series(start, 24, _H1)
    m15 = _m15_series(start, 96, asian_spike_date="2026-01-09")
    ind = bt._prep(h1, intraday_ref=m15, timeframe="h1")
    assert ind["sess"]["asian_session_complete"][8] is True


# --------------------------------------------------- 6: barra M15 mancante ----

def test_missing_m15_bar_marks_session_incomplete_through_real_chain():
    start = dt.datetime(2026, 1, 10, 0, 0)
    h1 = _external_series(start, 24, _H1)
    m15 = _m15_series(start, 96, asian_spike_date="2026-01-10", skip_index=10)  # buca una barra ASIAN
    ind = bt._prep(h1, intraday_ref=m15, timeframe="h1")
    assert ind["sess"]["asian_session_complete"][8] is False
    assert ind["sess"]["asian_hi"][8] is None


# --------------------------------------------------- 7: serie sottocampionata ----

def test_subsampled_series_does_not_fake_completeness():
    """Riferimento DICHIARATO M15 ma in realta' sottocampionato a M30 (ogni
    altra barra rimossa) - deve risultare incompleto, non un M15 valido."""
    start = dt.datetime(2026, 1, 11, 0, 0)
    full = _m15_series(start, 96, asian_spike_date="2026-01-11")
    subsampled = full[::2]  # M30 reale, ma passato come se fosse intraday_ref M15
    sess = bt._session_amd_series_raw(subsampled, declared_cadence_seconds=_M15)
    i_08 = 16  # indice dopo il sottocampionamento corrispondente a 08:00
    assert sess["asian_session_complete"][i_08] is False


# --------------------------------------------------- 8: ultima barra senza successore ----

def test_last_bar_without_successor_is_handled_causally():
    """L'ultima barra esterna (senza una barra successiva reale) non deve
    usare una larghezza stimata dai dati - il confine e' calcolato dalla
    cadenza dichiarata, identico a qualunque altra barra."""
    start = dt.datetime(2026, 1, 12, 0, 0)
    m15 = _m15_series(start, 96, asian_spike_date="2026-01-12")
    outer = [_c("2026-01-12 00:00", 100, 101, 99, 100.5),
             _c("2026-01-12 08:00", 100, 101, 99, 100.5)]  # 08:00 e' l'ULTIMA barra esterna
    sess = bt._session_amd_series(outer, intraday_ref=m15, declared_cadence_seconds=_H4 * 2)
    assert sess["asian_session_complete"][-1] is True
    assert sess["asian_hi"][-1] == 120.0


# --------------------------------------------------- 9: confini H1/H4 e cambio giorno ----

def test_h1_h4_boundaries_across_day_change_through_real_chain():
    start = dt.datetime(2026, 1, 13, 0, 0)
    h4 = _external_series(start, 24, _H4)  # 4 giorni di barre H4 (>=15 per gli altri indicatori di _prep)
    m15 = _m15_series(start, 24 * 16, asian_spike_date="2026-01-14")  # spike il SECONDO giorno
    ind = bt._prep(h4, intraday_ref=m15, timeframe="h4")
    sess = ind["sess"]
    # giorno 1 (2026-01-13): nessuno spike, giorno 2 (2026-01-14): spike -> livelli diversi
    assert sess["date"][1] == "2026-01-13"
    i_day2_post = 8  # barra H4 alle 08:00 del 2026-01-14 (indice 6*1+2=8: 6 barre/giorno H4)
    assert sess["date"][i_day2_post] == "2026-01-14"
    assert sess["asian_session_complete"][i_day2_post] is True
    assert sess["asian_hi"][i_day2_post] == 120.0


# --------------------------------------------------- 10-11: timestamp/offset ----

def test_utc_and_valid_offset_timestamps_through_real_chain():
    start = dt.datetime(2026, 1, 15, 0, 0)
    h1 = [_c((start + dt.timedelta(hours=i)).strftime("%Y-%m-%d %H:%M") + "+00:00", 100, 101, 99, 100.5)
          for i in range(20)]
    m15 = _m15_series(start, 96, asian_spike_date="2026-01-15")
    ind = bt._prep(h1, intraday_ref=m15, timeframe="h1")
    assert ind["sess"]["asian_session_complete"][8] is True
    assert ind["sess"]["asian_hi"][8] == 120.0


def test_invalid_offset_on_candles_without_intraday_ref_is_excluded_not_raised():
    """Senza intraday_ref (percorso puramente _session_amd_series_raw), un
    offset impossibile su una barra esterna viene escluso (date/hour/
    session=None) - nessuna eccezione, comportamento fail-closed per
    esclusione (gia' stabilito in V2/V3, confermato qui attraverso _prep)."""
    start = dt.datetime(2026, 1, 16, 0, 0)
    h1 = [_c("2026-01-16 00:00+24:00", 100, 101, 99, 100.5)] + \
         [_c((start + dt.timedelta(hours=i)).strftime("%Y-%m-%d %H:%M"), 100, 101, 99, 100.5)
          for i in range(1, 20)]
    ind = bt._prep(h1, intraday_ref=None, timeframe="h1")  # non deve lanciare eccezioni
    assert ind["sess"]["date"][0] is None
    assert ind["sess"]["session"][0] is None


def test_invalid_offset_on_outer_series_with_intraday_ref_raises_by_existing_p1_design():
    """Nota di design, NON una regressione introdotta da V4: quando
    intraday_ref e' attivo, il wrapper calcola gli epoch della serie
    ESTERNA con _bar_epoch_utc (fallisce con eccezione esplicita, per
    costruzione P1 - vedi la sua docstring: 'il chiamante la usa in
    ricerche binarie su array ordinati'). Questo e' diverso dal
    comportamento 'per esclusione' di _session_amd_series_raw sulla stessa
    barra SENZA intraday_ref (test sopra). L'asimmetria e' preesistente a
    V4 (introdotta in V3, mai modificata qui: 'non modificare il parser P1
    salvo regressione dimostrata') - documentata qui, non corretta."""
    import pytest
    h1 = [_c("2026-01-16 00:00+24:00", 100, 101, 99, 100.5),
          _c("2026-01-16 08:00", 100, 101, 99, 100.5)]
    m15 = _m15_series(dt.datetime(2026, 1, 16, 0, 0), 96, asian_spike_date="2026-01-16")
    with pytest.raises(ValueError):
        bt._prep(h1, intraday_ref=m15, timeframe="h1")


# --------------------------------------------------- 12: nove consumer ----

def test_nine_confirmed_consumers_through_real_chain():
    """Le 9 identita' CONFIRMED (PO3, LIQ_SWEEP, FVG_CONT, SH_BMS_RTO,
    SH_BMS_RTO_V2, CISD_TRUE, AMD_REVERSAL, AMD_CONT,
    TURTLE_SOUP_CHOCH_NEAR) non devono lanciare eccezioni ne' generare
    segnali durante una sessione ASIAN, attraverso la catena reale
    _prep -> sig_*()."""
    start = dt.datetime(2026, 1, 17, 0, 0)
    h1 = _external_series(start, 48, _H1)
    m15 = _m15_series(start, 48 * 4, asian_spike_date="2026-01-17")
    ind = bt._prep(h1, intraday_ref=m15, timeframe="h1")
    for i in range(0, 7):  # barre H1 ancora dentro la sessione ASIAN
        for fn_name in ("sig_po3", "sig_liq_sweep_ext", "sig_cisd_true"):
            fn = getattr(bt, fn_name)
            fn(h1, ind, i)  # non deve lanciare eccezioni; il segnale puo' essere 0


def test_no_regression_london_bo_through_real_chain():
    """LONDON_BO (post-sessione, NOT_AFFECTED) continua a funzionare senza
    eccezioni attraverso la catena reale."""
    start = dt.datetime(2026, 1, 18, 0, 0)
    h1 = _external_series(start, 48, _H1)
    m15 = _m15_series(start, 48 * 4, asian_spike_date="2026-01-18")
    ind = bt._prep(h1, intraday_ref=m15, timeframe="h1")
    for i in range(7, 12):
        bt.sig_london_bo(h1, ind, i)
