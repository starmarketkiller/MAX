---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, combinazioni, ensemble, ricerca]
created: 2026-08-10
updated: 2026-08-10
---

# Ricerca combinazioni multi-strategia — tre metodi indipendenti, stessa conclusione

Sessione del 10/08, su dati Dukascopy XAUUSD reali (storico pieno dopo
il fix del bug `bars`/`_fetch_dukascopy` — vedi
[[NEXUS EA - MALAYSIAN_SNR Porting Tier 1 (Specifica Tecnica)]] per il
dettaglio del bug). Tre tentativi indipendenti di trovare una
combinazione di strategie che batta la singola migliore, con metodi
diversi apposta per non ripetere lo stesso errore.

## Perché insistere sulle combinazioni
L'utente ha chiesto esplicitamente di non limitarsi alle 2-3 strategie
già andate bene (MACD/TURTLE_SOUP/BREAKOUT_ACC), ma di testare un pool
molto più ampio (10-15+ strategie, incluse quelle deboli) per vedere se
insieme — non singolarmente — formano un motore migliore. Ipotesi:
segnali di continuazione/ritracciamento letti oggi come singoli
potrebbero comporsi in qualcosa di più forte.

## Metodo 1 — accordo unanime, pool piccolo (Fase 2, `auto_combo_search.py`)
12 strategie forti, tutte le singole/coppie/triple (298 combinazioni),
voto UNANIME richiesto sulla stessa barra, split IS(60%)/OOS(40%)
integrato. **Nessuna combinazione batte le singole migliori.**

## Metodo 2 — pipeline gerarchica master→slave (Fase 3c, `phase3c_bias_pipeline.py`)
Non un voto simultaneo: il bias di BREAKOUT_ACC persiste, le altre 34
strategie eseguono solo se allineate. Alcuni miglioramenti isolati
(SAR, FVG_CONT, TSI) ma nessun vero "motore collettivo" — resta
un filtro a due strategie alla volta, non una combinazione ampia.

## Metodo 3 — ricerca greedy di un ensemble a voto, pool ampio (`ensemble_engine_search.py`)
Il test più diretto alla richiesta: pool di 20 strategie (tutte con
≥30 trade individuali su storico pieno, deboli incluse — non solo le
3 buone), ricerca greedy fino a 15 membri, voto a soglia (non unanime,
con 15 membri sarebbe irraggiungibile), punteggio robusto
(`expectancy_R × √trade`, non PF grezzo) per non ripetere l'errore del
primo tentativo (vedi sotto).

**Bug scoperto e corretto durante lo sviluppo**: la prima versione
usava PF grezzo con soglia minima di 8 trade — la ricerca convergeva
su JUDAS_SWING/IFVG/BB_SQUEEZE/SMS_BMS_RTO/MALAYSIAN_SNR (le stesse
strategie già segnalate come troppo rare per giudicare, vedi
[[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]]), PF
in-sample fino a 9.51 su 8-20 trade, OOS in perdita (PF 0.4-0.66) —
overfitting da manuale sull'ensemble stesso. Corretto: pool filtrato a
strategie con campione individuale reale, punteggio con penalità
continua sul campione piccolo invece di un taglio secco.

**Risultato dopo la correzione**: l'OOS peggiora quasi monotonicamente
a ogni strategia aggiunta.

| Round | Combo | OOS PF |
|---|---|---|
| 1 | MACD da sola | **1.58** |
| 5 | +4 strategie | 1.18 |
| 10 | +9 strategie | 1.13 |
| 15 | 15 strategie | 1.13 |

Verificato anche con soglie di voto fisse (non solo quella scelta dal
greedy) da 1 a 8 sul pool finale a 15: a campioni credibili (mv 1-3,
62-233 trade) nessuna soglia batte MACD da sola (1.58). A mv=4-5 il PF
sembra ottimo (2.75 su 17 trade, 3.88 su 3) ma sono campioni troppo
piccoli per fidarsene — e sceglierli a posteriori guardando l'OOS
sarebbe esattamente l'errore di disciplina che questa sessione ha
sempre evitato altrove.

## Conclusione
Tre metodi indipendenti (accordo unanime su pool piccolo, pipeline
gerarchica, voto greedy su pool ampio) arrivano alla stessa risposta:
**nessuna combinazione trovata finora batte la singola strategia
migliore (MACD, o TURTLE_SOUP/BREAKOUT_ACC a seconda del taglio
temporale)**. Non è una prova che non esista una combinazione buona —
lo spazio di ricerca è enorme (C(35,15) è intrattabile, nessun metodo
qui è stato esaustivo) — ma tre tentativi seri con metodi diversi non
l'hanno trovata.

## Dove guardare ancora, se si vuole insistere
- **Pesi diversi per membro** invece di un voto uniforme (una strategia
  "vale" più delle altre nel conteggio) — non testato in nessuno dei
  tre metodi sopra.
- **Combinazione condizionata al regime** (vedi il filtro di direzione
  dinamico proposto in [[NEXUS EA - MALAYSIAN_SNR Porting Tier 1 (Specifica Tecnica)]]
  — non ancora implementato) invece di una combinazione statica sempre
  attiva.
- **Storico più lungo**: con solo ~3,9 anni disponibili (in crescita),
  uno split 60/40 lascia comunque finestre dominate da un unico regime
  di mercato (vedi la scoperta "BUY-only = trend, non struttura" nello
  stesso documento) — più storico potrebbe rivelare pattern di
  combinazione che qui restano nascosti nel rumore di un solo regime.
- **Bitcoin** (dati già disponibili via Yahoo, 10 anni, cicli toro/orso
  veri) come banco di prova incrociato, non ancora esteso alla ricerca
  di combinazioni (finora usato solo per il test direzionale nel
  documento MALAYSIAN_SNR).

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - MALAYSIAN_SNR Porting Tier 1 (Specifica Tecnica)]] ·
[[NEXUS EA - Hedge nel Tempo]] ·
[[NEXUS EA - Motore Sito - Audit e Confronto 10Y]]
