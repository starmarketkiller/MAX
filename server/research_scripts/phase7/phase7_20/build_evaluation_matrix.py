#!/usr/bin/env python3
"""Phase 7.20 punto 1 (matrice) - valuta ogni strategia dell'universo
(Phase 7.20 punto 0) su 16 criteri indipendenti e assegna una delle 5
categorie. Il PF storico (dove disponibile) NON e' mai usato da solo
per classificare - e' un campo fra 16, sempre accompagnato da una nota
su qualita' campione/dati.

Tier A (9 strategie): dive-dive narrativo completo sui 16 criteri -
le strategie esplicitamente richieste (BREAKOUT_ACC/ORDER_BLOCK/TSI/
ADX_RSI/SAR) + le uniche altre con evidenza quantitativa reale
disponibile nel corpus (LIQ_SWEEP/FVG_CONT/BOLLINGER/MACD, da sweep37).

Tier B/C: classificazione compatta basata su regole esplicite e
verificabili (stato difetto + evidenza disponibile), non narrata
strategia per strategia - la matrice resta comunque COMPLETA (tutte
le 83 righe presenti, ognuna con una motivazione)."""
import os
import sys

PHASE720_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE720_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

CRITERIA = [
    ("integrita_implementativa", "Il TF guard/lo stato interno sono verificati puliti (non solo assunti)?"),
    ("identity_parity", "L'identita' canonica MQL5 vs eventuale motore Python e' accertata (non presunta)?"),
    ("affidabilita_dataset", "I dati usati per qualunque evidenza sono a tick reali, qualita' nota, tracciabile?"),
    ("evidence_quality", "Che tipo di evidenza esiste: nessuna / diagnostica / economica reale / entrambe?"),
    ("bug_noti", "Difetti strutturali noti (di qualunque classe, non solo cross-TF), fissati o no?"),
    ("meccanismo_comprensibile", "La logica del segnale e' spiegabile in termini discrezionali/umani?"),
    ("segnali_preliminari_edge", "Esiste un indizio quantitativo preliminare di comportamento non casuale?"),
    ("robustezza_storica", "Il pattern (se esiste) e' stato osservato in piu' di un regime/periodo?"),
    ("cost_sensitivity", "Sono disponibili spread/slippage/commissioni reali per stimare l'impatto costi?"),
    ("oos_gia_disponibile", "Esiste gia' un holdout/out-of-sample separato dal campione di scoperta?"),
    ("execution_realism", "L'evidenza viene da fill reali (broker) o solo da segnali teorici/Research Mode?"),
    ("sample_size", "Quanti eventi/trade indipendenti sono disponibili?"),
    ("dipendenza_pochi_regimi", "Il risultato dipende fortemente da pochi anni/una sola direzione?"),
    ("compatibilita_conto_piccolo", "Frequenza di trade e dimensione tipica dei movimenti sono compatibili con size ridotta?"),
    ("canonical_event_dataset_possibile", "E' possibile costruire un canonical event dataset (schema Phase 7.19) oggi?"),
    ("visual_audit_readiness", "Livello di Fidelity (Phase 7.19 A/B/C/D) raggiungibile oggi per un audit visivo?"),
]

CATEGORIES = ["READY_FOR_EDGE_VALIDATION", "PROMISING_BUT_NEEDS_INTEGRITY_WORK",
             "INSUFFICIENT_EVIDENCE", "GENUINE_NO_EDGE_CANDIDATE", "DO_NOT_USE_YET"]


def _breakout_acc():
    return {
        "category": "READY_FOR_EDGE_VALIDATION",
        "integrita_implementativa": "PULITA E VERIFICATA - guardia di cooldown per-direzione aggiunta e "
            "validata in Phase 7.9E/F/G (collasso empirico 95->0 con lo stato condiviso, esperimento "
            "controllato sull'ordine reale dei pass). Nessuna guardia TF-scoped necessaria per questa "
            "classe di difetto (il bug era un altro: nessun cooldown 'gia' tradato questo breakout', non "
            "contaminazione cross-TF).",
        "identity_parity": "Motore Python dichiarato fedele riga-per-riga (BREAKOUT_ACC e' single-TF per "
            "costruzione, non affetto dal difetto cross-TF di ORDER_BLOCK/TSI/altri).",
        "affidabilita_dataset": "Dataset canonico Phase 7.9H/7.9K costruito da trade log MT5 REALI "
            "(entry_fill_price/exit_fill_price/realized_pnl/realized_swap/realized_commission per evento, "
            "non solo segnali teorici).",
        "evidence_quality": "ECONOMICA REALE gia' esistente (non solo diagnostica) - 75 eventi con fill "
            "reali, MFE/MAE, orizzonti multipli, path anatomy completa.",
        "bug_noti": "Difetto di cooldown CONFERMATO E CORRETTO in Phase 7.9G. Difetto secondario di offset "
            "(forward path) trovato e corretto in Phase 7.9K (EMA100 precision, 0 eccezioni su 72 eventi "
            "valutabili - ma l'allineamento costante rende l'effetto NON isolabile, nessun gruppo di "
            "controllo disponibile in questo campione).",
        "meccanismo_comprensibile": "SI (parzialmente, dichiarato onestamente) - 'trend persistence / "
            "direction-dependent' e' un'etichetta descrittiva candidata, MAI affermata come meccanismo "
            "causale dimostrato (decisione Phase 7.9K: MECHANISM_PARTIALLY_SUPPORTED, confidence BASSA).",
        "segnali_preliminari_edge": "SI ma DEBOLE E ASIMMETRICO - BUY continuation 69.4% (60 eventi), SELL "
            "continuation solo 20.0% (15 eventi, 8/10 comparabili finiscono in FAILURE a 60 barre). Il "
            "pattern direzionale e' sopravvissuto a una correzione metodologica sostanziale sugli STESSI "
            "dati (non un campione indipendente) - persistenza, non prova di non-casualita' ne' di edge "
            "incrementale vs benchmark (mai testato).",
        "robustezza_storica": "NON VERIFICABILE con questo campione - un solo regime di mercato "
            "rappresentato (dichiarato esplicitamente in Phase 7.9J/K, invariato).",
        "cost_sensitivity": "DATI GIA' DISPONIBILI - realized_swap/realized_commission/slippage per ogni "
            "evento con fill reale, nessun nuovo dato necessario per un primo costo-sensitivity pass.",
        "oos_gia_disponibile": "NO - tutti i 75 eventi sono lo stesso campione di scoperta/correzione. "
            "Un vero holdout temporale non e' mai stato ritagliato.",
        "execution_realism": "ALTA - fill reali broker per la maggioranza degli eventi (non Research Mode "
            "puro), slippage segnale->fill gia' misurato per evento.",
        "sample_size": "75 eventi totali, MA fortemente sbilanciato 60 BUY / 15 SELL - il lato SELL ha un "
            "campione troppo piccolo per conclusioni proprie (solo 10 comparabili al netto dei censurati).",
        "dipendenza_pochi_regimi": "SI, FORTEMENTE (dichiarato in Phase 7.9K) - dipendenza da direzione "
            "(BUY >> SELL) e un solo regime di mercato storico. L'allineamento di trend non e' testabile "
            "in questo campione (nessun gruppo di controllo non-allineato).",
        "compatibilita_conto_piccolo": "DA VERIFICARE - non stimata in questa fase (SL/TP/size non "
            "riesaminati qui, nessun sizing proposto).",
        "canonical_event_dataset_possibile": "GIA' ESISTE (Phase 7.9H/K, schema v2) - compatibile in "
            "sostanza con lo schema EVENT_AUDIT_PACKET_V1 di Phase 7.19 (richiede solo un adapter, non "
            "nuovi dati).",
        "visual_audit_readiness": "Fidelity B raggiungibile oggi (dimostrato nell'esempio reale di Phase "
            "7.19) - stesso feed/fill reale, granularita' non tick-level.",
        "fragility_note": "8.7% degli eventi comparabili (4/46) cambiano ESITO (continuation<->failure) "
            "da una sola correzione di offset - la classificazione binaria a singolo orizzonte e' "
            "dimostrabilmente sensibile a dettagli metodologici minori. Da trattare con cautela in "
            "qualunque test economico (preferire MFE/MAE continui a un'etichetta binaria).",
    }


def _order_block():
    return {
        "category": "READY_FOR_EDGE_VALIDATION",
        "integrita_implementativa": "PULITA E VERIFICATA - guardia TF-scoped applicata (Phase 7.14) e "
            "validata dinamicamente su trace EA reale pre/post fix (guardia efficace al 100%, 0 mutazioni "
            "non canoniche post-fix). Perimetro OB_MIT chiuso (Phase 7.15): eredita il fix automaticamente "
            "(nessuno stato proprio), ma il comportamento dinamico con ENTRAMBE abilitate non e' mai stato "
            "osservato dal vivo (solo statico+deterministico).",
        "identity_parity": "APPROXIMATION_WITH_KNOWN_GAPS (Phase 7.16) - il motore Python NON e' fedeltà "
            "evento-per-evento provata contro un trace EA live, solo strutturalmente TF-scoped come "
            "l'implementazione V2. Non usare il motore Python come fonte primaria per un test economico.",
        "affidabilita_dataset": "Il trace diagnostico post-fix (Phase 7.14) e' a tick reali (100%, migliore "
            "qualita' di sweep37) ma e' RESEARCH MODE - nessun fill reale, solo eventi di zona/retest.",
        "evidence_quality": "SOLO DIAGNOSTICA per l'implementazione V2 attuale (canonica) - zero evidenza "
            "ECONOMICA post-fix. L'evidenza economica pre-fix (phase2_baseline, phase_partB) e' "
            "esplicitamente non riutilizzabile (HISTORICAL_CONTAMINATED, Phase 7.14 historical_evidence_"
            "migration_v1.json).",
        "bug_noti": "Difetto CROSS_TIMEFRAME_STATE_CONTAMINATION confermato e corretto in Phase 7.14. "
            "Nessun altro difetto strutturale noto per V2.",
        "meccanismo_comprensibile": "SI - zona di Order Block (ultima candela opposta prima di un "
            "movimento impulsivo) + retest, meccanismo SMC ampiamente discrezionale e spiegabile.",
        "segnali_preliminari_edge": "NESSUNO PER L'IMPLEMENTAZIONE V2 (canonica) - non ancora misurato. "
            "L'unica evidenza PF esistente (sweep37 non lo include; phase2_baseline/phase_partB "
            "contaminati) non e' utilizzabile.",
        "robustezza_storica": "NON VALUTABILE - nessun run economico V2 esiste su cui misurarla.",
        "cost_sensitivity": "NON DISPONIBILE - il trace post-fix e' Research Mode, nessun fill/costo reale "
            "catturato.",
        "oos_gia_disponibile": "NO - V2 non ha ANCORA un campione di scoperta economico, quindi la "
            "domanda OOS e' prematura (va prima costruito un dataset, poi split).",
        "execution_realism": "BASSA per ora (solo segnali Research Mode) - richiede un run con fill reali "
            "per un test economico credibile.",
        "sample_size": "8 eventi zona/retest osservati nella finestra diagnostica breve (Phase 7.14) - "
            "insufficiente per QUALUNQUE conclusione economica, sufficiente solo a validare il fix.",
        "dipendenza_pochi_regimi": "SCONOSCIUTA - mai misurata per V2.",
        "compatibilita_conto_piccolo": "DA VERIFICARE - non stimata in questa fase.",
        "canonical_event_dataset_possibile": "SI, MA VA COSTRUITO EX NOVO - richiede un run MT5 reale "
            "(non Research Mode) con InpStrategySelector isolato su V2, poi un builder che applichi lo "
            "schema EVENT_AUDIT_PACKET_V1 (Phase 7.19) - nessun dato di questo tipo esiste ancora.",
        "visual_audit_readiness": "Fidelity B raggiungibile con un nuovo run reale (dimostrato nell'esempio "
            "Phase 7.19, oggi pero' costruito su Research Mode, non fill reali - andrebbe rifatto con un "
            "run a fill reali per salire di fedelta').",
        "fragility_note": "Nessuna - il gap principale non e' fragilita' del pattern ma ASSENZA totale di "
            "un campione economico post-fix. Il fix stesso e' solidamente validato (causal validation "
            "separata dalla domanda di edge).",
    }


def _tsi():
    return {
        "category": "INSUFFICIENT_EVIDENCE",
        "integrita_implementativa": "PULITA E VERIFICATA - guardia TF-scoped applicata e validata "
            "dinamicamente in Phase 7.18 (guardia efficace al 100%, convergenza 100% EA reale post-fix vs "
            "ricostruzione Python TF-scoped nel periodo maturo comune).",
        "identity_parity": "PARTIAL_STRUCTURAL_MODEL_NOT_EVENT_LEVEL_PARITY_VALIDATED (Phase 7.18) - "
            "fiducia elevata dalla convergenza B/C di Phase 7.18, ma non parity evento-per-evento in senso "
            "stretto (nessun trace EA pluriennale raccolto).",
        "affidabilita_dataset": "Trace diagnostico post-fix a tick reali (Phase 7.18) ma finestra corta "
            "(8 mesi) e Research Mode (nessun fill).",
        "evidence_quality": "SOLO DIAGNOSTICA per V2 (canonica). Evidenza pre-fix (sweep37 S05, "
            "phase2_baseline, phase_partB) tutta classificata POSSIBLY_CONTAMINATED (Phase 7.17) - non "
            "riutilizzabile come evidenza di V2.",
        "bug_noti": "Difetto CROSS_TIMEFRAME_STATE_CONTAMINATION confermato e corretto in Phase 7.18 - il "
            "PIU' severo del corpus per meccanismo (filtro ricorsivo continuo, mai autoriparante).",
        "meccanismo_comprensibile": "PARZIALMENTE - TSI e' un oscillatore matematico (doppio smoothing "
            "EMA), il meccanismo del CALCOLO e' del tutto trasparente, ma il PERCHE' un cross TSI/signal "
            "dovrebbe anticipare un movimento di prezzo non e' una storia discrezionale altrettanto "
            "intuitiva quanto un pattern price-action (BREAKOUT_ACC/ORDER_BLOCK).",
        "segnali_preliminari_edge": "NESSUNO POSITIVO - il PF pre-fix (contaminato, sweep37 S05) era 0.76, "
            "il PIU' BASSO fra le 7 strategie di quella campagna insieme a BJORGUM. Nessuna fonte "
            "indipendente mostra un segnale preliminare positivo per TSI.",
        "robustezza_storica": "NON VALUTABILE per V2 - nessun run economico esiste.",
        "cost_sensitivity": "NON DISPONIBILE - Research Mode.",
        "oos_gia_disponibile": "NO.",
        "execution_realism": "BASSA - solo segnali Research Mode.",
        "sample_size": "CRITICO - solo 8 segnali D1 in 8 mesi (finestra Phase 7.18, EA reale post-fix). Il "
            "TF canonico D1 genera segnali D1 RARI per costruzione (attraversamento TSI/signal) - "
            "servirebbero ANNI di run reale solo per accumulare un campione minimo utilizzabile, prima "
            "ancora di poter giudicare l'economia.",
        "dipendenza_pochi_regimi": "SCONOSCIUTA per V2, ma il meccanismo ricorsivo rende ogni run "
            "sensibile alla profondita' del warm-up (dimostrato in Phase 7.18: 5 segnali residui B-vs-C "
            "spiegati ESATTAMENTE dalla differenza di warm-up, non dal difetto).",
        "compatibilita_conto_piccolo": "DA VERIFICARE, ma la rarita' dei segnali D1 la rende comunque "
            "poco interessante per un conto piccolo che cerca frequenza di verifica ragionevole.",
        "canonical_event_dataset_possibile": "SI IN TEORIA ma richiederebbe un run MOLTO piu' lungo (anni, "
            "non mesi) solo per accumulare un campione minimo - costo/beneficio sfavorevole rispetto a "
            "BREAKOUT_ACC/ORDER_BLOCK che hanno gia' dati o richiedono un run molto piu' breve.",
        "visual_audit_readiness": "Fidelity B raggiungibile con un run piu' lungo, ma bassa priorita' data "
            "la scarsita' di segnali attesi.",
        "fragility_note": "Il campione post-fix disponibile (8 eventi) e' troppo piccolo per QUALUNQUE "
            "affermazione, positiva o negativa - la classificazione INSUFFICIENT_EVIDENCE (non "
            "GENUINE_NO_EDGE_CANDIDATE) riflette proprio questo: il PF debole pre-fix e' un'indicazione, "
            "non una prova, ed e' comunque contaminato.",
    }


def _adx_rsi():
    return {
        "category": "DO_NOT_USE_YET",
        "integrita_implementativa": "NON VERIFICATA - NXS_Strat_ADXRSI() e' STATELESS (nessuno stato "
            "persistente fra barre, g_adx/g_rsi ricalcolati dal motore indicatori ogni tick) quindi NON a "
            "rischio di corruzione cumulativa come TSI/ORDER_BLOCK, MA non ha ALCUNA guardia TF e nessun "
            "bar-gate - letto direttamente dal sorgente in questa fase (non uno degli 20 candidati "
            "controllati in Phase 7.10). Trovato un problema strutturale NON ancora documentato altrove: "
            "mescola g_adx/g_rsi (calcolati su un TF fisso dal motore indicatori) con e50/price calcolati "
            "su NXS_EffTF() (TF variabile del router multi-TF) - un possibile disallineamento cross-TF di "
            "tipo diverso da quello di TSI/ORDER_BLOCK, mai quantificato.",
        "identity_parity": "NON VERIFICATA in questa fase.",
        "affidabilita_dataset": "L'unico dato quantitativo e' sweep37 (30% tick reali, qualita' inferiore "
            "ai diagnostici dedicati).",
        "evidence_quality": "SOLO sweep37 (PF singolo, nessun conteggio trade riportato in questo "
            "artifact) + un confronto indipendente su TradingView Pine ('MACD/ADX_RSI variante "
            "confermata' - testo ambiguo, non quantificato in dettaglio qui).",
        "bug_noti": "Nessun difetto CONFERMATO (mai auditata formalmente), ma il mescolamento g_adx/g_rsi "
            "(TF fisso) + e50/price (TF variabile) trovato in questa fase e' un candidato bug non "
            "investigato.",
        "meccanismo_comprensibile": "SI - trend EMA50 + banda RSI, filtro forza ADX>20. Meccanismo "
            "discrezionale semplice e spiegabile.",
        "segnali_preliminari_edge": "NEGATIVO - PF 0.82 in sweep37 (sotto 1.0), nessuna fonte indipendente "
            "mostra un segnale preliminare positivo.",
        "robustezza_storica": "NON VALUTABILE con i dati disponibili (un solo run sweep37).",
        "cost_sensitivity": "NON DISPONIBILE.",
        "oos_gia_disponibile": "NO.",
        "execution_realism": "BASSA-MEDIA (sweep37 e' 30% tick reali, non Research Mode puro ma non al "
            "livello dei diagnostici dedicati).",
        "sample_size": "SCONOSCIUTO - sweep37 riporta solo il PF aggregato, non il numero di trade per "
            "questa riga specifica.",
        "dipendenza_pochi_regimi": "SCONOSCIUTA.",
        "compatibilita_conto_piccolo": "NON VALUTATA.",
        "canonical_event_dataset_possibile": "SOLO DOPO un audit di integrita' dedicato (stesso schema "
            "gia' usato per BREAKOUT_ACC/ORDER_BLOCK/TSI) - prematuro costruirlo ora con un'identita' "
            "implementativa non accertata.",
        "visual_audit_readiness": "Fidelity D al massimo oggi (nessun trace reale dedicato).",
        "fragility_note": "Il PF debole (0.82) NON e' usato qui come criterio unico - la ragione primaria "
            "dell'esclusione e' l'integrita' non verificata, il PF debole e' una nota di cautela "
            "aggiuntiva, coerente con l'istruzione di non decidere sul solo PF.",
    }


def _sar():
    return {
        "category": "DO_NOT_USE_YET",
        "integrita_implementativa": "NON VERIFICATA - NXS_Strat_SAR() e' STATELESS (g_sar/g_ema9/g_ema21 "
            "ricalcolati dal motore indicatori ogni tick, nessuno stato persistente fra barre) quindi non "
            "a rischio di corruzione cumulativa, MA nessuna guardia TF e NESSUN bar-gate affatto (nemmeno "
            "un lastBarTime) - il piu' 'nudo' fra i candidati esaminati in questa fase.",
        "identity_parity": "NON VERIFICATA in questa fase.",
        "affidabilita_dataset": "SAR non compare nel set sweep37 (S01-S08) - nessun dato quantitativo "
            "MT5 dedicato trovato in questa fase.",
        "evidence_quality": "SOLO un confronto qualitativo su TradingView Pine: 'SAR ambiguo' (testo "
            "esplicito nel campo risultato della campagna) - nessun numero.",
        "bug_noti": "Nessun difetto CONFERMATO (mai auditata formalmente).",
        "meccanismo_comprensibile": "SI - Parabolic SAR sotto/sopra prezzo + allineamento EMA9/21, filtri "
            "opzionali di allineamento candela/pressione. Meccanismo discrezionale semplice.",
        "segnali_preliminari_edge": "NESSUNO - l'unica fonte indipendente lo descrive esplicitamente come "
            "'ambiguo'.",
        "robustezza_storica": "NON VALUTABILE - nessun dato quantitativo disponibile.",
        "cost_sensitivity": "NON DISPONIBILE.",
        "oos_gia_disponibile": "NO.",
        "execution_realism": "SCONOSCIUTA - nessun run dedicato trovato.",
        "sample_size": "SCONOSCIUTO - nessun conteggio trade disponibile in nessuna fonte.",
        "dipendenza_pochi_regimi": "SCONOSCIUTA.",
        "compatibilita_conto_piccolo": "NON VALUTATA.",
        "canonical_event_dataset_possibile": "SOLO DOPO un audit di integrita' dedicato E un primo run "
            "quantitativo (oggi non esiste nessuno dei due).",
        "visual_audit_readiness": "Fidelity D al massimo oggi.",
        "fragility_note": "Il gap principale qui e' l'assenza quasi totale di evidenza quantitativa "
            "propria (a differenza di ADX_RSI che almeno ha un PF sweep37) - 'ambiguo' su un motore terzo "
            "non basta a formulare un giudizio in nessuna direzione.",
    }


def _liq_sweep():
    return {
        "category": "PROMISING_BUT_NEEDS_INTEGRITY_WORK",
        "integrita_implementativa": "NON VERIFICATA - MAI controllata in nessuno dei 20 candidati di "
            "Phase 7.10. Letta in questa fase: NXS_Strat_LiqSweep() e' STATELESS (nessuno stato "
            "persistente proprio, riceve un riferimento SNXSSweepExt esterno gia' confermato altrove), "
            "nessuna guardia TF, nessun bar-gate interno. Il rischio di corruzione cumulativa e' basso "
            "(stateless) ma il rischio di segnali spuri su TF non canonico non e' escluso.",
        "identity_parity": "NON VERIFICATA in questa fase.",
        "affidabilita_dataset": "sweep37 (30% tick reali).",
        "evidence_quality": "SOLO sweep37 (PF singolo, nessun conteggio trade in questo artifact).",
        "bug_noti": "Nessun difetto CONFERMATO (mai auditata).",
        "meccanismo_comprensibile": "SI - reversal dopo uno sweep di liquidita' (rottura di un livello "
            "chiave seguita da rientro), con reason che riporta il livello esatto scatenante (Daily/"
            "Weekly/Monthly/Asia/Equal High-Low) - diagnostica gia' incorporata per capire quale livello "
            "produce l'edge.",
        "segnali_preliminari_edge": "IL PIU' POSITIVO DEL CORPUS - PF 1.04 in sweep37, l'UNICA delle 7 "
            "strategie di quella campagna sopra 1.0 (per quanto di poco e su qualita' dati 30% tick "
            "reali).",
        "robustezza_storica": "NON VALUTABILE - un solo run, nessuno split per regime.",
        "cost_sensitivity": "NON DISPONIBILE.",
        "oos_gia_disponibile": "NO.",
        "execution_realism": "BASSA-MEDIA (sweep37, non Research Mode puro).",
        "sample_size": "SCONOSCIUTO - PF aggregato senza conteggio trade in questo artifact.",
        "dipendenza_pochi_regimi": "SCONOSCIUTA.",
        "compatibilita_conto_piccolo": "NON VALUTATA.",
        "canonical_event_dataset_possibile": "SI, MA SOLO DOPO un audit di integrita' dedicato (stesso "
            "schema BREAKOUT_ACC/ORDER_BLOCK/TSI) - il candidato con il segnale piu' incoraggiante del "
            "corpus MERITA questo audit come priorita' immediata dopo questa fase.",
        "visual_audit_readiness": "Fidelity D oggi, B raggiungibile dopo un run diagnostico dedicato.",
        "fragility_note": "PF 1.04 e' debolissimo in valore assoluto (a malapena sopra breakeven) e su "
            "dati non ottimali - trattato qui SOLO come motivo per priorizzare l'audit di integrita', "
            "MAI come prova di edge.",
    }


def _fvg_cont():
    return {
        "category": "PROMISING_BUT_NEEDS_INTEGRITY_WORK",
        "integrita_implementativa": "NON VERIFICATA - MAI controllata in Phase 7.10. Letta in questa fase: "
            "STATELESS, nessuna guardia TF, nessun bar-gate. Nota aggiuntiva: STRAT_FVG_CONT e' "
            "RIUSATO come identita' da IFVG/FVG_MIT/FVG_MIT_WINDOW (NXS_Strategies_SMC.mqh) - un "
            "eventuale audit di integrita' futuro deve mappare esplicitamente questa condivisione "
            "(stesso pattern gia' visto per OB_MIT/ORDER_BLOCK in Phase 7.14/7.15).",
        "identity_parity": "NON VERIFICATA in questa fase.",
        "affidabilita_dataset": "sweep37 (30% tick reali) per il PF principale; un secondo confronto "
            "'motore sito' (A/B Python/Yahoo, non MT5) esplicitamente dichiarato NON VALIDATO su MT5 "
            "reale nel commento del codice sorgente stesso.",
        "evidence_quality": "sweep37 (PF singolo) + un A/B interno non validato (commento del codice: "
            "'Test A/B sul sito... PF 1.45->2.07... Non ancora validato su MT5 reale').",
        "bug_noti": "Nessun difetto CONFERMATO (mai auditata per il difetto cross-TF).",
        "meccanismo_comprensibile": "SI - gap a 3 candele + trend esterno H1 concorde (struttura letta da "
            "un motore esterno dedicato, non un proxy locale), con un gate di conferma reazione "
            "opzionale.",
        "segnali_preliminari_edge": "DEBOLE E MISTO - PF 0.96 in sweep37 (quasi breakeven), MA un test A/B "
            "interno (non MT5, non validato) suggerisce un miglioramento sostanziale (1.45->2.07) dopo "
            "un cambio di filtro di trend - segnale interessante ma esplicitamente non confermato sul "
            "motore canonico.",
        "robustezza_storica": "NON VALUTABILE.",
        "cost_sensitivity": "NON DISPONIBILE.",
        "oos_gia_disponibile": "NO.",
        "execution_realism": "BASSA-MEDIA (sweep37).",
        "sample_size": "SCONOSCIUTO.",
        "dipendenza_pochi_regimi": "SCONOSCIUTA.",
        "compatibilita_conto_piccolo": "NON VALUTATA.",
        "canonical_event_dataset_possibile": "SI, MA SOLO DOPO un audit di integrita' dedicato E dopo aver "
            "chiarito la condivisione con IFVG/FVG_MIT/FVG_MIT_WINDOW.",
        "visual_audit_readiness": "Fidelity D oggi.",
        "fragility_note": "Il segnale piu' incoraggiante (1.45->2.07) viene da un motore NON canonico "
            "(sito/Python) e il codice stesso lo dichiara non validato - da NON riusare come evidenza "
            "diretta, solo come indizio per priorizzare un audit dedicato.",
    }


def _bollinger():
    return {
        "category": "DO_NOT_USE_YET",
        "integrita_implementativa": "SUSPECT (Phase 7.10) - stateless, bare lastEvalBar, nessun valore "
            "ricorsivo accumulato, ma nessuna guardia TF - stesso profilo di rischio di ADX_RSI/MACD.",
        "identity_parity": "NON VERIFICATA in questa fase.",
        "affidabilita_dataset": "sweep37.",
        "evidence_quality": "Solo sweep37 (PF singolo).",
        "bug_noti": "Corretto un disallineamento temporale (shift1 vs shift2) il 17/07, PRIMA di questa "
            "sessione - non il difetto cross-TF, che resta SUSPECT non chiuso.",
        "meccanismo_comprensibile": "SI - mean reversion su bande di Bollinger con gate di conferma su "
            "chiusura barra.",
        "segnali_preliminari_edge": "NEGATIVO - PF 0.79 in sweep37.",
        "robustezza_storica": "NON VALUTABILE.", "cost_sensitivity": "NON DISPONIBILE.",
        "oos_gia_disponibile": "NO.", "execution_realism": "BASSA-MEDIA (sweep37).",
        "sample_size": "SCONOSCIUTO.", "dipendenza_pochi_regimi": "SCONOSCIUTA.",
        "compatibilita_conto_piccolo": "NON VALUTATA.",
        "canonical_event_dataset_possibile": "SOLO DOPO un audit di integrita' dedicato.",
        "visual_audit_readiness": "Fidelity D oggi.",
        "fragility_note": "PF sotto 1.0 e classificazione SUSPECT non chiusa - due ragioni indipendenti "
            "per l'esclusione, nessuna delle due decisiva da sola.",
    }


def _macd():
    return {
        "category": "DO_NOT_USE_YET",
        "integrita_implementativa": "NON VERIFICATA (non fra i 20 candidati Phase 7.10 con questo nome "
            "esatto - solo MACD_SMA200, una variante diversa, e' stata classificata SUSPECT). Da "
            "verificare separatamente prima di qualunque promozione.",
        "identity_parity": "NON VERIFICATA in questa fase.",
        "affidabilita_dataset": "sweep37.", "evidence_quality": "Solo sweep37 (PF singolo).",
        "bug_noti": "Nessun difetto CONFERMATO per questa esatta variante.",
        "meccanismo_comprensibile": "SI - cross MACD/signal, meccanismo standard e trasparente.",
        "segnali_preliminari_edge": "NEGATIVO - PF 0.79 in sweep37.",
        "robustezza_storica": "NON VALUTABILE.", "cost_sensitivity": "NON DISPONIBILE.",
        "oos_gia_disponibile": "NO.", "execution_realism": "BASSA-MEDIA (sweep37).",
        "sample_size": "SCONOSCIUTO.", "dipendenza_pochi_regimi": "SCONOSCIUTA.",
        "compatibilita_conto_piccolo": "NON VALUTATA.",
        "canonical_event_dataset_possibile": "SOLO DOPO un audit di integrita' dedicato.",
        "visual_audit_readiness": "Fidelity D oggi.",
        "fragility_note": "PF sotto 1.0 su un solo run a qualita' dati media - non decisivo da solo, ma "
            "combinato con l'integrita' non verificata non giustifica una promozione ora.",
    }


TIER_A_BUILDERS = {
    "BREAKOUT_ACC": _breakout_acc, "ORDER_BLOCK": _order_block, "TSI": _tsi,
    "ADX_RSI": _adx_rsi, "SAR": _sar, "LIQ_SWEEP": _liq_sweep, "FVG_CONT": _fvg_cont,
    "BOLLINGER": _bollinger, "MACD": _macd,
}

# --- Tier B: difetto CONFERMATO (non ancora fissato) su strategie ATTIVE o
# comunque non-RESEARCH_ONLY - classificazione compatta basata su regola. ---
DEFECT_CONFIRMED_UNFIXED = ["BAR_UPDN", "BB_SQUEEZE", "PIVOT_WICK", "PMAX", "RANGE_FADE",
                           "SH_BMS_RTO", "SH_BMS_RTO_V2", "SILVER_BULLET"]
SUSPECT_UNAUDITED_CLOSED = ["3COMMAS_BOT", "ICHIMOKU_HULL_MACD", "MACD_SMA200", "RSI_DIV_PINE"]
SAFE_NO_REAL_EVIDENCE = ["LEVEL_CONFLUENCE", "LEVEL_CONFLUENCE_M5", "LEVEL_REACTION",
                         "LEVEL_REACTION_M5", "WEEKLY_EXP", "WICK_SWEEP_RECLAIM", "WICK_SWEEP_REV"]
WRAPPER_OF_AUDITED = {"OB_MIT": "ORDER_BLOCK", "IFVG": "FVG_CONT", "FVG_MIT": "FVG_CONT",
                      "FVG_MIT_WINDOW": "FVG_CONT"}


def _compact_row(sid, category, rule, reason):
    return {"canonical_strategy_id": sid, "category": category, "rule_applied": rule, "reason": reason}


def build():
    universe = load_json(os.path.join(PHASE720_DIR, "strategy_universe_v1.json"))["payload"]["universe"]
    by_id = {u["canonical_strategy_id"]: u for u in universe}

    tier_a = {sid: {**fn(), "canonical_strategy_id": sid} for sid, fn in TIER_A_BUILDERS.items()}

    tier_b = []
    for sid in DEFECT_CONFIRMED_UNFIXED:
        tier_b.append(_compact_row(sid, "DO_NOT_USE_YET", "DEFECT_CONFIRMED_UNFIXED",
                                   "Difetto CROSS_TIMEFRAME_STATE_CONTAMINATION confermato in Phase "
                                   "7.10 (stesso meccanismo di BREAKOUT_ACC/ORDER_BLOCK/TSI pre-fix), "
                                   "MAI corretto. Stato: " + str(by_id[sid]["current_status"]) +
                                   ". Bloccato esplicitamente sull'applicazione dello stesso fix minimale "
                                   "gia' validato 3 volte in questa sessione - nessuna nuova modifica "
                                   "MQL5 autorizzata in questa fase di sola classificazione."))
    for sid in SUSPECT_UNAUDITED_CLOSED:
        tier_b.append(_compact_row(sid, "DO_NOT_USE_YET", "SUSPECT_INTEGRITY_UNRESOLVED",
                                   "Classificato SUSPECT in Phase 7.10 (stateless, bare-recompute, "
                                   "nessuna guardia TF) - stesso profilo di rischio di ADX_RSI/BOLLINGER/"
                                   "MACD in questa fase, mai chiuso con un audit dedicato."))
    for sid in SAFE_NO_REAL_EVIDENCE:
        tier_b.append(_compact_row(sid, "INSUFFICIENT_EVIDENCE", "SAFE_INTEGRITY_BUT_NO_REAL_EVIDENCE",
                                   "Integrita' CONFERMATA pulita rispetto al difetto cross-TF (Phase "
                                   "7.10, classificazione SAFE) - ma nessuna evidenza quantitativa reale "
                                   "trovata in questa fase (historical_tests assente nel census, al "
                                   "massimo conteggi grezzi di trigger senza esito economico)."))
    for sid, canonical in WRAPPER_OF_AUDITED.items():
        tier_b.append(_compact_row(sid, "DO_NOT_USE_YET", "WRAPPER_OF_TIER_A_OR_TIER_B_CANDIDATE",
                                   f"Riusa l'identita'/stato di {canonical} (wrapper diretto o "
                                   "condivisione di STRAT_* enum) - eredita automaticamente lo stato di "
                                   "integrita' di quella strategia, ma il comportamento dinamico con "
                                   "entrambe abilitate simultaneamente non e' mai stato osservato dal "
                                   "vivo (stesso gap documentato per OB_MIT in Phase 7.15)."))

    tier_b_ids = {r["canonical_strategy_id"] for r in tier_b}
    tier_a_ids = set(tier_a.keys())

    # --- Tier C: tutto il resto (RESEARCH_ONLY mai live, o ACTIVE/DISABLED/
    # EXPERIMENTAL non auditate e senza alcuna evidenza quantitativa trovata
    # in questa fase) - classificazione bulk con una regola esplicita unica. ---
    tier_c_ids = [u["canonical_strategy_id"] for u in universe
                 if u["canonical_strategy_id"] not in tier_a_ids and u["canonical_strategy_id"] not in tier_b_ids]
    tier_c = {
        "rule": "INSUFFICIENT_EVIDENCE per costruzione: nessuna evidenza quantitativa (PF/WR/sample) "
               "trovata in nessuna fonte consultata in questa fase (census/priority queue/sweep37/"
               "backtest_database), E integrita' rispetto al difetto CROSS_TIMEFRAME_STATE_CONTAMINATION "
               "mai auditata. La maggioranza (RESEARCH_ONLY) non e' mai stata live su MQL5 - varianti "
               "esplorative Python-only, non hanno prodotto alcun trade reale.",
        "category": "INSUFFICIENT_EVIDENCE",
        "n_strategies": len(tier_c_ids),
        "strategy_ids": sorted(tier_c_ids),
        "breakdown_by_status": {
            status: sorted(u["canonical_strategy_id"] for u in universe
                          if u["canonical_strategy_id"] in tier_c_ids and u["current_status"] == status)
            for status in ("ACTIVE", "DISABLED", "RESEARCH_ONLY", "EXPERIMENTAL")
        },
    }

    category_counts = {c: 0 for c in CATEGORIES}
    for v in tier_a.values():
        category_counts[v["category"]] += 1
    for r in tier_b:
        category_counts[r["category"]] += 1
    category_counts[tier_c["category"]] += tier_c["n_strategies"]

    payload = {
        "criteria": [{"id": cid, "question": q} for cid, q in CRITERIA],
        "classification_categories": CATEGORIES,
        "pf_alone_never_used_to_classify": True,
        "tier_a_deep_dive": tier_a,
        "tier_b_compact_rule_based": tier_b,
        "tier_c_bulk": tier_c,
        "category_counts": category_counts,
        "n_strategies_total_covered": len(tier_a) + len(tier_b) + tier_c["n_strategies"],
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE720_DIR, "evaluation_matrix_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  copertura totale: {payload['n_strategies_total_covered']}")
    print(f"  categorie: {payload['category_counts']}")


if __name__ == "__main__":
    main()
