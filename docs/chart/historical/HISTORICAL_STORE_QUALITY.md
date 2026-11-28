# Store storico Dukascopy — qualità dei dati (Fase 03)

Dataset `DUKASCOPY_XAUUSD_PHASE7`, finestra **2023-02-04 → 2024-08-03** (547 giorni, partizione `development_discovery`, già autorizzata). Nessun download, nessuna finestra sigillata o bloccata aperta; la guardia è stata consultata prima di ogni file giornaliero. Verdetto del verificatore indipendente: **PASS (13/13 controlli)**.

## Copertura per timeframe
| TF | Barre | COMPLETE | PARTIAL | GAP |
|---|---|---|---|---|
| M1 | 530.331 | 530.331 | 0 | 0 |
| M5 | 106.125 | 105.873 | 190 | 62 |
| M15 | 35.378 | 35.151 | 166 | 61 |
| M30 | 17.690 | 17.485 | 146 | 59 |
| H1 | 8.851 | 8.663 | 132 | 56 |
| **H4** | **2.393** | 1.884 (78,7 %) | 456 | 53 |
| D1 | 464 | 0 | 417 | 47 |
| W1 | 79 | 0 | 47 | 32 |
| MN1 | 19 | 0 | 4 | 15 |
Periodo effettivo: primo M1 `2023-02-05 23:00 UTC`, ultimo `2024-08-02 21:00 UTC` (+60 s). Prima barra H4: 2023-02-05 20:00.
D1/W1/MN1 non risultano mai COMPLETE perché il calendario non è verificato e ogni giorno contiene pause: è un limite dichiarato, non un difetto di costruzione.

## Controlli eseguiti (costruttore + verificatore indipendente)
- Tick: 61.404.484; conteggi per file = manifest (0 incongruenze); 0 non monotoni, 0 duplicati, 0 fuori fascia, 0 prezzi non positivi; 547 righe di intestazione saltate (1/file); prezzo 1804,594–2483,548.
- 547/547 file presenti; hash del manifest dati `7c4a0ff6…cd82a`; hash di ogni segmento verificato.
- M1 = manifest (530.331/530.331); ordine strettamente crescente; ogni barra allineata al bucket UTC; OHLC coerente su tutte le barre.
- Ri-aggregazione da M1 identica barra per barra per tutti gli 8 timeframe superiori; bilancio dei minuti (presenti + mancanti + bordo = bucket).
- Ri-derivazione da tick di 16 giorni campione (primo e ultimo inclusi): M1 identici.
- Buchi: 388 (77 weekend, 298 pause giornaliere, 13 altri incl. festività e 10–54 minuti infragiornalieri), 252.612 minuti totali; 2 giorni feriali senza tick (2023-04-07, 2024-03-29: Venerdì Santo).

## Provenienza e orologio
Origine: file tick decodificati Dukascopy (manifest dati con hash), barre dal solo **bid**, nessun volume. Timestamp = epoch del downloader. **La conversione UTC NON è verificata in modo indipendente** e non è dichiarata tale; il calendario è `UNVERIFIED` (inferito dalla ricorrenza dei buchi). Il feed Dukascopy **non** è mescolato con XM né considerato equivalente: i dataset restano separati e selezionabili.
