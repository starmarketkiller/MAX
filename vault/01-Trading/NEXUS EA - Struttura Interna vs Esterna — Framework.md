---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, struttura, choch, sweep, framework]
created: 2026-07-16
updated: 2026-07-16
---

# Struttura interna vs esterna — framework e primi test (16/07)

Teoria proposta dall'utente, verificata contro il codice esistente e la
letteratura ICT: **struttura interna** = swing minori su timeframe più
basso, **struttura esterna** = swing maggiori su timeframe più alto, e la
reazione su struttura esterna coinvolge più volume/forza di quella
interna. Confermata corretta (vedi ricerca in
[[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]] — "Round 2"),
con una precisazione: in letteratura ICT "interna/esterna" è usata sia in
senso multi-TF (come dice l'utente) sia sullo stesso TF con swing di
ampiezza diversa — due varianti valide della stessa idea.

## Cosa esisteva già nel codice (parziale, incoerente)
- **CHoCH**: `g_struct` (entry TF) e `g_structH1` (H1, calcolata apposta
  per essere "una seconda opinione" — commento esplicito nel codice) —
  ma **zero strategie leggono `g_structH1`**. Infrastruttura pronta, mai
  collegata.
- **Sweep**: `NXS_DetectSweep()` (generico, un estremo di 20 barre
  qualsiasi — di fatto un proxy debole di "interna") vs
  `NXS_DetectSweepExt()` (PDH/PDL/Asia High-Low/equal H-L — genuinamente
  "esterna", livelli di liquidità reali). Usate in modo incoerente: solo
  LIQ_SWEEP era rimasta sulla versione debole (corretto il 16/07, vedi
  [[Liq Sweep]]).
- **Order Block / FVG**: nessuna distinzione — un solo rilevamento a
  scala fissa, non esiste una versione "esterna".

## Infrastruttura costruita sul sito (16/07)
- `_fractal_choch_series()` — CHoCH/trend fedele a
  `NXS_ComputeStructureCore`: pivot fractal simmetrico (`wing` barre),
  trend da HH+HL/LH+LL con isteresi. Sostituisce il proxy rolling-extreme
  usato nei primi test del 16/07 (Turtle Soup mattina, IFVG Blocco 2).
- `_resample_ohlc()` + `_external_choch_series()` — la stessa logica
  applicata a un timeframe superiore **vero** (ricampionamento reale,
  non solo una finestra più larga sullo stesso TF), con forward-fill
  sull'ultima barra esterna completata (nessun look-ahead).
- Disponibili in `ind["choch_int"]` (trend, up, down) e
  `ind["choch_ext"]` (up, down) per qualunque strategia del motore sito.

## Risultato dei primi test: il gate "stesso bar" non funziona, i "due trigger separati" sì

**IFVG e TURTLE_SOUP** (richiedere CHoCH fedele sullo stesso bar del
trigger esistente): risultato **peggiore** del test già negativo di
stamattina — IFVG passa da 41 a 6 a **0** segnali; TURTLE_SOUP passa da
4-9 a **0** su ogni combinazione. Non un problema di soglie: un pivot
fractal richiede barre di conferma dopo di sé, quindi è sempre "vecchio"
di qualche barra — allinearlo esattamente al bar di un altro trigger
specifico è strutturalmente troppo raro. **Conclusione**: aggiungere CHoCH
come gate extra sullo stesso bar di un pattern già specifico non è la
strada giusta.

**LIQ_SWEEP** (interna = `sig_liq_sweep` originale, esterna =
`sig_liq_sweep_ext` ora attiva): qui invece la distinzione **funziona
davvero** — le due danno numeri chiaramente diversi (es. D1+HTF: interna
14 trade/PF3.30, esterna 141 trade/PF1.27; 4h no-HTF: interna PF0.86,
esterna PF1.32) su ogni combinazione testata. Non sono ridondanti, sono
prospettive diverse sullo stesso mercato.

**Lezione**: il valore del framework interna/esterna sta nell'avere **due
varianti separate di un pattern** (come già capita per caso con lo
sweep), non nel gate-are un pattern esistente con una conferma extra
sullo stesso bar. Da tenere a mente prima di applicare l'idea ad altre
strategie (Order Block, FVG, Turtle Soup stesso come pattern a sé).

## Aggiornamento (16/07 sera): ORDER_BLOCK/OB_MIT/FVG_CONT fatti — funziona come "filtro di direzione", non come gate sullo stesso bar

Confermata l'ipotesi lasciata in sospeso sopra: usare la struttura esterna
come **filtro di direzione** (il trend H1 concorda con la direzione del
segnale) invece che come richiesta di un evento CHoCH esatto sullo stesso
bar **funziona bene** — risultato opposto al test IFVG/TURTLE_SOUP.

| Strategia | Config reale | PF prima→dopo | DD% prima→dopo |
|---|---|---|---|
| ORDER_BLOCK | D1+HTF | 1.50→1.77 | 5.85→3.94 |
| OB_MIT | D1 | 1.71→1.80 | 7.15→3.94 |
| FVG_CONT | H4+HTF | 1.45→2.07 | 18.31→12.48 |

Miglioramento consistente su quasi ogni TF/config testato (non solo sul
profilo attuale), sempre a costo di un campione più piccolo (~40-55% in
meno di trade). **Applicato sia al sito che a MQL5** (`g_structH1`,
finalmente collegata dopo essere stata calcolata a vuoto). Per ORDER_BLOCK/
OB_MIT il filtro EMA50/nessun filtro è stato **integrato** col trend
esterno; per FVG_CONT il vecchio filtro EMA50 è stato **sostituito**
interamente. **Nessuna delle tre è ancora validata su MT5 reale.**

Nota di fedeltà importante: sul sito il trend esterno è verificato **al
momento dell'impulso/gap** (ho lo storico completo). In MQL5,
`g_structH1` è solo lo stato **corrente** (nessuno storico per barra) —
il controllo reale lì è "il trend H1 conferma ORA", non "confermava
quando si è formato il pattern". Stessa idea, punto di verifica
leggermente diverso: da tenere presente se i risultati MT5 divergeranno
da quelli del sito più del solito.

## Prossimo candidato
- **LIQ_SWEEP**: oggi ha solo la versione esterna attiva (sostituita alla
  interna). Da valutare se tenere `sig_liq_sweep` (interna) come setup
  separato invece di scartarla — la teoria dell'utente prevede entrambe,
  non una sola. Non ancora fatto.

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]] · [[Liq Sweep]] · [[Ifvg]] · [[Turtle Soup]] · [[NEXUS EA - Principi]]
