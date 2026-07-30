# REGISTRO DELLE LACUNE — NEXUS_MASTER_PROJECT_v18.md

> Fase D8, attività F. Lacune della **fonte**, non del progetto: elencano ciò
> che `NEXUS_MASTER_PROJECT_v18.md` non contiene. Una lacuna qui non implica che
> l'informazione non esista altrove — implica che non è ricavabile da questa
> fonte, e che dedurla sarebbe una deduzione presentata come dato.

| | |
|---|---|
| Fonte | `docs/sources/master/NEXUS_MASTER_PROJECT_v18.md` |
| SHA-256 | `72c51a725c152f8246ccce26d4b30578a25e80dfc817ecd13e935420bfbd16e2` |
| Data | 2026-07-26 |
| Lacune registrate | **34** |
| Bloccanti per il passo successivo | **13** |
| Blocchi indipendenti (radici della catena) | **2** |

## Legenda

| Campo | Significato |
|---|---|
| **Blocca** | `SÌ` = l'audit di fedeltà delle strategie non può procedere finché la lacuna resta aperta |
| **Fonte necessaria** | quale documento la colmerebbe |

---

## 1. Architettura

### GAP-ARCH-001 — Nessuna descrizione funzionale dei 59 moduli MQL5
**Descrizione.** La fonte elenca 59 moduli `NXS_*.mqh` per nome (righe 191–252)
senza descrivere cosa faccia nessuno di essi. Moduli con nome pesantemente
semantico — `NXS_AMDModel`, `NXS_Confluence`, `NXS_FibonacciContext`,
`NXS_HTFBias`, `NXS_Pressure`, `NXS_Reaction`, `NXS_Velocity`,
`NXS_StructureMultiLayer` — restano nomi senza definizione.
**Impatto.** Non è possibile stabilire quale modulo implementi quale concetto di
trading, né verificare che il concetto sia implementato correttamente.
**Fonte necessaria.** Specifica funzionale dei moduli, oppure lettura del codice
(fuori dallo scope di questo incarico).
**Blocca.** NO per l'audit documentale; SÌ per la mappatura concetto → modulo.
**Azione consigliata.** Richiedere una specifica dei moduli, o pianificare una
fase di lettura del codice con mandato esplicito.

### GAP-ARCH-002 — Architettura corrente e architettura target non sono separate
**Descrizione.** Il documento alterna descrizione dell'esistente e prescrizione
del futuro senza marcatura sistematica. Solo la sezione A4.0 §3 (righe
14646–14657) introduce `MUST`/`SHOULD`/`MAY`, e vale per i requisiti indicizzati.
**Impatto.** Un lettore automatico non può distinguere "com'è" da "come deve
essere"; il rischio è trattare una raccomandazione come uno stato di fatto.
**Fonte necessaria.** Nessuna: è un difetto di forma della fonte stessa.
**Blocca.** NO.
**Azione consigliata.** Nelle fasi successive citare sempre riga e sezione, mai
il documento in blocco.

### GAP-ARCH-003 — "Point 5" non è mai definito
**Descrizione.** Compare due volte come elemento bloccato (righe 70, 147) senza
alcuna definizione nel documento.
**Impatto.** Un blocco dichiarato ma non definito non è verificabile né
rimuovibile: nessuno può sapere quando è risolto.
**Fonte necessaria.** Chiarimento del proprietario.
**Blocca.** NO.
**Azione consigliata.** Chiedere al proprietario cosa sia "Point 5" e
registrarlo.

---

## 2. Strategie

### GAP-STRAT-001 — Nessuna strategia è nominata 🔴
**Descrizione.** Sonda esaustiva su 38 identificatori canonici: 36 a zero
occorrenze. Le due che rispondono (`MACD`, `SAR`) compaiono una volta ciascuna,
entrambe alla riga 1857, come **nomi di indicatore** in un reperto di
prestazioni sui `CopyBuffer` — non come identificatori di strategia.
**Impatto.** L'inventario delle strategie derivato da questa fonte è vuoto.
Nessun confronto di fedeltà è possibile: non c'è nulla contro cui confrontare.
**Fonte necessaria.** Documento che dichiari l'elenco canonico delle strategie.
**Blocca.** **SÌ.**
**Azione consigliata.** Fornire il documento delle strategie prima di aprire la
fase di fidelity audit.

### GAP-STRAT-002 — Nessun conteggio delle strategie 🔴
**Descrizione.** Il totale non è mai dichiarato. Gli unici indizi numerici sono
"numeri di selettore fissi come 17–37" (riga 1776) e array a dimensione fissa
`48`/`64` (riga 1790). La riga 1792 dice solo che "il conteggio corrente appare
sotto il limite".
**Impatto.** Non si può verificare la completezza di alcun inventario: manca il
denominatore.
**Fonte necessaria.** Registro canonico delle strategie.
**Blocca.** **SÌ.**
**Azione consigliata.** Come sopra.

### GAP-STRAT-003 — Nessuna regola di ingresso 🔴
**Descrizione.** `"entry rule"`: 0 occorrenze. Nessuna condizione di ingresso è
descritta per alcuna strategia.
**Impatto.** Il confronto codice ↔ specifica sugli ingressi è impossibile.
**Fonte necessaria.** I 13 PDF del corpus + una formalizzazione.
**Blocca.** **SÌ.**
**Azione consigliata.** Acquisire il corpus (GAP-SRC-001).

### GAP-STRAT-004 — Nessuna regola di uscita 🔴
**Descrizione.** Nessuna condizione di uscita di strategia. L'unico requisito
correlato è `NEXUS-LIFE-003` (riga 14785), che riguarda quando un trade è
*considerato finale*, non quando va chiuso.
**Impatto.** Come sopra.
**Fonte necessaria.** Come sopra.
**Blocca.** **SÌ.**

### GAP-STRAT-005 — Nessuna regola di stop loss o take profit 🔴
**Descrizione.** "stop loss" (13 occorrenze) e "take profit" (12) compaiono solo
in contesti di integrità dell'esecuzione, mai come parametro di strategia.
Nessun moltiplicatore ATR, nessuna distanza, nessun rapporto rischio/rendimento
(`risk-reward`, `R:R`: 0 occorrenze).
**Impatto.** Non è verificabile se gli SL/TP implementati corrispondano a
qualcosa di dichiarato.
**Fonte necessaria.** Corpus + formalizzazione.
**Blocca.** **SÌ.**

### GAP-STRAT-006 — Nessun criterio di selezione delle strategie
**Descrizione.** La fonte descrive che il routing è duplicato e fragile
(`AUD0-MQL-003`, riga 1776) ma non dice mai con quale criterio una strategia
venga attivata, esclusa o preferita.
**Impatto.** Il comportamento di selezione non è verificabile contro un
riferimento.
**Fonte necessaria.** Specifica del router.
**Blocca.** NO per l'audit documentale.

### GAP-STRAT-007 — Nessuna formula di conviction, scoring o ranking
**Descrizione.** La parola "conviction" non compare mai. Esistono i nomi
`NXS_EntryScore.mqh`, `NXS_Confluence.mqh`, `NXS_StratStats.mqh`, senza alcuna
descrizione.
**Impatto.** Qualunque punteggio implementato non ha un riferimento dichiarato:
non è possibile dire se sia corretto o inventato.
**Fonte necessaria.** Specifica dello scoring.
**Blocca.** NO, ma è rilevante: uno scoring non specificato che influenzi il
sizing ricadrebbe nella categoria "euristica non validata".

### GAP-STRAT-008 — Il "modello proprietario" è citato ma non identificato
**Descrizione.** La fonte raccomanda di "conservare il modello proprietario come
strategia isolata, con nomenclatura e condizioni esplicite prima della codifica"
(riga 15127), e la categoria "Sequence / Proprietary Models" esiste nel corpus
(22 occorrenze). Ma il modello non è mai identificato.
**Impatto.** Una strategia dichiarata degna di trattamento speciale non è
riconoscibile.
**Fonte necessaria.** I PDF della famiglia "Sequence" — che sono proprio i meno
leggibili del corpus (vedi GAP-SRC-003).
**Blocca.** NO subito, SÌ per quella specifica strategia.

---

## 3. Risk management

### GAP-RISK-001 — Nessun valore di rischio concreto
**Descrizione.** I quattro `NEXUS-RISK-*` (righe 14764–14775) dichiarano
principi — nessun bypass, incertezza = blocco, precedenza delle protezioni,
sizing deterministico — ma nessuna percentuale, tetto o formula.
**Impatto.** I principi sono verificabili come *comportamenti*; i parametri no.
**Fonte necessaria.** Specifica di risk management con numeri.
**Blocca.** NO.
**Azione consigliata.** Verificare i principi contro l'implementazione; trattare
i numeri come configurazione, non come requisito.

### GAP-RISK-002 — La parità live/backtest è dichiarata rotta, senza criterio di accettazione
**Descrizione.** Il gate delle protezioni ritorna "non bloccato" nel tester
(riga 2597) e i backtest non modellano i vincoli di esecuzione live (riga 2187).
La fonte chiede di rendere testabili drawdown giornaliero, limiti di trade,
concorrenza, cooldown e pausa — senza dire quando la parità sia raggiunta.
**Impatto.** Non esiste una condizione di uscita per questo lavoro.
**Fonte necessaria.** Definizione di accettazione della parità.
**Blocca.** NO.

### GAP-RISK-003 — Money management quasi assente anche nel corpus
**Descrizione.** "Risk & Money Management" ha **15 occorrenze indicative su
1092 pagine** (riga 15475): la densità più bassa dell'intero corpus, contro 1515
di "Support/Resistance & SNR" e 789 di "Entries & Confirmation".
**Impatto.** Anche acquisendo il corpus, la parte di money management resterà
probabilmente sottospecificata. È un'aspettativa da fissare **ora**, non da
scoprire dopo.
**Fonte necessaria.** Materiale dedicato, che potrebbe non esistere nel corpus.
**Blocca.** NO.
**Azione consigliata.** Non aspettarsi che il corpus risolva il money
management; pianificare una specifica autonoma.

---

## 4. Esecuzione

### GAP-EXEC-001 — Nessuna specifica dei percorsi grid, pyramiding e split
**Descrizione.** Il Block 11 (riga 2665) audita "Grid, Pyramiding, Split and
Institutional Exposure Paths" ma ne verifica l'integrità, non ne definisce la
logica.
**Impatto.** Percorsi che creano esposizione aggiuntiva non hanno un
riferimento dichiarato.
**Fonte necessaria.** Specifica dei percorsi di esposizione.
**Blocca.** NO.

### GAP-EXEC-002 — La modalità multi-timeframe è dichiarata senza mappatura
**Descrizione.** La fonte dice che la modalità valuta passate fisse D1, H4 e H1
su un solo grafico (riga 1708), ma non dice quale strategia usi quale
timeframe.
**Impatto.** Non verificabile se l'assegnazione dei timeframe sia corretta.
**Fonte necessaria.** Registro delle strategie con timeframe.
**Blocca.** NO.

### GAP-EXEC-003 — Il gate di licenza permissivo richiede una verifica non fornita
**Descrizione.** `AUD0-MQL-012` (riga 1897): un fallimento del controllo licenza
non fa fallire `OnInit`; l'EA resta caricato in modalità inattiva. La fonte
chiede di provare che nessun percorso — ordine, grid, pyramid, recovery, split,
Coach/comandi — possa creare esposizione fuori dal gate. La prova non è
allegata.
**Impatto.** Un `P0 verification requirement` dichiarato aperto.
**Fonte necessaria.** Evidenza di verifica sui percorsi.
**Blocca.** NO per il documento.

---

## 5. Sessioni

### GAP-SESS-001 — Nessuna sessione di mercato è definita
**Descrizione.** `London`, `New York`, `Asian`, `killzone`: **0 occorrenze
ciascuno**. Delle 136 occorrenze di "session", quasi tutte sono sessioni
HTTP/JWT.
**Impatto.** Le strategie di sessione — che nel progetto esistono come famiglia
— non hanno alcun riferimento orario dichiarato.
**Fonte necessaria.** Corpus (categoria "Sessions & Timing", 319 occorrenze
indicative) + formalizzazione.
**Blocca.** **SÌ** per le strategie di sessione.

### GAP-SESS-002 — Timezone, DST e calendario dichiarati necessari ma non definiti
**Descrizione.** La fonte raccomanda di "implementare calendario/sessioni con
timezone broker, DST e validazione temporale" (riga 15125) e di derivare la
chiusura di seduta dai dati di sessione del simbolo gestendo festivi e chiusure
anticipate. Nessuna specifica operativa.
**Impatto.** Il requisito è chiaro nella direzione, non nel contenuto.
**Fonte necessaria.** Specifica del calendario.
**Blocca.** NO.

---

## 6. Indicatori

### GAP-IND-001 — Nessun parametro di indicatore 🔴
**Descrizione.** L'unica riga che nomina indicatori (1857) elenca ADX, RSI,
Bollinger, MACD, SAR, ATR, medie mobili e Ichimoku come oggetto di chiamate
`CopyBuffer` a ogni tick. Nessun periodo, nessuna soglia, nessun uso.
**Impatto.** Non è verificabile se un indicatore sia calcolato con i parametri
giusti, perché non esistono parametri dichiarati.
**Fonte necessaria.** Corpus + specifica delle strategie.
**Blocca.** **SÌ.**

### GAP-IND-002 — Nessuna definizione dei concetti SMC/ICT
**Descrizione.** `fair value gap`, `liquidity sweep`, `break of structure`,
`swing high`, `swing low`, `premium`, `discount`, `displacement`: **0 occorrenze
ciascuno**. I concetti esistono solo come **etichette di categoria** nel blocco
A4.2, con riferimenti a pagine di PDF assenti.
**Impatto.** Ogni giudizio di fedeltà concettuale sulle strategie SMC/ICT è
impossibile.
**Fonte necessaria.** I 13 PDF.
**Blocca.** **SÌ.**

### GAP-IND-003 — Nessun filtro di volume
**Descrizione.** Nessuna menzione di un filtro basato sul volume, in nessuna
forma.
**Impatto.** Se il codice ne implementa uno, non ha riferimento.
**Fonte necessaria.** Specifica dei filtri.
**Blocca.** NO.

---

## 7. Testing

### GAP-TEST-001 — Nessun criterio numerico di validazione di un backtest
**Descrizione.** `AUD0-MQL-013` (riga 1905) dice che il profit factor da solo
non codifica numero minimo di trade, drawdown, recovery, expectancy, stabilità e
performance out-of-sample, e chiede "un punteggio robusto". Non fornisce né la
formula né le soglie.
**Impatto.** Non esiste un criterio dichiarato per accettare o rifiutare un
risultato di backtest.
**Fonte necessaria.** Specifica dei criteri di validazione.
**Blocca.** NO per il documento; SÌ per qualunque decisione basata su backtest.
**Azione consigliata.** Definire i criteri prima di eseguire nuove campagne,
non dopo aver visto i risultati.

### GAP-TEST-002 — Nessuna evidenza allegata
**Descrizione.** La fonte elenca dieci categorie di evidenza necessarie alla
chiusura dell'audit (righe 74–85): revisione MQL5 modulo per modulo, revisione
backend, revisione frontend, inventario test, inventario CI, build Docker
pulita, **compilazione MQL5**, parità backtest/runtime, backup/restore, replay
comandi e crash recovery. Nessuna è allegata.
**Impatto.** L'audit resta aperto per definizione della fonte stessa.
**Fonte necessaria.** Le evidenze.
**Blocca.** NO per questa fase.

### GAP-TEST-003 — Il metodo di calcolo delle coperture non è dichiarato
**Descrizione.** Le percentuali per area (MQL5 88%, Backend 88%, Testing 68%,
totale 91%) non hanno metodo di calcolo. Non sono riproducibili.
**Impatto.** Un indicatore non riproducibile non può misurare il progresso.
**Fonte necessaria.** Definizione della metrica.
**Blocca.** NO.

---

## 8. Documentazione

### GAP-DOC-001 — Il documento si dichiara fonte unica di verità senza coprire il proprio dominio
**Descrizione.** Riga 4: `Document role: single source of truth`. Il prodotto è
un Expert Advisor che opera con strategie; il documento non contiene alcuna
specifica di strategia.
**Impatto.** Chi lo tratta come completo trae conclusioni su un dominio che il
documento non copre. È la contraddizione C-1 dell'analisi.
**Fonte necessaria.** Un documento di strategie che diventi parte della fonte
unica, oppure una dichiarazione di ambito che restringa la pretesa.
**Blocca.** NO, ma va dichiarato.

### GAP-DOC-002 — Contraddizione fra "nessuna contraddizione architetturale" e un P0 di contratto
**Descrizione.** Riga 14867: `No contradiction currently requires architectural
redesign`. Riga 1785: il drift del contratto delle strategie è
`P0 strategy-contract integrity` e richiede di **generare** il registro da una
fonte canonica — un cambio strutturale.
**Impatto.** Le due affermazioni non sono conciliabili senza una definizione di
"riprogettazione architetturale", che manca.
**Fonte necessaria.** Chiarimento.
**Blocca.** NO.

### GAP-DOC-003 — Il registro cross-file elenca 4 contraddizioni, tutte di configurazione
**Descrizione.** Righe 533–551: formato utente admin, piano Render, branch
canonico, self-hosting. Nessuna riguarda strategie o trading.
**Impatto.** Il registro delle contraddizioni non copre il dominio di trading:
non è una garanzia di assenza, è assenza di controllo.
**Fonte necessaria.** Revisione delle contraddizioni sul dominio di trading.
**Blocca.** NO.

### GAP-DOC-004 — Un token appare in chiaro nella fonte
**Descrizione.** La stringa `NEXUS_BRIDGE_TOKEN_2026` compare 6 volte nel
documento, citata come reperto d'audit.
**Impatto.** Il documento archiviato contiene un valore che il requisito
`NEXUS-SEC-002` (riga 14807) vieta di lasciare in sorgente, bundle, log o token
statici condivisi. Archiviandolo, il repository conserva una copia in più.
**Fonte necessaria.** Nessuna: è una decisione operativa.
**Blocca.** NO.
**Azione consigliata.** Verificare che quel token sia stato ruotato. Se non lo
è, ruotarlo prima di qualunque esposizione del repository. **Non è stato
modificato in questa fase**: alterare la fonte ne invaliderebbe l'hash.

---

## 9. Dipendenze dalle fonti originali

### GAP-SRC-001 — I 13 PDF del corpus non sono nel repository 🔴
**Descrizione.** Il blocco A4.2 (righe 15058–15460) indicizza 13 PDF per
**1092 pagine**, di cui **912** con testo nativo o OCR. Riporta per ciascuno le
"pagine più indicative" per concetto. **Nessuno dei 13 file è presente.**
**Impatto.** L'audit di fedeltà — confronto fra codice e definizione d'origine —
è impossibile. È la lacuna che governa tutte le altre della sezione strategie.
**Fonte necessaria.** I 13 PDF elencati nell'analisi, sezione 26.
**Blocca.** **SÌ. È il blocco principale.**
**Azione consigliata.** Acquisirli e registrarli in `SOURCE_MANIFEST.json` con
hash, prima di aprire la fase di fidelity audit.

### GAP-SRC-002 — L'indicizzazione è per pagina, non per contenuto 🔴
**Descrizione.** Il corpus è descritto come "pagine più indicative" per
categoria. Nessuna regola è riprodotta. La fonte lo dichiara: "un'occorrenza non
dimostra che una regola sia corretta, completa o traducibile automaticamente in
codice" (riga 15486).
**Impatto.** Anche avendo i PDF, servirà una fase di **formalizzazione**: le
statistiche di occorrenza non sono una specifica.
**Fonte necessaria.** I PDF + lavoro di formalizzazione.
**Blocca.** **SÌ.**
**Azione consigliata.** Non pianificare il fidelity audit come lettura diretta:
prevedere una fase di estrazione e formalizzazione delle regole.

### GAP-SRC-003 — 180 pagine su 269 della famiglia "Sequence" non hanno testo estratto 🔴
**Descrizione.** `Sequence_2_unlocked.pdf`: **119 pagine, 0 estratte, 0
caratteri**. `Sequence.pdf`: 56/76. `Sequence_1.pdf`: 46/74.
**Impatto.** La categoria "Sequence / Proprietary Models" ha 22 occorrenze
indicative, la penultima densità del corpus. Questo numero **non dimostra** che
il tema sia poco trattato: dimostra che è poco *leggibile* con l'estrazione
usata. Ogni conclusione tratta da quella densità sarebbe infondata.
**Fonte necessaria.** Gli stessi PDF con OCR adeguato, o lettura visiva.
**Blocca.** **SÌ** per il modello proprietario.
**Azione consigliata.** Trattare la famiglia "Sequence" come non analizzata,
non come poco rilevante.

### GAP-SRC-004 — La verifica grafica supplementare è dichiarata incompleta
**Descrizione.** Riga 15083: `Additional graphical-page verification: IN
PROGRESS`. Riga 15085: `Final comparison against NEXUS: NOT YET DECLARED
COMPLETE`. La fonte stessa dice che le pagine grafiche con OCR assente o debole
richiedono verifica visiva diretta (riga 15486).
**Impatto.** Le strategie SMC/ICT sono in larga parte insegnate per immagini. La
parte visiva del corpus è quella non ancora verificata.
**Fonte necessaria.** Verifica visiva delle pagine grafiche.
**Blocca.** **SÌ** per i concetti derivati da grafici.

### GAP-SRC-005 — Il Master aggiornato annunciato non è stato fornito
**Descrizione.** Alla fase precedente era stata annunciata la consegna di
`NEXUS_CORPUS_SEMANTIC_AUDIT_PRELIMINARY_v1.md`, dei materiali di corso e di un
Master aggiornato. Di questi, in questo incarico è stato allegato **solo**
`NEXUS_MASTER_PROJECT_v18.md`, che è la versione già presente nel repository
(stesso SHA-256).
**Impatto.** La dipendenza D8 resta aperta: l'incarico ha archiviato e
analizzato una fonte, non ha ricevuto le fonti mancanti.
**Fonte necessaria.** I documenti annunciati.
**Blocca.** **SÌ.**
**Azione consigliata.** Confermare quali documenti esistono davvero e in quale
forma, prima di pianificare la fase successiva.

---

## Riepilogo

| Categoria | Lacune | Di cui bloccanti |
|---|---:|---:|
| Architettura | 3 | 0 |
| Strategie | 8 | 5 |
| Risk management | 3 | 0 |
| Esecuzione | 3 | 0 |
| Sessioni | 2 | 1 |
| Indicatori | 3 | 2 |
| Testing | 3 | 0 |
| Documentazione | 4 | 0 |
| Fonti originali | 5 | 5 |
| **Totale** | **34** | **13** |

I 34 identificatori sono tutti distinti; ogni lacuna compare in una sola
categoria. Le 13 bloccanti sono: `GAP-STRAT-001`, `GAP-STRAT-002`,
`GAP-STRAT-003`, `GAP-STRAT-004`, `GAP-STRAT-005`, `GAP-SESS-001`,
`GAP-IND-001`, `GAP-IND-002`, `GAP-SRC-001`, `GAP-SRC-002`, `GAP-SRC-003`,
`GAP-SRC-004`, `GAP-SRC-005`.

**Ma i blocchi indipendenti sono solo 2.** Le altre 11 sono conseguenze: si
risolvono da sé quando si risolvono le radici.

| Radice | Cosa sblocca |
|---|---|
| `GAP-SRC-005` — le fonti annunciate non sono state fornite | `GAP-SRC-001` e, a cascata, `GAP-SRC-002/003/004`, `GAP-IND-001/002`, `GAP-STRAT-003/004/005`, `GAP-SESS-001` |
| `GAP-STRAT-001` — nessuna strategia è nominata nella fonte | `GAP-STRAT-002` e ogni verifica di completezza dell'inventario |

### La catena di dipendenza

```text
GAP-SRC-005  (fonti annunciate non fornite)
   └── GAP-SRC-001  (13 PDF assenti)
          ├── GAP-SRC-002  (indicizzazione per pagina, serve formalizzazione)
          ├── GAP-SRC-003  (180 pagine "Sequence" illeggibili)
          ├── GAP-SRC-004  (verifica grafica incompleta)
          └── GAP-IND-002  (concetti SMC/ICT non definiti)
                 ├── GAP-STRAT-003  (regole di ingresso)
                 ├── GAP-STRAT-004  (regole di uscita)
                 ├── GAP-STRAT-005  (SL/TP)
                 └── GAP-SESS-001   (sessioni di mercato)

GAP-STRAT-001 (nessuna strategia nominata)
   └── GAP-STRAT-002 (nessun conteggio)
          └── ogni verifica di completezza dell'inventario
```

**Conseguenza operativa.** Risolvere `GAP-SRC-005` (fornire i documenti
annunciati) e `GAP-STRAT-001` (dichiarare l'elenco delle strategie) sblocca 11
delle 13 lacune bloccanti. Nessun'altra azione documentale le sblocca: non è un
problema che si risolve leggendo meglio la fonte disponibile.

## Collegamenti

`docs/sources/master/NEXUS_MASTER_PROJECT_v18.md` ·
`docs/audits/master/NEXUS_MASTER_PROJECT_v18_ANALYSIS.md` ·
`docs/audits/master/NEXUS_MASTER_STRATEGY_INVENTORY.json` ·
`docs/audits/master/NEXUS_MASTER_REQUIREMENTS.json` ·
`docs/sources/SOURCE_MANIFEST.json`
