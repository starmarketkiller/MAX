---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, escluse, molteplicità, bugfix]
created: 2026-08-11
updated: 2026-08-11
---

# Strategie escluse dal nucleo — analisi una-ad-una (11/08)

Richiesta esplicita dell'utente: applicare alle 34 strategie escluse lo
stesso metodo usato per il nucleo (vault prima, poi git, poi test sul
motore vero), una alla volta, cercando miglioramenti reali.

## 1. MALAYSIAN_SNR_BREAKOUT — chiuso, nessun miglioramento

Il vault (nota MALAYSIAN_SNR Porting Tier 1) aveva già la risposta: IS
37 trade PF 0.74 (in perdita), OOS 32 trade PF 1.88. Con la disciplina
IS-blind di tutta la sessione questa configurazione non verrebbe mai
scelta — il numero attraente è solo sull'OOS, l'IS dice il contrario.
Stesso pattern già visto con BREAKOUT_ACC su 1d. Nessun test aggiuntivo
necessario, il vault aveva già chiuso la domanda.

## 2. Le varianti "_v2" — 3 bug reali trovati e corretti

Git log (`2a5c2f1`) rivela che le 5 varianti "_v2" (portate da un brief
esterno, "Decomposizione Edge Strategie NEXUS") avevano 3 bug REALI
documentati e mai corretti (portati fedelmente, "non corretti
silenziosamente"), confermati a 0 trade:

- **SILVER_BULLET_V2**: check "FVG fresh" auto-referenziale — la barra
  che definisce il bordo del gap veniva confrontata contro se stessa
  (sempre vera), quindi `fresh` era sempre falso.
- **FVG_CONT_V2**: check "EntryAt50Pct" auto-referenziale — stesso
  meccanismo (`fvg_hi` definito come la barra corrente, sempre sopra il
  proprio centro per costruzione).
- **OTE_CONT_V2**: `fib618`/`fib705` invertiti sul lato SELL —
  intervallo impossibile (soglia superiore più bassa di quella
  inferiore), 0 trade SELL garantiti.

### Corretti e testati (storico ampio, walk-forward a 5 finestre)

| Strategia | TF | IS→OOS | Walk-forward | Verdetto |
|---|---|---|---|---|
| SILVER_BULLET_V2 | 15m | 2.19/22 → 1.52/13 | erratico, campioni 3-13/finestra | **troppo sottile per giudicare** |
| FVG_CONT_V2 | 4h | 1.11/50 → 1.73/42 | 3/5, oscilla 0.63-2.32 | **reale ma non ancora robusto** |
| OTE_CONT_V2 | tutti i TF | 0 trade anche dopo il fix | — | **strutturalmente morto** (lato BUY già quasi tautologico di suo, indipendente dal bug SELL) |

Nessuno dei tre è pronto per il nucleo, ma **il fix era comunque
corretto da fare**: passare da "0 trade, dead code" a "segnali reali,
seppur deboli" è di per sé un miglioramento onesto rispetto a codice
rotto ereditato da un brief esterno mai verificato. FVG_CONT_V2 è il più
promettente dei tre — da tenere d'occhio, stesso status di
TURTLE_SOUP_CHOCH (promettente, non confermato).

## 3. Famiglia SNR/MSNR — chiusa (vedi nota dedicata)
Tutte e 5 le varianti (rejection, Stadio 1, Stadio 3, RETEST,
RETEST+gate fuori-range) testate a fondo, nessuna regge un test onesto
sul motore vero. Dettaglio in "MALAYSIAN_SNR Porting Tier 1" e
"Riverifica su Storico Ampliato".

## 4. ORDER_BLOCK / OB_MIT — fonte "Secret of 4.11" trovata, rimandata
Esiste una fonte intera mai implementata (ciclo ZIKIR: breakout doppio→
pullback→entry, registro ISL/HSL, 5 tipi di Engulfing) che si
applicherebbe a ORDER_BLOCK/OB_MIT/FVG_CONT/FVG_MIT/IFVG e potenzialmente
BREAKOUT_ACC/TURTLE_SOUP/LIQ_SWEEP/SH_BMS_RTO. Portata paragonabile a
MSNR Tier 1 (un giorno di lavoro, alla fine nessun edge). **Su scelta
esplicita dell'utente, rimandata** — si continua il giro veloce sulle
altre, si torna qui solo se emerge un segnale forte altrove.
[[NEXUS EA - Fonte Secret of 4111 (Ali Yusoff)]]

## 5. Batch veloce (vault-only, nessun codice necessario)
- **BJORGUM**: bug reale già trovato e corretto (proxy testava
  tutt'altra strategia). "Back Check"/conferma flip testata e respinta.
  Config già ottimizzata, resta negativa nel lungo periodo (-8.6R reali).
- **ICHIMOKU**: disabilitata per rumore reale su MT5, non un problema di
  trigger.
- **RSI_DIV**: bug reale già corretto (vera divergenza, non rientro RSI
  generico). Config già ottimale. Resta un caso "segnale Python
  confermato, MT5 reale smentisce" — problema di esecuzione live, fuori
  scope per un fix di trigger.
- **STRUCT_REACT**: disabilitata per perdite reali confermate su MT5.
- **JUDAS_SWING**: TP dinamico già applicato. Rara per costruzione
  (finestra sessione 3h + sweep + CHoCH), non un caso di rigidità da
  correggere.
- **PO3**: TP dinamico già applicato, numeri già discreti (census OOS
  1.44/22) per una strategia a bassa frequenza per design.
- **SH_BMS_RTO**: caso reale di troppa rigidità (4 condizioni
  simultanee sulla stessa barra, come CISD) — ma **SH_BMS_RTO_V2 ha già
  risolto il problema** con una state machine multi-barra (SWEPT→
  WAITING→segnale), da cui il suo campione molto più ampio (224 OOS vs
  17). Nessun fix aggiuntivo necessario.
- **WEEKLY_EXP**: nota vault stale (diceva "0 trade"), il censimento di
  oggi mostra che scatta regolarmente (IS 1.06/54, OOS 1.09/39) — nessuna
  rigidità flaggata, solo dati preliminari.

## 6. IFVG e SMS_BMS_RTO — stesso fix "CHoCH a finestra" di TURTLE_SOUP, esiti opposti

Entrambe condividevano la stessa struttura di IFVG (già diagnosticata in
16/07): un CHoCH fractal fedele richiesto **sullo stesso bar** di altre
2-3 condizioni indipendenti (gap/failure-swing/rejection/discount-premium)
— la nota vault di IFVG aveva già generalizzato l'insight ("vero anche
per TURTLE_SOUP, non solo qui") ma non era mai stata applicata a se
stessa né a SMS_BMS_RTO. Corretta anche una claim vault obsoleta:
SMS_BMS_RTO diceva "non testabile sul motore sito" (proxy dichiarato) —
falso dal 04/08, esiste un'implementazione reale fedele.

Registrate `IFVG_CHOCH_WINDOW` (4h, vero TF di profilo) e
`SMS_BMS_RTO_CHOCH_WINDOW` (1d, vero TF di profilo), stessa detection
CHoCH fractal ma entro una finestra di 5 barre invece che sulla barra
esatta:

| Strategia | Baseline | Windowed | Verdetto |
|---|---|---|---|
| IFVG (4h) | 0.59/3 IS, quasi zero OOS | **3.32/7 IS, 1.53/10 OOS** — walk-forward volatile (0,0,6.71,7.9,0) | **promettente, non confermato** (stessa cautela di FVG_CONT_V2) |
| SMS_BMS_RTO (1d) | 0 trade strutturali ovunque | 1.15/5 IS, **0.0/2 OOS** — walk-forward quasi tutto a PF 0 | **negativo** |

Il fix sblocca il pattern in entrambi i casi (prova che l'architettura
"finestra invece di stesso-bar" è generalmente corretta), ma solo IFVG
mostra un segno diretto positivo — SMS_BMS_RTO resta debole anche
sbloccato, coerente con l'AND a 4 condizioni indipendenti già diagnosticato
come strutturalmente raro anche da sbloccato. Dettaglio in [[Ifvg]] e
[[Sms Bms Rto]].

## 7. NY_REVERSAL — stesso fix, qui negativo (importante: il fix non è universale)

Stessa struttura di IFVG/SMS_BMS_RTO (CHoCH sulla stessa barra dello
sweep+reclaim del range di Londra). Registrata `NY_REVERSAL_CHOCH_WINDOW`,
testata su 1h e 30m: a differenza di IFVG, qui il fix **peggiora** — il
campione cresce 3-4x ma il PF scende verso 1.0 e il drawdown esplode (30m:
IS dd 6.3%→25.4%, OOS dd 5.7%→16.8%). La OOS 4.92/11 della baseline sul 1h
era quasi certamente rumore (walk-forward oscilla 0-8.28), ma la finestra
non lo sostituisce con edge vero, solo con più trade mediocri.

**Conclusione generale sulla famiglia "CHoCH a finestra"**: non è un fix
universale. Funziona quando il pattern di base ha edge reale offuscato da
un timing troppo rigido (IFVG, FVG_MIT_WINDOW, TURTLE_SOUP_CHOCH — tutti
"promettenti"), non quando il pattern di base non ha edge (SMS_BMS_RTO,
NY_REVERSAL — entrambi negativi). Dettaglio in [[Ny Reversal]].

## 8. BB_SQUEEZE, DISP_REBAL — chiusi, vault-only

- **BB_SQUEEZE**: disabilitata per campione troppo piccolo su MT5 (0
  trade in 3 mesi/3 anni nel build reale). Nessuna rigidità diagnosticata
  nel codice — thin per rarità del setup (squeeze di volatilità), non per
  un bug. Nessun fix proposto, serve solo più storico live.
- **DISP_REBAL**: disabilitata per perdite reali confermate su MT5 (test
  v2.3.1: 10 trade, -53$, WR 30%). Non un problema di rigidità/trigger —
  il pattern scatta (103 setup rilevati in 3 mesi) ma perde quando
  eseguito. Chiuso, nessun margine di miglioramento realistico via fix di
  trigger.

## Prossimi passi
Restano da coprire: BOLLINGER/RANGE_FADE (proxy dichiarato), LIQ_VOID
(proxy dichiarato di FVG_CONT), ORDER_BLOCK_V2, OTE_CONT (v1),
SCALP_BB_FADE/EMA/RANGE_BRK/RSI_SNAP (in corso — PF vicino/sopra 1 ma
drawdown 35-79% su 15m, ipotesi filtro di regime/volatilità da testare),
SH_BMS_RTO_V2 (numeri già buoni, verificare solo se manca qualcosa),
SILVER_BULLET (v1).

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - CISD_TRUE (versione vera, negativa) e Censimento Completo (11-08)]] ·
[[NEXUS EA - MALAYSIAN_SNR Porting Tier 1 (Specifica Tecnica)]]
