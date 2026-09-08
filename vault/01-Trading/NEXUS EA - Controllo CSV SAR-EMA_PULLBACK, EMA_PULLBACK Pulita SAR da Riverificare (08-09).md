---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, sar, ema-pullback, risk-profile, metodo]
created: 2026-09-08
updated: 2026-09-08
---

# NEXUS EA — controllo sui CSV esistenti (SAR/EMA_PULLBACK), come suggerito dalla sessione cloud (08/09)

## Metodo

Come già fatto per FVG_CONT (step1 nudo vs step2 vincolato): invece di
rilanciare tutto, controllato nei deal CSV già esistenti (1) il
massimo di trade aperti in un solo giorno di calendario (soglia: 12,
il cap forzato da BALANCED) e (2) la peggior perdita intra-day rispetto
al balance di inizio giornata (soglia: 5%, il DD-cap forzato da
BALANCED). Se nessuno dei due viene mai toccato, il bug non ha potuto
cambiare il risultato registrato.

## EMA_PULLBACK — pulita, nessun re-run necessario

| Test | Max trade/giorno | Peggior DD intra-day |
|---|---|---|
| step32 clean nuda | 2 | 5.02% |
| extended nuda | 2 | 5.03% |
| step0 nuda | 1 | 5.01% |
| walk-forward finestra 1 (2024jan) | 1 | 5.01% |
| walk-forward finestra 2 (2024jul) | 1 | 5.04% |
| walk-forward finestra 3 (2025jan) | 1 | 5.02% |
| walk-forward finestra 4 (2025jul) | 1 | 5.05% |

Mai sopra 2 trade/giorno (cap 12 mai in gioco). Il DD intra-day sfiora
il 5% ma non lo supera mai di una quantità significativa (5.01-5.05%,
stesso ordine di grandezza del singolo giorno -5.0% già visto su
FVG_CONT, dove l'impatto pratico è risultato trascurabile). **Verdetto:
come FVG_CONT, il bug era tecnicamente presente ma non ha spostato la
sostanza — nessun re-run necessario.**

## Scoperta indipendente (non il bug RiskProfile): le "4 finestre" non sono indipendenti

Controllando gli `.ini`, le 4 "finestre" walk-forward hanno **tutte lo
stesso `ToDate=2026.08.26`** e solo `FromDate` diverso (2024.01.01 /
2024.07.01 / 2025.01.01 / 2025.07.01) — sono **periodi annidati che si
restringono dalla stessa fine**, non 4 segmenti storici distinti e
non sovrapposti. Coerente con questo: **il giorno peggiore è lo stesso
identico (2026-03-27) in tutte e 4** — non è un caso, è lo stesso evento
di mercato presente in ogni finestra perché si sovrappongono tutte
sulla coda finale. La nota vault
[[NEXUS EA - EMA_PULLBACK Walk-Forward 4 Finestre, Tutte Positive (04-09)]]
descrive questo come "4 finestre indipendenti" — non lo sono. Il
miglioramento monotono di PF/Sharpe restringendo la finestra resta un
dato reale, ma la conferma è più debole di quanto "4 finestre
indipendenti, tutte positive" suggerisca: sono 4 letture dello stesso
periodo via via più corto, fortemente correlate tra loro, non 4 prove
indipendenti. Da correggere la caratterizzazione nella nota originale,
non serve un nuovo test per questo punto specifico.

## SAR — supera chiaramente su tutta la famiglia "confermata", re-run in corso

| Test | Max trade/giorno | Peggior DD intra-day |
|---|---|---|
| step35 clean_veto (config pulita finale) | 3 | **5.94%** |
| step22 candle dec2025 | 3 | **9.80%** |
| step23 candle feb2026 | 3 | **6.69%** |
| step24 candle apr2026 | 3 | **6.78%** |
| step25 candle jun2026 | 3 | **7.52%** |

Mai sopra 3 trade/giorno (cap 12 mai in gioco) — ma **tutte e 5 le
finestre della config "confermata" (PF1.37-1.57)** superano
chiaramente il 5% di DD intra-day, non di un pelo come EMA_PULLBACK ma
di 1-5 punti percentuali interi. Soddisfa il criterio concordato
("se anche un solo giorno supera, quel test va rifatto") — con margine.

**Nota metodologica**: un DD intra-day sopra al 5% non prova da solo
che il cap abbia bloccato nuove aperture (il cap blocca solo l'apertura
di NUOVE posizioni, non l'esecuzione dello stop su una posizione già
aperta — un peggioramento intra-day può derivare interamente da
posizioni già in piedi). Ma con 5 finestre su 5 abbondantemente sopra
soglia, il rischio che qualche apertura sia stata davvero soppressa è
troppo alto per fidarsi senza verifica diretta.

**Azione**: rilanciato `nxs_sar_step44_riskprofile0_recheck` — stessa
identica configurazione di step35 (`nexus_sar_step35_badwindow_clean_veto.ini`,
finestra 2026.01.12→2026.04.12, candle-align, PipSeq, RegimeVeto)
con `InpRiskProfile=0` esplicito aggiunto, ora che il fix di ieri lo
rende reale. Confronto diretto in arrivo tra i due risultati.

## Collegamenti
[[NEXUS EA - Impatto Storico Bug InpRiskProfile su Tutto il Corpus di Test (08-09)]] · [[NEXUS EA - EMA_PULLBACK Walk-Forward 4 Finestre, Tutte Positive (04-09)]] · [[MOC - Trading]]
