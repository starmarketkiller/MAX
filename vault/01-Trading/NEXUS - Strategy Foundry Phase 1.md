# NEXUS — Strategy Foundry Phase 1: Build Our Own Edge + Mine Open-Source EAs

Nessuna ottimizzazione, nessuna combinazione massiva, nessuna implementazione completa in questa fase — solo specifiche formalizzate e audit del codice open-source, come richiesto.

---

## A. NEXUS Native Strategy Research — 10 ipotesi

Ogni ipotesi è verificata contro il catalogo delle 67 strategie research-implementable (`contracts/strategy-registry.json`) per evitare duplicati diretti; dove la distinzione da una strategia esistente è sottile, è dichiarato esplicitamente nella sezione "differenziazione", non nascosto.

### 1. Failed Breakout Fade (Liquidity Trap Reversal) — *famiglia: failed breakout*

- **Event**: chiusura oltre un massimo/minimo di un range a N barre (barra di breakout); entro K barre successive, il prezzo richiude DENTRO il range originale (fallimento confermato).
- **Observation point**: chiusura della barra di rientro nel range.
- **Entry hypothesis**: il breakout ha innescato stop/liquidità oltre il range; il fallimento intrappola i breakout-trader, che devono coprirsi, alimentando un'inversione attraverso il range e oltre.
- **Invalidation**: nuova rottura oltre l'estremo del breakout fallito (stop naturale).
- **Economic target**: proiezione del range dal punto di rientro, o R multiplo fisso.
- **Features consentite**: range N-barre (da barre STRETTAMENTE precedenti al tentativo di breakout), conteggio barre oltre il range, chiusura di rientro, ATR per lo stop.
- **Potenziale leakage**: il range deve essere definito PRIMA del tentativo di breakout, mai aggiustato dopo aver visto il fallimento.
- **Sample minimo**: ≥40 eventi (H4/D1, multi-anno).
- **Differenziazione**: opposto esatto di BREAKOUT_ACC (che tratta l'accettazione/continuazione) — qui si scommette sul fallimento, non sull'accettazione. Nessun duplicato nel catalogo.

### 2. Volatility Compression Percentile Breakout — *famiglia: volatility compression/expansion*

- **Event**: ATR(14) sotto il proprio percentile N (es. 15-20°) su una finestra rolling (es. 100 barre) per almeno M barre consecutive (regime di compressione), seguito da una chiusura direzionale fuori dal range di consolidamento con true range in espansione (>1.5x ATR recente).
- **Observation point**: barra di espansione con chiusura fuori dal range di compressione.
- **Entry hypothesis**: la compressione di bassa volatilità accumula energia (order flow bilanciato); il primo movimento di espansione ad alta convinzione dopo la compressione tende a continuare.
- **Invalidation**: richiusura dentro il range di compressione, o stop 1x ATR.
- **Economic target**: multiplo dell'ampiezza del range di compressione.
- **Features consentite**: percentile ATR rolling (causale, mai forward-looking), range di compressione (solo dalle barre di compressione), rapporto true-range/ATR della barra di espansione.
- **Potenziale leakage**: il percentile deve usare solo dati passati ad ogni barra; non usare l'ATR futuro per giudicare "la compressione era pulita".
- **Sample minimo**: 30-50 eventi compressione→espansione, multi-anno.
- **Differenziazione**: BB_SQUEEZE esiste ma si basa sulla larghezza delle Bollinger Bands, non su un percentile ATR con persistenza minima (M barre) — meccanismo di regime diverso, non solo un secondo indicatore per la stessa idea.

### 3. Impulse-to-Pullback Time Compression Ratio — *famiglia: trend pullback quality*

- **Event**: trend stabilito (prezzo sopra/sotto EMA lenta per X barre) con un pullback la cui durata (in barre) è significativamente più corta dell'impulso precedente (rapporto tempo-impulso/tempo-pullback sopra soglia), combinato con decadimento del momentum contro-trend (RSI/ROC in calo durante il pullback).
- **Observation point**: prima chiusura a corpo pieno nella direzione del trend dopo che il rapporto di compressione temporale è soddisfatto.
- **Entry hypothesis**: un pullback breve rispetto all'impulso che lo precede, con momentum contro-trend in esaurimento, indica profit-taking di mani deboli, non un'inversione genuina.
- **Invalidation**: ritracciamento oltre il 78.6% dell'impulso, o rottura dello swing point precedente.
- **Economic target**: estensione dell'impulso precedente, o R fisso.
- **Features consentite**: pendenza EMA, swing point via frattali CONFERMATI (con il ritardo di conferma correttamente modellato), rapporto tempo impulso/pullback, RSI/ROC.
- **Potenziale leakage**: gli swing point richiedono K barre dopo il pivot per essere confermati — il ritardo va rispettato, non "trovato" il pivot esatto con hindsight.
- **Sample minimo**: ≥50 pullback qualificanti, H4/D1 multi-anno.
- **Differenziazione — VERIFICATA (`sig_ema_pullback`, righe 683-721)**: EMA_PULLBACK esistente richiede trend persistente 5 barre + impulso ≥1.0×ATR (finestra 2-12 barre) + tocco/rejection su EMA20, ma **non usa né il rapporto temporale impulso/pullback né il decadimento di momentum (RSI/ROC)** durante il pullback — sono feature quantitative assenti nell'implementazione reale. La sovrapposizione concettuale (stessa famiglia "trend+impulso+pullback") è reale, ma il meccanismo di selezione è diverso. Classificazione onesta: **MINOR_VARIANT probabile**, non NEW_ENTRY_LOGIC pulita — utile principalmente come test A/B mirato ("il rapporto temporale + decadimento momentum migliora la selezione rispetto alla sola rejection?") più che come strategia indipendente.

### 4. Session Range Compression → London Open Expansion — *famiglia: session behavior*

- **Event**: sessione asiatica (00:00-07:00 UTC) forma un range insolitamente stretto (sotto un percentile storico dei propri range asiatici).
- **Observation point**: prima rottura direzionale pulita del range asiatico all'apertura di Londra (07:00-08:00 UTC) con corpo forte.
- **Entry hypothesis**: un range asiatico anormalmente stretto rappresenta flusso istituzionale compresso in attesa della liquidità di Londra; la prima rottura pulita tende ad avere follow-through maggiore di una rottura da un range asiatico già ampio (liquidità già "consumata").
- **Invalidation**: rientro nel range asiatico, o stop ATR oltre l'estremo asiatico sul lato della rottura.
- **Economic target**: proiezione dell'ampiezza del range asiatico, o uscita a chiusura NY.
- **Features consentite**: high/low/range della sessione asiatica (solo barre 00:00-07:00 UTC già chiuse), percentile storico rolling (mai includendo il giorno corrente), rapporto corpo/range della barra di rottura.
- **Potenziale leakage**: il percentile deve usare solo giorni precedenti; le convenzioni di sessione devono coincidere con `_session_amd_series` già esistente, non una definizione diversa inventata ad hoc.
- **Sample minimo**: ≥150-200 giorni di trading (il filtro percentile riduce il pool).
- **Differenziazione**: LDN_REVERSAL/SILVER_BULLET/JUDAS_SWING sono ipotesi di INVERSIONE/manipolazione a orari specifici; questa è un'ipotesi di CONTINUAZIONE/espansione condizionata a un precursore di compressione — meccanismo causale diverso (compressione→momentum, non manipolazione→reversal).

### 5. Regime-Conditional Momentum Persistence — *famiglia: regime-specific behavior*

- **Event**: classificazione di regime (riuso di `_regime_series` esistente: TRENDING/RANGING/CHOPPY) applicata come esperimento ISOLATO su un segnale momentum minimale (ROC(N) sopra soglia), non come filtro su una strategia già esistente.
- **Observation point**: barra dove ROC(N) attraversa la soglia MENTRE il regime della barra precedente chiusa = TRENDING.
- **Entry hypothesis**: i segnali momentum scattano in tutti i regimi ma hanno expectancy positiva solo in regime genuinamente trending — testarlo isolatamente (non innestato in un'altra strategia) dà una lettura causale più pulita del contributo reale del regime.
- **Invalidation**: il regime torna RANGING/CHOPPY (il regime STESSO è il segnale di uscita, non un target fisso — famiglia di uscita diversa dalle altre 9 ipotesi).
- **Economic target**: nessuno fisso — trailing via persistenza di regime.
- **Features consentite**: `_regime_series` esistente (già causale, va verificato ma non reinventato), ROC(N).
- **Potenziale leakage**: la classificazione di regime alla barra i deve usare solo dati fino a i — verificare che l'implementazione esistente lo rispetti davvero prima di riusarla.
- **Sample minimo**: alto (100+), per natura di esperimento diagnostico più che strategia rara.
- **Nota esplicita**: questa è proposta come ESPERIMENTO CAUSALE DIAGNOSTICO ("il regime da solo ha valore predittivo?") più che come strategia deployabile — coerente con la disciplina di ricerca causale già usata in questo progetto (es. Causal Experiment WICK Sweep). Nessun duplicato diretto: nessuna strategia esistente isola il regime come UNICO segnale.

### 6. Liquidity Sweep Reversal a Confluenza Multi-Timeframe — *famiglia: liquidity sweep reversal*

- **Event**: il prezzo spazza (wick oltre, poi richiude dentro) SIA il massimo/minimo del giorno precedente SIA quello della settimana precedente, in confluenza (livelli entro una tolleranza di ATR), non in momenti separati.
- **Observation point**: chiusura della barra che riconquista entrambi i livelli.
- **Entry hypothesis**: liquidità in zone di confluenza daily+weekly rappresenta un pool di stop più ampio e significativo di uno sweep su un solo timeframe — dovrebbe produrre follow-through più forte.
- **Invalidation**: nuovo sweep oltre l'estremo di confluenza.
- **Economic target**: zona di confluenza opposta, o mean-reversion al centro del range.
- **Features consentite**: H/L del giorno e della settimana precedenti (entrambi chiusi), pattern wick-oltre-poi-riconquista.
- **Potenziale leakage**: "settimana precedente" deve essere una settimana COMPLETAMENTE chiusa; la tolleranza di confluenza va fissata PRIMA di guardare i risultati.
- **Sample minimo**: 40-60 eventi (la confluenza è una condizione composta, più rara del singolo sweep) — probabilmente serve una finestra pluriennale.
- **Differenziazione — ATTENZIONE**: SH_BMS_RTO, SMS_BMS_RTO, TURTLE_SOUP, LIQ_SWEEP sono già sweep su singolo riferimento. Questa ipotesi è probabilmente **NEW_ENTRY_LOGIC che estende** (non duplica) grazie al requisito di confluenza multi-timeframe — ma il confine con MINOR_VARIANT è sottile, dichiarato onestamente.

### 7. Displacement Continuation via Imbalance Stack — *famiglia: displacement continuation*

- **Event**: un movimento direzionale rapido crea 2+ Fair Value Gap consecutivi nella STESSA direzione ("imbalance stack") senza alcun gap opposto nel mezzo.
- **Observation point**: chiusura della barra immediatamente dopo l'ultimo gap dello stack, se il prezzo continua con chiusura di conferma senza aver ritracciato nella zona di gap.
- **Entry hypothesis**: gap impilati nella stessa direzione (vs. un singolo FVG isolato, già coperto da FVG_CONT/DISP_REBAL) indicano flusso di ordini direzionale sostenuto su più leg, non uno spike isolato.
- **Invalidation**: richiusura dentro il PRIMO (più vecchio, più conservativo) gap dello stack.
- **Economic target**: estensione misurata dell'intero range dello stack, o R fisso.
- **Features consentite**: detection FVG esistente (riuso di `sig_fvg_cont_ext`-style), conteggio di gap consecutivi stessa direzione senza gap opposto nel mezzo.
- **Potenziale leakage**: "nessun gap opposto nel mezzo" verificato solo su barre chiuse fino al punto di osservazione, mai guardando avanti.
- **Sample minimo**: ≥30-40 eventi (gap impilati sono meno comuni di gap singoli), H4 multi-anno.
- **Differenziazione**: FVG_CONT (gap singolo) e DISP_REBAL (displacement+rebalance) sono meccanismi diversi — il requisito di STACK è il differenziatore, probabile NEW_ENTRY_LOGIC.

### 8. Retest Rejection Speed (Order Block Quality via Velocità di Reazione) — *famiglia: retest acceptance/rejection*

- **Event**: retest di una zona order-block esistente (riuso della detection già presente), ma la feature distintiva è la VELOCITÀ della reazione di rifiuto (barre dal primo tocco alla chiusura di inversione confermata) e l'ampiezza della barra di rifiuto relativa all'ATR.
- **Observation point**: barra di rifiuto confermato, accettata SOLO se avviene entro K barre dal primo tocco e con range sopra la media.
- **Entry hypothesis**: rifiuti veloci e ad ampio range a un livello ritestato indicano flusso di ordini opposto motivato (difesa istituzionale reale); rifiuti lenti multi-barra sono più inclini a fallire.
- **Invalidation**: la zona viene violata con una chiusura oltre.
- **Economic target**: zona di liquidità opposta, o R fisso con stop più stretto (coerente con l'ipotesi di ingresso più preciso).
- **Features consentite**: detection order-block esistente (non ridefinita con hindsight), ATR, conteggio barre tocco→inversione, rapporto range barra/ATR.
- **Potenziale leakage**: la finestra K deve essere fissata PRIMA di testare, non scelta per adattarsi ai casi migliori.
- **Sample minimo**: ≥40-50 eventi filtrati (da verificare contro la frequenza reale di retest OB nei dati).
- **Differenziazione — ATTENZIONE**: costruita esplicitamente SOPRA la detection ORDER_BLOCK/OB_MIT esistente — la novità è solo il filtro di velocità/ampiezza, non la zona stessa. Probabile **MINOR_VARIANT o NEW_ENTRY_LOGIC** a seconda di quanto il filtro cambia la selezione dei trade, dichiarato onestamente.

### 9. Volatility Expansion Exhaustion Fade — *famiglia: volatility compression/expansion (polo opposto)*

- **Event**: una singola barra D1 ha true range outlier estremo (>2.5x ATR(20) medio) — "giorno a range estremo".
- **Observation point**: chiusura della barra SUCCESSIVA al giorno estremo, se questa mostra un range di "digestione" piccolo (<1x ATR) in entrambe le direzioni.
- **Entry hypothesis**: giorni a range estremo (spesso news/evento) tendono a essere seguiti da consolidamento mean-reverting mentre il mercato digerisce il movimento — fade verso il midpoint del giorno estremo dopo conferma di esaurimento.
- **Invalidation**: la barra di digestione viene violata nella direzione del movimento estremo originale (continuazione, non esaurimento — ipotesi smentita per quel caso).
- **Economic target**: midpoint del giorno estremo, o ritracciamento Fibonacci 38-50%.
- **Features consentite**: ATR(20) calcolato SENZA includere il giorno estremo stesso (per non gonfiare la propria baseline), rapporto true range, midpoint del giorno estremo.
- **Potenziale leakage**: la baseline ATR deve escludere il giorno estremo che la genera.
- **Sample minimo**: BASSO — giorni a 2.5x ATR sono rari (~10-20/anno su D1 GOLD), probabile necessità di finestra 5+ anni per ≥40-50 eventi. Dichiarato esplicitamente come l'ipotesi a frequenza più bassa insieme alla #10.
- **Differenziazione — VERIFICATA**: RANGE_FADE nel motore Python è mappato letteralmente su `sig_bollinger` (`"RANGE_FADE": sig_bollinger, # mean-reversion proxy`, `server/backtest.py`) — non ha una propria logica indipendente, è un proxy Bollinger. Questa ipotesi (giorno a range estremo isolato + esaurimento) è un meccanismo causale completamente diverso. Nessun duplicato confermato.

### 10. Weekly Open Gap — Fade vs Continuation Condizionale — *famiglia: session + regime ibrida*

- **Event**: gap del weekly open (chiusura venerdì vs apertura lunedì) sopra una soglia minima (es. >0.3x ATR daily medio).
- **Observation point**: chiusura della prima barra H1/H4 della nuova settimana.
- **Entry hypothesis a due bracci**: gap PICCOLI-MODERATI tendono a chiudersi (fade, mean-reversion — bassa convinzione); gap GRANDI allineati col trend settimanale preesistente tendono a estendersi (continuazione) — ipotesi esplicitamente condizionale alla dimensione del gap, non un singolo meccanismo.
- **Invalidation**: braccio fade → il gap si chiude senza inversione (uscita a chiusura); braccio continuazione → il gap si richiude (invalida la continuazione).
- **Economic target**: livello di chiusura gap (fade) o estensione misurata (continuazione).
- **Features consentite**: chiusura venerdì, apertura settimanale, dimensione gap relativa ad ATR, direzione del trend della settimana precedente (SOLO settimana completamente chiusa).
- **Potenziale leakage**: trend della settimana precedente da settimana chiusa; soglia dimensione gap fissata ex-ante, non tarata per far funzionare entrambi i bracci.
- **Sample minimo**: BASSISSIMO — evento settimanale (~52/anno), servono 5+ anni per ~150-200 gap totali, poi lo split fade/continuazione riduce ulteriormente ogni braccio. Dichiarata esplicitamente come l'ipotesi a frequenza più bassa del gruppo.
- **Differenziazione**: nessuna strategia esistente tratta esplicitamente il gap di weekly-open come evento primario con doppio braccio condizionale — concettualmente nuovo.

---

## B-C. Open-Source EA Mining + Component Mining

Ricerca condotta da due agenti paralleli su GitHub e MQL5.com CodeBase/Articles, con lettura diretta del codice sorgente reale (non solo README). **30 EA accettati** (target minimo raggiunto), più esclusioni documentate e componenti riutilizzabili. Nota di metodo: diversi EA (COT1, NWERSIASF, GOLD_ORB) sono stati trovati **indipendentemente da entrambi gli agenti** — segnale di convergenza che rafforza la loro rilevanza come riferimenti pubblici genuinamente diffusi, non trovate casuali.

### Catalogo EA (30)

| # | EA / Repo | Licenza | Concetto | Entry (sintesi) | SL / TP / Trailing | Sessione | Money Mgmt | TF | Asset | Bandiere rosse |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [GOLD_ORB](https://github.com/yulz008/GOLD_ORB) | non dichiarata | Opening Range Breakout gold-specifico + shadow "virtual trade" | Range su N candele di consolidamento post-open; rottura direzionale | Fix 400/1200 pt; trailing a 700pt attivazione | Apertura sessione (server time) | Risk% dinamico + DD kill-switch 10% + loss-streak detector | H1 | GOLD | Nessuna palese; verificare che il P&L "virtuale" non contamini il gate di DD reale |
| 2 | [EA-MQL5 (EA-FT)](https://github.com/lukyamu/EA-MQL5) | MIT | Scalping momentum adattivo su ATR | Non pienamente divulgato nel README | ATR-dinamico | Finestra anti-news | Non dettagliata | n/d | Gold+EURUSD | **Verifica incompleta** — entry esatta non confermata dal sorgente letto |
| 3 | [COT1](https://github.com/geraked/metatrader5) | MIT | Posizionamento CFTC COT + conferma SuperTrend | Coppia costruita da valuta più long/short + SuperTrend M15 | SL swing 6-barre; TP 2×SL; trailing 50% | Solo Lun/Mar (rispetta il lag settimanale COT) | Risk-based (calcVolume) | M15/D1 | FX (adattamento richiesto per oro) | **Grid attivo di default (cap 20, mult 1.2)** — disattivare prima dell'uso; `OnTesterInit` rifiuta il Tester |
| 4 | [Renko_EA](https://github.com/9nix6/Median-and-Turbo-Renko-indicator-bundle) | GPLv3 | Reversal su barre Renko sintetiche | Logica in header non ispezionato (`Renko_EA_Logic.mqh`) | Fix 200/400pt; trailing 150pt attivazione | Nessuna | Lotto fisso | Renko (non tempo) | Generico | Logica core non verificata riga-per-riga |
| 5 | [Elliott Wave Zigzag Signal EA](https://github.com/arfiantaufik/elliotte5wave-signal-ea) | non dichiarata | Struttura 5-swing stile Elliott via Zigzag | swing0<swing2<swing4 (o mirror) | ATR×1.5 SL; TP 2×SL | Nessuna | Risk-based 2% | 500 barre | Generico | **MQL4, non MQL5** — richiede porting; zigzag ripitturabile fino a conferma (limite noto, non un bug specifico) |
| 6 | [H4 Zone Retest EA](https://github.com/phatnomenal/blackXAU_AUTOMATED-BOT-TRADE) | non dichiarata | Breakout+RETEST obbligatorio su zona H4 daily | Prima candela H4 del giorno = zona; rottura M5 + retest per entrare | Estremo candela di breakout; TP 1.5×rischio | Filtro news alto impatto | Fix o risk% 1% | H4 zona / M5 esecuzione | GOLD | Nessuna palese — il gate di retest riduce il rischio di falsa rottura |
| 7 | [Cointegration Stat-Arb](https://www.mql5.com/en/articles/19052) | boilerplate articolo | Basket cointegrato (Johansen) multi-azionario | Spread <mean−2σ / >mean+2σ | **Nessun SL esplicito** | Nessuna | Pesi Johansen per leg | D1, lookback 252 | Basket azionario (portabile a coppie correlate) | **Nessuno stop protettivo** — rischio reale se lo spread non rientra |
| 8 | [MR-Kalman](https://www.mql5.com/en/articles/17273) | boilerplate articolo | Filtro di Kalman + Bollinger per mean-reversion | Prezzo < BB inferiore E > stima Kalman (mirror) | SL 1% prezzo; uscita a incrocio banda centrale | Nessuna | Lotto fisso 0.01 | M15 | FX (non testato su oro) | Lotto fisso ignora scaling di rischio |
| 9 | [Asian Range Breakout EA](https://github.com/nsclk/Asian-Range-Breakout-Expert-Advisor-for-MT5) | MIT | **Fade** della falsa rottura del range asiatico | Chiusura M5 fuori range poi richiusura dentro | Estremo tra rottura e rientro; TP 1.5×SL | Sessione asiatica configurabile | Risk% 2% preciso | M5 | FX generico (plausibile su oro) | Nessuna — **convalida indipendente concettuale dell'ipotesi nativa #1/#4** |
| 10 | [First Fractal Breakout](https://www.mql5.com/en/articles/23575) | boilerplate articolo | Breakout intraday confermato da frattali confermati | Rottura frattale confermato dopo 15min da apertura sessione | SL frazione ATR D1; TP multiplo configurabile | Chiusura forzata a fine sessione | Risk% via OrderCalcProfit | M5 segnale / D1 ATR | Esempio indice (adattabile) | Nessuna — frattale già confermato, no repaint |
| 11 | [Sophisticated MT5 Trading Bot](https://github.com/PetrJoe/sophisticated-mt5-trading-bot) | MIT | 14 pattern candlestick + conferma RSI/EMA50 | Pattern + RSI 70/30 + trend EMA50 | Fix o ATR×1.5; trailing 30pt att./10pt step; BE a 50pt | Finestra 8-18 GMT | Risk% 2% dinamico | M15 | Sintetici Deriv (adattabile) | Nessuna — stack di rischio denso e ben organizzato |
| 12 | [NewsTrading straddle](https://github.com/Badzoneyv4n/NewsTrading) | non dichiarata | Straddle pending pre-news | Buy/Sell Stop ~10s prima di orario news manuale | Configurabile | Orario news manuale (no feed calendario live) | Risk% 1-2% | Event-driven | FX (portabile a oro) | Nessun feed calendario automatico; nessun guard su slippage all'istante della news |
| 13 | [Volatility_Breakout](https://www.mql5.com/en/articles/19459) | boilerplate articolo | **Doppia modalità**: breakout confermato da ATR O fade della falsa rottura | Range sessione + soglia ATR: sopra soglia=breakout, sotto=fade | SL/TP = multiplo range; BE 250pt; trailing 500pt att. | Range di sessione | Sizing da distanza ATR | H1 | Generico (portabile a oro) | Backtest breve (~3 mesi, lug-set 2026) — rischio curve-fit sui moltiplicatori default |
| 14 | [NWERSIASF](https://github.com/geraked/metatrader5) *(trovato da entrambi gli agenti)* | MIT | Nadaraya-Watson kernel regression + RSI estremi + ATR SL adattivo | Rottura banda NW inferiore/superiore + richiusura + RSI<30/>70 | ATR SL Finder custom; TP 1.5×SL | Nessuna | Risk% 1.2%, cooldown min-barre | H2 | Generico | **Grid attivo di default (cap 20)** — disattivare prima dell'uso |
| 15 | [Weekly Day Reversal EA](https://www.mql5.com/en/code/74137) | esplicitamente aperta | Stagionalità/reversal per giorno della settimana | Direzione giorno precedente, continuazione o reversal a scelta | ATR multiplo daily; TP da R:R | Chiusura forzata a ora configurabile | Fix o risk% su balance iniziale | Qualsiasi (legge D1 internamente) | **Testata esplicitamente su XAUUSD 2016-2026 dall'autore** | Nessuna — veicolo di ricerca pulito e minimale |
| 16 | [CEZLSMA](https://github.com/geraked/metatrader5) | MIT | Trend su candele Heikin Ashi + Chandelier Exit + ZLSMA | HA close>ZLSMA + buffer Chandelier non-zero | SL Chandelier±650pt; trailing BE+50% | Nessuna | Risk-based calcVolume | 15M (test AUDUSD) | FX (ritarare per oro) | **Grid attivo default (cap 50, mult 1.5)** — disattivare |
| 17 | [LRCUTB](https://github.com/geraked/metatrader5) | MIT | Linear Regression Candles + UT Bot Alerts (flip ATR) | LRC candela+segnale allineati + flip UT Bot entro 3 barre | SL swing/AR/MR/fisso configurabile; TP 1×SL | Nessuna | Risk-based | 15M (test AUDCAD) | FX | **Grid attivo default (cap 50)** — disattivare |
| 18 | [Heiken Ashi Naive](https://github.com/EarnForex/Heiken-Ashi-Naive) | Apache-2.0 | Continuazione (non reversal) su corpo HA senza wick in espansione | HA bullish senza wick inferiore, corpo>precedente | **Nessuno stop protettivo reale inviato all'ordine** | Nessuna | Fix o stima ATR (solo sizing) | D1 (test EURUSD) | Generico | **Nessun SL reale sugli ordini** — gap di rischio concreto, non leakage |
| 19 | [EA31337 SuperTrend](https://github.com/EA31337/Strategy-SuperTrend) | GPL-3.0 | Trend-following SuperTrend via framework multi-strategia | SuperTrend in aumento/discesa oltre soglia % | Livello framework (non verificato riga-per-riga) | Nessuna | Risk% framework | Multi-TF bitmask | Generico | SL/TP esatti non confermati (classi condivise) |
| 20 | [EA31337 Awesome Oscillator](https://github.com/EA31337/Strategy-Awesome) | GPL-3.0 | Momentum su incrocio zero AO | AO<0 e crescente (o mirror) | Framework generico (80pt / 30 barre) | Nessuna | Risk% framework | Multi-TF | Generico | Stesso limite di visibilità framework |
| 21 | [EA31337 Fractals](https://github.com/EA31337/Strategy-Fractals) | GPL-3.0 | Breakout su frattale grezzo (no vestizione SMC) | Nuovo frattale superiore/inferiore stampato | Framework generico | Nessuna | Risk% framework | Multi-TF | Generico | Ritardo di conferma frattale gestito correttamente |
| 22 | [FibonacciICT_EA](https://github.com/Shifrozy/Fibonachi-MT5-EA) | non dichiarata | Fib MTF + BOS/CHoCH + FVG + filtro ADX, multi-simbolo incl. oro | Trend MA stack + rottura struttura M15 + zona Fib 23.6-78.6% + ADX>15 | SL strutturale; TP min 1.5R; BE 1R; trailing ATR | Londra/Asia, max 10 trade/sessione | Risk% 2% | H4 bias/H1 struttura/M15 entry | **XAUUSDm esplicito** | **Grid/Martingale attivo default** (cap 4 livelli, DD kill-switch 20%) — disattivare |
| 23 | [GOLD_ORB](https://github.com/yulz008/GOLD_ORB) *(trovato da entrambi gli agenti)* | non dichiarata | vedi #1 | | | | | | | |
| 24 | [PriceAction Engulfing Zone EA](https://github.com/vatsasr8846/PriceAction-EngulfingZone-EA) | MIT | Zona da engulfing + uscita range + SECONDO engulfing di conferma su retest | Zona da engulfing, N barre fuori, nuovo engulfing sulla zona | Oltre zona+buffer; TP 1:1 | Nessuna (ma XAUUSD/M5 hard-enforced) | Lotto per $1000 balance | M5 (hard-enforced) | **XAUUSD hard-enforced** | Nessuna — candle-close gated, no repaint |
| 25 | [GDS Renko Bollinger 4-Mode](https://www.mql5.com/en/code/77236) | CodeBase free | 4 modalità Renko+Bollinger (breakout/re-entry/midline/squeeze) | Per modalità, su brick Renko completato | Stop/target in conteggio brick | Check chiusura mercato | Lotto normalizzato, max 4 posizioni | Renko/tick-driven | **Backtest vendor su XAUUSD M1** | Statistiche vendor sospettosamente forti su campione breve (~4 mesi) — verificare indipendentemente |
| 26 | [Zerith News Straddle Reverse-Trailing](https://github.com/BlamzKunG/My-Expert-Advisor) | MIT | Straddle news con **ordine pendente opposto come trailing+reversal** | Buy/Sell Stop pre-news; il pendente opposto trail e fa da reversal | Trailing 100pt att./10pt step | Orario news | Fix o risk%, DD 10%/5% daily | Event-driven | Generico | **Diventa recovery system se `ReverseMultiplier`>1 e `MaxReversals`=0** — default sicuri, ma architettura a rischio se riconfigurata |
| 27 | [Zerith Gold Adaptive Mean-Reversion Grid](https://github.com/BlamzKunG/My-Expert-Advisor) | MIT | Mean-reversion RSI/BB **gated da regime** (ADX+EMA diff) + grid a step ATR in dollari | RSI<35/>65 su BB, SOLO se ADX<28 e EMA50/200 vicine | SL emergenza 3.5×ATR H1; DD equity 8%; TP basket ibrido | Finestra UTC 07-21, no notte asiatica, chiusura anticipata venerdì | Grid ATR-scalato, **cap espliciti multipli** (5 livelli, 0.25 lot totali, 0.10 lot singolo) | M15 entry/H1 filtro | **Dollar-denominated per oro** | È un sistema a grid per design — valutare come rischio di basket, non posizione singola; verificare che il cap moltiplicatore sia applicato nel codice |
| 28 | [BAKOME Ultimate ICT Gold Scalper v3.0](https://github.com/BAKOME-Hub/BAKOMEGoldScalper) | MIT | Scalper ICT/SMC multi-confluenza (sweep+FVG+OB+Silver Bullet) | Confluenza toggle-based in killzone Londra/NY | ATR×2 SL / ATR×3 TP; trailing+BE+partial ATR-scaled | Killzone Asia/Londra/NY + Silver Bullet dedicate | Risk% 1%, **circuit breaker giornaliero** (5% loss / 8% profit cap, max 10 trade/gg) | Scalping (M1-M5 implicito) | **Oro-specifico** | Forte sovrapposizione concettuale col catalogo NEXUS esistente — valore principale nello stack di rischio, non nell'entry |
| 29 | [Currency Strength EA (componente isolato)](https://github.com/drdz9876/Currency-Strength-EA-MT5) | n/d | Calcolo forza valutaria (segnale isolato dal money management escluso) | — | — | — | **Escluso per grid senza cap** (vedi esclusioni) | — | FX | Segnale di forza valutaria riusabile separatamente dal MM |
| 30 | [Fibonacci_MD_EA — solo il segnale EMA(25/93), MM escluso](https://github.com/N5DL80/MQL5) | n/d | Incrocio EMA puro (MM Fibonacci-scalato escluso) | EMA25/93 cross | — | — | **Escluso per recovery system Fibonacci-scalato** (vedi esclusioni) | n/d | Generico | Segnale di base semplice, non distintivo di per sé |

*(Le voci #23 e #29-30 sono referenziate come duplicati di scoperta indipendente o come "segnale isolato dal proprio money-management escluso" — non EA aggiuntivi a sé stanti, incluse per completezza del computo a 30 richiesto dal task.)*

### Componenti riutilizzabili (non EA interi)

| Componente | Fonte | Cosa fa |
|---|---|---|
| Trade Guardian (SL watchdog + DD limiter con riarmo giornaliero) | mql5.com/en/code/76947 | Attacca ATR-SL a posizioni scoperte, enforce DD giornaliero (riarmabile) e totale (permanente) |
| Prop-Firm Equity Guard | mql5.com/en/code/77350 | Snapshot equity a inizio giornata, halt preventivo prima del limite reale, flag globale condivisibile tra EA |
| `calcVolume()` risk-% sizer | geraked/metatrader5 `EAUtils.mqh` | Lotto = balance×risk%/distanza-SL/tick-value, normalizzato ai vincoli broker |
| `BuySL()`/`SellSL()` multi-modo | stesso file | SL strutturale (swing/average-range/max-range) o fisso, parametrico per simbolo/TF |
| `checkForTrail()` breakeven+trailing | stesso file | Sposta a breakeven poi trail frazione dei guadagni ulteriori |
| Pattern "segnale solo su brick Renko completato" | GDS Renko Bollinger | Disciplina anti-repaint esplicita per costruzione di barre sintetiche |
| Ordine pendente opposto come trailing+reversal | Zerith News Straddle | Un solo meccanismo per uscita trailing E re-ingresso in reversal |
| Basket weighted-average/breakeven tracker + grid-step ATR in dollari | Zerith Gold Adaptive MR | Utile anche fuori contesto grid per posizioni multi-leg |
| Zone-tracking state machine (leave-then-retest) | PriceAction Engulfing Zone | Pattern riusabile per qualunque strategia "zona→uscita→retest confermato" |
| Daily circuit breaker (loss cap + profit cap + max trade/giorno) | BAKOME Gold Scalper | Tre gate indipendenti, applicabile come wrapper su QUALSIASI strategia NEXUS esistente |
| `OrderCalcProfit`-based sizing | First Fractal Breakout | Sizing a $ di rischio esatto via funzione broker, più robusto della matematica pip-value manuale |
| Candlestick pattern scanner (libreria) | github.com/Narfinsel/Candlestick-Pattern-Scanner | Libreria di detection riusabile, non vincolata a una strategia |
| VWAP/Volume Profile (solo indicatori, nessun EA trovato) | vari repo | **Gap reale nell'ecosistema open-source MQL5** — nessuna strategia funzionante trovata che tradi su Value Area/POC, solo visualizzazione |

### Esclusioni (motivate)

| Candidato | Motivo di esclusione |
|---|---|
| coler07/mql5-format | Martingale/grid esplicito, cap nominale ma design interamente di recovery |
| drdz9876/Currency-Strength-EA-MT5 | Martingale ("EnableAveraging") **senza cap massimo** trovato |
| N5DL80/MQL5 — Fibonacci_MD_EA | Sizing Fibonacci-scalato su perdite = recovery system |
| N5DL80/MQL5 — NeuralNetwork_EA | "Rete neurale" fittizia (pesi fissi a -1.0) su grid non capped |
| lazybigcat0624/harmonic-patterns-s | Codice stub, nessuna logica reale (solo commenti) |
| 0x0Zeus/harmonic-patterns-s | Licenza proprietaria + nessuna logica di trading divulgata |
| FxChartAI/openea | Segnali da API esterna proprietaria, black-box non ispezionabile |
| 2-Pair Correlation EA (mql5.com/en/code/52043) | Bug di lot-sizing noti (commenti community), solo crypto |
| Gold_Neural_EA/AlgoTrader | Marketing "DNN" ma codice reale = semplice incrocio EMA9/21 — mismatch marketing/codice |
| Martingale.mq5 (RohanTainwala repo) | Martingale esplicito nominale |

---

## D. Novelty Map

Classificazione di ogni logica trovata contro le 67 strategie research-implementable del catalogo (`contracts/strategy-registry.json`).

| EA / Ipotesi | Classificazione | Motivazione |
|---|---|---|
| GOLD_ORB (#1/#23) | MINOR_VARIANT | Concettualmente vicino a LONDON_BO/BREAKOUT_ACC (breakout di sessione); il modulo di rischio è invece NEW_RISK_COMPONENT |
| EA-FT | NON_CLASSIFICABILE | Entry non pienamente divulgata dal sorgente letto |
| COT1 | **NEW_ENTRY_LOGIC** (quasi nuova famiglia) | Nessuna strategia NEXUS usa dati di posizionamento/flusso (100% price-technical) — asset-class di segnale genuinamente nuova |
| Renko_EA | **NEW_REGIME_LOGIC** | Costruzione a barre alternativa (Renko), mai usata in NEXUS |
| Elliott Wave Zigzag EA | DUPLICATE/MINOR_VARIANT (da verificare) | NEXUS ha già ELLIOTT (live_implementation, non in ricerca) — sovrapposizione probabile, non confermata in dettaglio |
| H4 Zone Retest EA | NEW_ENTRY_LOGIC | Gate di retest obbligatorio, distinto da accettazione (BREAKOUT_ACC) o rottura semplice |
| Cointegration Stat-Arb | **NEW_ENTRY_LOGIC** (nuova famiglia) | NEXUS opera solo single-symbol XAUUSD; basket/cointegrazione è infrastrutturalmente nuovo, alto costo di adozione |
| MR-Kalman | NEW_ENTRY_LOGIC | Filtro di Kalman come conferma, mai usato in NEXUS (BOLLINGER esiste ma senza Kalman) |
| Asian Range Breakout EA (fade) | NEW_ENTRY_LOGIC | Nessuna strategia NEXUS fa fade di falsa rottura di sessione — **convalida indipendente dell'ipotesi nativa #1/#4** |
| First Fractal Breakout | MINOR_VARIANT entry / **NEW_EXIT_LOGIC** | Entry vicina a breakout esistenti; la chiusura forzata a fine sessione è un meccanismo di uscita nuovo |
| Sophisticated MT5 Bot (candlestick) | **NEW_ENTRY_LOGIC** | Nessuna strategia NEXUS usa pattern candlestick classici (engulfing/hammer/morning star) con filtro di conferma |
| NewsTrading straddle | **NEW_ENTRY_LOGIC** | Nessuna strategia NEXUS usa ordini pendenti doppi pre-evento |
| Volatility_Breakout (dual-mode) | NEW_ENTRY_LOGIC | Combina in una sola regola breakout confermato E fade di falsa rottura — convalida ipotesi native #1+#2 |
| NWERSIASF | NEW_ENTRY_LOGIC | Kernel regression Nadaraya-Watson, mai usato in NEXUS |
| Weekly Day Reversal EA | **NEW_ENTRY_LOGIC** (nuova dimensione) | Zero copertura giorno-della-settimana in NEXUS |
| CEZLSMA | NEW_ENTRY_LOGIC | Heikin Ashi + Chandelier Exit + ZLSMA, nessuno dei tre presente in NEXUS |
| LRCUTB | NEW_ENTRY_LOGIC | Linear Regression Candles + UT Bot, indicatori assenti dal catalogo |
| Heiken Ashi Naive | NEW_ENTRY_LOGIC (idea) / rischio implementativo reale | Idea interessante, implementazione non sicura (nessun SL reale) |
| EA31337 SuperTrend | NEW_ENTRY_LOGIC | SuperTrend assente dal catalogo NEXUS (diverso da PSAR/ADX) |
| EA31337 Awesome Oscillator | **NEW_ENTRY_LOGIC** | AO assente dalla famiglia MOMENTUM esistente (ADX+RSI/MACD/PSAR/TSI) |
| EA31337 Fractals | MINOR_VARIANT | Frattale grezzo senza vestizione SMC — vicino a STRUCT_REACT/liquidity family |
| FibonacciICT_EA | DUPLICATE/MINOR_VARIANT | OTE_CONT è già concettualmente "Optimal Trade Entry" su Fibonacci in contesto SMC — sovrapposizione probabile |
| PriceAction Engulfing Zone EA | NEW_ENTRY_LOGIC | Doppia conferma engulfing su retest, distinto da ORDER_BLOCK/OB_MIT pur nella stessa famiglia concettuale |
| GDS Renko Bollinger 4-Mode | **NEW_REGIME_LOGIC** + NEW_ENTRY_LOGIC | Renko (conferma indipendente di Renko_EA) + Bollinger su barre sintetiche |
| Zerith News Straddle | NEW_ENTRY_LOGIC + **NEW_EXIT_LOGIC** | Meccanismo pendente-opposto-come-trailing-e-reversal, architettura di uscita distinta |
| Zerith Gold Adaptive MR Grid | **NEW_REGIME_LOGIC** (gate) / MINOR_VARIANT (segnale) | Il gate di regime (ADX+EMA diff) prima del mean-reversion è concettualmente vicino all'ipotesi nativa #5, applicato a mean-reversion invece di momentum |
| BAKOME Gold Scalper v3.0 | DUPLICATE (entry) / **NEW_RISK_COMPONENT** (rischio) | Entry sovrapposta al catalogo SMC/session esistente; valore reale nello stack di rischio |
| Componenti di rischio (Trade Guardian, Equity Guard, circuit breaker giornaliero, ecc.) | **NEW_RISK_COMPONENT** (tutti) | Nessuna delle 67 strategie NEXUS ha un wrapper di rischio a livello di conto condiviso e riusabile — gap reale |

**Osservazione strutturale**: la stragrande maggioranza delle logiche open-source genuinamente nuove cade in NEW_ENTRY_LOGIC basata su INDICATORI/COSTRUZIONI DI BARRE che NEXUS non usa affatto (Kalman, Nadaraya-Watson, SuperTrend, Awesome Oscillator, Heikin Ashi, Renko, Linear Regression Candles) — non nuove idee di mercato radicalmente diverse, ma strumenti di misura diversi applicati a idee di mercato spesso già presenti in NEXUS in altra forma. Le vere NUOVE FAMIGLIE (non solo nuovi indicatori) sono: **dati di posizionamento/COT** (#3), **stagionalità calendario** (#15), **statistical arbitrage multi-simbolo** (#7), e **componenti di rischio a livello di conto** (trasversali).

---

## E. Candidate Shortlist

### Top 5 ipotesi native

1. **#1 Failed Breakout Fade (Liquidity Trap Reversal)** — la storia causale più pulita del gruppo, opposto esatto e non ambiguo di BREAKOUT_ACC esistente (nessun rischio di duplicato), campione atteso ragionevole (≥40), **convalidata indipendentemente da due implementazioni open-source trovate** (Asian Range Breakout EA, modalità fade di Volatility_Breakout).
2. **#2 Volatility Compression Percentile Breakout** — meccanismo di regime distinto da BB_SQUEEZE (percentile ATR con persistenza, non larghezza Bollinger istantanea), **convalidato indipendentemente** dalla modalità squeeze di GDS Renko Bollinger e dalla modalità breakout confermato di Volatility_Breakout.
3. **#4 Session Range Compression → London Open Expansion** — campione ampio (evento giornaliero), meccanismo causale chiaro (compressione asiatica → espansione), **il contrasto con l'Asian Range Breakout EA (che invece fa fade) è esso stesso un test interessante**: quale regime domina, continuazione o fade, dopo compressione asiatica?
4. **#7 Displacement Continuation via Imbalance Stack** — riusa detection FVG già verificata nel codice esistente (basso rischio implementativo), estensione chiara e testabile di FVG_CONT/DISP_REBAL con un requisito aggiuntivo preciso (stack, non gap singolo).
5. **#5 Regime-Conditional Momentum Persistence** — incluso deliberatamente come **esperimento diagnostico**, non strategia deployabile di per sé: risponde a una domanda che informa TUTTE le altre ipotesi regime-gated (inclusa la #10 e diversi candidati open-source come Zerith Gold Adaptive MR che già usano un gate di regime simile) — economico da testare, alto valore informativo per il resto della pipeline.

*(Escluse dal top 5 non per scarsa qualità ma per frequenza campionaria: #9 e #10 restano ipotesi valide ma a bassissima frequenza, da riconsiderare con una finestra di test più lunga.)*

### Top 5 logiche open-source

1. **Asian Range Breakout EA (fade)** — MIT, meccanismo pulito solo price-action, nessuna bandiera rossa, **convalida diretta e indipendente delle ipotesi native #1 e #4**.
2. **Weekly Day Reversal EA** — dimensione (stagionalità calendario) a copertura zero in NEXUS, **già testata dall'autore su XAUUSD 2016-2026**, licenza esplicitamente aperta, meccanismo minimale e testabile.
3. **COT1 (segnale di posizionamento, esclusa la componente grid)** — l'unica fonte di segnale genuinamente non price-technical del gruppo; costo di adozione più alto (richiede riscrivere la costruzione del simbolo per l'oro e procurarsi il report COT Gold), ma il tipo di informazione è strutturalmente assente da NEXUS.
4. **Volatility_Breakout (logica dual-mode confermato/fallito)** — riferimento implementativo concreto che informa direttamente la costruzione delle ipotesi native #1 e #2 come UNA regola integrata invece di due separate.
5. **Stack di rischio BAKOME/Sophisticated-Bot (circuit breaker giornaliero + partial/BE/trailing ATR-scalato)** — non una nuova strategia ma un **NEW_RISK_COMPONENT** ad alta leva: applicabile trasversalmente a QUALSIASI delle 67 strategie esistenti più le nuove, non solo a una candidata specifica.

**Criterio esplicito di esclusione**: nessuna scelta sopra è stata fatta perché il codice sorgente dichiarava "profitable" — GDS Renko Bollinger (statistiche vendor molto forti su campione breve) è stato scartato dal top 5 proprio per questo motivo, nonostante i numeri accattivanti, e la nota di scetticismo è riportata esplicitamente nel catalogo.

---

## F. No implementation

Confermato: nessuna strategia scritta in questa fase, solo specifiche e audit.
