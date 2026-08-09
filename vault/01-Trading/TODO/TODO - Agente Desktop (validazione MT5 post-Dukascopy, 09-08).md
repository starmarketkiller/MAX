---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, todo, agente-desktop, mt5, dukascopy]
created: 2026-08-09
updated: 2026-08-09
---

# TODO — agente desktop: validazione MT5 dopo la sessione Dukascopy (09/08)

Per **chi ha accesso alla macchina** (MetaEditor, MT5, storico broker). Questa
sessione (remota, Linux headless, senza MT5) ha passato la giornata a testare
tutte le 37 strategie su dati Dukascopy reali (XAUUSD M15, ~1 anno, fetch
ancora in corso verso 10 anni) col motore Python (`server/backtest.py`) e
verificando dal vivo sul sito (`optimize_per_strategy`/`optimize_multi_tf`).
Tre scoperte cambiano le priorità rispetto a [[TODO - Backtest 10Y]] (15-17/07)
— leggi prima quella per il contesto storico, questa aggiorna cosa contare
adesso.

**Prima di tutto**: se il punto 2 di [[TODO - Agente Desktop (consegna remediation)]]
("Compilare l'EA in MetaEditor") non è ancora stato fatto, va fatto prima di
qualunque test qui sotto — nessuna riga di `MQL5/` risulta mai compilata.

---

## 🔴 1. Priorità massima — il nucleo hedge mai testato per davvero

[[TODO - Backtest 10Y]] lo segnalava già a luglio come "potenziale da
sfruttare, non ancora testato": **BREAKOUT_ACC + TURTLE_SOUP + THREE_BAR_DELIVERY_BREAK
(alias CISD)** sommate algebricamente fanno +7.6R su 6 anni, ma è un calcolo a
tavolino (somma di R), mai un backtest reale con le tre attive insieme
(margine condiviso, `InpMaxConcurrent`, corsie hedge).

**Perché conta ancora di più oggi**: nella sessione Dukascopy di oggi
**BREAKOUT_ACC è l'unica strategia (di 36) positiva su tutti e 5 i timeframe
testati (15m/30m/1h/4h/1d)** con campione ≥15 trade ovunque — nessun'altra ci
arriva. Combinata con la conferma MT5 6 anni (+4.3R, unica positiva anche nel
2024) e lo screening Yahoo 10 anni di luglio, è il candidato con più prove
indipendenti di tutto il progetto. Vale la pena isolarla ora, non aspettare.

**Come**: `InpStrategySelector` è già `input` (commit `d9ac0dc`, luglio) — non
serve ricompilare per selezionare. Per un test delle tre insieme (non isolate
una alla volta), usa i profili `InpStrat_*`/`InpUseStrat_*` (anch'essi già
`input`, commit `dc480f8`): disattiva tutte le altre 34, lascia solo
BREAKOUT_ACC + TURTLE_SOUP + THREE_BAR_DELIVERY_BREAK attive, storico più
lungo disponibile dal broker, **`InpTesterProtectionParity = true`**
(default — vedi punto 3).

**Report atteso**: Net/PF/DD/Sharpe combinato, non le tre isolate — quello già
c'è (vedi [[NEXUS EA - Hedge nel Tempo]]). La domanda a cui questo test
risponde: il margine/le corsie condivise riducono l'edge combinato rispetto
alla somma algebrica, o no?

---

## 🔴 2. Il vero LIQ_VOID non è mai stato testato — è dormiente di default

Scoperta di oggi, verificata a tre livelli nel codice (non un'ipotesi):

1. `NXS_Inputs.mqh:261` — `InpUseHTFBias = false` di default.
2. `NXS_HTFBias.mqh:15-17` — con quel flag spento, `NXS_GetHTFBias()` ritorna
   **sempre** `HTF_NEUTRAL`, senza calcolare nulla.
3. `NXS_Strategies_Institutional.mqh:430,452` — `NXS_Strat_LiquidityVoid()`
   richiede `htf.bias == HTF_BULL` (buy) o `HTF_BEAR` (sell) come condizione
   obbligatoria, nessun fallback su NEUTRAL.

**Conseguenza**: LIQ_VOID non genera un segnale nella configurazione di
produzione attuale, punto. E il motore Python del sito la testa come proxy di
FVG_CONT (`server/backtest.py:3311`, dichiarato nel codice: "liquidity void =
FVG proxy") — quindi ogni numero "LIQ_VOID" visto finora (sito, Dukascopy,
Yahoo) è in realtà FVG_CONT sotto un'altra etichetta. **Non sappiamo ancora
nulla della vera LIQ_VOID.**

**Come testarla**: unico modo per avere un dato reale è un run isolato con
`InpUseHTFBias = true` **esplicitamente forzato** (contro il default) +
`InpStrategySelector` puntato solo su LIQ_VOID. Annotare chiaramente nel
report che è un test con HTF bias forzato attivo, non la configurazione di
produzione — se il risultato è buono, la decisione se attivare
`InpUseHTFBias` in produzione (che influenza altre strategie gated dallo
stesso bias, non solo LIQ_VOID) è dell'utente, non implicita in questo test.

---

## 🟠 3. Ri-validare SAR/MACD/RSI_DIV/ADX_RSI — i vecchi numeri sono pre-remediation

[[NEXUS EA - Backtest 10Y Segmentato - Analisi]] (15/07) le indica come le 4
peggiori del portafoglio (-34.3R/-21.1R/-17.5R/-15.3R, ~75% della perdita
totale). Oggi, sullo stesso simbolo ma dati Dukascopy (~1 anno) e motore
sito, **tutte e 4 mostrano PF 1.2-2.1, verdetto FORTE** con campioni via via
più larghi (fino a 150-200 trade su 1h/30m/15m).

Non è detto che si contraddicano: il test di luglio era **pre-remediation**
(25/07) — `InpTesterProtectionParity` non esisteva ancora come gate esplicito
(i cap di conto erano disattivati in blocco nel tester), e il calcolo R non
escludeva ancora i trade con rischio iniziale non ricostruibile (vedi
[[DEC - Cambi di comportamento post-remediation]] §1-2). **I numeri di luglio
e quelli di oggi non sono direttamente confrontabili finché non c'è un test
MT5 fresco con la parità attiva.**

**Come**: stesso storico/setup del punto 1, isolare le 4 una alla volta (o
insieme, se si vuole anche la lettura combinata) con `InpTesterProtectionParity
= true`. Segmentare per anno se lo storico del broker lo permette, stesso
formato di [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] — permette un
confronto diretto riga per riga col vecchio ranking invece di un numero isolato.

---

## 🟡 4. Se c'è tempo: sweep completo con la parità attiva

`results/sets/SWEEP_37_DataCollectionMode.set` è già pronto e carica
`InpStrategySelector` in Optimization 1→37 + `InpDataCollectionMode=true` (
bypassa contesa di slot/margine, utile per WR/PF/R per strategia, **non** per
validare il P&L assoluto — quello serve il profilo normale, vedi
[[TODO - Backtest 10Y]] per il dettaglio). Non ancora eseguito nemmeno a
luglio ("non ancora eseguito nessun run reale con questa configurazione").
Se c'è tempo dopo i punti 1-3, è il modo più veloce per aggiornare l'intero
ranking in un colpo solo.

Manca solo la chiave di licenza nel `.set` (lasciata vuota) — riempirla se
il tuo EA la richiede.

---

## 🟢 5. Opzionale ma risolutivo — Simbolo Personalizzato Dukascopy in MT5

MT5 oggi usa **esclusivamente** lo storico del broker collegato al terminale
(confermato: zero riferimenti a "dukascopy" in tutto `MQL5/`) mentre Python/il
sito usano **esclusivamente** lo snapshot Dukascopy — due feed di prezzo
diversi, sempre. Questo da solo garantisce che i risultati non coincidano mai
al 100%, anche a parità di logica (spread/quotazioni diversi fra broker e
Dukascopy).

**Se vuoi eliminare questa variabile** per isolare le differenze rimaste a
sola logica (non più a dati): MT5 supporta l'import di storico tick esterno
come "Simbolo Personalizzato" (Ctrl+U → Crea simbolo personalizzato → scheda
Tick → Importa tick). Script pronto per generare il CSV:

```bash
python3 server/research_scripts/export_dukascopy_ticks_mt5.py \
    --start 2021-01-01 --end 2026-08-09 --out xauusd_ticks_mt5.csv
```

- Fonte: stessa API Dukascopy già usata dal fetch di produzione, ma con
  bid/ask **separati** (il fetch di produzione tiene solo il mid — serviva
  una funzione nuova, non riusa `dukascopy_fetch.fetch_day_ticks`).
- Formato CSV: `<DATE>,<TIME>,<BID>,<ASK>,<LAST>,<VOLUME>` — quello
  documentato per l'import tick di MT5. **Non verificato contro un'istanza
  MT5 reale** (nessun accesso qui) — fai UN giorno di prova
  (`--start`/`--end` uguali) e verifica che l'import vada a buon fine prima
  di lanciare un range multi-anno.
- Riprendibile: salta i giorni già scritti nel CSV se lo rilanci.
- **Scala reale, testata oggi**: ~217.000 tick/giorno, ~10 MB/giorno →
  **~3.6 GB/anno**. Per 3-5 anni servono 10-18 GB di disco libero. Esegui
  questo script sulla tua macchina (dove hai spazio e MT5), non sul
  container Render (1GB condiviso col database) né chiedendolo a questa
  sessione remota di scaricarlo e poi trasferirtelo.
- Dopo l'import: Strategy Tester → simbolo personalizzato → modello
  **"Ogni tick basato su tick reali"** — è il confronto più pulito possibile
  con Python, che invece lavora su OHLC aggregato (nessuna simulazione
  tick-by-tick nel motore Python attuale — vedi nota sotto).

**Se dopo aver allineato i dati vedi ancora differenze**: a quel punto è
sicuramente logica, non più prezzo. Le aree più probabili, in ordine:
1. **Ordine di tocco SL/TP nella stessa barra**: `backtest.py` controlla
   sempre SL prima di TP (righe 3746-3755, entrambe le direzioni) — una
   convenzione conservativa, non una simulazione tick-accurate. Se MT5 "ogni
   tick reali" mostra l'ordine opposto su una barra specifica, è qui che
   guardare.
2. **Timezone/sessioni**: già corretto per Python oggi (`_session_amd_series`),
   verificare che l'offset del tuo broker (`InpServerGMTOffset`) sia
   impostato correttamente per il confronto.
3. Gli indicatori (EMA/ATR/PSAR/ADX/MACD) sono scritti a mano in `backtest.py`
   e già verificati riga-per-riga contro le funzioni MQL5 native in sessioni
   precedenti — meno probabile che sia qui, ma se serve isolare: stampa il
   valore su una barra specifica e confrontalo con la Finestra Dati di MT5.

---

## Cosa riportare indietro

Stesso formato di [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]: Net, PF,
Drawdown Max (Equity), Sharpe, per strategia (e per anno se segmentato). Per
il punto 2 (LIQ_VOID), specificare esplicitamente che `InpUseHTFBias` era
forzato a `true`. Annotare eventuali bug/anomalie nel log (stesso schema di
`executed` rotto/`DERIVA CONTRATTO` già noto da
[[TODO - Agente Desktop (consegna remediation)]] §3).

## Cosa NON serve rifare

- Il fix del bug Asian-range di oggi (`server/backtest.py`, `_session_amd_series`)
  è **solo lato Python** — l'MQL5 reale calcola l'Asian range da `InpTFEntry`
  fine-grained fin dall'inizio (`NXS_AMDModel.mqh:46`), non aveva questo bug.
  Nessuna azione MT5 necessaria per questo.
- I 4 proxy "stale" nel registro (LONDON_BO/WEEKLY_EXP/SH_BMS_RTO/SMS_BMS_RTO)
  sono un problema di `contracts/strategy-registry.json` non rigenerato, non
  di MQL5 — quelle 4 hanno già la loro implementazione reale sia in MQL5 sia
  nel porting Python (dal 04/08). Nessuna azione qui.

## Collegamenti
[[MOC - Trading]] · [[TODO - Backtest 10Y]] ·
[[TODO - Agente Desktop (consegna remediation)]] ·
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]] ·
[[NEXUS EA - Hedge nel Tempo]] ·
[[DEC - Cambi di comportamento post-remediation]]
