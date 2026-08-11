---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: TSI
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: TSI

## Tipo
Momentum

## Trigger meccanico
RSI>52 + prezzo sopra EMA20 con EMA20 in salita (short speculare) — riportata alla logica del sito.

⚠️ **Scoperta 15/07**: non è il vero True Strength Index (William Blau,
doppio smoothing EMA del momentum) — il commento nel codice lo dichiara
esplicitamente ("simplified RSI/EMA proxy"). Test A/B col vero TSI: PF
1.35→1.42, drawdown quasi azzerato (10.57%→4.99%), ma **-73% di trade**. Non
ancora corretto — è un trade-off frequenza/qualità che va deciso
esplicitamente, non un fix "gratis" come SAR/ADX_RSI. Dettaglio:
[[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]].

## Configurazione attuale (v2.5.0)
- **Timeframe**: D1
- **SL**: 1.5× ATR · **TP**: 4.5× ATR
- **Filtro HTF**: True
- **Trailing**: stretto (incassa presto)
- **Rischio per trade**: 0.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, CONFIG PRECEDENTE (diversa da quella sopra))
- **3 mesi**: 0 trade eseguiti in questo build. (1780 setup rilevati ma nessuno eseguito — strategia disabilitata/bloccata)
- **3 anni**: 0 trade eseguiti in questo build. (1355 setup rilevati ma nessuno eseguito — strategia disabilitata/bloccata)

## Risultati (backtest 10y segmentato v2.5.0, 5 anni affidabili 2019-2023)
539 trade totali — ora esegue davvero (era 0 trade in v2.4.8). R per anno:
2019 -2.3 · 2020 -2.1 · 2021 -1.3 · 2022 -1.2 · 2023 +1.1. **Somma -5.8R — 1
anno su 5 positivo (solo 2023)**. Dettaglio:
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]].

## Stato
⏳ PENDING — la riabilitazione ha funzionato dal punto di vista dell'esecuzione
(539 trade, campione ampio) ma il segnale resta negativo in 4 anni su 5,
con un miglioramento solo nell'ultimo anno da monitorare.

## Aggiornamento 11/08 — variante "cross da zona estrema" testata, negativa

Il trigger MQL5 (`NXS_Strat_TSI`) è un cross puro TSI/signal-line, senza
alcun filtro di zona — verificato riga-per-riga, il port Python è già
fedele al 100%, non era un bug da correggere. Ipotesi nuova (non di
fedeltà): richiedere che il cross parta da una zona di momentum estremo
(soglia=15, mediana del TSI assoluto su XAUUSD 1d) invece di un cross
qualunque vicino allo zero - stessa logica per cui RSI si usa quasi
sempre con soglie di ipercomprato/ipervenduto.

Registrata `TSI_EXTREME`, testata su 1d (vero TF di profilo) e 4h:

| TF | OOS baseline | OOS extreme | Walk-forward extreme |
|---|---|---|---|
| 1d | 0.71/39 | **0.63/22 (peggio)** | 3/5, con una finestra a 0.25 |
| 4h | 1.24/169 | 1.24/108 (identico, meno trade) | 3/5, stesso pattern del baseline |

**Negativo su entrambi i TF** — su 1d peggiora, su 4h è semplicemente
lo stesso segnale con meno campione (nessun guadagno di qualità).
L'ipotesi non regge. **TSI resta un problema aperto senza soluzione
trovata** dopo aver esaurito: fix del trigger (già fatto, era necessario
ma non sufficiente), filtro di regime WEAK_TREND (smentito, artefatto
di motore/TF sbagliati), cross da zona estrema (appena testato,
negativo). Prossime idee non ancora tentate: cambiare i periodi
long/short/signal (25/13/7, mai ottimizzati per l'oro specificamente),
o accettare che TSI su D1 XAUUSD semplicemente non ha edge con questo
approccio e valutare la sua rimozione dal nucleo.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]]
