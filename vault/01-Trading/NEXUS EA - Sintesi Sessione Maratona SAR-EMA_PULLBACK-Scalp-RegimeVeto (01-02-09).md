---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, sar, ema_pullback, scalp, regime-veto, risk-shield, sintesi]
created: 2026-09-02
updated: 2026-09-02
---

# NEXUS EA — Sintesi sessione maratona (01-02/09): SAR, EMA_PULLBACK, scalp, veto di regime

## Perché questa nota

Sessione lunghissima (dalle 05:30 del 01/09 fino a sera del 02/09, con
molti filoni intrecciati). Nota di sintesi per non perdere il filo — se
cerchi "qual è la config giusta per SAR/EMA_PULLBACK" o "cosa abbiamo
provato per lo scalp", parti da qui.

## ⭐ SAR — configurazione confermata (la più solida di tutta la sessione)

**Verificata direttamente sui 5 report reali il 02/09** (non a memoria —
importante perché nel corso della notte è stata scambiata per errore con
un'altra config a lotto fisso, vedi sotto):

- Strategia: SAR (selettore 4), **timeframe H4 nativo**
- Filtro: `InpSAR_RequireCandleAlign=true` — candela H4 di ingresso
  allineata alla direzione del segnale (trovato il 31/08 analizzando 112
  trade nudi: vincenti allineati 69% delle volte, perdenti 46%, quasi
  casuale)
- **Lotto: NATURALE a rischio%, NON fisso** (nessun `InpUsePipSeq`)
- Rischio/SL/TP: default del profilo (1.0% / 1.0×ATR / 6.0×ATR)
- Tutti gli altri filtri disattivati per l'isolamento (cooldown, max
  loss, auto-close, trailing, Elliott, anti-revenge)

| Punto di partenza | Trade | PF | Netto | DD bilancio/equity |
|---|---|---|---|---|
| Nov 2025 | 94 | 1.45 | +$1451.17 | $767.62/$805.46 |
| Dec 2025 | 89 | 1.43 | +$1324.65 | $714.93/$738.05 |
| Feb 2026 | 58 | 1.37 | +$648.44 | $404.78/$688.03 |
| Apr 2026 | 42 | 1.52 | +$628.92 | $273.93/$305.45 |
| Giu 2026 | 30 | 1.57 | +$481.02 | $273.93/$301.32 |

**Tutti e 5 i punti positivi**, PF 1.37-1.57, coerente su tutta la
finestra temporale (nov2025-ago2026). Questa è LA configurazione
confermata di SAR, da non toccare senza una scoperta forte e verificata
sul motore vero.

**Nove raffinamenti tentati sopra questa base, TUTTI falliti dal vivo**
(SLReclaim, risk scaling, stop stretto 0.85xATR, pressione+candela,
breakeven, partial-take, ProfitReclaim v1/v2/v3) — l'edge di SAR dipende
dal lasciare correre i vincenti fino al TP largo (6xATR), qualunque cosa
tagli quella coda peggiora il risultato. Vedi
[[NEXUS EA - Spoglia e Reintegra su SAR, Filtro Candela H4 Trovato e Validato (30-31-08)]]
per il dettaglio dei 9 tentativi.

**Decimo tentativo (02/09, sera): parziale a soglia pip FISSA invece che
ATR** — nuovo meccanismo `NXS_ManageFixedPipPartial` (mai provato prima,
richiesto esplicitamente dall'utente: lotto 0.02, chiudi metà a +150 pip
fissi, lascia correre il resto). Testato sull'intera finestra
nov2025-ago2026 (step39): 99 trade, PF1.46, netto $2467.70, DD equity
$1438.97, Sharpe 1.66 — contro un raddoppio "ingenuo" del solo lotto
(senza parziale) che avrebbe dato circa netto $2900 e DD proporzionale.
**Stessa conclusione dei 9 tentativi precedenti**: anche con soglia pip
fissa (non ATR), tagliare metà posizione in anticipo rende peggio del
semplice raddoppio del lotto senza toccare nulla — Sharpe peggiora
(2.01→1.66), DD equity cresce più che proporzionalmente. L'edge di SAR
resta legato a lasciare correre l'intera posizione fino al TP.

### ⚠️ Errore corretto durante la notte: lotto fisso 0.05 vs lotto naturale

A un certo punto ho usato per sbaglio un file di test (`step20`) che
aveva `InpUsePipSeq=true, InpPipSeqLot=0.05` — un ESPERIMENTO A PARTE
(lotto fisso, mai la config validata) per verificare la fragilità del
lotto fisso già nota da prima (interagisce male con i gate di margine).
Su quella config sbagliata, la finestra gennaio-aprile 2026 sembrava un
disastro (-$1159.87, 34/41 perdenti) — un artefatto della fragilità del
lotto fisso, NON un problema della config reale. Sulla config vera
(lotto naturale), la stessa area temporale (nov2025-feb2026, include
anche uno streak di 8 perdite consecutive 23-30/12) è **positiva**:
+$906.68, 10/29 vincenti. **Lezione**: verificare SEMPRE quale file di
config si sta usando prima di trarre conclusioni — specialmente dopo
una sessione lunga con molti file simili.

## EMA_PULLBACK — baseline solido, nessun filtro trovato migliora

- Baseline pulito (senza filtri): **PF1.41, netto $677.24**, 80 trade
  (ott2023-ago2026, tick reali M15)
- Filtro pressione 2h allineata (trovato su campione piccolo): si
  modera molto su campione esteso (PF3.11→1.39 circa), non un vero
  filtro
- Filtro allineamento candela: rumore puro per questa strategia
  (diversamente da SAR)
- **Analisi MFE profonda**: i vincenti catturano il 96% (mediana) del
  proprio picco di profitto flottante — il take-profit funziona bene.
  10 perdenti su 48 avevano toccato oltre $25 di profitto flottante
  prima di girare in perdita (stesso fenomeno "regala il picco" di SAR,
  ma qui minoritario)
- Grafico prezzo/bilancio/equity confrontabile pubblicato come artifact
  (vedi file locale `emapb_price_equity_page.html`)

**Verdetto**: EMA_PULLBACK è già robusto così com'è, non ha bisogno di
filtri aggiuntivi (a differenza di SAR che aveva bisogno del filtro
candela per stabilizzarsi).

## Scalp: BAR_UPDN e BREAKOUT_ACC — entrambe fallite

Vedi [[NEXUS EA - Ricerca Scalp BAR_UPDN e BREAKOUT_ACC, Piano BOLLINGER+RSI (02-09)]]
per il dettaglio completo. In sintesi:

- **BAR_UPDN** (pattern price-action puro, M15): PF0.72 nudo, PF0.77
  col raffreddamento anti-inseguimento — non abbastanza
- **BREAKOUT_ACC sbloccata da D1 a M15**: PF0.64, stesso esito
- **Bug trovato** (ipotesi dell'utente, confermata): nessuno stato "già
  tradato questo pattern" in entrambe — il motore inseguiva lo stesso
  trend riaprendo ripetutamente. Corretto con raffreddamento a N barre,
  miglioramento solo marginale — non era la causa dominante
- **Pattern MFE/giveback presente anche qui**: stesso fenomeno di
  SAR/EMA_PULLBACK
- **Piano non ancora eseguito**: BOLLINGER + RSI + candela di conferma
  (mean-reversion, archetipo mai provato — BAR_UPDN e BREAKOUT_ACC erano
  entrambe continuazione). BOLLINGER esiste già nel motore (D1, PF1.17)
  ma bloccata dal terzo cancello (vedi sotto)

## Scoperte strutturali (bug, non idee di trading)

### Il "terzo cancello" NXS_Profile_Enabled

Whitelist separata da `InpStrat_X` e da `InpStrategySelector` —
`NXS_Profile_Enabled(name)`, attiva quando `InpUseStrategyProfiles=true`
(default). Se una strategia non è esplicitamente nella whitelist, viene
rifiutata in silenzio (`profile_disabled`), **zero trade senza errori
visibili**, a prescindere da come la selezioni. Solo 21 delle 48
strategie del motore erano abilitate. Sbloccate stanotte: BB_SQUEEZE,
ORDER_BLOCK (per test). **BOLLINGER risulta ancora bloccata** — da
sbloccare prima di testarla. Bug della stessa famiglia già trovato il
28/08 per PMAX/BAR_UPDN ecc. — **controllare sempre questo cancello
PRIMA di concludere che una strategia non ha segnali**.

### RiskShield EQUITY_BREAKER reso per-strategia

Bloccava tutto il conto quando UNA strategia aveva Sharpe basso su 50
trade. Richiesto dall'utente esplicitamente ("vorrei bloccare solamente
la strategia in questione"). Refattorizzato: `NXS_RS_Breaker_Check` è
ora una funzione pura, `NXS_RS_Breaker_Update` calcola lo Sharpe
separatamente per strategia (parsing dal commento del deal). I 4 call
site di `NXS_CommonExposurePreflight` (PRIMARY/GRID/PYRAMID/INST)
aggiornati per passare `stratName`. **Non testato ancora in produzione**
(in isolamento singola-strategia non cambia nulla per costruzione).

### Veto di regime — esisteva già, mai collegato al percorso usato stanotte

`_nxs_regime_veto()` in `NXS_SignalQuality.mqh`: scarta segnali
mean-reversion (BOLLINGER, BB_SQUEEZE, RANGE_FADE, RSI_DIV,
MALAYSIAN_SNR) in regime STRONG_TREND, e segnali trend-follow (tra cui
**SAR**, ADX_RSI, MACD, TSI, EMA_PULLBACK, ICHIMOKU, BJORGUM,
BREAKOUT_ACC, LONDON_BO) in regime RANGING/CHOPPY. Era agganciato SOLO
al modello istituzionale (`InpUseInstitutionalCore`, off di default, mai
usato in nessun test isolato). Collegato stanotte anche al percorso a
profili con un nuovo flag dedicato `InpProfileRegimeVeto` (off di
default, opt-in per test) in `NXS_OpenTrade`.

**Test preliminari fatti PRIMA di scoprire l'errore del lotto fisso**
(quindi da rifare sulla config vera a lotto naturale, non ancora
verificati):
- Solo veto, finestra gen-apr 2026 (lotto 0.05 fisso, ora sappiamo
  sbagliato come baseline): tagliava 12/41 trade, PF2.02, +$4393
- Veto + parziale insieme: PF1.85, +$7291 su 89 trade
- Questi numeri sono inquinati dal lotto fisso fragile — **da
  riverificare sulla config a lotto naturale prima di trarre conclusioni**

**Errore scoperto due volte**: anche il test "step35_clean_veto" (nome
scelto per indicare "grid/pyramid/split disattivati per isolare l'effetto
veto") aveva ANCORA `InpUsePipSeq=true, InpPipSeqLot=0.05` — "clean" non
si riferiva al lotto. Quindi **nessuno dei due test veto sopra è mai
stato fatto sulla config reale**. Lanciati la sera del 02/09 step40
(baseline vera, lotto naturale, stessa finestra 12gen-12apr26) e step41
(stessa finestra con `InpProfileRegimeVeto=true`) per il confronto
finalmente pulito.

### Risultato finale (pulito): il veto non taglia NIENTE su questa finestra

step40 (baseline) vs step41 (veto attivo), stessa finestra 12gen-12apr26,
lotto naturale: **32 trade in entrambi, PF1.50 in entrambi, netto
$750.66 vs $752.24** (differenza $1.58, trascurabile). Zero trade
tagliati dal veto.

Verificato nel codice che non è un bug di wiring: `_nxs_regime_veto()`
legge `g_regime`, calcolato ad ogni tick da `NXS_DetectRegime()`
(`NXS_MarketAnalysis.mqh`) in base all'ADX sul TF di SAR (H4) — RANGING/
CHOPPY solo con ADX sotto 15-20 (più una condizione di volatilità per
CHOPPY). Il veto è correttamente collegato e correttamente valutato per
tutti e 32 i trade, ma la condizione non si è mai verificata: nella
peggior serie di perdite di SAR l'ADX H4 a quanto pare non è mai sceso
abbastanza da classificare il mercato come ranging/choppy.

**Conclusione**: quella serie di perdite probabilmente non nasce da un
mercato piatto misclassificabile con l'ADX, ma da falsi breakout dentro
un trend/volatilità che l'ADX considera comunque "sano". Il veto di
regime così com'è costruito (solo ADX) **non risolve questo problema
specifico** per SAR — filone chiuso, non abbandonato a metà: il
meccanismo funziona, semplicemente non è la leva giusta per questa
sequenza di perdite.

## Prossimi passi (in ordine)

1. **Riverificare il veto di regime su SAR con la config VERA** (lotto
   naturale, non 0.05 fisso) — i numeri di cui sopra sono inquinati e
   vanno rifatti da capo. Buona notizia: la config vera è già solida
   ovunque (nessuna finestra catastrofica come quella trovata per
   sbaglio a lotto fisso), quindi il test andrà giudicato su un
   miglioramento più sottile (taglia trade in regime sbagliato senza
   toccare i vincenti grossi?), non su un salvataggio da una crisi che
   in realtà non esiste sulla config reale.
2. Sbloccare BOLLINGER dal terzo cancello e testarla come base per lo
   scalp mean-reversion (as-is prima, poi con RSI+candela di conferma
   se promettente)
3. Aggiungere SAR e BAR_UPDN/BREAKOUT_ACC alle liste di classificazione
   di `_nxs_regime_veto` se mancanti (verificare — BAR_UPDN non
   risultava classificata quando controllato)
4. WEEKLY_EXP — non ancora iniziata (task tracciato separatamente)
5. Cross-strategy: confronto grafico prezzo/bilancio/equity per SAR
   (fatto per EMA_PULLBACK, non ancora per SAR)

## Lezione meta della sessione

Tre volte stanotte un numero sorprendente (positivo o negativo) si è
rivelato un artefatto di una config diversa da quella che si pensava di
star testando — non un vero risultato:
1. ATR sbagliato (M15 invece di H4) nel meccanismo di split-trade
2. ReconcileBroker mai chiamata nel Tester → stato sempre sul fallback
3. Lotto fisso 0.05 scambiato per la config validata di SAR

**Prima di reagire a un numero sorprendente, ricontrollare sempre quale
file/configurazione l'ha prodotto**, non solo se il numero è plausibile.
