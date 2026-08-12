---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, censimento, storico-esteso, sito]
created: 2026-08-12
updated: 2026-08-12
---

# Riverifica censimento via motore del sito — storico esteso 2016-2026 (12/08)

Richiesta esplicita dell'utente: rifare il test su tutte le strategie
usando il motore DEL SITO (`https://nexus-backend-8o4y.onrender.com`),
non la chiamata diretta a `run_backtest` usata per tutta la sessione.

## Scoperta preliminare: il sito ha 3 anni di storico in più

Il sito ha uno storico Dukascopy che copre **2016-08-11 → oggi**, contro il
file locale usato in tutta questa sessione (**2019-05-20 → oggi**). "Adesso
che abbiamo tutto lo storico" si riferiva a questo — non un refresh, un
dataset più ampio mai usato prima nella sessione. Confermato lato codice:
`/api/backtest/run` non esponeva `bars`/`bar_range` (usava sempre il
default di 800 barre) — aggiunto oggi, additivo/retrocompatibile
(`server/app.py`), deployato su Render (commit `7e0bd71`).

## Metodo
Stesso di `full_census.py`: flat baseline SL1.5×/TP3.0×, IS(60%)/OOS(40%),
un TF per strategia (real profile TF dove noto), `bars=200000` (forza il
motore a usare tutto lo storico disponibile). Chiamate dirette
all'endpoint HTTP del sito (non `run_backtest` in-process).

## Limite tecnico incontrato: il sito non regge tutte le 59 in un colpo

Il primo giro ha saturato il backend (verosimilmente Render "starter" a
worker singolo) dopo poche richieste pesanti consecutive, causando prima
una cascata di 502 poi un crash reale (`/api/health` stesso rispondeva 502
per alcuni minuti, poi Render l'ha riavviato da solo). Rilanciato con
pausa più ampia (8s) e retry con backoff (20/40/60s) — recuperate la
maggior parte, ma **14 strategie non si sono mai completate dopo 3
tentativi**, sempre le stesse: `AMD_REVERSAL`, `LDN_REVERSAL`, `LIQ_SWEEP`,
`LIQ_VOID`, `OTE_CONT`, `OTE_CONT_V2`, `PO3`, `SCALP_BB_FADE`, `SCALP_EMA`,
`SCALP_RANGE_BRK`, `SCALP_RSI_SNAP`, `SH_BMS_RTO`, `SH_BMS_RTO_V2` (+
`ELLIOTT`, atteso — nessuna implementazione Python, 422 non 502).

Pattern consistente su più tentativi (non rumore transitorio): quasi tutte
basse-TF/alta-frequenza (15m, o TF con migliaia di trade sui 10 anni) —
verosimilmente il calcolo supera il timeout del gateway Render (che non è
aggirabile da un client, indipendentemente da quanto lungo si imposti il
timeout lato chiamante). **45/59 completate puliteremente.**

## Risultati (45 strategie complete, IS 60%/OOS 40%, storico 2016-2026)

| Strategia | TF | IS PF/n/dd | OOS PF/n/dd |
|---|---|---|---|
| ADX_RSI | 1d | 1.22/95/5.91 | 1.17/52/8.65 |
| AMD_CONT | 30m | 1.08/619/35.52 | 1.30/423/16.61 |
| BB_SQUEEZE | 1d | 0.0/2/1.99 | None/2/0.0 |
| BJORGUM | 4h | 1.07/336/24.35 | 0.81/265/37.26 |
| BOLLINGER | 1d | 1.21/79/9.7 | 0.78/53/13.81 |
| BREAKOUT_ACC | 1d | 1.29/75/6.02 | 2.01/54/5.88 |
| CISD_TRUE | 1h | 0.91/437/40.73 | 0.98/281/20.41 |
| CRT | 30m | 1.27/10115/40.87 | 1.24/6827/36.47 |
| DISP_REBAL | 4h | 2.90/5/1.99 | 0.99/3/1.99 |
| EMA_PULLBACK | 1h | 1.08/447/24.29 | 1.28/304/10.92 |
| FVG_CONT | 4h | 1.27/418/13.23 | 1.28/281/16.72 |
| FVG_CONT_V2 | 4h | 1.29/86/5.85 | 1.54/56/4.7 |
| FVG_MIT | 4h | 1.13/164/13.56 | 0.97/107/25.94 |
| FVG_MIT_WINDOW | 4h | 1.07/461/28.53 | 1.07/319/18.33 |
| ICHIMOKU | 4h | 0.75/147/37.93 | 1.12/104/13.81 |
| IFVG | 4h | 0.66/3/1.0 | 5.19/5/1.0 |
| IFVG_CHOCH_WINDOW | 4h | 0.46/7/2.97 | 2.85/15/3.94 |
| JUDAS_SWING | 1h | 0.32/13/6.64 | 0.54/11/5.59 |
| LONDON_BO | 4h | 1.13/241/16.1 | 1.22/154/17.57 |
| MACD | 4h | 1.13/411/21.74 | 1.54/286/14.9 |
| MALAYSIAN_SNR | 1d | None/3/0.0 | 0.93/2/1.0 |
| MALAYSIAN_SNR_BREAKOUT | 4h | 1.16/154/14.44 | 1.24/103/6.69 |
| MALAYSIAN_SNR_V2_RETEST | 1h | 1.22/396/11.68 | 1.25/161/7.32 |
| MALAYSIAN_SNR_V2_RETEST_OUTRANGE | 30m | 1.04/500/10.63 | 0.89/181/12.59 |
| MALAYSIAN_SNR_V2_STAGE1 | 1h | 1.23/224/10.47 | 1.22/131/9.99 |
| MALAYSIAN_SNR_V2_STAGE3 | 1h | 0.87/117/21.77 | 1.52/71/13.18 |
| NY_REVERSAL | 1h | 0.88/32/7.54 | 2.34/14/2.46 |
| NY_REVERSAL_CHOCH_WINDOW | 1h | 1.39/110/13.28 | 0.59/61/18.11 |
| OB_MIT | 30m | 1.04/189/14.64 | 1.01/122/17.65 |
| ORDER_BLOCK | 30m | 1.04/189/14.64 | 1.01/122/17.65 |
| ORDER_BLOCK_V2 | 30m | 0.87/376/32.94 | 1.27/218/19.87 |
| RANGE_FADE | 1d | 1.21/79/9.7 | 0.78/53/13.81 |
| RSI_DIV | 1h | 0.85/715/55.98 | 0.91/481/36.15 |
| SAR | 4h | 1.08/587/26.55 | 1.24/397/20.4 |
| SILVER_BULLET | 1h | 1.12/156/11.87 | 0.84/88/14.41 |
| SILVER_BULLET_V2 | 1h | 1.16/17/1.88 | 0.34/8/2.74 |
| SMS_BMS_RTO | 1d | None/0/0.0 | None/0/0.0 |
| SMS_BMS_RTO_CHOCH_WINDOW | 1d | 2.27/8/1.0 | 0.54/3/1.0 |
| STRUCT_REACT | 1h | 0.88/715/44.96 | 0.90/476/36.48 |
| THREE_BAR_DELIVERY_BREAK | 4h | 0.82/88/11.13 | 1.12/45/5.14 |
| TSI | 1d | 1.40/71/5.04 | 0.89/59/9.43 |
| TSI_EXTREME | 1d | 1.36/53/9.68 | 0.71/39/12.97 |
| TURTLE_SOUP | 1h | 1.11/825/25.37 | 0.96/575/31.08 |
| TURTLE_SOUP_CHOCH | 4h | 1.35/85/5.13 | 1.05/69/7.43 |
| WEEKLY_EXP | 1h | 1.16/82/5.9 | 1.07/54/12.54 |

Nota: ORDER_BLOCK e OB_MIT mostrano numeri identici — non un bug di
questo giro, coerente con una relazione proxy/condivisione di logica già
nota tra le due (da verificare con calma, non approfondito qui).

## Confronto con la finestra 2019-2026 (locale, già in vault) — nucleo

| Strategia | OOS locale (2019-26) | OOS sito (2016-26) | Lettura |
|---|---|---|---|
| CRT | 1.25/4711 | 1.24/6827 | **Quasi identico** — conferma forte, non artefatto di finestra |
| TURTLE_SOUP (flat) | 0.96/398 | 0.96/575 | **PF identico**, campione +45% — conferma che è debolezza reale, non rumore |
| ADX_RSI | 1.24/31 (sottile) | 1.17/52 | Campione quasi raddoppiato con PF stabile — **più storico aiuta esattamente il problema D1 già diagnosticato** |
| TSI | 0.71/39 | 0.89/59 | Migliora ma **resta sotto pareggio** — "problema aperto" confermato, solo meno severo |
| SAR | 1.22/276 | 1.24/397 | Coerente, campione più ampio |
| MACD | 1.65 (Python flat) | 1.54/286 | Coerente, stesso ordine di grandezza |
| BREAKOUT_ACC | 2.71/38 (WF reale 1/5, rumore noto) | 2.01/54 | Ancora attraente sull'aggregato ma **il verdetto WF resta quello vero**, non cambia nulla |
| FVG_MIT | 1.01/78 | 0.97/107 | Coerente, resta debole |
| THREE_BAR_DELIVERY_BREAK | 1.49/24 (sottile, WF 2/5) | 1.12/45 | Campione quasi raddoppiato, PF scende — **coerente con "debole", non un caso fortunato** |

**Non disponibili dal sito** (limite tecnico sopra): LIQ_SWEEP,
LDN_REVERSAL, AMD_REVERSAL — 3 delle 16 del nucleo. Nessuna nuova
evidenza raccolta su queste tre, restano ai verdetti già in vault
(storico 2019-2026 locale).

## Conclusione

Nessuna sorpresa che ribalti un verdetto già dato — il quadro del nucleo
si conferma sostanzialmente stabile passando da 7 a 10 anni di storico.
Il valore aggiunto principale è **statistico**: i campioni D1/4h più
sottili (ADX_RSI, THREE_BAR_DELIVERY_BREAK) guadagnano trade reali con la
finestra più ampia, rendendo i verdetti già dati più solidi (non li
cambia, li conferma con più dati). CRT e TURTLE_SOUP mostrano una
stabilità notevole tra le due finestre — il tipo di conferma indipendente
che vale più di un singolo walk-forward aggiuntivo.

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - Riverifica su Storico Ampliato (11-08)]] ·
[[NEXUS EA - CISD_TRUE (versione vera, negativa) e Censimento Completo (11-08)]]
