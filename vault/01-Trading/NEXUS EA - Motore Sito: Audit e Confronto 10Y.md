---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, sito, backtest-lab, audit, hedge]
created: 2026-07-15
updated: 2026-07-15
---

# Motore sito — audit del codice ed esecuzione diretta a 10 anni

Il motore Python (`server/backtest.py`) è raggiungibile e funzionante in
questo ambiente (Yahoo Finance via proxy, 2512 barre giornaliere XAUUSD,
2016-07→2026-07 — **la stessa identica finestra dei 10 anni segmentati su
MT5**). Ho letto il codice riga per riga ed eseguito direttamente i backtest
mancanti. Due scoperte cambiano come usare questo strumento d'ora in poi.

## Scoperta #1: il motore del sito non ha NESSUN hedge — è strutturalmente a singola posizione

In `run_backtest()` (`backtest.py:725-837`), la variabile posizione è
**`pos = None`**, singolare, non una lista. Il ciclo principale fa
`if pos: continue` — finché una posizione è aperta, **nessun nuovo segnale
viene nemmeno controllato**, indipendentemente da quale strategia lo
genererebbe. Quando si passa una lista di più strategie (`strategies=[...]`),
non girano in parallelo: competono per lo **stesso identico slot**, vince la
prima con segnale non-zero nell'ordine della lista.

**Conclusione**: il concetto di "hedge nel tempo" o "corsie indipendenti"
(quello che rende profittevole il nucleo TURTLE_SOUP+BREAKOUT_ACC+CISD su
MT5) **non è testabile sul motore del sito così com'è oggi**, perché il sito
non può mai avere due posizioni aperte insieme, di due strategie diverse o
della stessa. Non è un limite di dati, è un limite di design del motore.
Rende anche onore a [[NEXUS EA - Principi]] #5: gran parte del divario
sito↔MT5 documentato negli anni potrebbe venire proprio da qui, non solo
dalla differenza nei dati (daily Yahoo vs multi-TF broker).

> **Implicazione pratica**: per validare il nucleo hedge, l'unico strumento
> valido resta un backtest isolato su MT5 con le tre strategie attive insieme
> (già in [[TODO - Backtest 10Y]]) — il sito non può rispondere a questa
> domanda nemmeno in teoria, finché non viene esteso a multi-posizione.

## Scoperta #2: il proxy "SAR" del sito non è Parabolic SAR — è identico a EMA_PULLBACK

`sig_sar()` (`backtest.py:387-397`) è etichettato come nuova strategia SMC
("strutturali/SMC, v2.2.8") ma la sua logica è un incrocio EMA20/EMA50 quasi
identica a `sig_ema_pullback()`. Verificato eseguendo entrambe su XAUUSD D1
10y: **producono la sequenza di trade IDENTICA, operazione per operazione**
(stesso entry price, stesso exit, stesso timing — 84/84 trade uguali). Il
sito non sta testando Parabolic SAR in nessun modo — sta testando due volte
lo stesso incrocio di medie con un nome diverso.

**Conseguenza grave**: il numero citato nello screening ("SAR → PF1.52",
riportato in [[NEXUS EA - Screening Strategie (sito 10y)]] e usato per
giustificare il fix HTF di v2.5.0 su SAR) **non dice nulla sulla vera
strategia SAR** (Parabolic SAR + EMA9/EMA21 nel codice MQL5 reale, vedi
[[Sar]]). Il fix è stato applicato sulla base di un test che, di fatto, non
ha mai toccato la logica reale della strategia. Questo spiega ulteriormente
— oltre a quanto già scritto in
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]] — perché SAR resta la
peggiore in assoluto su MT5 (0/6 anni positivi): il fix non era mai stato
testato per davvero, nemmeno sul motore più debole.

## Esecuzione diretta 10y (XAUUSD, D1, dati Yahoo reali, baseline SL1.5/TP3.0 salvo indicato)

| Strategia | Trade | PF | WR% | DD% | Net |
|---|---|---|---|---|---|
| BJORGUM | 27 | 2.47 | 55.6 | 2.97 | +1.929 |
| OB_MIT | 68 | 1.45 | 44.1 | 4.03 | +1.903 |
| TSI | 245 | 1.35 | 40.8 | 10.57 | +6.182 |
| BREAKOUT_ACC | 133 | 1.34 | 39.8 | 10.57 | +2.783 |
| MACD | 68 | 1.38 | 41.2 | 4.96 | +1.647 |
| ADX_RSI | 212 | 1.26 | 39.2 | 11.44 | +3.625 |
| FVG_CONT | 199 | 1.25 | 38.7 | 11.41 | +3.220 |
| ICHIMOKU | 76 | 1.21 | 38.2 | 6.82 | +1.022 |
| ORDER_BLOCK | 86 | 1.18 | 39.5 | 7.78 | +1.049 |
| SAR ⚠️ | 84 | 1.17 | 38.1 | 12.38 | +842 |
| EMA_PULLBACK | 84 | 1.17 | 38.1 | 12.38 | +842 |
| **RSI_DIV** | 75 | 0.85 | 29.3 | 19.40 | -837 |
| **TURTLE_SOUP** | 63 | 0.83 | 30.2 | 10.71 | -716 |
| **CISD** | 18 | 0.99 | 33.3 | 3.03 | -18 |

**SAR = EMA_PULLBACK riga per riga** (vedi scoperta #2). RSI_DIV/CISD/TURTLE_SOUP
erano assenti dallo screening originale — ora coperte, con risultato negativo
o marginale su questo motore.

## Sweep SL/TP/HTF per le 3 strategie mancanti dallo screening (best config trovata)

| Strategia | Migliore config sito 10y | PF | Trade | Nota |
|---|---|---|---|---|
| RSI_DIV | SL1.0 · TP4.5 · HTF off | **1.09** | 79 | Debole ma marginalmente positiva — l'HTF filter non aiuta qui, a differenza della maggior parte delle altre |
| CISD | SL1.5 · TP3.0 · HTF off | **0.99** | 18 | Mai profittevole su nessuna combinazione testata sul sito, campione piccolo |
| TURTLE_SOUP | SL1.5 · TP3.0 · HTF off | **0.83** | 63 | Mai profittevole sul sito, in nessuna combinazione — conferma la divergenza già nota in [[NEXUS EA - Principi]] #5 ("TURTLE_SOUP: 0.77 sul sito, 2.12 su MT5") con un numero fresco molto vicino a quello storico |
| SAR (nota: dato invalidato, vedi sopra) | SL1.0 · TP4.0 · HTF on | 1.50 | 94 | Combacia col numero storico (PF1.52) ma **non è un test di SAR**, è EMA_PULLBACK travestito |

## Cosa questo cambia per il piano di lavoro

1. **CISD e TURTLE_SOUP restano affidabili solo su MT5** — il sito non è uno
   strumento utile per queste due (mai profittevoli lì, in nessuna config).
   Non usarlo per tunarle. La fonte di verità resta il backtest MT5 diretto.
2. **SAR va ri-testata da zero, sia sul sito (fixando il proxy) sia su MT5
   isolata** — al momento non esiste NESSUN test valido della vera logica
   Parabolic SAR, né qui né probabilmente nella giustificazione originale del
   fix v2.5.0.
3. **MACD ha un edge raw positivo confermato anche sul sito** (PF 1.38,
   68 trade, 10 anni) — il problema visto su MT5 (-21.1R) probabilmente non è
   nel segnale stesso ma nell'esecuzione (sizing, spread M15, interazione con
   altri gate). Prioritario un test MT5 isolato di sola MACD
   (`InpStrategySelector`) per separare "segnale sbagliato" da "esecuzione
   sbagliata".
4. Il sito non potrà **mai** validare il nucleo hedge nel suo design attuale
   — non allocare tempo a provarci finché il motore non supporta posizioni
   multiple simultanee.

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Principi]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Hedge nel Tempo]] · [[TODO - Backtest 10Y]] · [[Sar]]
