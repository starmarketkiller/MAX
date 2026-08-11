---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, recovery, grid, drawdown, walk-forward]
created: 2026-08-11
updated: 2026-08-11
---

# Fase C, primo passo: baseline recovery uniforme + scoperta di un buco di misurazione (11/08)

Richiesta esplicita dell'utente (Fase C): partendo dal nucleo, testare
l'aumento del rischio e costruire un sistema di gestione posizioni non a
grid semplice ma con gestione diversa per gamba (recovery, pyramiding),
"operazioni ottimizzate che aiutino solo il trade". Nota dell'utente:
**"recovery, non revolver"** - il concetto da costruire è il recovery
(gambe aggiunte in avversità), non un meccanismo a rotazione separato.

## Cosa esisteva già

Il motore (`run_backtest`) ha da tempo un'infrastruttura "legs" con:
- **pyramiding** (`pyramid_max_legs/pyramid_r/pyramid_risk_mult`): gambe
  aggiunte SUL PROFITTO, opt-in, default off.
- **grid recovery** (`grid_max_legs/grid_step_atr/grid_risk_mult/
  grid_regime_filter`): gambe aggiunte in AVVERSITÀ, porting di
  `NXS_ManageGrid` (MQL5), opt-in, default off. **`InpEnableGrid=false`
  di default nell'EA live** - non è mai stato attivo sul conto demo.

Limite noto: tutte le gambe di una posizione condividono lo stesso SL/TP
- solo size ed entry cambiano per gamba, non la logica di uscita. È
  esattamente il limite che l'utente ha chiesto di superare.

## Passo 1 - baseline: il recovery uniforme (già esistente) aiuta o no?

`recovery_baseline.py`: walk-forward a 5 finestre, con vs senza recovery
(1-2 gambe), sui 5 candidati più solidi del nucleo (CRT, FVG_CONT,
TURTLE_SOUP, EMA_PULLBACK, SAR).

| Strategia | Effetto del recovery (PF/DD "a trade chiuso") |
|---|---|
| CRT | Migliora entrambi, 5/5 finestre |
| FVG_CONT | Migliora molto entrambi, 5/5 finestre |
| TURTLE_SOUP | Neutro/lieve miglioramento |
| EMA_PULLBACK | **Peggiora nettamente** (DD fino a +25 punti) |
| SAR | **Peggiora nettamente** (DD quasi raddoppiato) |

Prima conclusione (prima di scavare oltre): il recovery uniforme **non è
un miglioramento universale** - aiuta le strategie di tipo
breakout/continuazione (un ritracciamento spesso precede la ripartenza)
e danneggia quelle di tipo pullback/mean-reversion (un ritracciamento
profondo è spesso un'inversione vera). Già di per sé un argomento a
favore della richiesta dell'utente: gestione diversa per tipo di setup,
non un meccanismo unico.

## Passo 2 - il numero "troppo bello" e la sua causa

Il miglioramento di drawdown su CRT/FVG_CONT era sospetto (PF piu alto E
drawdown piu basso insieme, insolito per un meccanismo che aumenta
l'esposizione media). Verifica: `max_dd_pct` di `run_backtest` si
aggiorna **solo alla chiusura del trade** (la equity curve non è
mark-to-market bar-per-bar) - non vede l'escursione flottante durante un
trade aperto, ne' l'effetto di una seconda gamba aggiunta proprio nel
punto di massima avversità.

**Fix**: aggiunto `track_floating_dd` (opt-in, default `False`, zero
effetto sul comportamento esistente - solo motore a posizione singola per
ora) a `run_backtest()` (`server/backtest.py`) - marca a mercato ogni
barra tutte le gambe aperte, riporta `floating_max_dd_pct` accanto al
`max_dd_pct` esistente.

Risultato con il nuovo metro, FVG_CONT@4h finestra (0.6-0.8):

| Config | PF | DD chiuso | DD flottante |
|---|---|---|---|
| no_recovery | 1.58 | 11.36% | 11.76% |
| recovery_1leg | 3.39 | **5.86%** | **16.38%** |

Il drawdown "a trade chiuso" del recovery (5.86%) era un'illusione della
metrica - il rischio flottante reale è **più alto** con il recovery
(16.38% vs 11.76%), non più basso. Il miglioramento di PF resta
probabilmente reale (è P&L realizzato, non soggetto a questo bias), ma
"anche il rischio migliora" era falso.

## Passo 3 - scoperta collaterale: CRT ha un rischio flottante strutturale

Su CRT@30m, **anche senza recovery**: DD chiuso 35.0%, DD flottante
**107.16%**. Causa: lo stop di CRT è ancorato al wick della candela di
sweep (non un multiplo ATR) - quando il wick è minimo, `risk_dist` è
piccolissimo, e il target (lato opposto del range) può essere lontano.
Questo produce trade con multipli-R realizzati anche molto alti quando
funzionano (visto fino a 40.96R su un campione di 200 trade) - parte del
motivo per cui il PF di CRT è così forte - ma anche escursioni flottanti
enormi quando un trade si avvicina al target e poi inverte prima di
chiuderlo (il "picco" flottante mai realizzato gonfia il picco della
curva, la successiva chiusura a -1R sembra un crollo enorme rispetto a
quel picco fantasma).

**Non è un rischio di conto attivo oggi** (CRT gira senza recovery, size
fissa per rischio_pct, i trade realizzati restano correttamente limitati
a -1R sul lato perdita) - ma è un avvertimento reale per qualunque
sistema futuro che decida size/aggiunte di gambe guardando l'equity
flottante (come un recovery/pyramid dinamico), e per l'esecuzione live
(uno stop tecnico molto stretto è più vulnerabile a gap/slippage di uno
stop ATR-scaled).

## Conclusione e prossimo passo

1. Il recovery uniforme non va bene per tutte le strategie - conferma la
   richiesta dell'utente di differenziare per gamba/scenario.
2. Il drawdown "a trade chiuso" non basta per giudicare un sistema di
   recovery/pyramid - va sempre affiancato dal drawdown flottante (ora
   disponibile via `track_floating_dd=True`).
3. CRT (la strategia più solida del nucleo) ha una caratteristica
   strutturale (stop stretto su sweep minimi) da tenere presente prima di
   usarla come base per un sistema a gambe multiple.

Prossimo passo: progettare la gestione per-gamba differenziata
(recovery con uscita propria, non lo stesso SL/TP della gamba originale)
solo sulle strategie dove il recovery uniforme ha già mostrato un
vantaggio anche sul drawdown flottante (da riverificare con il nuovo
metro prima di procedere).

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - Audit Ricetta Ufficiale vs Baseline Piatta (11-08)]] ·
[[NEXUS EA - Riverifica su Storico Ampliato (11-08)]]
