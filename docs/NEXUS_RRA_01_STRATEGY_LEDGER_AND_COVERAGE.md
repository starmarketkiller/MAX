# NEXUS RRA-01 — Historical Evidence Ledger, Strategy/Variant Map & Coverage

Estende i 7 censimenti di `NEXUS_RRA_01_RESEARCH_RECOVERY_MASTER.md`. Non duplica RI-01: questo è un indice di lettura umana sulle stesse fonti che RI-01 già importa (`phase7_26/*.json` via `ingest.import_phase7_26`) o potrebbe importare (`behavior_lab_v1`, non ancora `contextual_edge_phase1`). Nessun numero qui è stato ricalcolato — tutti provengono dai 7 censimenti.

## 1. Registro storico per famiglia (stato di test, non di implementazione)

Vocabolario addendum: `TESTED_VALID` (edge/fix dimostrato con evidenza diretta) · `TESTED_INCONCLUSIVE` (testato, esito non dirimente) · `TESTED_INVALID` (testato, refutato/negativo) · `PARTIALLY_TESTED` (evidenza parziale, mai un test formale completo) · `NEVER_TESTED` (perimetro censito esplicito, mai letto un outcome) · `UNKNOWN` (non determinabile dagli artifact censiti).

| Famiglia | Stato | Evidenza chiave | Fase/fonte |
|---|---|---|---|
| RECLAIM/SWEEP (H004→H006) | TESTED_INCONCLUSIVE | Discovery SUPPORTED(n=300)→contaminazione post-hoc scoperta→true holdout BORDERLINE (ΔP=0.057<0.15, BUY/SELL incoerenti)→dependence HIGH→**E2 finale, promotion_allowed=false** | Phase5/5.5/6/6.5/6.6 |
| BREAKOUT_ACC | PARTIALLY_TESTED | Defect cross-TF confermato e fissato (7.9E/F/G); post-fix edge validation 7.21: PF1.62, CI95 include zero, concentrazione 133.7% (fallisce), OOS=1 trade perdente | 7.9*, 7.21 |
| ORDER_BLOCK | PARTIALLY_TESTED | Defect confermato con prova diretta (0% overlap pre/post-fix, 7.13), fix validato (7.14) ma residuo non spiegato (7.15/7.16); edge validation 7.22: PF1.86, concentrazione 196.8% (fallisce), OOS=0 | 7.13-16, 7.22 |
| TSI | TESTED_VALID (claim=fix, non edge) | Defect 100% barre D1 divergenti (7.17), fix FIX_CAUSALLY_VALIDATED su trace live (7.18) — **nota: registry edge-validation segna ancora DEFECT_BLOCKED, non riconciliato** | 7.17/7.18 |
| LIQ_SWEEP | TESTED_INCONCLUSIVE | Integrità MQL5 OK ma Python non idoneo per P&L (7.23); dataset pronto con limite (7.24); edge validation 7.25: storico PF1.484, **OOS realmente negativo** (-$539, unico caso del corpus con OOS sufficiente E negativo) | 7.23-25 |
| MACD | TESTED_INVALID | Registry=FAILED; First Serious 3Y=SERIOUS_VALIDATION_FAIL; MACD 80vs40 barre neutro/peggiora | vault, registry |
| SAR | TESTED_INCONCLUSIVE/misto | "Verdetto Definitivo" confermata 4/5 finestre; ma First Serious 3Y=BORDERLINE; H015 external validation Dukascopy FAIL (PF0.61); SAR_LIVE 6y=-34.3R TESTED_INVALID — **3 verdetti diversi su 3 test diversi, non riconciliati** | vault, 7.7A |
| ADX_RSI | TESTED_INVALID | Backtest 6y -15.3R; nota vault: "filtro ADX mai davvero calcolato nonostante il nome" | vault |
| RSI_DIV | TESTED_INCONCLUSIVE (parità) | Registry=FAILED; **confronto 3 motori: TradingView dice perdita, Python-sito dice profitto sullo stesso periodo-ish** — unico caso di disaccordo sul segno stesso | vault "Confronto 3 Motori" |
| CRT | TESTED_INVALID | Costi-dominante confermato, PF 0.08-0.25 con costi reali, DD chiuso 100% | vault, registry FAILED |
| TURTLE_SOUP | TESTED_INVALID | DISATTIVATA, PF mai >0.94 in 9 configurazioni | vault |
| WICK_SWEEP_REV/RECLAIM | TESTED_INVALID | Entry Timing Study (il più rigoroso tick-level del corpus): shadow PF5.80 irrealizzabile, reale PF0.78-0.80 su 4 varianti — **FILONE CHIUSO, IPOTESI REFUTATA** | vault |
| SCALP (BB_FADE/EMA/RANGE_BRK/RSI_SNAP) | TESTED_INVALID | CHIUSO, 5 ingredienti indipendenti, nessuno funziona | vault |
| AMD_CONT / LDN_REVERSAL | TESTED_INVALID | DISATTIVATE, PF sempre <1 | vault |
| LEVEL_CONFLUENCE / LEVEL_REACTION | TESTED_INVALID | CHIUSA, mai sopra pareggio dopo 5 iterazioni stesso giorno | vault |
| VOLATILITY_BREAKOUT_CONFIRMED | TESTED_INVALID | Serious 3Y: n=183, PF0.867, CI95 include zero, FAIL→ARCHIVE | 7.8i |
| FVG_CONT | PARTIALLY_TESTED | Unica strategia che batte Buy&Hold con SELL genuino; defect_status registry=UNKNOWN_REMEDIATION (non chiaro se risolto) | vault, registry |
| IFVG / FVG_MIT / OB_MIT | TESTED_INVALID | Dead-code (redirect NXR disattivato), disattivate per questo motivo, non per esito economico | vault 25-08 |
| MALAYSIAN_SNR | PARTIALLY_TESTED | Corretta M30 PF1.75, mixed su altri TF | vault, registry CANDIDATE |
| SH_BMS_RTO / SMS_BMS_RTO | PARTIALLY_TESTED | v1 più promettente ma campione piccolo, mai formalizzato oltre | vault |
| STRUCT_REACT | PARTIALLY_TESTED | Prima conferma positiva, poi peggiora con filtro Elliott, bloccata da "terzo cancello silenzioso" mai sbloccato per testarla di nuovo | vault |
| EMA_PULLBACK | TESTED_VALID (con riserva) | Walk-forward 4 finestre tutte positive — ma da riverificare dopo il bug InpRiskProfile (non confermato se l'ha toccata) | vault |
| CISD_TRUE | TESTED_INVALID | Non promossa, PF instabile 0.77-2.03 | vault |
| SEQ-0009/0014/0015 (sequence discovery) | NEVER_TESTED | Collasso strutturale (embargo≫gap mediano) blocca l'inferenza PRIMA di qualunque lettura di outcome — categoria distinta da "testato e refutato" | 7.4, 7.5b, 7.6a-e |
| BAR_UPDN, PIVOT_WICK, PMAX, BB_SQUEEZE, SH_BMS_RTO_V2, SILVER_BULLET, RANGE_FADE | UNKNOWN | DEFECT_CONFIRMED per analogia strutturale (stesso pattern di BREAKOUT_ACC pre-fix) ma impatto **non misurato empiricamente** — diverso da ORDER_BLOCK/TSI dove la quantificazione esiste | 7.10 |

## 2. Untested Experiment Registry — gap espliciti (perimetro censito dichiarato)

Perimetro: i 7 censimenti RRA-01 (research_scripts phase2-28, vault/01-Trading, MQL5/Include/NEXUS_v1, caccia trasversale repo). Fuori perimetro: cartelle `vault/01-Trading/Strategie/` (39 file), `TODO/` (3), `_phase4_artifacts/` (27) — non censite, quindi qualunque combinazione lì dentro è `UNKNOWN`, non `NEVER_TESTED`.

| Opportunità | Stato | Meccanismo ipotizzato | Cosa la falsificherebbe |
|---|---|---|---|
| Volume (tick/real) come feature/detector | NEVER_TESTED (non implementato) | Volume anomalo precede breakout/sweep genuini vs falsi | Backtest con volume-filtro vs senza, stesso periodo, stesso detector |
| iFVG (inverse FVG) | NEVER_TESTED (non implementato, solo nome in una nota) | Mitigazione di FVG in direzione opposta come segnale di esaurimento | Implementazione + edge validation come ORDER_BLOCK |
| Divergenza MACD | NEVER_TESTED (non implementato, solo RSI divergence esiste, e duplicata) | Stesso principio di RSI_DIV applicato a MACD | Implementazione + confronto diretto con RSI_DIV sullo stesso periodo |
| Motore di confluenza generico (multi-detector) | NEVER_TESTED (nessun modulo trovato) | Combinare 2+ detector indipendenti aumenta selettività senza aumentare proporzionalmente i falsi positivi | Costruire sopra `candidate_signature.py`/`baseline_engine_v4.py`, testare su una famiglia nota (es. RECLAIM+struttura) |
| Timeframe M1/M5/W1 nella ricerca causale (behavior_lab_v1) | NEVER_TESTED (coperti solo M15/H4) | Stesso detector impulso/pullback potrebbe avere dinamiche diverse a grana più fine/grossa | Estendere `bars.py` a M1/M5/W1, ripetere lo smoke test BL-01 |
| Pattern candlestick come filtro standalone | NEVER_TESTED isolato (solo inline dentro altre strategie) | Engulfing/hammer/shooting star come conferma indipendente, non solo gate interno | Estrarre il modulo, testarlo da solo su un detector esistente |
| 9 strategie DEFECT_CONFIRMED non quantificate (BAR_UPDN, PIVOT_WICK, PMAX, BB_SQUEEZE, SH_BMS_RTO, SH_BMS_RTO_V2, SILVER_BULLET, RANGE_FADE) | UNKNOWN (impatto) | Stesso pattern di contaminazione di BREAKOUT_ACC/ORDER_BLOCK, impatto probabilmente materiale ma non misurato | Applicare il protocollo same-feed A/B/C già rodato (7.9/7.13) a ciascuna |
| g_adx/g_rsi/g_macd non ricalcolati per-pass (nuovo, Fase F) | NEVER_TESTED (appena scoperto, zero quantificazione) | Stesso meccanismo di BREAKOUT_ACC pre-fix: segnali su TF non-canonico leggono indicatori dell'entry-TF | Stesso protocollo A/B/C su ADX_RSI |
| Confluenza prezzo-indicatore come classe propria (oltre le singole strategie) | PARTIALLY_TESTED | `NXS_Reaction.mqh` la implementa ma mai validata isolata | Isolare e testare come le altre feature |

## 3. Coverage Matrix — rappresentazione sparsa (solo combinazioni osservate)

Non materializzata esaustivamente (richiesto dal task). Dimensioni effettivamente incrociate nei dati censiti, con combinazione osservata e esito:

- **BREAKOUT_ACC × D1 × TREND × tutte le sessioni × BUY/SELL × EMA100/20 trend-align × entry-on-break/exit-nativo × Dukascopy+MT5-live × Python+MT5**: PARTIALLY_TESTED, pattern BUY-dominante (66.7%→69.4% post-fix) non distinguibile da trend-alignment (confuso 100% nel campione).
- **ORDER_BLOCK × D1 × (non testato per regime) × tutte le sessioni × BUY-dominante (12/13) × displacement-ATR entry × native SL/TP × MT5-live**: PARTIALLY_TESTED, concentrazione estrema, SELL n=1 non valutabile.
- **LIQ_SWEEP × D1 × (non testato per regime) × tutte le sessioni × direzione non isolata × sweep-reclaim entry × ATR-fisso MQL5 vs dinamico-Python exit (MISMATCH STRUTTURALE) × MT5-only per P&L**: TESTED_INCONCLUSIVE, OOS negativo.
- **RECLAIM × H4 × vol/trend terzili × tutte le sessioni × BUY/SELL separati × sweep+reclaim entry × ATR-normalizzato exit × Dukascopy-Python**: TESTED_INCONCLUSIVE, asimmetria BUY/SELL irrisolta (intero effetto concentrato su un lato).
- **BUY-dominance × 3 strategie (BREAKOUT_ACC/ORDER_BLOCK/LIQ_SWEEP) × D1 × benchmark regime-matched**: TESTED_INCONCLUSIVE/leggermente refutativo — nessuna batte `REGIME_MATCHED_RANDOM_LONG` in modo significativo dopo Bonferroni (7.27).
- **MACD × H4 × tutte le sessioni × Python+MT5+TradingView**: TESTED_INVALID, concorde su tutti e 3 i motori (unico caso di accordo totale).
- **RSI_DIV × H1 × Python(sito)+TradingView**: TESTED_INCONCLUSIVE — disaccordo sul segno stesso del risultato tra motori.

Celle NEVER_TESTED/UNKNOWN strutturalmente più dense di quelle testate: nessuna strategia del corpus è mai stata incrociata sistematicamente per sessione × regime × direzione con potenza statistica sufficiente (n tipico 30-180 per famiglia, spesso <50).

## 4. Test da NON ripetere (evidenza negativa sufficiente)

- CRT (costi-dominante, 2 implementazioni, sempre negativo con costi reali).
- SCALP_BB_FADE/EMA/RANGE_BRK/RSI_SNAP (5 ingredienti indipendenti testati, nessuno funziona).
- TURTLE_SOUP in qualunque configurazione TF/direzione (9 config, mai PF>0.94).
- AMD_CONT, LDN_REVERSAL (testate da zero, mai PF>1).
- LEVEL_CONFLUENCE/LEVEL_REACTION come segnale standalone (5 iterazioni stesso giorno, mai sopra pareggio).
- WICK_SWEEP_REV/RECLAIM in tutte le varianti timing (REV/RECLAIM/RECLAIM_TICK/RECLAIM_LIMIT_RETEST) — il filone più rigoroso del corpus, chiuso con refutazione esplicita.
- SEQ-0015/SEQ-0009 con lo stesso embargo/gap design — non è l'ipotesi a essere refutata, è la combinazione embargo≫gap mediano che collassa l'inferenza: va ridisegnato il design, non ripetuto l'esperimento identico.
