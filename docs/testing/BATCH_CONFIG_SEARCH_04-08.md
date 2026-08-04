# Ricerca configurazione batch — tutte le strategie sopravvissute alla Fase 1

Eseguito su richiesta esplicita ("continua con trovare la configurazione
per tutte le strategie"), dopo AMD_CONT e SILVER_BULLET (deep-dive
completi a mano). Applica meccanicamente la parte automatizzabile della
disciplina NQROS v3.1 (Fase 1/3/6/8-lite/4) a tutte le altre strategie con
baseline positiva — non sostituisce un deep-dive completo (Fase 0/2/5/7/9/10
restano da fare a mano se si vuole promuovere una di queste a "mantieni").

Script: `server/research_scripts/find_all_configs.py`. Regole imposte
dopo un primo tentativo fallito (vedi sotto "Falso partenza"):
- baseline richiede ≥25 trade (così i due tagli OOS hanno ≥10 ciascuno)
- al massimo **1 toggle + 1 parametro di gestione** nella combinazione
  dichiarata (mai più di 2, per non impilare filtri come già successo su
  SILVER_BULLET)
- OOS richiede ≥10 trade per lato, altrimenti MARGINALE
- **PF Out-of-Sample sopra 3.0 → MARGINALE automatico**, anche a campione
  sufficiente: troppo bello per fidarsene senza revisione manuale

## Falso partenza (onestà del processo)

Il primo tentativo (senza questi limiti) ha impilato fino a 5 parametri
insieme e prodotto `SH_BMS_RTO`/`SMS_BMS_RTO` con **PF Out-of-Sample
49.54 su 9 trade**, marcato "PASS" dalla logica originale. Sbagliato:
esattamente il tipo di overfitting-per-accumulo-di-filtri già segnalato a
mano su SILVER_BULLET, qui riprodotto senza controllo umano. Corretto
prima di accettare qualunque risultato — vedi le regole sopra.

## PASS (6) — regge il gate OOS

| Strategia | TF | Baseline PF | Config trovata | Combo PF/trade | OOS in→out | Stress |
|---|---|---|---|---|---|---|
| IFVG | 4h | 2.06 | atr_tp=4.0 | 2.28/34 | 2.65→1.81 | 1.72 |
| LONDON_BO | 1wk | 1.71 | htf_filter=True, breakeven_r=1.5 | 2.00/25 | 1.49→2.19 | 2.12 |
| WEEKLY_EXP | 1wk | 1.71 | htf_filter=True, breakeven_r=1.5 | 2.00/25 | 1.49→2.19 | 2.12 |
| FVG_MIT | 4h | 1.24 | trailing_atr=2.0 | 1.41/43 | 0.83→2.55 | 2.42 |
| ICHIMOKU | 1h | 1.09 | atr_tp=4.0 | 1.19/72 | 1.03→1.77 | 1.59 |
| BJORGUM | 4h | 1.06 | atr_sl=2.0 | 1.09/97 | 0.83→1.71 | 1.63 |
| TURTLE_SOUP | 1h | 1.01 | atr_sl=1.0 | 1.22/49 | 1.55→1.02 | 0.89 |

Nota: LONDON_BO/WEEKLY_EXP condividono la stessa funzione Python
(collisione già documentata) — un solo risultato indipendente, non due.
TURTLE_SOUP è il più marginale del gruppo (OOS scende quasi a 1.0 con
costi stress a 0.89 — un pass, ma appena).

## MARGINALE (5) — non scartate, ma non abbastanza pulite per fidarsene subito

| Strategia | Motivo | Dettaglio |
|---|---|---|
| TSI | PF OOS 5.73 sopra soglia 3.0 | Troppo bello, serve revisione manuale prima di adottare |
| LIQ_VOID | PF OOS 3.55 sopra soglia 3.0 | Idem |
| OTE_CONT | PF OOS 4.39 sopra soglia 3.0 | Idem |
| OB_MIT | Campione OOS troppo piccolo (7 trade) | Sotto la soglia di 10, non giudicabile |

## FAIL (2 genuini + 2 "nessun miglioramento trovato")

| Strategia | Motivo | Nota |
|---|---|---|
| PO3 | PF crolla sotto 1.0 fuori campione (0.94, stress 0.89) | Fallimento genuino del gate |
| FVG_CONT | Nessun parametro batte la baseline (PF 3.15) con campione ≥25 | La baseline stessa resta forte — non è "la strategia è cattiva", è "non ho trovato di meglio con questi vincoli" |
| MACD | Nessun parametro batte la baseline (PF 2.94) con campione ≥25 | Idem |

## SKIP (7) — campione già troppo piccolo per tentare la ricerca

ADX_RSI (24tr), NY_REVERSAL (22tr), ORDER_BLOCK (12tr), SAR (18tr),
SH_BMS_RTO (17tr), SMS_BMS_RTO (17tr), THREE_BAR_DELIVERY_BREAK (15tr).

Non è un giudizio negativo — è lo stesso limite di dati che ha già bloccato
parte del lavoro su AMD_CONT/SILVER_BULLET (storico H4/W1 troppo corto per
alcuni). Riverificare quando c'è più storico.

## Stato rispetto al ciclo completo v3.1

Questo è **Fase 1/3/6/8-lite/4 meccanizzate**, non un deep-dive completo.
Mancano ancora, per ogni strategia PASS/MARGINALE, prima di considerarle
pronte:
- Fase 0/2 (bottleneck/anatomia) — qui saltate, la ricerca è stata a
  griglia diretta, non guidata da un'ipotesi sui dati
- Fase 5 (risk_pct — qui non testato, MaxDD non riportato)
- Fase 9/10 (punteggio, decisione, diario)
- Gli stessi due rischi aperti di AMD_CONT/SILVER_BULLET: fedeltà motore
  Python vs MQL5 reale (mai verificata), storico H4/W1 corto (limite Yahoo)
