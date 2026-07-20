# Nexus — Evidence Index (M4)

Generato da evidence_engine v1.1.0 · fingerprint `57ab33e922aa679f` · deterministico, senza interpretazioni.

- **Claims totali**: 639
- **Evidence links totali**: 639
- **Status**: {'partially_supported': 1, 'supported': 638}
- **Strength**: {'moderate': 221, 'strong': 418}
- **Scope**: {'code_history': 125, 'data_quality': 2, 'documentation': 253, 'execution_integrity': 165, 'metadata': 65, 'signal_level': 29}

## Disponibilita' baseline per strategia (M4.1)

Campo controllato `baseline_availability_state`: distingue a macchina i motivi dell'assenza, senza inferenze dal testo libero.

### Baseline disponibile (8)
ADX_RSI, BJORGUM, BOLLINGER, BREAKOUT_ACC, FVG_CONT, LIQ_SWEEP, MACD, TSI

### Attesa ma assente (1) — anomalia reale, tracciata come data quality issue
SAR

### Non ancora osservata (28) — stato NORMALE e transitorio: lo sweep in corso non e' ancora arrivato a queste passate. Non e' un'anomalia.
AMD_CONT, AMD_REVERSAL, BB_SQUEEZE, DISP_REBAL, ELLIOTT, EMA_PULLBACK, FVG_MIT, ICHIMOKU, IFVG, JUDAS_SWING, LDN_REVERSAL, LIQ_VOID, LONDON_BO, MALAYSIAN_SNR, NY_REVERSAL, OB_MIT, ORDER_BLOCK, OTE_CONT, PO3, RANGE_FADE, RSI_DIV, SH_BMS_RTO, SILVER_BULLET, SMS_BMS_RTO, STRUCT_REACT, THREE_BAR_DELIVERY_BREAK, TURTLE_SOUP, WEEKLY_EXP

### Invalida (0) — candidato presente ma squalificato (identity mismatch / incompleta / checksum)
(nessuna)

### Non determinabile (0)
(nessuna)

## Issue di qualita' collegate alle evidenze
- `dqi-missing-S04-sweep37-baseline-e6ce816` (missing_artifact, severity medium)

## Limiti
- Le metriche sono SEMPRE a livello segnale (lotto fisso, strategia isolata): mai Net PnL/Max DD di conto, mai inferiti dai CSV di sweep.
- Copertura timeline = completa PER LE EVIDENZE DISPONIBILI (complete_for_available_evidence), mai storia assoluta.
- Nessun claim di giudizio (buona/cattiva/pronta per il live) viene generato: fuori scope M4.
- Le run baseline mancanti per passate non ancora eseguite sono assenze transitorie (sweep in corso).
