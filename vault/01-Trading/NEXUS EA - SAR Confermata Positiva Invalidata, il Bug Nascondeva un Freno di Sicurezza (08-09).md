---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, sar, bug, risk-profile, p0, dd]
created: 2026-09-08
updated: 2026-09-08
---

# NEXUS EA — SAR "confermata positiva" invalidata: il bug nascondeva un freno di sicurezza (08/09)

## Il test

Rilanciato `nxs_sar_step44_riskprofile0_recheck` — stessa identica
configurazione di `nexus_sar_step35_badwindow_clean_veto.ini` (finestra
2026.01.12→2026.04.12, candle-align, PipSeq lotto fisso 0.05,
RegimeVeto), con `InpRiskProfile=0` esplicito aggiunto ora che il fix
di ieri lo rende reale. Vedi
[[NEXUS EA - Controllo CSV SAR-EMA_PULLBACK, EMA_PULLBACK Pulita SAR da Riverificare (08-09)]]
per il criterio che ha portato a questo re-run mirato (DD intra-day
5.94-9.80% su tutte le 5 finestre della config confermata, ben oltre
la soglia di attenzione).

## Risultato: DIVERSO, non identico — il bug ha davvero cambiato le cose

| | step35 (pre-fix, BALANCED forzato) | **step44 (post-fix, Custom vero)** |
|---|---|---|
| Trade | 29 | **31** |
| Net | $4393.20 | **$4743.77** |
| PF | 2.02 | **1.90** |
| Sharpe | 5.03 | **6.26** |
| DD balance | 34.39% | **42.54%** |
| DD equity | 45.47% | **53.67%** |

## Causa esatta, confermata

Il punteggio segnale è **fisso a 60.0** in entrambi i run (29/29 e
31/31 trade, nessuna eccezione) — il gate sul voto NON è la causa qui
(diverso dal caso FVG_CONT). La causa è `InpMaxDailyDDPct`:
l'`.ini` chiede esplicitamente `InpMaxDailyDDPct=100.0` (nessun
vincolo, intento dichiarato del test "badwindow" — vedere la strategia
sotto stress reale). Pre-fix, `InpRiskProfile` bloccato su BALANCED
forzava **5.0%** silenziosamente — un freno di sicurezza mai
richiesto ma sempre attivo, che limitava quante nuove posizioni
potessero aprirsi durante un giorno già in perdita. Post-fix, il
100% richiesto è finalmente reale: **nessun freno**, la strategia apre
2 posizioni in più proprio nelle finestre di fine febbraio/inizio
marzo 2026, componendo perdite che il cap nascosto aveva sempre
impedito senza che nessuno lo sapesse.

**In altre parole**: il PF2.02 "confermato" di questa finestra non
era il vero comportamento a rischio scoperto della strategia — era il
comportamento con un airbag di sicurezza che nessuno aveva installato
di proposito e nessuno sapeva fosse lì. Tolto l'airbag (come l'.ini
chiedeva fin dall'inizio), il vero profilo di rischio è peggiore:
PF1.90, **DD equity 53.67%** — ben oltre qualunque soglia utilizzabile
per un conto reale o una prop firm.

## Impatto sul verdetto SAR

La riga "SAR ✅ Confermata — PF1.37-1.57 su 5 finestre" nella
[[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]]
si basa su questa stessa famiglia di test (step22-25, step35),
**tutte con lo stesso identico bug e la stessa identica esposizione**
(DD intra-day 5.94-9.80% già misurato su ognuna). Il campione mostra
che rimuovere il freno nascosto peggiora sia il PF che soprattutto il
DD in modo sostanziale, non marginale come in FVG_CONT/EMA_PULLBACK.
**La verifica "confermata positiva" di SAR non è più affidabile senza
un re-run completo delle altre 4 finestre.**

## Non ancora fatto — in attesa di conferma

Le altre 4 finestre (step22 dec2025, step23 feb2026, step24 apr2026,
step25 jun2026) non sono state ancora rilanciate con `InpRiskProfile=0`
vero. Il meccanismo è ormai chiaro e consistente (non serve più
indagare, solo eseguire) — ma non li rilancio senza conferma esplicita,
dato il costo (4 backtest aggiuntivi) e perché la conclusione
potrebbe già bastare così com'è per riclassificare SAR come "da
rivalidare" nel piano master, senza necessariamente rifare tutto
subito.

## Collegamenti
[[NEXUS EA - Controllo CSV SAR-EMA_PULLBACK, EMA_PULLBACK Pulita SAR da Riverificare (08-09)]] · [[NEXUS EA - Impatto Storico Bug InpRiskProfile su Tutto il Corpus di Test (08-09)]] · [[NEXUS EA - Sintesi Sessione Maratona SAR-EMA_PULLBACK-Scalp-RegimeVeto (01-02-09)]] · [[MOC - Trading]]
