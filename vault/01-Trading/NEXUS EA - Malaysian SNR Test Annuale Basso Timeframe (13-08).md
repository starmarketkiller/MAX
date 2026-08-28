---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, malaysian-snr, escluse, basso-timeframe]
created: 2026-08-13
updated: 2026-08-13
---

# Malaysian SNR su Gold — test annuale basso timeframe (13/08)

Ricerca su M15/M5/M1 (QML base + varianti QMX stretta/lasca), in continuità
con [[NEXUS EA - MALAYSIAN_SNR Porting Tier 1 (Specifica Tecnica)]] e la
chiusura dell'11/08 ([[NEXUS EA - Strategie Escluse, Analisi Una-ad-Una (11-08)]]
§1/§3). Prezzi: candele M1 BID/ASK Dukascopy — non lo spread del broker
offshore reale dell'utente. Modello base: commissione $7/lotto, slippage
$0.05; stress: spread ×1.5, commissione $10/lotto, slippage $0.15. Leva
1:500 non crea edge (incide su margine/lotto, non su PF/expectancy).

## Verdetto

**Nessuna variante va abilitata live, rischio 5% non applicato.** Coerente
con lo stato già chiuso l'11/08 — nessun cambio di codice necessario.

## Il collo di bottiglia è la qualità, non la frequenza

QML base non manca di segnali: 192 trade (M15), 453 (M5), 1.103 (M1) nei
fold di sviluppo. Su M5: 4.478 zone → 25.790 touch → 2.819 conferme armate
→ 1.485 rotture struttura → **78 confluenze QMX** (il filtro più
selettivo) → 55 segnali → 52 trade eseguiti. Nessuno dei tre fold QML base
è positivo dopo i costi su nessun timeframe — allentare i blocchi
aumenterebbe l'esposizione a segnali già classificati senza edge netto,
non è la leva giusta.

## Esito per rapporto setup→esecuzione (QMX lasca)

| Ordine | Setup → esecuzione | Trade sviluppo | Fold positivi | Exp. sviluppo (R) | Trade validazione | PF validazione | Exp. validazione (R) | Verdetto |
|---|---|---|---|---|---|---|---|---|
| 1 | H1 → M15 | 26 | 1/3 | 0.09 | n/a | n/a | n/a | FAIL sviluppo |
| 2 | M30 → M5 | 52 | 3/3 | 0.25 | 17 | 0.55 | -0.36 | FAIL validazione |
| 3 | M15 → M1 | 123 | 0/3 | -0.37 | n/a | n/a | n/a | FAIL sviluppo |

QMX stretta è troppo rara per essere valutata (1 trade su M15, 0 su M5, 4
su M1).

## I costi spiegano M1, non il fallimento M5 in validazione

M5 in sviluppo conserva un margine netto (+0.251R). M1 è quasi piatto
lordo (+0.005R) ma i costi lo affondano (-0.372R, costi ≈ -0.377R/trade) —
**economicamente inadatto**, non serve nemmeno riverificarlo con un broker
più economico. M5 invece fallisce la validazione **anche lordo**
(-0.199R/trade prima dei costi): non è un problema di costi, è un
problema di generalizzazione — il segnale che funziona nello sviluppo non
regge nel regime della validazione.

## Prossimi passi consigliati (dalla ricerca)

1. Concentrare la V4 su **M30→M5** — unico rapporto con 3/3 fold di
   sviluppo positivi. M1 sospeso finché l'edge lordo non supera i costi.
2. Aggiungere un filtro di contesto *prima* del prossimo test, testato uno
   alla volta: origine dell'impulso/fresh SNR, direzione/pendenza
   trendline, qualità dell'engulf QMX, distanza dal prossimo livello
   opposto, sessione/volatilità.
3. Acquisire un secondo periodo fresco come holdout finale (la validazione
   2024 è già stata osservata — riusarla come test finale sarebbe
   adattamento retrospettivo).
4. Confermare i finalisti su tick grezzo + contratto broker reale (stop
   level, lotto minimo, commissioni vere) prima di qualunque promozione.

Domande aperte per la V4: cosa distingue i 52 trade QMX positivi in
sviluppo dai 17 negativi in validazione; se il valore viene dalla
geometria QMX o dal regime di volatilità/sessione in cui compare; se le
ancore della trendline vanno selezionate con la regola 1/2+Sequence
invece della tolleranza geometrica attuale.

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - MALAYSIAN_SNR Porting Tier 1 (Specifica Tecnica)]] ·
[[NEXUS EA - Strategie Escluse, Analisi Una-ad-Una (11-08)]]
