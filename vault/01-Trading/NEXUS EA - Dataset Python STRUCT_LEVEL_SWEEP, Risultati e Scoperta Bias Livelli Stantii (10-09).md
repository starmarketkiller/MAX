# Dataset Python offline STRUCT_LEVEL_SWEEP - risultati e un bias metodologico trovato eseguendolo

Script: `server/research_scripts/struct_level_sweep_dataset.py`. Fonte dati: `nxs_m15_gold_extended.csv`
(M15, 2023.10.02 -> 2026.08.25 - dati SIMULATI/futuri del progetto NEXUS, non storico GOLD reale:
il prezzo arriva a superare $5500 a inizio 2026 per poi ritracciare a ~$4600 ad agosto - una
dinamica di mercato sintetica, tenerlo presente per qualunque soglia in pip assoluti).

Nessun codice di Structure Engine/Reaction Engine/strategie toccato. Nessun SL/TP usato per
definire successo - solo reclaim/broken/MFE/MAE a orizzonti di tempo fissi.

## Fedelta' dichiarata

- **SWING (H4, wing=3)**: fedele, nessuna dipendenza da ATR, replica esatta di `NXS_IsSwingHigh/Low`.
- **WICK_H4**: fedele, replica esatta di `_NXS_WickSweep_UpdateLevel` (soglia 15 pip fissi).
- **PIVOT multi-TF (H1/H4/D1, wing=5)**: fedele su H1/H4 (resample M15->H4 verificato **bit-esatto**
  contro `nxs_h4_gold_29-08.csv`, 2533 barre, diff massima 0.0). **D1 non verificato** contro un file
  di riferimento - confine giornata approssimato a mezzanotte, non al vero orario di apertura sessione
  del broker.
- **SNR_H4** (rolling 12 chiusure H4): fedele, nessuna dipendenza da ATR.
- **OB/FVG: NON replicati** in questo primo giro - dipendono da `g_atr` (handle live, warm-up non
  bit-verificabile offline) + soglia di displacement sulla candela successiva, due gradi di liberta'
  in piu' che avrebbero reso il confronto meno onesto rispetto alle altre 4 fonti. Rimandabile a un
  secondo giro.
- **MFE/MAE_5m: NON calcolabile** - M15 e' il dato piu' fine disponibile nel repo (nessun M1/M5).
  Calcolati invece 15m/30m/1h/4h (1/2/4/16 barre M15).

## Scala del dataset

13.224 livelli candidati generati (SWING 893, WICK_H4 6680, PIVOT H1 2116/H4 548/D1 82, SNR_H4 2905)
-> 484.552 touch event totali (556 censurati per fine-dataset, esclusi dalle statistiche). Safety cap
di 50 touch per livello (documentato nello script) per evitare costi computazionali spropositati su
livelli "incollati" al prezzo (soprattutto SNR_H4, ricalcolato ogni barra).

## SCOPERTA: il bin "100+" era inquinato da livelli stantii di oltre un anno

Prima lettura (tutti i touch, nessun filtro di eta'): il bin 100+ mostrava **36% reclaim, MFE_1h
mediano -1640 pip, MAE_1h mediano +1759 pip** - numeri assurdi per un orizzonte di 1 ora. Causa
isolata riga per riga: alcuni "livelli" (swing/pivot/wick formati a inizio 2025 quando GOLD era
~$2950) venivano "toccati" per la PRIMA volta solo a fine gennaio 2026, quando il prezzo (in questo
dataset simulato) aveva gia' superato $5560 - una differenza di oltre 2600 pip accumulata in oltre
300 giorni di trend, non uno sweep. L'entry ipotetico usato per MFE/MAE (il prezzo del livello,
corretto per sweep genuini di poche decine/centinaia di pip) diventa privo di senso quando il primo
touch arriva a distanza di mesi e migliaia di pip - non e' un bug di calcolo, e' un difetto del
modello: **un "livello" non dovrebbe restare valido all'infinito**, o quantomeno un touch cosi'
lontano nel tempo non e' lo stesso fenomeno di uno sweep a poche ore/giorni dalla nascita del livello.

Verificato: `age_at_touch_hours` mediano per il bin 100+ = **1780 ore (~74 giorni)**, contro
348-359 ore (~14-15 giorni) per TUTTI gli altri bin (0-10...75-100). Il 44.8% di TUTTI i touch del
dataset ha eta' > 30 giorni al momento del touch.

### Ricalcolo filtrato a livelli "freschi" (eta' <= 30 giorni al touch) - `struct_level_sweep_bins_fresh30d.csv`

| bin | n | %reclaim | median MFE_1h | mean MFE_1h | median MAE_1h | mean MAE_1h | median MFE_4h | mean MFE_4h | median age(h) |
|---|---|---|---|---|---|---|---|---|---|
| 0-10 | 82665 | 100.0 | 46.3 | 70.5 | 12.3 | 31.8 | 75.3 | 115.9 | 202.5 |
| 10-20 | 39164 | 100.0 | 56.6 | 84.8 | 18.7 | 43.3 | 91.6 | 139.9 | 197.9 |
| 20-30 | 23163 | 100.0 | 62.0 | 93.1 | 27.4 | 52.7 | 102.2 | 155.9 | 196.2 |
| 30-40 | 15903 | 100.0 | 61.7 | 95.3 | 36.8 | 60.0 | 105.0 | 161.7 | 197.0 |
| 40-50 | 11641 | 100.0 | 64.1 | 99.1 | 45.9 | 67.4 | 108.9 | 168.1 | 201.8 |
| 50-75 | 19435 | 100.0 | 61.6 | 98.7 | 61.7 | 79.1 | 108.5 | 168.7 | 196.0 |
| 75-100 | 11858 | 100.0 | 57.3 | 103.9 | 84.4 | 98.2 | 110.2 | 184.6 | 192.2 |
| **100+** | 63493 | **73.6** | **30.9** | -200.1 | 176.9 | 467.7 | 40.4 | -140.2 | 254.5 |

Il filtro sposta il bin 100+ da "sembra rotto per sempre" (36% reclaim, MFE deeply negativo) a
"reclama comunque piu' spesso che no" (73.6%, MFE mediano leggermente positivo a 1h) - una lettura
completamente diversa. La MEDIA resta negativa (tirata da una coda di trend-continuation genuini
entro 30 giorni, che esistono davvero e vanno tenuti distinti dal reversal).

## SCOPERTA 2: sotto i 100 pip, reclaim ~100% quasi ovunque - il bin scheme e' probabilmente troppo corto per questo range di prezzo

Anche filtrando a soli livelli freschi, **tutti i bin da 0-10 a 75-100 mostrano 100.0% reclaim** entro
l'orizzonte di 5 giorni. Interpretazione piu' plausibile: con GOLD in questo dataset scambiato a
$4000-5500+, uno sfondamento di 100 pip (=$10) e' una frazione minuscola del range di volatilita'
reale dello strumento a questi livelli di prezzo (range H4 tipici molto piu' ampi) - probabilmente
rientra nel "rumore" quasi per costruzione, non e' ancora un test genuino del livello. **La vera
differenziazione probabile vive TUTTA dentro/oltre l'attuale bin 100+** (che qui abbiamo gia' visto
splittarsi in "sweep genuino filtrato per eta'" vs "trend continuation stantio"). Prossimo passo
naturale, se si vuole approfondire: estendere i bin oltre 100 (100-150, 150-200, 200-300, 300-500,
500+) invece di trattarli come un unico blocco, e/o normalizzare la profondita' di sfondamento
rispetto all'ATR/volatilita' corrente invece che in pip assoluti fissi.

## First touch vs repeated touch (tutti i bin, dati non filtrati per eta')

- First touch: n=12.250, 95.5% reclaim, penetrazione mediana 34.8 pip.
- Repeat touch: n=471.746, 72.9% reclaim, penetrazione mediana 52.9 pip.

I "primi touch" sono una minoranza netta del campione (2.5%) - la stragrande maggioranza dei touch
osservati e' chop ripetuto su livelli gia' esistenti (specialmente WICK_H4/SNR_H4, ricreati/ritoccati
di continuo). I first touch reclamano piu' spesso e penetrano meno dei touch ripetuti - plausibile:
un livello appena nato e' "difeso" meglio la prima volta, i touch successivi arrivano quando il
livello e' gia' stato eroso/testato piu' volte.

## Distribuzione per source_tf (non filtrato per eta')

| source | source_tf | n | %reclaim | median penetration (pip) |
|---|---|---|---|---|
| PIVOT | D1 | 2218 | 52.0 | 618.05 |
| PIVOT | H1 | 76155 | 72.1 | 52.60 |
| PIVOT | H4 | 18251 | 67.6 | 69.40 |
| SNR_H4 | H4 | 105828 | 73.7 | 49.80 |
| SWING | H4 | 31417 | 69.2 | 60.30 |
| WICK_H4 | H4 | 250127 | 74.9 | 50.70 |

PIVOT/D1 si distingue nettamente (reclaim piu' basso, penetrazione mediana >10x le altre fonti) -
coerente con l'essere la fonte piu' "strutturale"/rara e quindi piu' esposta proprio al bias dei
livelli stantii descritto sopra (verificabile: la maggior parte dei suoi touch probabilmente cade
nel bin 100+ e ha eta' elevata).

## Conclusioni su quali campi/stati sono realmente informativi (richiesto esplicitamente dall'utente prima di passare alla telemetria MQL5)

- **age_at_touch e' informativo E necessario come filtro**, non solo un campo descrittivo - senza
  filtrarlo il bin 100+ e' inutilizzabile.
- **touch_number (first vs repeat) e' informativo**: comportamento diverso e sistematico.
- **source_tf e' informativo**, soprattutto per isolare D1 (raro, strutturale, diverso dagli altri).
- **Il bin scheme 0-10...100+ e' probabilmente sotto-dimensionato** per questo range di prezzo -
  bisogna raffinarlo oltre i 100 pip prima di considerarlo definitivo.
- **reclaimed/broken cosi' come definiti (chiusura M15 di ritorno, orizzonte 5 giorni) sono
  utilizzabili**, ma "broken" andrebbe probabilmente ridefinito in funzione dell'eta' (un vero
  structural break e' un fenomeno di breve/medio termine, non "mai piu' tornato in 5 giorni" per un
  livello di un anno fa che ovviamente non torna).
- **MFE/MAE a orizzonti fissi (15m/30m/1h/4h) sono utili SOLO se accoppiati al filtro eta'** - da soli
  senza quel filtro danno numeri fuorvianti.
- OB/FVG restano da aggiungere in un secondo giro, se si decide che vale la pena l'onere di
  replicare fedelmente la dipendenza da ATR.

Prossimo passo (non ancora fatto, in attesa di indicazioni): raffinare i bin oltre 100 pip e/o
normalizzare per ATR, poi eventualmente ridefinire il dataset con un filtro eta' incorporato
direttamente nello script (non solo come analisi post-hoc) prima di considerare lo schema definitivo
e passare alla telemetria MQL5 tick-level.
