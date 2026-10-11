# Fonti per lo storico CPI, NFP, FOMC e PCE

Inventario al 2026-10-11. Nessun dato è stato scaricato, nessun servizio acquistato. Il calendario di `/api/calendar` è `SYNTHETIC_DEMO` e non vale come evidenza.

Raggiungibilità provata da questo container cloud (solo `HEAD`/pagina indice). Il PC può avere esiti diversi.

| Evento | Cosa serve | Fonte ufficiale | Costo e accesso | Da qui | Note |
|---|---|---|---|---|---|
| CPI | data e ora di pubblicazione | BLS, calendario e archivio release (`bls.gov/schedule/news_release/cpi.htm`, archivio news release CPI) | gratuito | **403** (BLS blocca client non browser) | ora convenzionale 08:30 New York, **non verificata da qui** |
| CPI | valore actual (prima pubblicazione) | ALFRED (St. Louis Fed), serie CPIAUCSL e CPILFESL con le vintage | gratuito, chiave API con registrazione | web: nessuna risposta; API: **400** senza chiave (host raggiungibile) | serve la vintage del giorno di uscita, non il valore rivisto |
| CPI, NFP | valori | BLS Public Data API v2 (`api.bls.gov`) | gratuito; senza chiave limiti giornalieri bassi, chiave gratuita con registrazione | **200** | dà i valori, non gli orari; i valori sono rivisti |
| NFP | data e ora | BLS Employment Situation, calendario e archivio | gratuito | **403** | ora convenzionale 08:30 New York, non verificata da qui |
| NFP | actual alla prima uscita | ALFRED, serie PAYEMS (vintage) | gratuito, chiave | come sopra | la prima stima viene rivista nei due mesi successivi |
| PCE | data e ora | BEA, Personal Income and Outlays (`bea.gov/news/schedule`, archivio release) | gratuito | **200** | **08:30 verificata** sulla pagina BEA il 2026-10-11 |
| PCE | valori | BEA API (NIPA) oppure ALFRED (PCEPI, PCEPILFE) | gratuito, registrazione (UserID BEA o chiave FRED) | BEA 200; FRED API raggiungibile | — |
| FOMC | date delle riunioni | Fed, `federalreserve.gov/monetarypolicy/fomccalendars.htm` | gratuito | **200** | elenca le date, non l'ora |
| FOMC | ora dello statement | comunicati Fed (`newsevents/pressreleases/monetaryYYYYMMDDa.htm`) | gratuito | **200** | **"For release at 2:00 p.m."** verificato su 2025-01-29 e 2025-09-17; va letto per ogni riunione, non assunto |
| Tutti | forecast/consensus | nessuna fonte ufficiale gratuita | consensus Bloomberg/Reuters a pagamento; Forex Factory e Investing.com hanno termini d'uso che limitano lo scraping | Forex Factory **403** | non usare senza licenza chiara |
| Tutti | actual, forecast, previous con orario | calendario economico MetaQuotes dentro MT5 (`CalendarValueHistory`) | incluso nel terminale | solo dal PC | funziona sul terminale, non nel Strategy Tester; serve uno script di export dedicato (non scritto) e una verifica dei termini MetaQuotes |

## Regole per costruire lo storico

1. Una riga per pubblicazione, con il formato di `release_time.py` (`REQUIRED_COLUMNS`): evento, periodo di riferimento, data e ora locali, fuso, URL della fonte, istante di lettura.
2. Data e ora vanno lette dall'archivio della singola pubblicazione, non dedotte dal calendario pianificato. Le uscite possono slittare (per esempio per chiusure del governo federale).
3. `actual` è il valore della prima pubblicazione (vintage ALFRED del giorno), non quello rivisto.
4. `forecast` resta vuoto se non c'è una fonte con licenza. Un forecast senza `forecast_source` è rifiutato da `validate_rows`.
5. La conversione UTC ed Europe/Rome la fa `to_utc_and_rome`. Nelle settimane di disallineamento DST (marzo e ottobre/novembre) un'uscita delle 08:30 di New York cade alle 13:30 di Roma invece che alle 14:30: `dst_mismatch` la marca.
6. Allineamento con il prezzo: la barra M15 che contiene `release_utc` è quella dell'evento. Le barre del Behavior Lab sono in UTC, quindi non serve altra conversione.

## Cosa manca per iniziare

Una chiave FRED (gratuita, registrazione a nome dell'utente) per le vintage ALFRED, e un accesso da browser o dal PC alle pagine BLS. Senza queste due cose CPI e NFP non hanno un orario verificato né un actual alla prima uscita.
