---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, architettura]
created: 2026-07-12
updated: 2026-07-15
---

# NEXUS EA — panoramica

## Cos'è
Expert Advisor MQL5 che opera oro (XAUUSD/GOLD) e BTC su MT5, pensato per conti piccoli
(~€200-1000, XM Global demo, hedge mode, leva 1:100). Non è uno scalper generico: è un
portafoglio di ~30 strategie indipendenti (trend, mean-reversion, SMC/price-action),
ciascuna con il proprio timeframe, rischio e uscite.

## La filosofia guida
**"L'EA deve operare esattamente come il suo backtest."** Il Backtest Lab del sito
(motore Python, `server/backtest.py`) è la fonte di verità: se una strategia rende bene
lì ma perde su MT5, la causa non è "il mercato è diverso" ma che l'EA non replica la
stessa logica. Gran parte del lavoro è stato *portare* la logica del sito dentro MQL5
strategia per strategia (vedi [[NEXUS EA - Log Versioni]]).

## Architettura tecnica
- **Multi-timeframe su un solo grafico**: un'istanza EA calcola ogni strategia sul SUO
  timeframe ottimale (D1/H4/H1) tramite una cache di handle indicatori
  (`NXS_ActivateTF`), non serve aprire tre grafici.
- **Profili per-strategia** (`NXS_StrategyProfiles.mqh`): ogni strategia ha il proprio
  SL/TP (x ATR), timeframe, rischio %, gate HTF, larghezza/attivazione del trailing.
- **Hedge per strategia**: ogni strategia opera nella sua corsia (long e short possono
  coesistere), non competono per slot condivisi — così ciascuna rende come nel suo
  backtest isolato.
- **Il conto come regolatore**: un gate sul margin level proiettato decide se aprire un
  nuovo trade. Un trade in profitto alza l'equity → alza il margine libero → apre spazio
  ad altre strategie. Un drawdown lo abbassa → frena da solo. "Profitto = margine =
  spazio per altre strategie."
- **Scudo anti-rovina**: rischio dimensionato per strategia, tetto di esposizione che
  scala col saldo, cap per direzione/timeframe.

## Il vincolo del conto piccolo (scoperta importante)
Su ~€1000 con strategie HTF (D1/H4), ogni trade è già al **lotto minimo 0.01** —
il rischio % per-strategia è quindi *inerte* finché il conto non cresce abbastanza da
far pesare quel % oltre il minimo broker. Le uniche leve reali su un conto piccolo sono:
1. **concorrenza** (più posizioni da 0.01 aperte insieme),
2. **crescita del conto** (quando il saldo sale, il rischio % ricomincia a mordere).

Questo è il motore della visione a scaglioni: piccolo conto → poche strategie robuste
a lotto minimo → profitto → conto cresce → si sbloccano size e strategie via via.

## Obiettivo dichiarato dall'utente (15/07)
Scalare un conto da **€200 a idealmente €1.000.000**, con interesse
composto, **su un orizzonte di tempo indefinito** — non un target a
scadenza fissa. Implicazioni esplicite:
- Il volume/opportunità di mercato non è costante: alcune operazioni tenute
  aperte più a lungo (con runner o gestione posizione adatta, non chiusura
  rapida a TP fisso) possono valere più dell'intero contributo di
  un'altra strategia chiusa velocemente. Da tenere in mente quando si
  valutano trailing/exit management per-strategia (vedi già
  [[NEXUS EA - Log Versioni]] v2.4.5, trailing per-strategia).
- **Fase iniziale su conto piccolo (€200-1000)**: ipotesi dell'utente da
  valutare — usare inizialmente **solo i segnali HTF** (timeframe più alti),
  per massimizzare la probabilità di esecuzione reale su un conto che parte
  già al lotto minimo (vedi sezione sotto, "Il vincolo del conto piccolo").
  Meno strategie attive ma più affidabili, non tutte e 37 da subito.
- Ogni strategia deve restare **indipendente** dalle altre — non deve
  dipendere dal fatto che altre strategie occupino o liberino uno slot
  condiviso (vedi architettura "hedge per strategia" sotto, e
  [[NEXUS EA - Motore Sito: Audit e Confronto 10Y]] per il caso opposto/di
  cui diffidare: il motore sito che invece compete per un unico slot).

## Cosa NON è portabile dal sito
Le strategie di sessione/Elliott (SILVER_BULLET, AMD_*, JUDAS_SWING, LDN/NY_REVERSAL,
PO3, ELLIOTT) richiedono modellazione intraday/di sessione che il motore Python
(daily-oriented, dati Yahoo) non ha. Vanno validate direttamente su MT5, isolate via
`InpStrategySelector`.

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Log Versioni]] · [[Sito Backtest Lab - Note Tecniche]]
