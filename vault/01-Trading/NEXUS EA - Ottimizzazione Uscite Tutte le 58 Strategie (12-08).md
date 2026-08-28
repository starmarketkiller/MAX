---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, exit-management, censimento, tutte-le-strategie]
created: 2026-08-12
updated: 2026-08-12
---

# Ottimizzazione uscite — tutte le 58 strategie (12/08)

Richiesta esplicita dell'utente: estendere la ricerca SL/TP/breakeven/
trailing fatta per CRT/FVG_CONT a **tutte** le strategie, nucleo e non.
`research_scripts/exit_optimizer_all_strategies.py`, interrotto una volta
dal riavvio del container e ripreso senza perdite (salvataggio
incrementale — 44/58 già salvate su disco al riavvio).

## ATTENZIONE — la griglia di massa è più grezza di quella dedicata

Per stare in un tempo ragionevole su 58 strategie (vedi collaudo tempi:
CRT 30m/griglia piena 7m38s, un solo caso da 15m con griglia piena
50m6s), la griglia è stata dimezzata su ogni asse: SL∈{1.0,2.0} (non più
1.5), TP∈{3.0,6.0} (non più 4.5), BE∈{0,1.5} (non più 1.0), trail∈{1.5,3.0}
(non più 1.0), HTF∈{True,False}.

**Confermato che questo fa perdere il vincitore migliore, non solo in
teoria**: per CRT e FVG_CONT avevamo già una ricerca dedicata con griglia
piena (vedi [[NEXUS EA - Ottimizzazione Uscite Strutturali CRT e FVG_CONT (12-08)]]).
Confronto diretto:

| Strategia | Batch (griglia grezza) | Ricerca dedicata (griglia piena) |
|---|---|---|
| CRT | pf 1.25→1.31, dd 36.73→34.39% | **pf 1.25→1.39, dd 36.73→28.05%** (be=1.0+trail=1.0) |
| FVG_CONT | pf 1.55→1.56, dd 13.41→16.97% | **pf 1.55→1.74, dd 13.41→7.06%** (sl1.5/tp6.0/be1.5, htf=True) |

Per queste due, **usa i numeri della ricerca dedicata**, non quelli del
batch — il batch li ha letteralmente mancati (SL=1.5 e TP=4.5 non erano
nella sua griglia ridotta). Per le altre 56, non esiste una ricerca più
fine con cui confrontare: il risultato del batch è il miglior dato
disponibile, ma va trattato come **una rosa di candidati da verificare
meglio prima di portare in MQL5**, non un numero definitivo — lo stesso
principio, non ancora applicato a tutte.

## Risultato aggregato

| Esito | N | Strategie |
|---|---|---|
| Migliorato | 19 | vedi tabelle sotto |
| Nessun miglioramento | 26 | AMD_CONT, AMD_REVERSAL, BJORGUM, BREAKOUT_ACC, FVG_CONT_V2, FVG_MIT, ICHIMOKU, LDN_REVERSAL, LIQ_SWEEP, LONDON_BO, MALAYSIAN_SNR_BREAKOUT, MALAYSIAN_SNR_V2_RETEST, MALAYSIAN_SNR_V2_RETEST_OUTRANGE, MALAYSIAN_SNR_V2_STAGE1, MALAYSIAN_SNR_V2_STAGE3, NY_REVERSAL, ORDER_BLOCK_V2, PO3, RSI_DIV, SCALP_RANGE_BRK, SCALP_RSI_SNAP, SILVER_BULLET, STRUCT_REACT, THREE_BAR_DELIVERY_BREAK, TURTLE_SOUP, TURTLE_SOUP_CHOCH |
| Troppo sottile (IS<15 trade) | 13 | BB_SQUEEZE, DISP_REBAL, IFVG, IFVG_CHOCH_WINDOW, JUDAS_SWING, MALAYSIAN_SNR, OB_MIT, ORDER_BLOCK, OTE_CONT_V2, SILVER_BULLET_V2, SMS_BMS_RTO, SMS_BMS_RTO_CHOCH_WINDOW, WEEKLY_EXP |

## Le 19 migliorate — divise per affidabilità del campione

### Campione robusto (OOS n≥100) — le più credibili

| Strategia | TF | Config vincente | PF OOS | DD OOS | n |
|---|---|---|---|---|---|
| CRT* | 30m | be=1.0 trail=1.0 (dedicata) | 1.25→1.39 | 36.73→28.05% | 5032 |
| FVG_CONT* | 4h | sl1.5/tp6.0/be1.5/htf=True (dedicata) | 1.55→1.74 | 13.41→7.06% | 127 |
| SCALP_BB_FADE | 15m | sl1.0/tp6.0/be0/htf=False/trail3.0 | 0.90→1.04 | 57.03→49.64% | 1248 |
| SCALP_EMA | 15m | sl2.0/tp6.0/be0/htf=True/trail3.0 | 0.88→1.14 | 68.49→29.05% | 1037 |
| EMA_PULLBACK | 1h | sl1.0/tp6.0/be0/htf=True/trail3.0 | 1.16→1.67 | 14.61→**18.43%** ⚠️ | 212 |
| MACD | 4h | sl1.0/tp6.0/be0/htf=False/trail3.0 | 1.31→1.72 | 8.8→**15.52%** ⚠️ | 185 |
| SAR | 4h | sl2.0/tp6.0/be0/htf=True/trail3.0 | 1.44→1.58 | 8.99→8.71% | 176 |
| LIQ_VOID | 4h | sl1.0/tp6.0/be0/htf=False/trail3.0 | 1.55→1.56 | 13.41→16.97% | 178 |
| SH_BMS_RTO_V2 | 1h | sl1.5/tp3.0/be0/htf=True/trail3.0 | 1.28→1.37 | 13.22→11.87% | 148 |
| FVG_MIT_WINDOW | 4h | sl1.5/tp3.0/be0/htf=True/trail3.0 | 1.06→1.22 | 16.77→11.63% | 129 |

\* CRT/FVG_CONT: numeri della ricerca dedicata, non del batch (vedi sopra).
⚠️ EMA_PULLBACK e MACD migliorano il PF ma **peggiorano il drawdown** —
stesso trade-off già visto su FVG_CONT prima della scoperta dell'overlay:
PF più alto non è automaticamente "meglio", dipende da cosa si
ottimizza. Non portare senza guardare anche la walk-forward per intero.

**LIQ_VOID = FVG_CONT identico** (stessi numeri esatti) — non un bug di
oggi, è la relazione proxy già nota (LIQ_VOID eredita il segnale di
FVG_CONT, vedi vault "Giro veloce completato (11-08)"). Non è una
seconda conferma indipendente, è la stessa strategia contata due volte.

### Campione sottile (OOS n<100) — solo un indizio, non una conclusione

| Strategia | n | PF OOS | Lettura |
|---|---|---|---|
| SH_BMS_RTO | 8 | 1.74→2.09 | Troppo pochi trade per qualunque conclusione |
| OTE_CONT | 9 | 2.32→3.22 | Idem — PF "3.22" su 9 trade è rumore, non edge |
| SH_BMS_RTO n=8, OTE_CONT n=9 | | | entrambe sotto la soglia minima usata altrove in sessione (50) |
| TSI | 21 | 1.35→2.60 | Interessante (TSI è un "problema aperto" del nucleo) ma il campione è troppo piccolo per chiudere la questione — da riverificare con griglia dedicata |
| ADX_RSI | 24 | 1.77→1.93 | Miglioramento modesto, campione ancora sottile per il D1 |
| TSI_EXTREME | 22 | 0.40→0.65 | Resta sotto pareggio anche dopo il miglioramento |
| NY_REVERSAL_CHOCH_WINDOW | 38 | 0.75→1.32 | Da riverificare |
| BOLLINGER / RANGE_FADE | 45 | 0.67→0.76 | **Stessi numeri identici tra le due** — altra coppia proxy nota, non due conferme |
| CISD_TRUE | 94 | 0.78→1.06 | Al limite della soglia, il miglioramento di drawdown (31%→11%) è comunque marcato |

## Cosa NON è cambiato

Le 26 "nessun miglioramento" includono 5 del nucleo attuale
(AMD_CONT, AMD_REVERSAL, BREAKOUT_ACC, LDN_REVERSAL, LIQ_SWEEP, LONDON_BO,
TURTLE_SOUP — la loro configurazione attuale resta la migliore trovata,
nessuna azione richiesta) e RSI_DIV/STRUCT_REACT/THREE_BAR_DELIVERY_BREAK
tra le altre — nessuna sorpresa, coerente con le diagnosi già fatte in
sessione per questi problemi aperti.

## Prossimi passi consigliati

1. **TSI** merita una ricerca dedicata a griglia piena (come CRT/FVG_CONT)
   prima di chiunque altro — è un "problema aperto" del nucleo, e questo
   giro (per quanto sottile) è il primo segnale di miglioramento mai
   trovato.
2. Le 10 robuste vanno guardate una per una prima di portare qualunque
   cosa in MQL5 — specialmente MACD/EMA_PULLBACK per il trade-off DD.
3. Le 13 "troppo sottili" non sono chiuse — sono strategie con un
   campione IS insufficiente persino per la griglia grezza, non
   necessariamente senza edge.

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - Ottimizzazione Uscite Strutturali CRT e FVG_CONT (12-08)]]
