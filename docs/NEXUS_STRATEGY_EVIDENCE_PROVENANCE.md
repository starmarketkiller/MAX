# NEXUS — PROVENIENZA DEI RISULTATI STORICI PER STRATEGIA

> Fase A, punto 7. **Documento generato** da `contracts/gen_strategy_docs.py`.
> Non contiene giudizi: solo da dove viene ogni numero.

| | |
|---|---|
| Round corrente | `sweep37-baseline-e6ce816` |
| Strategie live | 37 |
| Misurate sul round corrente | **8** |
| Con dato surrogato (altro round) | **1** |
| Mai misurate | **28** |

## I tre stati

| Stato | Significa | Si puo' usare per… |
|---|---|---|
| `MEASURED` | passata isolata completata sul round corrente, con `run_id` | confrontare il comportamento del trigger dentro la stessa campagna |
| `SURROGATE` | esistono numeri, ma di un altro round | **niente che riguardi il codice attuale** |
| `UNKNOWN` | nessuna passata isolata | niente: assenza di misura, non misura di assenza |

Avvertenza che accompagna **tutti** i numeri, presa dal knowledge base e non
riscritta:

> PF/WR/expectancy del round corrente: strategia ISOLATA, lotto fisso 0.01, DataCollectionMode - misurano il comportamento del trigger, non il P&L di portafoglio

Misurano il **comportamento del trigger** isolato a lotto fisso. Non sono un
edge, e non sono il P&L di portafoglio.

---

## Round corrente — 8 strategie

| Strategia | Trade | WR % | PF | Exp. R | run_id |
|---|---|---|---|---|---|
| `MACD` | 1244 | 55.95 | 0.79 | -0.038 | `sweep37-baseline-e6ce816__S03__MACD__20260718_205653` |
| `ADX_RSI` | 915 | 48.55 | 0.82 | -0.028 | `sweep37-baseline-e6ce816__S01__ADX_RSI__20260718_161350` |
| `TSI` | 839 | 54.86 | 0.76 | -0.028 | `sweep37-baseline-e6ce816__S05__TSI__20260719_022556` |
| `BJORGUM` | 397 | 49.02 | 0.68 | -0.071 | `sweep37-baseline-e6ce816__S06__BJORGUM__20260719_052449` |
| `LIQ_SWEEP` | 292 | 50.0 | 1.04 | 0.004 | `sweep37-baseline-e6ce816__S07__LIQ_SWEEP__20260719_080122` |
| `FVG_CONT` | 251 | 45.85 | 0.96 | -0.013 | `sweep37-baseline-e6ce816__S08__FVG_CONT__20260719_193743` |
| `BREAKOUT_ACC` | 216 | 47.59 | 0.85 | -0.024 | `sweep37-baseline-e6ce816__S09__BREAKOUT_ACC__20260720_184509` |
| `BOLLINGER` | 144 | 55.14 | 0.79 | -0.033 | `sweep37-baseline-e6ce816__S02__BOLLINGER__20260718_190107` |

---

## Dato surrogato — 1 strategia

```text
strategy:             SAR
historical_status:    SURROGATE
source_round:         round precedente (file 20260717)
current_isolated_run: MISSING
run_id:               assente
trades:               261   PF 0.6   exp -0.09R
```

Nota registrata nel knowledge base:

> ATTENZIONE: file piu' recente disponibile per S04 datato 17/07 (round precedente): la passata S04 del round corrente non risulta nei report

`SAR` va **programmata per una nuova passata isolata**. I numeri
restano leggibili ma non descrivono il codice della baseline corrente, e non
vanno usati per giudicarla.

---

## Mai misurate — 28 strategie

Tutte girano. Nessuna ha una passata isolata.

| Strategia | Sel | TF | Funzione research | Collisione | Bug storici | Fix registrati |
|---|---|---|---|---|---|---|
| `AMD_CONT` | 28 | — | `sig_amd_cont` | — | 1 | 2 |
| `AMD_REVERSAL` | 24 | — | `sig_amd_reversal` | — | 1 | 0 |
| `BB_SQUEEZE` | 12 | D1 | `sig_bb_squeeze` | — | 1 | 2 |
| `DISP_REBAL` | 35 | H4 | `sig_disp_rebal` | — | 1 | 2 |
| `ELLIOTT` | 36 | — | `—` | — | 1 | 0 |
| `EMA_PULLBACK` | 11 | H4 | `sig_ema_pullback` | — | 1 | 2 |
| `FVG_MIT` | 19 | D1 | `sig_fvg_mit` | — | 1 | 2 |
| `ICHIMOKU` | 13 | H4 | `sig_ichimoku` | — | 1 | 2 |
| `IFVG` | 18 | H4 | `sig_ifvg` | — | 2 | 2 |
| `JUDAS_SWING` | 29 | — | `sig_judas_swing` | — | 1 | 0 |
| `LDN_REVERSAL` | 30 | — | `sig_ldn_reversal` | — | 1 | 1 |
| `LIQ_VOID` | 34 | H4 | `sig_fvg_cont` | — | 1 | 2 |
| `LONDON_BO` | 10 | D1 | `sig_breakout` | WEEKLY_EXP | 1 | 2 |
| `MALAYSIAN_SNR` | 26 | D1 | `sig_malaysian_snr` | — | 3 | 2 |
| `NY_REVERSAL` | 31 | — | `sig_ny_reversal` | — | 1 | 2 |
| `OB_MIT` | 20 | D1 | `sig_ob_mit_ext` | — | 2 | 2 |
| `ORDER_BLOCK` | 15 | D1 | `sig_order_block_ext` | — | 1 | 2 |
| `OTE_CONT` | 25 | D1 | `sig_ote_cont` | — | 2 | 2 |
| `PO3` | 33 | — | `sig_po3` | — | 1 | 0 |
| `RANGE_FADE` | 37 | D1 | `sig_bollinger` | BOLLINGER | 3 | 2 |
| `RSI_DIV` | 14 | H1 | `sig_rsi_div` | — | 1 | 0 |
| `SH_BMS_RTO` | 21 | D1 | `sig_ob_mit` | SMS_BMS_RTO | 1 | 2 |
| `SILVER_BULLET` | 23 | — | `sig_silver_bullet` | — | 1 | 2 |
| `SMS_BMS_RTO` | 22 | D1 | `sig_ob_mit` | SH_BMS_RTO | 1 | 0 |
| `STRUCT_REACT` | 16 | H1 | `sig_struct_react` | — | 1 | 0 |
| `THREE_BAR_DELIVERY_BREAK` | 27 | H4 | `sig_cisd` | — | 1 | 2 |
| `TURTLE_SOUP` | 17 | H1 | `sig_turtle_soup` | — | 0 | 0 |
| `WEEKLY_EXP` | 32 | D1 | `sig_breakout` | LONDON_BO | 1 | 2 |

---

## Cosa serve per chiudere questa pagina

29 passate isolate: le 28 mai eseguite piu' quella
surrogata, sulla baseline corrente. Finche' mancano, ogni affermazione sul
portafoglio riguarda 8 strategie su 37 ed e' estesa alle altre
per analogia — che non e' evidenza.

## Collegamenti

`docs/NEXUS_STRATEGY_INVENTORY.md` · `docs/NEXUS_STRATEGY_MISMATCH_REPORT.md` ·
`docs/NEXUS_STRATEGY_PRIORITY_MATRIX.md`
