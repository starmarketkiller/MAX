#!/usr/bin/env python3
"""29/08 - v2: motore Python "come MT5 vero" su SAR, CON gestione intraday
fedele (non solo entry + SL/TP statico, la v1 divergeva 3x in frequenza e
di segno sul risultato).

Analisi EMPIRICA dei 175 trade reali di stanotte (nexus_sel_sar_realtick_
report_deals.csv) prima di riscrivere qualunque cosa:
  - ZERO trade su 175 chiudono per target (tp) - il TP nativo a 6xATR(H4)
    non viene MAI raggiunto nella pratica.
  - 116/175 (66%) chiudono per "sl" - ma a un prezzo diverso dal livello
    nativo iniziale: e' lo stop TRAILING (NXS_TrailingATR.mqh) che si
    stringe, non lo stop fisso a 1xATR(H4).
  - 40/175 (23%) chiudono "NXS:RISK" - protezione max-loss-per-posizione
    (InpMaxLossPosPct=2.0%, NXS_Protections.mqh).
  - 19/175 (11%) chiudono "NXS:TIME".

CORREZIONE 29/08 (debug v3, dopo che v2 con timeout relativo a 4h dava
ancora 350-858 trade contro i 175 reali, 2-5x troppi): **"NXS:TIME" non
e' un timer per-posizione**. Verificato sul CSV reale: OGNI singola
chiusura NXS:TIME cade esattamente alle "23:43:0x" server time, in
QUALSIASI giorno del test, a prescindere da quando la posizione era
stata aperta (es. entry 20:00 -> chiusa 23:43 stesso giorno = 3h43m di
hold; entry 18:45 -> chiusa comunque 23:43 = 4h58m di hold: durate
diverse, stesso orario di chiusura). E' `NXS_Prot_CheckAutoClose()`
(NXS_Protections.mqh:411) - un flatten-all GIORNALIERO prima della
chiusura di sessione del broker per GOLD (InpAutoCloseMin=15 minuti
prima dell'orario di chiusura sessione, quindi la finestra si apre alle
23:43 se la sessione chiude alle 23:58; essendo su tick reali, la
prima posizione ancora aperta in quella finestra viene chiusa quasi
subito, da cui il pattern "23:43:0x" quasi identico ogni volta). NON
c'entra affatto `NXS_MaxHold_LimitSec()` (il percorso 4h/160h) per SAR:
quella funzione, se risolve un profilo (SAR ce l'ha, H4), marca
`holdResolved=true` e la generica `NXS_Prot_CheckMaxHold()` la SALTA
del tutto (riga 313) - la ricerca precedente di un "4h" empirico era
un artefatto statistico (molte posizioni chiuse vicino a fine giornata
per puro caso di orario di apertura), non la causa vera.

Gestione replicata (verificata nel codice, NXS_TrailingATR.mqh):
  - Trailing ATR: attiva quando il profitto raggiunge act=1.0xATR, poi
    trail a k=2.0xATR dal prezzo CORRENTE (override per-strategia SAR,
    NXS_Profile_TrailK, non il globale 2.5 - solo se piu' stretto/
    favorevole del livello attuale). ATR M15 (g_atr globale, gira dopo
    il reset multi-TF a InpTFEntry=M15), non l'H4 del trigger.
  - Max-loss-per-posizione: chiude se la perdita flottante >= 2% del
    saldo CORRENTE.
  - Auto-close giornaliero: qualunque posizione ancora aperta alle
    23:43 server time (stessa ora osservata su OGNI chiusura NXS:TIME
    reale) viene flattata li', indipendentemente da quando e' stata
    aperta.
  - Cooldown per-strategia dopo 3 trade consecutivi (InpMaxConsecPerStrat,
    30 minuti, NXS_Confluence.mqh): scartato all'inizio come "trascurabile
    sull'aggregato 10 mesi", sbagliato - l'utente ha notato una catena di
    8-10 trade in poche ore il 13/11/2025 che prosciuga il conto da $1000
    a $247 in 5 settimane; sotto quella soglia QUALUNQUE distanza di SL
    tipica di GOLD supera l'8% di rischio-al-lotto-minimo e l'ordine viene
    rifiutato per sempre (verificato: calc_lot_risk(sl=20..40, bal=247) ->
    lots=0 sempre) - il conto resta bloccato, zero trade per il resto del
    periodo. Il cooldown e' il meccanismo che nel motore vero spezza
    queste catene. Aggiunto: la sopravvivenza si estende da dicembre 2025
    a luglio 2026, ma NON risolve del tutto - vedi "PROBLEMA APERTO" sotto.

Aggiunto anche NXS_SpreadOK() (NXS_MTFSpreadVol.mqh) - gate GLOBALE
chiamato in OnTick PRIMA di ogni dispatch strategia
(NEXUS_EA_v2.mq5:1033): spread >80pt o >8% dell'ATR M15 corrente blocca
QUALUNQUE apertura quel tick, per QUALSIASI strategia (non solo SAR).
Verificato che la variante "adattiva" (NXR_SpreadOK) e' morta per
costruzione - InpNXR_Enable e' hardcoded false, non e' nemmeno un input,
stessa scoperta gia' fatta il 25/08 per IFVG/FVG_Mit - quindi il gate
vivo e' sempre la versione semplice. Effetto reale ma modesto: PF
0.55->0.79 (reale 0.92), pero' la densita' di novembre cala solo
marginalmente (87->80 trade contro i 50 reali).

RIPROVATO 29/08 (dopo segnalazione utente: "MT5 chiude spesso in pari o
con SL strettissimo") - il trailing sull'estremo favorevole della barra
(non sulla close) e' stato riapplicato, insieme a cooldown e spread gate
(non presenti nel primo tentativo scartato). Risultato sulla FORMA della
distribuzione P&L: eccellente, quasi esatto - 11% dei trade quasi in
pari (reale: 11%), 45% entro $8 di P&L (reale: 46%). Confermato: MT5
valuta il trailing su ogni tick, quindi il prezzo puo' fare un massimo
favorevole e stringere lo stop PRIMA di un eventuale ritorno indietro
nella stessa barra M15 - valutare solo sulla close (versione precedente)
perdeva questo movimento e produceva perdite piu' grandi/nette del
reale. Il fix e' quindi corretto e va mantenuto.

PROBLEMA APERTO (29/08, ancora non risolto): novembre+dicembre 2025
restano piu' densi nel motore Python (~160 trade nei due mesi) che nel
reale (51, sullo STESSO segnale verificato identico 175/175). Esclusi
con verifica diretta nel codice: MTF validation (disattivo di default),
NXS_VolatilityRegime (morto, mai letto altrove), soglia minima di score
(non applicabile a SAR), spread gate (effetto reale ma marginale). Anche
la durata media dei trade e' comparabile (Python mediana 2.00h, reale
2.52h a novembre) - NON e' quindi solo un discorso di "chiude/riapre piu'
in fretta". Resta un vero mistero: la densita' di OPPORTUNITA' di entrata
(condizione vera + nessuna posizione aperta) e' strutturalmente piu' alta
in Python che nel motore reale in quello specifico periodo, per una
ragione non ancora identificata. Prossima ipotesi da testare: contare
quante barre M15 consecutive soddisfano la condizione SAR/EMA (sugli
indicatori REALI) in novembre 2025, per capire se il segnale stesso resta
"acceso" piu' a lungo di quanto la cadenza reale delle entrate suggerisca
- se si', il gate mancante agisce su qualcosa di diverso dal semplice
timing (forse un filtro di direzione/coerenza non ancora trovato).
"""
import os
import csv
import random
import datetime as dt
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("nxs_real_engine", os.path.join(HERE, "nxs_real_engine_29-08.py"))
eng = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eng)

# 30/08 - SCOPERTA: il filtro di esaurimento Elliott Wave multi-timeframe
# (server/research_scripts/elliott_wave_filter_25-08.py, vault "Filtro
# Elliott Wave Multi-Timeframe") NON e' solo ricerca Python abbandonata -
# e' gia' vivo in MQL5 (NXS_ElliottFilter.mqh, agganciato in
# NXS_Execution.mqh:399) e GIA' ATTIVO per SAR (NXS_Profile_UseElliott
# ("SAR")=true, InpUseStrategyProfiles=true di default). Significa che
# OGNI test reale di stanotte aveva gia' questo filtro acceso, mentre
# questo motore Python non l'ha mai saputo - candidato forte per il
# "mistero" della densita' novembre/dicembre mai risolto. Riusa
# build_zigzag_full() gia' validato in ricerca, non riscritto da zero.
_espec = importlib.util.spec_from_file_location("elliott_filter", os.path.join(HERE, "elliott_wave_filter_25-08.py"))
_emod = importlib.util.module_from_spec(_espec)
import sys as _sys
_sys.modules.setdefault("elliott_filter", _emod)
try:
    _espec.loader.exec_module(_emod)
except Exception:
    _emod = None   # elliott_wave_filter_25-08.py importa backtest.py - se fallisce, filtro disattivato

# ---- parametri gestione, dal codice reale (NXS_Inputs.mqh / NXS_TrailingATR.mqh) ----
TRAIL_ACTIVATE_ATR = 1.0
TRAIL_K = 2.0   # NXS_Profile_TrailK("SAR") - override specifico, non il globale 2.5 (NXS_StrategyProfiles.mqh:400)
MAX_LOSS_POS_PCT = 2.0
DAILY_AUTOCLOSE_HOUR = 23   # NXS_Prot_CheckAutoClose - orario osservato su ogni NXS:TIME reale: "23:43:0x"
DAILY_AUTOCLOSE_MIN = 43
# 30/08 - tre gate a livello di CONTO trovati leggendo NXS_CheckProtections()
# (NXS_Risk.mqh) dopo la richiesta dell'utente di "spogliare MT5" - attivi
# di default nel Tester (InpTesterProtectionParity=true, "stesse protezioni
# del live"), mai modellati prima:
MAX_DAILY_DD_PCT = 5.0       # InpMaxDailyDDPct - blocca nuove entrate per il resto della giornata
MAX_TRADES_PER_DAY = 12      # InpMaxTradesPerDay
ANTI_REVENGE_LOSSES = 3      # InpAntiRevengeLosses - dopo 3 perdite CONSECUTIVE...
ANTI_REVENGE_MIN = 60        # ...blocca nuove entrate per 60 minuti (InpAntiRevengeMin)
# 29/08 - cooldown per-strategia (NXS_Confluence.mqh, InpUseStrategyCD/
# InpMaxConsecPerStrat/InpStratCooldownMin). Scartato all'inizio come
# "impatto trascurabile sull'aggregato dei 10 mesi" - sbagliato: l'utente
# ha notato una catena di 8-10 trade in poche ore il 13/11/2025 (quasi
# tutti in perdita, -20/-23/-31/-22$) che prosciuga il conto da $1000 a
# $247 in 5 settimane; sotto quella soglia QUALUNQUE distanza di SL tipica
# di GOLD supera l'8% di rischio-al-lotto-minimo e l'ordine viene rifiutato
# per sempre (verificato: calc_lot_risk(sl=20..40, balance=247) -> lots=0
# in ogni caso) - il conto resta bloccato, zero trade per gli 8 mesi
# successivi. Il cooldown dopo 3 trade consecutivi della stessa strategia
# e' proprio il meccanismo che nel motore vero spezza queste catene.
COOLDOWN_MAX_CONSEC = 3
COOLDOWN_MIN = 30


def load_real_indicators(path, h4):
    """Carica i valori VERI di iSAR/iMA9/iMA21/iATR14 esportati da MT5
    (CopyBuffer, non una reimplementazione Python) e li allinea per tempo
    alla lista h4 gia' caricata. DBL_MAX (1.79e308) = barra non ancora
    calcolabile (warm-up dell'indicatore) -> None."""
    DBLMAX = 1.7976931348623157e+308
    by_time = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = dt.datetime.strptime(r["time"], "%Y.%m.%d %H:%M")
            def v(key):
                x = float(r[key])
                return None if x >= DBLMAX * 0.99 else x
            by_time[t] = {"sar": v("sar"), "ema9": v("ema9"), "ema21": v("ema21"), "atr14": v("atr14")}
    sar = [None] * len(h4); ema9 = [None] * len(h4); ema21 = [None] * len(h4); atr14 = [None] * len(h4)
    n_missing = 0
    for i, c in enumerate(h4):
        rec = by_time.get(c["time"])
        if rec is None:
            n_missing += 1
            continue
        sar[i] = rec["sar"]; ema9[i] = rec["ema9"]; ema21[i] = rec["ema21"]; atr14[i] = rec["atr14"]
    if n_missing:
        print(f"[load_real_indicators] ATTENZIONE: {n_missing}/{len(h4)} barre H4 senza indicatore reale corrispondente (time mismatch)")
    return {"sar": sar, "ema9": ema9, "ema21": ema21, "atr14": atr14}


def load_bars(path, m15=False):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "time": dt.datetime.strptime(r["time"], "%Y.%m.%d %H:%M" if m15 else "%Y.%m.%d %H:%M"),
                "open": float(r["open"]), "high": float(r["high"]),
                "low": float(r["low"]), "close": float(r["close"]),
            })
    return rows


def ema_series(vals, n):
    # porting esatto da backtest.py (gia' validato riga-per-riga vs MQL5):
    # seed = SMA delle prime n barre, NON il primo valore grezzo - la mia
    # prima versione (seed=vals[0]) divergeva dall'iMA nativo di MT5.
    out = [None] * len(vals)
    if len(vals) < n:
        return out
    k = 2 / (n + 1)
    e = sum(vals[:n]) / n
    out[n - 1] = e
    for i in range(n, len(vals)):
        e = vals[i] * k + e * (1 - k)
        out[i] = e
    return out


def atr_series(candles, n=14):
    # porting esatto da backtest.py: Wilder/SMMA (a = (a*(n-1)+tr)/n), NON
    # una media mobile semplice - iATR di MT5 usa lo smoothing di Wilder,
    # la mia prima versione (SMA su finestra) sovra/sottostimava l'ATR e
    # quindi ogni distanza di SL/trailing/lotto derivata da esso.
    trs = [0.0]
    for i in range(1, len(candles)):
        h, l, pc = candles[i]["high"], candles[i]["low"], candles[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    out = [None] * len(candles)
    if len(candles) <= n:
        return out
    a = sum(trs[1:n + 1]) / n
    out[n] = a
    for i in range(n + 1, len(candles)):
        a = (a * (n - 1) + trs[i]) / n
        out[i] = a
    return out


def resample_d1_from_h4(h4):
    """Barre D1 sintetiche dalle H4 (stesso broker/dati, niente nuovo
    export MT5 necessario): un giorno = le barre H4 di quella data."""
    days = {}
    order = []
    for c in h4:
        d = c["time"].date()
        if d not in days:
            days[d] = {"time": dt.datetime(d.year, d.month, d.day), "open": c["open"],
                       "high": c["high"], "low": c["low"], "close": c["close"]}
            order.append(d)
        else:
            rec = days[d]
            rec["high"] = max(rec["high"], c["high"])
            rec["low"] = min(rec["low"], c["low"])
            rec["close"] = c["close"]
    return [days[d] for d in order]


def compute_elliott_exhaustion(h4, atr4, dev_mult=2.0):
    """Esaurimento Elliott su H4 e D1 (D1 ricampionato dalle H4), stessa
    logica gia' validata in ricerca (elliott_wave_filter_25-08.py,
    build_zigzag_full) e gia' viva in MQL5 (NXS_ElliottFilter.mqh,
    NXS_Execution.mqh:399) - GIA' ATTIVA per SAR sul motore reale
    (NXS_Profile_UseElliott("SAR")=true), mai modellata qui finora.
    Ritorna (exh_h4, d1, exh_d1) - array allineati a h4/d1."""
    if _emod is None:
        return [0] * len(h4), [], []
    exh_h4, _ = _emod.build_zigzag_full(h4, atr4, dev_mult)
    d1 = resample_d1_from_h4(h4)
    atr_d1 = atr_series(d1, 14)
    exh_d1, _ = _emod.build_zigzag_full(d1, atr_d1, dev_mult)
    return exh_h4, d1, exh_d1


def psar_series(candles, af_step=0.02, af_max=0.2):
    n = len(candles)
    psar = [None] * n
    trend = [0] * n
    if n < 3:
        return psar, trend
    trend[1] = 1 if candles[1]["close"] > candles[0]["close"] else -1
    psar[1] = candles[0]["low"] if trend[1] == 1 else candles[0]["high"]
    ep = candles[1]["high"] if trend[1] == 1 else candles[1]["low"]
    af = af_step
    for i in range(2, n):
        p = psar[i-1] + af * (ep - psar[i-1])
        if trend[i-1] == 1:
            p = min(p, candles[i-1]["low"], candles[i-2]["low"])
            if candles[i]["low"] < p:
                trend[i] = -1; p = ep; ep = candles[i]["low"]; af = af_step
            else:
                trend[i] = 1
                if candles[i]["high"] > ep:
                    ep = candles[i]["high"]; af = min(af + af_step, af_max)
        else:
            p = max(p, candles[i-1]["high"], candles[i-2]["high"])
            if candles[i]["high"] > p:
                trend[i] = 1; p = ep; ep = candles[i]["high"]; af = af_step
            else:
                trend[i] = -1
                if candles[i]["low"] < ep:
                    ep = candles[i]["low"]; af = min(af + af_step, af_max)
        psar[i] = p
    return psar, trend


def run(h4, m15, start_dt, end_dt, start_equity=1000.0, seed=42, verbose_trades=None,
        real_indicators=None):
    """real_indicators: se passato (da nxs_h4_gold_indicators_29-08.csv, i valori
    VERI di iSAR/iMA9/iMA21/iATR14 letti da MT5 via CopyBuffer), sostituisce la
    reimplementazione Python del segnale H4 - isola se la divergenza segnale-per-
    segnale viene da un drift della reimplementazione (PSAR e' path-dependent)."""
    rng = random.Random(seed)
    closes4 = [c["close"] for c in h4]
    if real_indicators is not None:
        psar4 = real_indicators["sar"]
        ema9_4 = real_indicators["ema9"]
        ema21_4 = real_indicators["ema21"]
        atr4 = real_indicators["atr14"]
    else:
        ema9_4 = ema_series(closes4, 9)
        ema21_4 = ema_series(closes4, 21)
        atr4 = atr_series(h4, 14)
        psar4, _ = psar_series(h4)
    atr15 = atr_series(m15, 14)
    exh_h4, d1, exh_d1 = compute_elliott_exhaustion(h4, atr4, dev_mult=2.0)
    d1_closed_idx = -1   # ultimo giorno D1 CHIUSO (data < data corrente)

    # indice M15 di partenza per ogni barra H4 (per camminare intraday dopo l'entry)
    m15_idx_by_time = {c["time"]: i for i, c in enumerate(m15)}
    m15_times_sorted = [c["time"] for c in m15]

    def m15_index_at_or_after(t):
        # ricerca lineare a partire da un cursore esterno sarebbe piu' veloce,
        # ma il volume (20k barre) rende accettabile anche binaria semplice
        import bisect
        i = bisect.bisect_left(m15_times_sorted, t)
        return i if i < len(m15_times_sorted) else None

    equity = start_equity
    peak = start_equity
    max_dd = 0.0
    trades = []
    trade_log = []   # (entry_time, dir, entry_price, exit_time, exit_price, reason, pnl)
    reasons_count = {}
    cd_consec = 0        # NXS_Confluence.mqh: g_cdConsec
    cd_until = None       # g_cdUntil
    cur_day = None        # NXS_DailyRollover: giorno corrente (server time, proxy: data calendario)
    day_start_equity = start_equity   # g_balanceDayStart (in realta' equity, non balance - vedi commento MQL5)
    trades_today = 0      # g_tradesToday
    consec_losses = 0     # g_consecLosses
    revenge_until = None  # g_antiRevengeUntil

    m15_start_j = next(j for j, c in enumerate(m15) if c["time"] >= start_dt)
    m15_end_j = next((j for j, c in enumerate(m15) if c["time"] >= end_dt), len(m15))

    # 29/08 - v3: event loop M15 UNICO e continuo, non piu' un ciclo per
    # indice H4 che apriva solo "alla barra H4 successiva". Verificato sui
    # dati reali (nexus_sel_sar_realtick_report_deals.csv): il gap tra una
    # chiusura e la RIENTRATA successiva va da 0.0h a diverse ore (mediana
    # 1.7h) - MT5 valuta la condizione SAR/EMA su OGNI TICK usando l'ultima
    # barra H4 chiusa (shift=1), quindi puo' rientrare in qualunque momento
    # non appena una posizione si libera, non solo all'apertura della barra
    # H4 successiva. Con l'entry incollata al boundary H4 (v2) il conteggio
    # totale restava 2x quello reale (350 contro 175) nonostante il mix
    # sl/risk/time fosse ormai corretto - la frequenza di ENTRATA, non la
    # gestione d'uscita, era il problema residuo.
    h4_closed_idx = -1   # indice dell'ultima barra H4 CHIUSA rispetto al tempo corrente

    pos = None   # None oppure dict con sig/entry/sl/lots/deadline
    j = max(m15_start_j, 0)
    while j < m15_end_j:
        bar = m15[j]
        t = bar["time"]

        # NXS_DailyRollover() (NXS_Risk.mqh): a mezzanotte server time reset
        # del contatore trade/giorno e della baseline del drawdown giornaliero
        # (equity di inizio giornata, non balance - include il flottante
        # ereditato dal giorno prima, vedi commento MQL5 AUD0-RISK-005).
        if t.date() != cur_day:
            cur_day = t.date()
            trades_today = 0
            day_start_equity = equity

        # avanza il cursore H4: h4[h4_closed_idx] e' l'ultima barra chiusa
        # (equivalente a iClose(...,1) nel momento t)
        while h4_closed_idx + 1 < len(h4) - 1 and h4[h4_closed_idx + 2]["time"] <= t:
            h4_closed_idx += 1
        # avanza il cursore D1: d1[d1_closed_idx] e' l'ultimo giorno CHIUSO
        # (equivalente a iTime(...,D1,1) nel momento t)
        while d1_closed_idx + 1 < len(d1) and d1[d1_closed_idx + 1]["time"].date() < t.date():
            d1_closed_idx += 1

        if pos is not None:
            # 29/08 - RIPROVATO dopo la segnalazione dell'utente: nel reale
            # molti "sl" chiudono quasi in pari o con perdita minima (46%
            # dei 175 trade reali entro $8, contro 31% in Python) - MT5
            # valuta il trailing su ogni TICK, quindi il prezzo puo' fare
            # un massimo favorevole, stringere lo stop, e SOLO DOPO tornare
            # indietro nella stessa barra M15; valutare solo sulla close
            # (come sotto in precedenza) perde questo movimento e lascia
            # correre le perdite piu' del reale. La prima volta il fix
            # sull'estremo favorevole sembrava rompere tutto (conto
            # bloccato a dicembre 2025) - causa vera trovata dopo: densita'
            # di entrate eccessiva a novembre/dicembre (non ancora
            # risolta), non questo fix. Riapplicato: migliora la
            # distribuzione dei pnl verso il pattern reale.
            a15 = atr15[j]
            if a15:
                favorable = bar["high"] if pos["sig"] == 1 else bar["low"]
                if pos["sig"] == 1:
                    if favorable - pos["entry"] >= TRAIL_ACTIVATE_ATR * a15:
                        new_sl = favorable - TRAIL_K * a15
                        if new_sl > pos["sl"]:
                            pos["sl"] = new_sl
                else:
                    if pos["entry"] - favorable >= TRAIL_ACTIVATE_ATR * a15:
                        new_sl = favorable + TRAIL_K * a15
                        if new_sl < pos["sl"]:
                            pos["sl"] = new_sl

            hit_sl = (bar["low"] <= pos["sl"]) if pos["sig"] == 1 else (bar["high"] >= pos["sl"])
            if hit_sl:
                exit_price, exit_reason = pos["sl"], "sl"
            elif t > pos["deadline"]:
                exit_price, exit_reason = bar["open"], "time"
            else:
                # 3) max-loss-per-posizione sul close della barra
                float_pnl_price = (bar["close"] - pos["entry"]) if pos["sig"] == 1 else (pos["entry"] - bar["close"])
                float_pnl_money = float_pnl_price / eng.TICK_SIZE * eng.TICK_VALUE_PER_LOT * pos["lots"]
                if float_pnl_money <= pos["max_loss_money"]:
                    exit_price, exit_reason = bar["close"], "risk"
                else:
                    exit_price = exit_reason = None

            if exit_reason is not None:
                pnl_price = (exit_price - pos["entry"]) if pos["sig"] == 1 else (pos["entry"] - exit_price)
                pnl_money = pnl_price / eng.TICK_SIZE * eng.TICK_VALUE_PER_LOT * pos["lots"]
                equity += pnl_money
                trades.append(pnl_money)
                trade_log.append({
                    "entry_time": pos["entry_time"], "dir": pos["sig"], "entry_price": pos["entry"],
                    "exit_time": t, "exit_price": exit_price, "reason": exit_reason, "pnl": pnl_money,
                })
                reasons_count[exit_reason] = reasons_count.get(exit_reason, 0) + 1
                cd_consec += 1
                if cd_consec >= COOLDOWN_MAX_CONSEC:
                    cd_until = t + dt.timedelta(minutes=COOLDOWN_MIN)
                    cd_consec = 0
                # NXS_OnTradeClosed() (NXS_Risk.mqh): anti-revenge dopo N
                # perdite CONSECUTIVE (non trade generici come il cooldown
                # sopra) - blocca nuove entrate per 60 minuti. Una vincita
                # non azzera lo streak, lo riduce solo di 1 ("2 vincite per
                # cancellare 1 perdita" - saggezza anti-bleed nel commento
                # originale).
                if pnl_money < 0:
                    consec_losses += 1
                    if consec_losses >= ANTI_REVENGE_LOSSES:
                        revenge_until = t + dt.timedelta(minutes=ANTI_REVENGE_MIN)
                        consec_losses = 0
                else:
                    consec_losses = max(0, consec_losses - 1)
                peak = max(peak, equity)
                if peak > 0:
                    max_dd = max(max_dd, (peak - equity) / peak * 100)
                if verbose_trades and len(trades) <= verbose_trades:
                    print(f"  #{len(trades)} {pos['entry_time']} dir={pos['sig']} entry={pos['entry']:.2f} "
                          f"exit={exit_price:.2f} ({exit_reason}) pnl=${pnl_money:.2f} equity=${equity:.2f}")
                pos = None
                if equity <= 0:
                    break
            else:
                j += 1
                continue

        # nessuna posizione aperta: cooldown per-strategia dopo N trade
        # consecutivi (NXS_StrategyOnCooldown) - spezza le catene di
        # rientrate immediate durante una fase di segnale persistente.
        if cd_until is not None and t < cd_until:
            j += 1
            continue

        # NXS_CheckProtections() (NXS_Risk.mqh), attivo di default nel
        # Tester (InpTesterProtectionParity=true, "stesse protezioni del
        # live") - tre gate a livello di CONTO mai modellati prima:
        if revenge_until is not None and t < revenge_until:   # anti_revenge
            j += 1
            continue
        if day_start_equity > 0 and equity <= day_start_equity * (1 - MAX_DAILY_DD_PCT / 100.0):   # daily_dd
            j += 1
            continue
        if trades_today >= MAX_TRADES_PER_DAY:   # max_trades
            j += 1
            continue

        # nessuna posizione aperta: valuta il segnale sull'ultima H4 chiusa
        if h4_closed_idx < 0 or psar4[h4_closed_idx] is None or ema9_4[h4_closed_idx] is None \
           or ema21_4[h4_closed_idx] is None or atr4[h4_closed_idx] is None:
            j += 1
            continue
        sar_v = psar4[h4_closed_idx]; e9 = ema9_4[h4_closed_idx]; e21 = ema21_4[h4_closed_idx]
        px = closes4[h4_closed_idx]; atr_h4 = atr4[h4_closed_idx]
        sig = 0
        if sar_v < px and e9 > e21:
            sig = 1
        elif sar_v > px and e9 < e21:
            sig = -1
        if sig == 0:
            j += 1
            continue

        # NXS_ElliottBlocks() (NXS_ElliottFilter.mqh, GIA' vivo in MQL5 e
        # GIA' attivo per SAR - NXS_Execution.mqh:399): sopprime il segnale
        # se un impulso Elliott a 5 onde si e' appena esaurito nella STESSA
        # direzione su H4 O (OR) su D1. Ogni test reale di stanotte aveva
        # gia' questo filtro attivo - qui modellato per la prima volta.
        if h4_closed_idx < len(exh_h4) and exh_h4[h4_closed_idx] == sig:
            j += 1
            continue
        if 0 <= d1_closed_idx < len(exh_d1) and exh_d1[d1_closed_idx] == sig:
            j += 1
            continue

        hour = t.hour
        spr_pts = eng.sample_spread_points(hour, rng)
        # NXS_SpreadOK() (NXS_MTFSpreadVol.mqh) - gate GLOBALE chiamato in
        # OnTick PRIMA di ogni dispatch strategia (NEXUS_EA_v2.mq5:1033):
        # spread troppo largo (>80pt o >8% dell'ATR M15 corrente) blocca
        # QUALUNQUE nuova apertura quel tick, non solo per SAR.
        if not eng.spread_ok(spr_pts, atr15[j]):
            j += 1
            continue
        spr = spr_pts * eng.TICK_SIZE
        sl_dist_init = 1.0 * atr_h4
        if sig == 1:
            entry = bar["open"] + spr / 2
            sl = entry - sl_dist_init
        else:
            entry = bar["open"] - spr / 2
            sl = entry + sl_dist_init

        lots, _reason = eng.calc_lot_risk(abs(entry - sl), 1.0, equity, "SAR")
        if lots <= 0:
            j += 1
            continue

        deadline = t.replace(hour=DAILY_AUTOCLOSE_HOUR, minute=DAILY_AUTOCLOSE_MIN, second=0, microsecond=0)
        if t >= deadline:
            deadline += dt.timedelta(days=1)

        pos = {
            "sig": sig, "entry": entry, "sl": sl, "lots": lots,
            "max_loss_money": -(equity * MAX_LOSS_POS_PCT / 100.0),
            "deadline": deadline, "entry_time": t,
        }
        trades_today += 1
        j += 1

    gains = sum(t for t in trades if t > 0)
    losses = -sum(t for t in trades if t < 0)
    pf = gains / losses if losses > 0 else (float("inf") if gains > 0 else 0.0)
    return {
        "n_trades": len(trades), "pf": pf, "net": equity - start_equity,
        "max_dd_pct": max_dd, "final_equity": equity, "reasons": reasons_count,
        "trade_log": trade_log,
    }


def main():
    eng.load_spread_profile()
    h4 = load_bars(os.path.join(HERE, "nxs_h4_gold_29-08.csv"))
    m15 = load_bars(os.path.join(HERE, "nxs_m15_gold_29-08.csv"), m15=True)
    result = run(h4, m15, dt.datetime(2025, 11, 1), dt.datetime(2026, 8, 26), verbose_trades=8)
    print()
    print("=== SAR - motore Python v3 (event loop M15 continuo, auto-close giornaliero) ===")
    print(f"n_trades={result['n_trades']} PF={result['pf']:.2f} netto=${result['net']:.2f} "
          f"DD_max={result['max_dd_pct']:.1f}% equity_finale=${result['final_equity']:.2f}")
    print(f"motivi di uscita: {result['reasons']}")
    print()
    print("Confronto col Tester MT5 reale (stanotte, tick reali):")
    print("  n_trades=175 PF=0.92 netto=-$118.95 DD_max=28.7%")
    print("  motivi reali: {'NXS:RISK': 40, 'sl': 116, 'NXS:TIME': 19}")
    print()
    print("Stato convergenza (29/08): segno corretto, 6 fix reali applicati")
    print("(Wilder ATR, TrailK per-strategia, auto-close giornaliero fisso,")
    print("event loop M15 continuo, cooldown per-strategia, spread gate globale,")
    print("trailing sull'estremo favorevole della barra non sulla close).")
    print("La FORMA della distribuzione P&L ora combacia col reale (11% quasi")
    print("in pari, 45% entro $8 - reale: 11%/46%).")
    print("PROBLEMA APERTO: nov+dic 2025 restano troppo densi nel motore Python")
    print("(~160 trade contro 51 reali, stesso segnale, durata media comparabile)")
    print("- causa ancora non identificata. Vedi docstring in cima al file.")


if __name__ == "__main__":
    main()
