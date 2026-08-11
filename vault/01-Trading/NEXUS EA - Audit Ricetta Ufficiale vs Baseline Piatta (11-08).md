---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, audit, walk-forward, mql5-profiles]
created: 2026-08-11
updated: 2026-08-11
---

# Audit: profili MQL5 esistenti vs baseline piatta (11/08)

Richiesta esplicita dell'utente: prima di aggiungere altro, controllare se
tra tutte le modifiche/test fatti in passato esisteva già un profilo
migliore ma non riconosciuto come tale — come è successo con CRT, dove un
"errore" di implementazione (v1) aveva rivelato qualcosa di valido prima
ancora di trovare la versione corretta (v3).

## Perché serviva

Ogni test di QUESTA sessione (walk-forward, riverifica storico ampliato,
ecc.) ha sempre usato una baseline piatta (SL 1.5×ATR / TP 3.0×ATR, niente
filtro HTF, niente breakeven). I profili "ufficiali" in
`NXS_StrategyProfiles.mqh` (SL/TP/HTF/BE per strategia, quasi tutti con
filtro HTF acceso) risalgono a un ciclo di ricerca precedente ("sito",
dati Yahoo) e **non erano mai stati testati con il motore corretto di oggi
sul nuovo storico Dukascopy 2019-2026**.

## Metodo

`profile_recipe_audit.py`: per 26 strategie (13 del nucleo + 13 escluse,
tutte con una voce in `NXS_Profile_Get`), confronto diretto flat vs
ricetta ufficiale, stesso TF di profilo, stesso storico, IS(60%)/OOS(40%).
Poi `profile_recipe_walkforward.py`: le 6 ricette che sembravano
migliori nel confronto singolo, validate a 5 finestre.

**Punto chiave**: le "ricette" testate sono i profili MQL5 **già in
produzione**, non proposte nuove — l'audit verifica se la config
esistente fosse già più forte del flat usato tutta la sessione (analogo
al caso CRT), non se serva un cambiamento.

## Risultati — walk-forward a 5 finestre sui 6 candidati

| Strategia | TF | Ricetta batte flat | Note |
|---|---|---|---|
| FVG_CONT | 4h | **5/5** | margine ampio, n alto (51-95/finestra) |
| TURTLE_SOUP | 1h | **4/5** | n alto (66-204/finestra) |
| EMA_PULLBACK | 1h | **4/5** | n alto (90-110/finestra) |
| SAR | 4h | 3/5 | entrambi comunque profittevoli quasi ovunque, alla pari |
| TSI | 1d | 3/5 | campioni sottili (11-13/finestra), range erratico 0.74-1.9 |
| ADX_RSI | 1d | 3/5 | campioni sottili (13-26/finestra), range erratico 0.7-2.68 |

TSI e ADX_RSI mostrano lo stesso limite strutturale già documentato per
BREAKOUT_ACC su D1: pochi trade per finestra, varianza alta — non è un
difetto del profilo, è la scarsità di barre giornaliere anche su 2.636
giorni di storico.

Le restanti 20 strategie (7 del nucleo + 13 escluse): la ricetta ufficiale
non ha battuto il flat nel confronto singolo IS/OOS, oppure il campione
era troppo sottile per essere informativo (0-19 trade totali su D1 per
molte delle escluse: OB_MIT, ORDER_BLOCK, OTE_CONT, WEEKLY_EXP,
SMS_BMS_RTO, MALAYSIAN_SNR, IFVG, BB_SQUEEZE).

## Conclusione — Fase A e Fase B

**Nessuna modifica al codice necessaria.** L'audit conferma che la
configurazione MQL5 attuale regge (FVG_CONT/TURTLE_SOUP/EMA_PULLBACK) o è
equivalente (SAR/TSI/ADX_RSI) rispetto alla baseline piatta usata tutta
la sessione — non è mai emerso un caso analogo a CRT, dove il "profilo
migliore" era nascosto per errore. Sul gruppo delle 13 strategie escluse
con profilo storico (Fase B): nessuna "perla" trovata — o campione
troppo sottile o nessun miglioramento reale.

Questo è un risultato negativo onesto ma utile: la config demo attuale
(16 strategie) non stava lasciando sul tavolo un profilo migliore già
scoperto in passato.

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - Riverifica su Storico Ampliato (11-08)]] ·
[[NEXUS EA - Config Demo 15 Strategie (10-08)]]
