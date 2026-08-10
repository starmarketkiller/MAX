---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, demo, multi-tf, exit-management, mt5]
created: 2026-08-10
updated: 2026-08-10
---

# Config conto demo 3000€, 15 strategie — analisi e stato

Richiesta dell'utente: conto demo con almeno 15 strategie (non solo le 2-3
migliori), ciascuna sul suo timeframe ottimizzato, rischio 5-10%, collegato
al sito per leggere i trade. Prima di configurare l'EA: test per migliorare
drawdown/PF sulle strategie così così, e riconciliazione con la storia di
ottimizzazione MQL5 già esistente.

## Le 15 candidate (dal report di stato ottimizzazione)
BREAKOUT_ACC, TURTLE_SOUP, MACD (buone) · LONDON_BO, FVG_MIT, LIQ_SWEEP,
AMD_CONT, FVG_CONT, TSI, ADX_RSI, SAR, EMA_PULLBACK (così così/benino) ·
THREE_BAR_DELIVERY_BREAK, LDN_REVERSAL, AMD_REVERSAL (potenziale, campione
ancora piccolo). Escluse le "rare per design" (troppo poco storico per
dire qualsiasi cosa, verificato più volte oggi) e le CRITICA pure.

## Scoperta: esiste già un secondo layer di ottimizzazione MQL5 (15/07-v2.5.1)
`NXS_StrategyProfiles.mqh` contiene profili per-strategia (SL/TP, HTF,
breakeven, trailing, timeframe, rischio %, enable/disable) da un ciclo di
ricerca precedente basato su sweep sito (Yahoo) **e test reali su MT5 con
broker vero** (fino a 1.496 trade/strategia su 10 anni). Non va ignorato o
sovrascritto dai soli dati di oggi.

**Bandiera rossa importante**: MACD, RSI_DIV e FVG_CONT sono confermate
solide sia sul sito Yahoo sia (dopo fix bug proxy) con la logica vera —
eppure su MT5 reale, campione enorme, sono risultate **CRITICA** (PF
0.51-0.88). Tre casi indipendenti nella stessa direzione fanno sospettare
un problema di **esecuzione MT5** (spread/sizing/gate), mai risolto (vedi
[[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]]). MACD è una delle
3 "buone confermate" di oggi (Python, storico Dukascopy pieno, OOS PF
1.63) — il buon risultato su Python **non garantisce** l'esecuzione reale.

**Decisione**: MACD e FVG_CONT entrano nel demo a rischio ridotto rispetto
alle altre 13, non al 5-10% pieno, finché l'esecuzione reale non conferma
o smentisce quanto trovato oggi — è esattamente il test isolato con
logging spread/sizing che il documento di luglio raccomandava e non è mai
stato fatto.

## Scan multi-TF completo (35 strategie × 15m/30m/1h/4h/1d, bars=70000)
Ipotesi dell'utente ("più trade e migliori sui TF bassi") **mezza vera**:
frequenza sì (MACD 21→1410 trade passando da 1d a 15m), qualità **al
contrario** — il PF OOS migliore è quasi sempre su 1d/4h, non su 15m. Sui
TF bassi molte strategie a campione enorme hanno PF mediocre/negativo
(BJORGUM 0.89/1043, BOLLINGER 1.01/1148, RSI_DIV 0.94/377) — più rumore,
non più edge.

**Due scoperte solide** (PF buono E campione ampio, timeframe diverso dal
default 4h): **AMD_CONT su 30m** (PF 1.52, 169 trade) ed **EMA_PULLBACK su
1h** (PF 1.54, 124 trade) — promosse al nuovo timeframe per il demo.

**Tre "vistose ma su campione piccolo" (MACD/TURTLE_SOUP/BREAKOUT_ACC su
1d, PF 2.1-3.2 su 20-33 trade)** — verificate con walk-forward a 5
finestre prima di fidarsene, stesso trattamento di tutto il resto oggi:

| Strategia | 1d (range PF, n/finestra) | 4h (range PF, n/finestra) |
|---|---|---|
| MACD | 0.0-3.86, **1-6 trade** | 0.98-1.63, 45-57 trade |
| TURTLE_SOUP | 0.42-8.64, 11-21 trade | 0.75-2.59, 43-58 trade |
| BREAKOUT_ACC | 0.33-4.45, 7-13 trade | 0.94-1.78, 44-56 trade |

**Smentito**: il PF alto su 1d era rumore da campione minuscolo (1-21
trade a finestra, altalena da quasi-zero a 8.64) — non un edge reale, la
stessa trappola di LDN_REVERSAL/AMD_REVERSAL di oggi. Il 4h resta stabile
su tutte le finestre per tutte e tre. **MACD/TURTLE_SOUP/BREAKOUT_ACC
restano su 4h nel demo**, non passano a 1d.

## Test isolato exit-management (breakeven/trailing/TP dinamico), 15 strategie
Una leva alla volta, selezione IS-blind, verifica OOS — non mescolato con
SL/TP come la griglia di Fase 3.

**13 delle 15**: nessuna leva batte il default (0/False scelto su tutte e
3 le leve, anche sull'in-sample) — conferma Fase 3, la gestione d'uscita
non aiuta quando SL/TP sono già ben tarati.

**4 casi con valore scelto sull'IS ma smentiti sull'OOS** (LIQ_SWEEP
dynamic_tp, THREE_BAR_DELIVERY_BREAK/LDN_REVERSAL/AMD_REVERSAL trailing) —
scartati correttamente dallo script, nessun falso positivo passato.

**1 solo "aiuta" apparente**: FVG_MIT + breakeven 0.5R (OOS PF 1.52→4.23,
49 trade) — ma scelto sull'IS come "il meno peggio" di una griglia tutta
in perdita (IS PF 0.39, baseline IS già debole a 0.68). Walk-forward a 5
finestre: **smentito**, BE0.5 peggiora in 4 finestre su 5 (script
`fvgmit_be_walkforward.py`). Il PF 4.23 era concentrato in una fetta
fortunata dello split 60/40.

**Conclusione onesta**: nessuna delle 15 candidate ha un miglioramento
credibile da breakeven/trailing/TP dinamico isolati. Il default (SL 1.5×
ATR / TP 3.0× ATR, nessuna gestione d'uscita aggiuntiva) resta il
migliore su tutte, confermando via IS/OOS + walk-forward quanto la Fase 3
aveva già suggerito con la griglia combinata.

## Filtro di regime esteso (6 candidate senza test precedente)
Solo **FVG_CONT + STRONG+WEAK_TREND** aiuta davvero (OOS PF 1.26→1.32, 91
trade, campione affidabile). AMD_CONT, EMA_PULLBACK, THREE_BAR_DELIVERY_BREAK
peggiorano o sono invariate; LDN_REVERSAL/AMD_REVERSAL non hanno scelto
nessun filtro sull'IS. Confermato: non è una leva universale.

## Timeframe finale proposto per il demo (15 strategie)
4h (default, invariato): MACD*, TURTLE_SOUP, BREAKOUT_ACC*, LONDON_BO,
FVG_MIT, LIQ_SWEEP, FVG_CONT*, TSI, THREE_BAR_DELIVERY_BREAK.
30m: AMD_CONT. 1h: EMA_PULLBACK. 1d: ADX_RSI, SAR (coerente col profilo
MT5 reale già esistente). 15m: LDN_REVERSAL, AMD_REVERSAL (campione più
solido lì secondo lo scan).
*MACD e FVG_CONT a rischio ridotto per la bandiera rossa storica MT5
sopra, non per un problema trovato oggi.

## Config implementata in `NXS_StrategyProfiles.mqh` (commit 78bb300)
- AMD_CONT/LDN_REVERSAL/AMD_REVERSAL: profilo nuovo (TF dallo scan, SL/TP
  default, rischio prudente 0.4-0.5%).
- EMA_PULLBACK: TF H4→H1.
- MACD: rischio 1.5%→0.5% (bandiera rossa storica MT5).
- FVG_CONT: rischio 0.4% confermato (era già prudente).
- `NXS_Profile_Enabled()`: diventa il gate esplicito delle 15 — le altre
  20 spente. Attivo solo dietro `InpUseStrategyProfiles=true` (non
  esposto come `input`, quindi sempre attivo per ora — nota aperta).

## Cap di rischio aggregato (richiesto dopo la config, 10/08)
`InpMaxConcurrent` limita solo il NUMERO di posizioni, non la somma del
rischio — con 15 strategie indipendenti (fino al 3% ciascuna) che possono
aprire sulla stessa barra, l'esposizione reale può superare di molto il
rischio "per trade" nominale (vedi anche la discussione sul conto 3000€
in questa stessa conversazione). Implementato:
- `NXS_OpenRiskPct()` (`NXS_Globals.mqh`) — somma la distanza SL-prezzo
  ATTUALE (non il rischio storico all'apertura, quindi una posizione già
  a breakeven pesa meno) su tutte le posizioni NEXUS aperte, come % 
  dell'equity corrente.
- `InpMaxAggregateRiskPct` (`NXS_Inputs.mqh`, default 15.0, 0=disattivo).
- Gate in `NXS_CheckProtections()` (`NXS_Risk.mqh`): un nuovo ingresso
  viene rifiutato (reason="aggregate_risk_cap") se il rischio già aperto
  è al tetto o oltre — reject esplicito, non un clamp silenzioso della
  size, stesso principio di AUD0-RISK-002/003.

## Prossimo passo
Config demo completa lato codice. Resta da decidere se rendere
`InpUseStrategyProfiles` `input` (per poter tornare a "tutte e 35" via
.set senza ricompilare) — non urgente se il demo è l'unico uso previsto
per ora.

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - Ricerca Combinazioni Multi-Strategia (10-08)]] ·
[[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]] ·
[[NEXUS EA - MALAYSIAN_SNR Porting Tier 1 (Specifica Tecnica)]]
