---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, malaysian-snr, liquidity-grab, scalp, mql5]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — MALAYSIAN_SNR corretta a M30 (PF1.75, 5/5), liquidity-grab D/W/M bocciata (25/08)

## Contesto

L'utente ha chiesto strategie a turnover veloce (anche solo "100 pip alla
volta") per far vedere subito attività all'EA in demo, temendo che la
maggior parte delle strategie live (H4/D1) possa non aprire nulla per
giorni. Due filoni: (1) riverificare MALAYSIAN_SNR/STRUCT_REACT già
esistenti, (2) una nuova idea "liquidity grab" su massimi/minimi
giornalieri/settimanali/mensili.

## MALAYSIAN_SNR — il risultato più forte di tutta la sessione

`NXS_Strat_MalaysianSNR_Rejection` non era mai stata testata sulla
ricetta live esatta. Trovato un campanello d'allarme già nel codice:
`NXS_Profile_Risk("MALAYSIAN_SNR")` era 0.4% (tier minimo) con commento
"PF 0.00" — qualcuno aveva già osservato dal vivo che perdeva sempre e
aveva tagliato il rischio al minimo invece di correggerla. Era anche su
EffTF=D1 (lentissima).

`malaysian_snr_live_signal_25-08.py` — il livello chiave resta identico
in ogni test (H4 ultime 12 chiusure + bonus W1 ultime 8 chiusure,
storyline H4/D1) — cambia solo quanto spesso si controlla il tocco:

| EffTF | n | PF (m1/m2) | Finestre | risk_dist mediano |
|---|---|---|---|---|
| D1 (nativo, prima) | 117 | 0.76 | 1/5 | $30.82 |
| H4 | 491 | 0.99 | 2/5 | $17.21 |
| H1 | 817 | 1.49 | 5/5 | $12.48 |
| **M30** | **1289** | **1.75** | **5/5 (entrambe le direzioni)** | **$10.42** |
| M15 | 2157 | 1.69 | 5/5 BUY / 4/5 SELL | $9.10 |

Da D1 (rotta, SELL PF0.60) a M30 (robusta, simmetrica, campione grande)
solo controllando il tocco ogni 30 minuti invece che una volta al
giorno — stesso identico livello H4/W1. Nessun tocco intrabar mancato,
nessun cambio di logica.

**Applicato**: `NXS_Profile_TF("MALAYSIAN_SNR")` D1→M30, tier di rischio
0.4%→1.8% (non al massimo — prima conferma live ancora da avere su
questa TF). Nota dichiarata: il test non modella il gate HTF generico
(EMA200, `htf=true` nel profilo) che il vero EA applica in aggiunta —
atteso neutro/migliorativo, non verificato.

## Liquidity-grab D/W/M — bocciata, ma per un motivo diverso da CRT

Nuova idea (mai esistita prima, non un porting): sweep di PDH/PDL/PWH/
PWL/PMH/PML con fade su M15/M30, stop nativo o ATR fisso, target fisso
in dollari ($5/$8/$12). `liquidity_grab_dwm_scalp_25-08.py` — 48
combinazioni testate.

**Risultato**: 0/5 finestre su TUTTE le 48 combinazioni, PF che non
supera 0.52 nemmeno nel caso migliore. Importante: `risk_dist` mediano
resta sano ($2-4, non schiacciato come i $1.22 di CRT) — non è un
problema di costi/stop troppo stretto, è che il meccanismo stesso
("fare fade di uno sweep D/W/M con un target fisso") non ha edge
direzionale, punto. La frequenza era comunque buona (fino a 3.4
trade/giorno) — non è un problema di "non scatta abbastanza".

**Nessuna azione**: idea scartata, nessun codice toccato.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - CRT Costi-Dominanti Confermati, Elliott H4 BUY-only Attivata (25-08)]]
