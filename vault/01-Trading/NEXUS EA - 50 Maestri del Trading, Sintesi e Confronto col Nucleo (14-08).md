---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, metodologia, 50-trader, sintesi]
created: 2026-08-14
updated: 2026-08-14
---

# 50 maestri del trading — sintesi e confronto col nucleo NEXUS (14/08)

Materiale portato dall'utente (sintesi Gemini, 50 trader raggruppati in 5
pilastri, con codice Pine Script d'esempio). Qui non ripeto le biografie —
gran parte delle attribuzioni storiche (es. la regola esatta di Homma nel
1700) sono ricostruzioni/aneddoti, non specifiche verificabili come il
codice che testiamo su NEXUS. Il valore vero è incrociare i 5 pilastri con
quello che il motore ha già, cosa manca davvero, e cosa non si applica
affatto a un EA tecnico su XAUUSD.

## Avvertenza metodologica — NON fondere i pilastri in un unico filtro

Il codice "Master Strategy" fornito combina regime (SMA200) + contrazione
volatilità (VCP) + breakout + volume + candela, tutto in AND. Stesso
pattern già diagnosticato oggi su IFVG_CHOCH_WINDOW (troppe condizioni
simultanee → collasso di frequenza). Ogni pilastro va testato **separato**
prima di considerare una fusione.

## I 5 pilastri vs il nucleo NEXUS

### Pilastro 1 — Trend Following & Breakout
**Già presente**: BREAKOUT_ACC, LONDON_BO (nucleo, funzionano), CRT
(candle-range breakout, Tier A). Il filtro HTF per-strategia
(`NXS_Profile_HTF`) è concettualmente il filtro SMA200/regime di Tudor
Jones, già applicato dove serve.

**Nuovo testato oggi** (Donchian/Dennis, Darvas): vedi sezione risultati
sotto — non promuovibili ancora.

**Non applicabile**: Michael Marcus (leva discrezionale alta, non
sistematizzabile), Louis Bacon (trading su catalizzatori macro/news, NEXUS
non ha un feed fondamentale oltre al calendario ad alto impatto già
usato per il blocco news).

### Pilastro 2 — Price Action e Teoria dell'Asta
**Già presente in modo sostanziale**: l'intero motore SMC/ICT (FVG_CONT,
FVG_MIT, ORDER_BLOCK, OB_MIT, IFVG, LIQ_SWEEP, struttura/CHoCH) **è**
teoria dell'asta applicata — accumulazione/manipolazione/distribuzione di
Wyckoff è letteralmente il modello AMD già nel motore
(`NXS_AMDModel.mqh`). ELLIOTT esiste già (rinominazione in sospeso,
"FIVE_SWING_IMPULSE"). I pattern a candela (corpo forte, rejection) sono
il filtro di base di quasi ogni strategia SMC qui.

**Genuinamente assente**: Market Profile / Value Area / Point of Control
(Steidlmayer) — richiederebbe un vero volume profile, mai calcolato nel
motore. Angoli di Gann — bassa priorità, nessun fondamento statistico
solido dietro, storicamente controverso.

**Non applicabile**: Bob Volman (scalping a 70 tick) — serve tick data
vero, la cache qui si ferma a M15.

### Pilastro 3 — Global Macro & Riflessività
**Quasi tutto non applicabile**: Buffett, Munger, Icahn, Ackman, Templeton
sono investitori value/attivisti su singoli titoli azionari — non
traspongono a un EA tecnico su oro. Soros/Druckenmiller/Dalio (scommesse
su cambi di regime macro/tassi) richiederebbero un feed di dati
intermarket (DXY, tassi reali) che NEXUS non ha oggi — idea già annotata
come "outside the box" il 13/08, mai implementata, stesso ordine di
grandezza di lavoro del Market Profile.

### Pilastro 4 — Quant, Statistica, Rischio
**Kelly Criterion (Thorp)**: NEXUS usa rischio fisso per trade
(`risk_pct`), non size Kelly-ottimale — genuinamente diverso, ma il Kelly
richiede stime stabili di win-rate/payoff che sono instabili fuori
campione: rischioso applicarlo alla lettera, da trattare con cautela se
mai testato.

**Non applicabile**: Simons/Shaw (stat-arb ad alta frequenza, altra classe
di asset/infrastruttura), Black-Scholes/Derman (pricing di opzioni, NEXUS
non tratta opzioni), Taleb (tail-hedge via opzioni OTM, stesso motivo).

**Collegamento reale trovato ieri**: il "Volatility Targeting" descritto
oggi (dimensiona la posizione sull'inverso della volatilità realizzata)
è la stessa idea del Volatility Regime Adapter già scritto in MQL5
(`NXS_EA_VolAdapt_Sample`/`Multipliers`, `NXS_EdgeAdaptive.mqh`) —
**mai collegato**, dormiente da sempre nonostante `InpVolAdapt_Enable=true`
di default. Completarlo ha più senso che costruirne uno nuovo — vedi nota
vault "Incidente Sicurezza e Setup Desktop (13-08)" per l'elenco completo
delle 4 funzionalità dormienti trovate.

### Pilastro 5 — Momentum & Mean Reversion
**Già presente**: TURTLE_SOUP **è** il pattern "Turtle Soup" di Linda
Raschke (falso breakout + reversal) — stesso nome, stesso trader, già nel
nucleo. Il Triple Screen di Alexander Elder (trend settimanale + oscillatore
giornaliero + ingresso orario) è strutturalmente quello che il filtro HTF
multi-timeframe di NEXUS fa già.

**Nuovo testato oggi** (Z-Score breakout): vedi sotto.

**Non applicabile**: CANSLIM/O'Neil-Ryan (crescita utili >25%, criterio
azionario/fondamentale, non ha senso su un CFD su oro).

**Da provare, non ancora fatto**: VCP di Minervini nella sua forma vera
(contrazioni **progressivamente più strette**, non una singola squeeze
come BB_SQUEEZE già nel motore) — raffinamento specifico, diverso da
quello che c'è.

## Risultati dei 3 candidati testati oggi

Tutti e tre condividono lo stesso pattern sospetto: IS debole/marginale
(sotto o appena sopra 1.0), OOS molto forte. **Non è indipendente da
strategia a strategia — è un segnale di regime**: il periodo OOS attuale
(l'ultimo ~40% dei ~3.5 anni scaricati finora, quindi circa l'ultimo anno
e mezzo) è probabilmente un trend forte per l'oro che premia qualunque
breakout-momentum, non un'evidenza di edge specifico delle regole
testate. Stessa disciplina "IS-blind" già usata per scartare
MALAYSIAN_SNR_BREAKOUT l'11/08.

| Strategia | TF | IS pf/n | OOS pf/n | Verdetto |
|---|---|---|---|---|
| DONCHIAN_TURTLE (Dennis) | 4h | 0.97/140 | 1.98/92 | trappola IS-blind |
| DONCHIAN_TURTLE (Dennis) | D1 | 1.84/31 | 2.39/21 | campione troppo sottile |
| DARVAS_BOX (Darvas) | 4h | 0.97/140 | 2.03/89 | trappola IS-blind |
| DARVAS_BOX (Darvas) | D1 | 1.84/31 | 3.84/14 | campione troppo sottile |
| Z_SCORE_BREAKOUT | 4h | 0.99/93 | 2.09/61 | trappola IS-blind |
| Z_SCORE_BREAKOUT | D1 | 5.99/15 | 2.53/4 | campioni entrambi inutilizzabili |

**Nessuno dei tre promuovibile ora.** Prima di scartarli o promuoverli:
riverificare con IS/OOS scambiati (l'attuale periodo OOS diventa IS) e/o
quando il fetch Dukascopy avrà coperto più anni — se il pattern regge solo
nel trend recente, è un artefatto di regime, non edge.

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - Incidente Sicurezza e Setup Desktop (13-08)]] ·
[[NEXUS EA - Strategie Escluse, Analisi Una-ad-Una (11-08)]]
