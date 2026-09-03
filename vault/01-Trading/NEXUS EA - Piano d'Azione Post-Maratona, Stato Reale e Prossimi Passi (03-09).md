---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, piano, roadmap, candlestick, gestione, mt5-library]
created: 2026-09-03
updated: 2026-09-03
---

# NEXUS EA — Piano d'azione post-maratona: stato reale, cosa manca, prossimi passi

## Perché questa nota

Fine di una sessione lunghissima (01-03/09) con molti filoni intrecciati.
L'utente ha chiesto onestà sullo stato reale, un piano d'azione strutturato
dal mancante al presente, e più iniziativa da parte mia nel capire cosa
controllare senza doverlo chiedere ogni volta. Questa nota è il punto di
ripartenza per la prossima sessione dopo `/clear`.

## Stato reale — cosa è VERAMENTE completato

**Solo SAR è a uno stato di verifica solido e chiuso.** Tutto il resto è
esplorazione in corso, alcune piste chiuse con una risposta (anche
negativa, ma vera), altre aperte.

| Strategia/filone | Stato | Nota |
|---|---|---|
| **SAR** | ✅ Confermato | Lotto naturale, candle-align H4, 5 finestre tutte positive PF1.37-1.57. Vedi [[NEXUS EA - Sintesi Sessione Maratona SAR-EMA_PULLBACK-Scalp-RegimeVeto (01-02-09)]] |
| SAR — 9 raffinamenti (SLReclaim, breakeven, parziali ecc.) | ✅ Chiuso (falliti) | Risposta definitiva: l'edge vive nel lasciare correre fino a TP largo |
| SAR — veto di regime | ✅ Chiuso (bocciato) | Bug trovato e corretto (ADX su TF sbagliato), testato dopo il fix: peggiora la baseline |
| SAR — parziale a pip fissa / volume | ✅ Chiuso (fallito) | Stesso esito dei 9 raffinamenti precedenti |
| EMA_PULLBACK | ✅ Confermato robusto | PF1.41 nudo, nessun filtro trovato migliora |
| BAR_UPDN / BREAKOUT_ACC (scalp) | ✅ Chiuso (falliti) | PF0.72/0.64 anche dopo fix bug di inseguimento |
| **PIVOT_WICK** (strategia nuova) | 🔶 In corso | tpMult=1.0 confermato ancora negativo su 10 mesi (PF0.90, -$844, 1538 trade). OneShotLevel testato isolato: -28% trade ma WR/payoff invariati (0.79→0.77 PF) — riduce volume, non cambia l'edge. Vedi [[NEXUS EA - PIVOT_WICK step2 e OneShotLevel Analizzati, Nessun Fix (03-09)]]. Ipotesi aggiornata: probabile problema di trigger/edge, non di uscita — prossimo test isolato: `RequireWick=true` da solo |
| BOLLINGER + RSI + candela (scalp mean-reversion) | ⬜ Non iniziato | Piano scritto il 02/09, mai eseguito |
| WEEKLY_EXP | ⬜ Non iniziato | Task tracciato da settimane, mai isolato su MT5 |
| RiskShield per-strategia | 🔶 Scritto, non testato dal vivo | Non cambia nulla in isolamento per costruzione |

**Bug strutturali trovati e corretti stanotte** (di sistema, non di
trading — probabilmente i contributi più preziosi della sessione):
1. Terzo cancello `NXS_Profile_Enabled` — whitelist silenziosa, bloccava strategie senza errore visibile
2. Quarto cancello `NXS_StrategyKnown` — contratto di registro separato, stesso sintomo
3. Veto di regime — calcolava l'ADX sul timeframe sbagliato (M15 invece del TF nativo della strategia)

Tutto pushato e **mergiato su `main`** (PR #23, 03/09).

## Perché la sessione è sembrata incasinata

Tre volte un numero sorprendente si è rivelato un artefatto di config
sbagliata, non un risultato vero (lotto fisso scambiato per la baseline,
ATR sbagliato, ReconcileBroker mai chiamata). Ogni volta la causa era la
stessa: troppi file di test simili in una notte lunga, verificato
tardi invece che subito. **Lezione operativa per le prossime sessioni**:
prima di reagire a un numero, controllare SEMPRE quale file/config l'ha
prodotto — mettere questo controllo all'inizio del ragionamento, non alla
fine.

## Piano d'azione — dal mancante al presente

### Fase 0 — Chiudere i filoni aperti adesso (immediato)

1. ~~**PIVOT_WICK step2** (tpMult=1.0) — in coda, aspettare il risultato~~
   **Fatto (03/09, sessione background)**: ancora negativo (PF0.90).
   OneShotLevel testato isolato, stesso esito (riduce volume non edge).
   Vedi nota dedicata. Prossimo: `RequireWick=true` isolato prima di
   continuare col punto 2 sotto.
2. **Filtro candela + re-entry per PIVOT_WICK** (richiesto esplicitamente):
   - Riattivare `InpPivotWickRequireWick=true` e confrontare contro il tpMult più vicino (i due fix potrebbero sommarsi: tpMult risolve "il bersaglio è troppo lontano", il wick risolve "l'ingresso è di bassa qualità" — sono cause diverse dello stesso sintomo)
   - **Re-entry "tipo Xander"**: non è chiaro a cosa si riferisca esattamente questo nome — verificare con l'utente nella prossima sessione, o cercare se esiste un sistema di re-entry pubblico con questo nome prima di implementare alla cieca
   - Idea di re-entry generica da testare comunque: quando uno stop viene colpito e il prezzo INVERTE entro N barre nella direzione originale del trade, ri-entrare una volta (diverso dal bug di inseguimento di BAR_UPDN — lì il problema era rientrare troppo, qui l'ipotesi è che lo stop è troppo stretto e un secondo tentativo dopo l'inversione catturerebbe il vero movimento)

### Fase 1 — Censire quello che MT5 offre già (mai fatto finora)

Ricognizione veloce fatta stanotte, cartella
`MQL5/Experts/Free Robots` del terminale: **28 EA pronti, 7 pattern di
candele giapponesi × 4 oscillatori di conferma (CCI/MFI/RSI/Stoch)**:

- Three Black Crows / Three White Soldiers
- Bullish/Bearish Engulfing
- Bullish/Bearish Harami
- Bullish/Bearish Meeting Lines
- Dark Cloud Cover / Piercing Line
- Hanging Man / Hammer
- Morning Star / Evening Star / Doji Star

~~Da fare (prossima sessione): leggere il codice sorgente di questi 28
(o almeno 1 per famiglia...)~~ **Fatto (03/09, sessione background)**:
lette le 7 logiche di pattern (1 variante RSI per famiglia + verifica
struttura sulle altre 3 oscillatori). Trovato un **bug reale** nel
codice sorgente Piercing Line (if senza graffe → il pattern vero non
segnala mai, il fallback segnala sempre BUY) presente identico nelle
4 varianti — da NON portare così com'è. Dettaglio completo, mappa
copertura vs NEXUS e candidato consigliato (Meeting Lines, unica
famiglia senza filtro di trend impilato) in
[[NEXUS EA - Censimento 28 EA Candlestick Free Robots, Bug Piercing Line Trovato (03-09)]].
Ancora da fare: variante MFI non letta (dedotta per analogia), nessun
backtest ancora fatto sui 4 pattern nuovi (Harami/MeetingLines/
PiercingLine-fix/MorningEveningStar) — solo lettura del codice finora.

**Censimento `Experts/Examples`/`Indicators/Examples` — fatto (03/09)**:
`Experts/Examples` contiene solo demo SDK generiche MetaQuotes
(ChartInChart, Controls, Math 3D, MACD Sample, Moving Average), niente
di utile per strategie. `Indicators/Examples` sono le implementazioni
di riferimento degli indicatori nativi MT5 — non serve portarne il
codice, sono già richiamabili via funzione nativa (`iAlligator`,
`iDeMarker`, `iMFI`, `iForce`, ecc.). Confrontato con `NXS_*.mqh`:
**Ichimoku e Fractals già usati** in NEXUS (ICHIMOKU, Bjorgum zones);
**Alligator/Gator, Heiken Ashi, DeMarker, MFI, Force Index non usati
da nessuna parte** — gap reali, non ancora sfruttati, candidati per
nuovi filtri di contesto o strategie se emerge un'ipotesi concreta (non
aggiungere solo perché disponibili — stessa regola "niente filtri
perché suonano professionali" del Master Roadmap §12).

### Fase 2 — Revisione architetturale dell'EA (mai fatta in modo sistematico)

L'utente chiede esplicitamente: polarità, poligamia (multi-strategia/
multi-posizione concorrente), conferme, correlazioni. Da fare:

1. **Mappare tutti i "cancelli"** (già 4 trovati quest'estate/stanotte:
   profilo TF, profilo enabled, registro strategie, veto di regime) — c'è
   ragione di sospettare che ce ne siano altri non ancora scoperti.
   Metodo: per ogni nuova strategia aggiunta, verificare esplicitamente
   tutti e 4 i cancelli PRIMA di lanciare il primo test, invece di
   scoprire il blocco a posteriori (come successo con PIVOT_WICK)
2. **Come l'EA gestisce operatività concorrente**: quante strategie
   possono avere posizioni aperte insieme sullo stesso simbolo (modalità
   Hedge confermata sul conto), come si distribuisce il rischio tra loro,
   se c'è un vero coordinamento o sono indipendenti (rilevante per capire
   se un conflitto di esposizione tra strategie sta silenziosamente
   danneggiando i risultati quando girano insieme, cosa mai testata
   quest'estate — tutti i test sono stati isolati a una strategia alla
   volta)
3. **Conferme/correlazioni tra strategie**: nessuna strategia oggi
   guarda cosa fanno le altre (es. non aprire in controtendenza a un
   segnale di un'altra strategia più affidabile) — da valutare se vale la
   pena costruire, ma solo dopo aver capito il punto 2

### Fase 3 — Base di conoscenza esterna sul trading (mai iniziata)

Richiesta esplicita dell'utente, con enfasi che **la strategia è solo il
20%, il resto è gestione, disciplina, qualità del segnale non quantità**:

1. Pattern di candele: quali funzionano da sole (i 7 della Fase 1 + le
   varianti classiche: Doji, Spinning Top, Marubozu) vs quali servono
   solo come FILTRO su un altro segnale (quello che PIVOT_WICK sta già
   testando)
2. thepatternsite.com (Bulkowski) — statistiche reali di affidabilità
   per pattern grafici classici (non solo candele: testa/spalla, doppio
   massimo/minimo, triangoli, bandiere) — dati quantitativi, non opinioni
3. Se disponibile, il PDF "All You Need To Know" citato dall'utente —
   chiedere di condividerlo se non è pubblicamente reperibile
4. **Gestione del rischio come argomento a sé** (non solo SL/TP per
   trade): dimensionamento posizione adattivo, gestione della sequenza di
   perdite, quando fermarsi, psicologia — questo è il pezzo esplicitamente
   segnalato come "80% del risultato" e mai affrontato sistematicamente
   in NEXUS finora (solo protezioni reattive tipo ESL/RiskShield, non una
   filosofia di gestione)

### Fase 4 — Sintesi: verso "il miglior EA possibile"

Obiettivo dichiarato dall'utente: un EA capace di adattarsi a qualunque
mercato, rischio, modalità di gestione. Questo è un obiettivo a lungo
termine, non un singolo prossimo passo — il valore di questa nota è
scomporlo: Fase 1-2 sono infrastruttura (sapere cosa c'è, capire come
gira davvero), Fase 3 è conoscenza di base (senza la quale si continua a
scoprire per tentativi quello che la letteratura di trading già sa),
Fase 0 è chiudere il lavoro già in mano. **Il "miglior EA al mondo" si
costruisce iterando su questo ciclo, non con un salto unico.**

## Nota su /clear

`/clear` è un comando lato client (resetta la conversazione), non posso
eseguirlo io — l'utente lo lancia quando è pronto. Questa nota è scritta
apposta per essere il punto di ripartenza della prossima sessione: chi
riprende (io o un'altra sessione) dovrebbe leggere prima questa nota,
poi [[NEXUS EA - Sintesi Sessione Maratona SAR-EMA_PULLBACK-Scalp-RegimeVeto (01-02-09)]]
per il dettaglio di cosa è stato verificato.
