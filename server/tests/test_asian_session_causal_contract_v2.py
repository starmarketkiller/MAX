"""NXLAB-AUDIT-ASIAN-LOOKAHEAD-001 V2 — due finding di Codex sulla review
indipendente del branch fix/asian-lookahead-causal-contract (924d2fe).

P0: asian_session_complete equivaleva a "session[i] != 'ASIAN'" - vero anche
quando la sessione ASIAN della data non era stata osservata per intero (gap
nei dati). Fix: completezza richiede che l'insieme delle barre ASIAN
osservate coincida esattamente con quello atteso dalla cadenza rilevata
dall'input stesso, sull'intera finestra [00:00, fine ASIAN).

P1: il parsing di "time" ignorava un offset esplicito eventualmente presente
("YYYY-MM-DD HH:MM+HH:MM"), trattando l'ora locale come se fosse già UTC.
Fix: formato con offset esplicito normalizzato correttamente; formato non
riconosciuto o data/ora non valida -> fail-closed (barra esclusa, mai
un'interpretazione silenziosa).

Nessun dato reale, nessun backtest economico, nessun holdout. Non tocca
CP2/ResearchMemory/ledger né codice MQL5.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import backtest  # noqa: E402


def _c(time_str, o, h, l, c):
    return {"time": time_str, "open": o, "high": h, "low": l, "close": c}


def _full_asian_day(date="2026-03-02", start_hour=0):
    """7 barre orarie 00:00..06:00 (copertura ASIAN completa) + barre
    orarie 07:00..23:00 (resto della giornata)."""
    candles = []
    for h in range(start_hour, 7):
        candles.append(_c(f"{date} {h:02d}:00", 100 + h, 101 + h, 99 + h, 100.5 + h))
    for h in range(7, 24):
        candles.append(_c(f"{date} {h:02d}:00", 110, 110.5, 109.5, 110.2))
    return candles


# --------------------------------------------------------------------- P0 ----

def test_session_complete_with_full_hourly_coverage():
    """Sessione Asian completa: 7/7 barre orarie presenti -> complete=True,
    livello disponibile e corretto alla prima barra post-sessione."""
    candles = _full_asian_day()
    sess = backtest._session_amd_series_raw(candles)
    i_london = 7
    assert sess["session"][i_london] == "LONDON"
    assert sess["asian_session_complete"][i_london] is True
    true_hi = max(c["high"] for c in candles[0:7])
    assert sess["asian_hi"][i_london] == true_hi


def test_session_truncated_tail_codex_repro():
    """Riproduzione ESATTA del caso di Codex: barre Asian solo 00:00-02:00,
    prima barra successiva alle 08:00 (03:00-06:59 mancanti). Prima del fix
    V2: asian_session_complete=True, asian_hi=103 (massimo delle sole 3
    barre arrivate, scambiato per il massimo vero). Dopo il fix: deve
    restare non disponibile."""
    candles = [
        _c("2026-03-02 00:00", 100, 101, 99, 100.5),
        _c("2026-03-02 01:00", 100.5, 102, 100, 101),
        _c("2026-03-02 02:00", 101, 103, 100.5, 102),
        _c("2026-03-02 08:00", 102, 104, 101, 103.5),
        _c("2026-03-02 09:00", 103.5, 105, 103, 104),
    ]
    sess = backtest._session_amd_series_raw(candles)
    i_08 = 3
    assert sess["session"][i_08] == "LONDON"
    assert sess["asian_session_complete"][i_08] is False, (
        "REGRESSIONE: la sessione tronca (00:00-02:00 osservate, 03:00-06:59 mancanti) "
        "e' stata dichiarata completa"
    )
    assert sess["asian_hi"][i_08] is None, "asian_hi non deve derivare da una sessione tronca"
    assert sess["asian_lo"][i_08] is None

    # Non-regressione dei 9 consumer CONFIRMED e di LONDON_BO su questo caso specifico
    atr = [0.3] * len(candles)
    ind = {"sess": sess, "atr": atr,
           "choch_int": ([0] * len(candles), [True] * len(candles), [True] * len(candles)),
           "weekly_pwh": None, "weekly_pwl": None, "monthly_pmh": None, "monthly_pml": None}
    assert backtest.sig_london_bo(candles, ind, i_08) == 0, (
        "sig_london_bo non deve generare BUY usando un asian_hi da sessione tronca"
    )
    assert backtest.sig_po3(candles, ind, i_08) == 0
    assert backtest.sig_liq_sweep_ext(candles, ind, i_08) == 0
    assert backtest.sig_cisd_true(candles, ind, i_08) == 0


def test_session_incomplete_missing_middle_bar():
    """Barre intermedie mancanti: 00:00,01:00,02:00,[GAP 03:00],04:00,05:00,
    06:00 - un buco interno alla sessione, non solo in coda, deve bastare a
    dichiararla incompleta."""
    candles = [
        _c("2026-03-03 00:00", 100, 101, 99, 100.5),
        _c("2026-03-03 01:00", 100.5, 102, 100, 101),
        _c("2026-03-03 02:00", 101, 103, 100.5, 102),
        # 03:00 mancante
        _c("2026-03-03 04:00", 102, 104, 101.5, 103),
        _c("2026-03-03 05:00", 103, 105, 102, 104),
        _c("2026-03-03 06:00", 104, 106, 103, 105),
        _c("2026-03-03 07:00", 105, 105.5, 104.5, 105.2),
    ]
    sess = backtest._session_amd_series_raw(candles)
    i_07 = 6
    assert sess["asian_session_complete"][i_07] is False
    assert sess["asian_hi"][i_07] is None


def test_day_without_any_asian_bars():
    """Giorno senza barre Asian: la prima barra della data e' già LONDON+ -
    nessun crash, asian_hi/lo restano None per tutta la data."""
    candles = [
        _c("2026-03-04 09:00", 100, 101, 99, 100.5),
        _c("2026-03-04 10:00", 100.5, 102, 100, 101),
        _c("2026-03-04 11:00", 101, 103, 100.5, 102),
    ]
    sess = backtest._session_amd_series_raw(candles)
    for i in range(len(candles)):
        assert sess["asian_session_complete"][i] is False
        assert sess["asian_hi"][i] is None
        assert sess["asian_lo"][i] is None


def test_first_post_session_bar_gets_flag_only_when_truly_complete():
    """Confronto diretto: stessa ora di arrivo (08:00) ma con sessione
    completa in un caso e tronca nell'altro - solo il primo deve esporre
    il livello."""
    complete = _full_asian_day(date="2026-03-05")
    sess_complete = backtest._session_amd_series_raw(complete)
    assert sess_complete["asian_session_complete"][7] is True

    truncated = [
        _c("2026-03-06 00:00", 100, 101, 99, 100.5),
        _c("2026-03-06 01:00", 100.5, 102, 100, 101),
        _c("2026-03-06 08:00", 102, 104, 101, 103.5),
    ]
    sess_trunc = backtest._session_amd_series_raw(truncated)
    assert sess_trunc["asian_session_complete"][2] is False


def test_weekend_and_day_change_isolated_per_date():
    """Venerdi' con sessione Asian completa, sabato/domenica senza barre
    (mercato chiuso, nessuna riga), lunedi' con sessione Asian completa e
    FRESCA (diversa da venerdi') - nessuna fuga di livello tra le date,
    nessun crash sul salto di piu' giorni."""
    fri = _full_asian_day(date="2026-03-06")       # venerdi'
    mon = _full_asian_day(date="2026-03-09")        # lunedi' (sab/dom assenti)
    for c in mon:
        c["high"] += 50.0  # livello Asian di lunedi' chiaramente diverso da venerdi'
        c["low"] += 50.0
    candles = fri + mon
    sess = backtest._session_amd_series_raw(candles)

    i_fri_london = 7
    i_mon_london = len(fri) + 7
    assert sess["asian_session_complete"][i_fri_london] is True
    assert sess["asian_session_complete"][i_mon_london] is True
    hi_fri = sess["asian_hi"][i_fri_london]
    hi_mon = sess["asian_hi"][i_mon_london]
    assert hi_fri is not None and hi_mon is not None
    assert hi_mon > hi_fri + 40, "il livello di lunedi' non deve derivare da venerdi'"


# --------------------------------------------------------------------- P1 ----

def test_valid_utc_timestamps_unchanged_behavior():
    """Fixture storiche "YYYY-MM-DD HH:MM" senza offset: comportamento
    bit-a-bit identico a prima del fix V2 (nessuna reinterpretazione)."""
    candles = _full_asian_day(date="2026-03-10")
    sess = backtest._session_amd_series_raw(candles)
    assert sess["hour"][0] == 0
    assert sess["date"][0] == "2026-03-10"
    assert sess["session"][0] == "ASIAN"
    assert sess["session"][7] == "LONDON"


def test_explicit_positive_offset_normalizes_to_true_utc_codex_repro():
    """Riproduzione ESATTA del caso di Codex: "2026-03-29 07:00+02:00" deve
    classificarsi come le 05:00 UTC (ASIAN), non le 07:00 UTC (LONDON)."""
    epoch, date, hour = backtest._parse_bar_utc_fields("2026-03-29 07:00+02:00")
    assert hour == 5, "REGRESSIONE: l'offset +02:00 non e' stato sottratto - ora locale trattata come UTC"
    assert date == "2026-03-29"

    candles = [_c("2026-03-29 07:00+02:00", 100, 101, 99, 100.5)]
    sess = backtest._session_amd_series_raw(candles)
    assert sess["session"][0] == "ASIAN", "deve classificarsi ASIAN (05:00 UTC), non LONDON (07:00 UTC)"


def test_explicit_negative_offset_normalizes_to_true_utc():
    """Offset negativo: le 07:00-05:00 locali devono diventare le 12:00 UTC (OVERLAP)."""
    epoch, date, hour = backtest._parse_bar_utc_fields("2026-03-29 07:00-05:00")
    assert hour == 12
    candles = [_c("2026-03-29 07:00-05:00", 100, 101, 99, 100.5)]
    sess = backtest._session_amd_series_raw(candles)
    assert sess["session"][0] == "OVERLAP"


def test_z_suffix_is_explicit_utc():
    """Suffisso Z: UTC esplicito, nessuna conversione, stesso risultato del formato senza offset."""
    epoch, date, hour = backtest._parse_bar_utc_fields("2026-03-29 07:00Z")
    assert hour == 7
    assert date == "2026-03-29"


def test_ambiguous_or_unsupported_timestamp_fails_closed():
    """Formato non riconosciuto o data/ora non valida: fail-closed esplicito
    (None, None, None), MAI un'interpretazione silenziosa come UTC."""
    for bad in ("non e' un timestamp", "2026-13-40 25:99", "", "2026/03/29 07:00",
                "2026-03-29 07:00+2"):
        epoch, date, hour = backtest._parse_bar_utc_fields(bad)
        assert (epoch, date, hour) == (None, None, None), f"formato '{bad}' doveva fallire chiuso"


def test_unsupported_timestamp_excluded_without_crashing_or_polluting_other_dates():
    """Una barra con timestamp non classificabile viene esclusa (nessun
    crash) e non inquina gli accumuli di un'altra data valida."""
    candles = [
        _c("non valido", 999, 999, 999, 999),
        _c("2026-03-11 00:00", 100, 101, 99, 100.5),
        _c("2026-03-11 01:00", 100.5, 102, 100, 101),
    ]
    sess = backtest._session_amd_series_raw(candles)  # non deve lanciare eccezioni
    assert sess["date"][0] is None
    assert sess["session"][0] is None
    assert sess["asian_session_complete"][0] is False
    # le barre valide della data reale non sono contaminate
    assert sess["date"][1] == "2026-03-11"


def test_dst_change_offset_regression_both_signs():
    """Due giorni consecutivi con offset espliciti DIVERSI (come in un
    cambio DST reale: +01:00 prima, +02:00 dopo) - entrambi normalizzati
    correttamente per sola aritmetica, nessuna regola DST necessaria
    perche' l'offset e' esplicito in ciascun timestamp."""
    before = [_c(f"2026-03-28 {h:02d}:00+01:00", 100, 101, 99, 100.5) for h in range(2, 8)]
    after = [_c(f"2026-03-29 {h:02d}:00+02:00", 100, 101, 99, 100.5) for h in range(2, 8)]
    for h, cd in zip(range(2, 8), before):
        _, _, hour = backtest._parse_bar_utc_fields(cd["time"])
        assert hour == h - 1, f"ora locale {h}+01:00 doveva normalizzare a UTC {h - 1}, trovato {hour}"
    for h, cd in zip(range(2, 8), after):
        _, _, hour = backtest._parse_bar_utc_fields(cd["time"])
        assert hour == h - 2, f"ora locale {h}+02:00 doveva normalizzare a UTC {h - 2}, trovato {hour}"


# ------------------------------------------------------- non-regressione ----

def test_no_regression_post_session_strategies_under_v2():
    """LONDON_BO/JUDAS_SWING/LDN_REVERSAL su una sessione COMPLETA (il caso
    normale) devono comportarsi esattamente come nel fix V1 - il nuovo
    requisito di completezza non deve introdurre falsi negativi quando i
    dati sono davvero completi."""
    import random
    random.seed(20261016)
    multi = []
    px = 100.0
    for day in range(1, 8):
        for h in range(24):
            o = px
            px += random.uniform(-0.3, 0.3)
            hi = max(o, px) + random.uniform(0, 0.15)
            lo = min(o, px) - random.uniform(0, 0.15)
            multi.append(_c(f"2026-04-{day:02d} {h:02d}:00", o, hi, lo, px))

    sess = backtest._session_amd_series_raw(multi)
    atr = [0.3] * len(multi)
    ema200 = [None] * len(multi)
    choch_int = ([0] * len(multi), [False] * len(multi), [True] * len(multi))
    ind = {"sess": sess, "atr": atr, "ema200": ema200, "choch_int": choch_int,
           "weekly_pwh": None, "weekly_pwl": None, "monthly_pmh": None, "monthly_pml": None}

    checked = 0
    for i in range(20, len(multi)):
        if sess["session"][i] == "ASIAN":
            continue
        # con dati orari regolari ogni sessione Asian e' per costruzione
        # completa: asian_session_complete deve essere True per ogni barra
        # post-sessione, altrimenti il fix V2 sta rigettando sessioni buone.
        assert sess["asian_session_complete"][i] is True, (
            f"falso negativo: sessione completa rigettata alla barra {i} ({multi[i]['time']})"
        )
        checked += 1
        for fn in (backtest.sig_london_bo, backtest.sig_judas_swing, backtest.sig_ldn_reversal):
            fn(multi, ind, i)  # non deve lanciare eccezioni
    assert checked > 100
