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

## Prossimi candidati (non ancora fatti)
- **LIQ_SWEEP**: oggi ha solo la versione esterna attiva. Valutare se
  tenere anche `sig_liq_sweep` (interna) come setup separato invece di
  scartarla — la teoria dell'utente prevede entrambe, non una sola.
- **ORDER_BLOCK / OB_MIT / FVG_CONT**: nessuna versione esterna esiste.
  Da costruire (impulso/gap che nasce da/coincide con una rottura di
  struttura esterna) prima di giudicare se aiuta — non testato ancora.
- **g_structH1 su MQL5**: la proposta originale (collegarla come conferma
  incrociata) resta in sospeso — dato il risultato negativo del test
  "stesso bar" sul sito, andrebbe ripensata come **filtro di direzione**
  (concorde/discorde con l'esterna) più che come richiesta di CHoCH
  esatto sullo stesso bar, prima di portarla su MQL5 dove tocca strategie
  già live.

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]] · [[Liq Sweep]] · [[Ifvg]] · [[Turtle Soup]] · [[NEXUS EA - Principi]]
