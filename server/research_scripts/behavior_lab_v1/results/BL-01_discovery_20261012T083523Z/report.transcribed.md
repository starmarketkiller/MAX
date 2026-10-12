<!-- Transcription of report.md written by run_experiment/bl01 on the research PC
     (C:/Users/User/ClaudeWork/MAX-bl01/server/research_scripts/behavior_lab_v1/data/bl01/20261012T083336Z/report.md),
     relayed as text by the PC session; content unchanged. -->

# BL-01: validazione su dati reali di BL-H4M15-IPC-001
Esplorativo: discovery 2023-02-04 → 2024-08-03. Nessun risultato qui e' una prova confermativa.

## 1. HEAD, ambiente e hash dei dati
HEAD 87f7f10eca3c6ee7c23190017e42286974d64e48; nessuna modifica non committata; manifest MATCH 605249c6...; discovery 547/547 giorni; warmup 92/92; params_sha256 7c66d51c...; smoke 106.35s; discovery 712.58s; Windows-11-10.0.26100-SP0 Python 3.12.10.

## 2. Qualita' dei dati
smoke: tick audit PASS_WITH_NOTES (11.728.159 tick, 0 crossed/nonpositive/non-monotonic/duplicati, spread_above_max=55, mean_spread=0.373), 0 disallineamenti H4/M15, 0 differenze vs Phase 7.1, buchi M15 weekend=15/pausa=53/altri=2, DST {"US_DST":20,"US_STANDARD":21}.
discovery: tick audit PASS_WITH_NOTES (72.159.303 tick, stessi 0 anomalie, spread_above_max=325, mean_spread=0.356), 0 disallineamenti, 0 differenze vs Phase 7.1, buchi M15 weekend=89/pausa=345/altri=16, DST {"US_DST":22,"US_STANDARD":23}, 0 file giornalieri mancanti.

## 3. Statistiche reali del detector
Barre H4 nello split: 2394. Impulsi 107 (firing 4.47%, NORMAL). Pullback 95 (firing 3.97%, NORMAL). Funnel eventi: CLOSED=49, CANCELLED_ANCHOR_BROKEN=4, UNCONFIRMED=36, RISK_OUT_OF_BOUNDS=6. Selezione: events_seen=95 (closed_share 51.6%), controls_seen=4598 (closed_share 39.2%).
Per trimestre (n, P(+2R) Wilson, exp.netta R): 2023Q1 4/25.0%/-0.046; 2023Q2 6/33.3%/0.498; 2023Q3 7/28.6%/-0.143; 2023Q4 11/45.5%/0.543; 2024Q1 7/14.3%/-0.325; 2024Q2 9/44.4%/0.578; 2024Q3 5/40.0%/0.426. Positivi 4/6 con n≥5.
Per direzione: BUY n=29 41.4%/+0.448R; SELL n=20 25.0%/-0.008R.
Per sessione: LONDON n=7 42.9%/+0.286; LONDON_NY_OVERLAP n=7 14.3%/-0.236; NEW_YORK n=8 37.5%/+0.427; OFF n=9 22.2%/-0.040; TOKYO n=18 44.4%/+0.524.
Concentrazione oraria massima: 14.3% (sotto soglia 35%).

## 4. Confronto con baseline M15 senza filtro H4
Eventi H4→M15 (n=49): P(+2R)=34.7% [22.9,48.7], exp.netta=0.262R, CI95 bootstrap mensile [-0.061,0.528]R (16 blocchi), PF=1.555, spread medio 0.055R, MFE/MAE mediani 0.876/0.812R.
Controllo M15 (n=1803): P=23.6% [21.7,25.6], exp.netta=-0.045R, CI95 [-0.134,0.037]R (19 blocchi), PF=0.924, MFE/MAE mediani 0.758/1.024R.
A parità di direzione/sessione/volatilità: delta P=0.092, delta exp=0.269R; eventi migliori in 13/25 celle usabili; 0 eventi senza controllo comparabile.
Sensibilità costi (eventi): resta positivo fino a +0.10R extra (0.162), breakeven_win_rate_gross=33.3%. Trimestri positivi 4/6 (controllo 2/7).

## 5. Limiti metodologici
Discovery esplorativa, una sola ipotesi, nessuna correzione multipli; prezzi Dukascopy non feed XM; nessuno slippage/commissione; eventi non indipendenti (bootstrap mensile descrittivo); controllo descrittivo non baseline v4 abbinato; finestre 2025-2026 non holdout indipendenti.

## 6. Decisione
**INVESTIGATE** (BL01_DECISION_RULES_V1). Check: n_closed≥60 ✗ | net expectancy>0 ✓ | CI95 mensile low>0 ✗ | adjusted delta vs control>0 ✓ | event better in ≥60% celle ✗ | positivo in ≥60% trimestri n≥5 ✓ | resta >0 con +0.10R costo extra ✓ | nessuna direzione sotto -0.1R con n≥20 ✓ | nessuna ora UTC sopra 35% ✓.
Né GO né STOP: non leggere internal_validation; serve una nuova domanda preregistrata.

## 7. Prossimo esperimento consigliato (non eseguito)
INVESTIGATE: il vantaggio non regge a parità di direzione/sessione/volatilità — preregistrare una domanda sul solo effetto del contesto H4 contro il controllo abbinato. Ogni nuova domanda richiede un nuovo hypothesis_id.
