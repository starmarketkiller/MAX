---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, candlestick, mt5-library, research, bug]
created: 2026-09-03
updated: 2026-09-03
---

# NEXUS EA — Censimento dei 28 EA candlestick "Free Robots", bug trovato in Piercing Line (03/09)

## Perché

Fase 1 del [[NEXUS EA - Piano d'Azione Post-Maratona, Stato Reale e Prossimi Passi (03-09)]]:
leggere il codice sorgente dei 28 EA in `MQL5/Experts/Free Robots`
(7 pattern di candele × 4 oscillatori di conferma CCI/MFI/RSI/Stoch) per
estrarre la LOGICA di riconoscimento pattern — non per usarli così come
sono, ma per portare in NEXUS (stile BAR_UPDN/PIVOT_WICK) i pattern non
ancora coperti. Letta una variante RSI per famiglia (`CheckPattern()` +
`CheckConfirmation()` + `CheckCloseSignal()`), verificato poi che la
struttura è identica tra oscillatori (solo l'indicatore di conferma
cambia). Sono EA campione standard MetaQuotes (MQL5.com), non scritti
da noi.

## Le 7 logiche di pattern (estratte dal codice, non dai nomi)

Tutte con soglia relativa al corpo medio (`AvgBody`, media mobile del
corpo delle ultime N candele, N = `InpAverBodyPeriod`), valutate su bar
chiuse (index 1/2/3, mai bar 0 → nessun repaint):

1. **3 Black Crows / 3 White Soldiers**: 3 candele consecutive con corpo
   > media, stesso colore, midpoint (High+Low)/2 in sequenza
   decrescente (crows) o crescente (soldiers).
2. **Engulfing** (bull/bear): candela 2 di colore opposto alla 1,
   corpo 1 > media, close/open della 1 "ingloba" open/close della 2,
   **richiede anche un trend precedente** (`MidOpenClose(2)` vs
   `CloseAvg(2)`, media dei close) nella direzione da invertire.
3. **Harami**: stesso schema di Engulfing ma invertito (candela piccola
   dentro il corpo della precedente, grande e sopra media) + stesso
   filtro di trend precedente.
4. **Meeting Lines**: due candele lunghe (> media) di colore opposto il
   cui close converge (`|Close1-Close2| < 0.1×AvgBody`) — **nessun
   filtro di trend**, unica famiglia senza questo requisito.
5. **Dark Cloud Cover / Piercing Line**: candela lunga seguita da una di
   colore opposto che apre oltre l'estremo della precedente (gap) e
   chiude dentro il corpo della precedente, + filtro di trend. **Bug
   trovato, vedi sotto.**
6. **Hanging Man / Hammer**: corpo nel terzo superiore del range
   (ombra inferiore lunga), + filtro di trend + gap del corpo rispetto
   alla candela precedente.
7. **Morning/Evening Star + varianti Doji**: pattern a 3 candele,
   candela centrale piccola (doji: <10% AvgBody, star: <50% AvgBody),
   gap o chiusura oltre il midpoint della prima candela.

**Conferma** (in tutte le famiglie, stessa struttura): il pattern da
solo non basta, deve allinearsi con l'oscillatore in zona estrema —
RSI<40/>60, Stoch<30/>70, CCI<-50/>+50 (MFI non ancora verificato, per
analogia probabile <30/>70). **Uscita**: non è la logica del pattern
inverso, ma l'oscillatore che rientra dalla zona estrema (RSI che
riattraversa 30 o 70) — coerente con l'impostazione "pattern +
oscillatore" come sistema di mean-reversion in ipercomprato/ipervenduto,
non un sistema di trend-following.

## Bug reale trovato — Piercing Line, tutte e 4 le varianti

In `CheckPattern()` di `DarkCloud PiercingLine {CCI,MFI,RSI,Stoch}.mq5`
(riga ~573-582, identico nelle 4), il blocco Piercing Line è scritto
senza graffe sull'`if`:

```mql5
if((Close(1)-Open(1)>AvgBody(1)) && ... && (Open(1)<Low(2)))
   return(true);              // <- unico statement legato all'if
  {
   ExtPatternDetected=true;    // <- blocco NON condizionale: gira
   ExtSignalOpen=SIGNAL_BUY;   //    SEMPRE se l'if sopra è falso,
   ExtPatternInfo="...";       //    MAI se l'if sopra è vero
   ExtDirection="Buy";
   return(true);
  }
```

Effetto: se le condizioni del vero pattern Piercing Line sono
soddisfatte, la funzione ritorna `true` **prima** di impostare
`ExtPatternDetected`/`ExtSignalOpen` → il pattern rilevato non genera
mai un segnale reale. Se le condizioni sono false, il blocco sotto gira
comunque senza condizione → segnale BUY "Piercing Line" **ogni volta**
che si arriva a quel punto senza aver già trovato Dark Cloud Cover.
In pratica: Piercing Line com'è scritto qui **non testa il pattern**,
apre BUY quasi sempre (falso positivo strutturale). Bug di sorgente
MetaQuotes, non nostro — ma va evitato di portarlo in NEXUS così com'è,
va riscritto con le graffe corrette.

## Copertura vs NEXUS — cosa manca davvero

| Pattern | In NEXUS oggi | Note |
|---|---|---|
| 3 Black Crows/White Soldiers | Non presente come strategia dedicata | Vicino a BAR_UPDN ma non identico (BAR_UPDN è single-bar momentum, questo è 3-bar sequenza midpoint) |
| Engulfing | Non presente | — |
| **Harami** | **Assente** | Segnalato dalla nota post-maratona come mancante |
| **Meeting Lines** | **Assente** | Idem — unica famiglia senza filtro di trend, potenzialmente più "pulita" da testare isolata |
| **Dark Cloud/Piercing Line** | **Assente** | Piercing Line da riscrivere (bug sopra), Dark Cloud Cover ok così com'è |
| Hanging Man/Hammer | Parzialmente coperto (PIVOT_WICK usa wick di rigetto, logica imparentata ma non identica: qui serve anche il filtro di trend e il gap di corpo) | — |
| **Morning/Evening Star (+ Doji)** | **Assente** | 4 varianti (star/doji × bull/bear), pattern a 3 candele mai provato in NEXUS |

## Non ancora verificato

- Variante MFI non letta (solo dedotta per analogia dalle altre 3).
- `MQL5/Experts/Examples` e `MQL5/Indicators/Examples` (indicatori
  nativi: ADX, Ichimoku, Fractals, Gator, Heiken Ashi, DeMarker, Force
  Index, MFI) — censimento non ancora fatto, restava come punto
  secondario della Fase 1.
- Nessuno di questi 4 pattern nuovi (Harami/MeetingLines/PiercingLine-
  fix/MorningEveningStar) è stato ancora testato su GOLD — solo lettura
  del codice, nessun backtest.

## Prossima azione consigliata

Non portare i 28 EA così come sono (mean-reversion su oscillatore,
filosofia diversa dal resto di NEXUS). Estrarre invece le 4 logiche
mancanti (Harami, Meeting Lines, Piercing Line corretto, Morning/
Evening Star) come nuove strategie candidate in stile PIVOT_WICK/
BAR_UPDN, poi seguire il protocollo standard (§P2.4 Master Roadmap):
trigger nudo prima, BUY/SELL separati, TF nativo, prima di qualunque
filtro. **Meeting Lines è il candidato più interessante da testare per
primo**: unica famiglia senza il filtro di trend precedente già
impilato, quindi il test più pulito per capire se il pattern grezzo ha
edge indipendente prima di aggiungere altro sopra (stessa lezione
imparata più volte in questa indagine: non impilare filtri prima di
misurare il trigger nudo).

Nessuna modifica al codice MQL5 fatta in questa sessione (solo lettura
del codice terzo) — implementare le nuove strategie richiede accordo
esplicito prima di toccare `NXS_Strategies*.mqh` (vedi
[[feedback_no_live_mql5_without_asking]]).

## Collegamenti
[[NEXUS EA - Piano d'Azione Post-Maratona, Stato Reale e Prossimi Passi (03-09)]] ·
[[NEXUS EA - MASTER ROADMAP v3]] · [[MOC - Trading]] · [[MOC - Strategie]]
