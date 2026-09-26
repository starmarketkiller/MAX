#!/usr/bin/env python3
"""Phase 7.12 - Coda delle priorita' (punto 3). Include i 10
DEFECT_CONFIRMED residui, i 5 SUSPECT gia' noti, e le nuove candidate
di questa fase (OB_MIT, FVG_MIT_WINDOW). MAI PF o rendimento storico
contaminato come criterio. TSI/BAR_UPDN NON messe automaticamente in
testa - l'ordine e' giustificato da 7 criteri espliciti per candidato.
I gap di registry (CRT/FVG_MIT_WINDOW) sono trattati come categoria
separata (rendere eseguibile codice bloccato, non un fix di stato).
"""
import os
import sys

PHASE712_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE712_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import save_json, wrap_with_provenance  # noqa: E402

# Criteri (mai PF/rendimento storico):
# 1. gravita_propagazione        - severita' del meccanismo e ampiezza della propagazione
# 2. raggiungibilita             - la strategia e' abilitata di default / configurazione reale
# 3. evidenza_storica_in_gioco   - QUANTITA' di evidenza storica potenzialmente coinvolta
#                                  (mai la sua QUALITA'/esito)
# 4. rilevanza_config_operativa  - quanto e' rilevante per una prima config circoscritta
# 5. isolabilita_misurabilita    - quanto e' facile isolare/misurare l'effetto con un test
# 6. costo_test_diagnostico      - costo/complessita' del test (inverso: basso = meglio)
# 7. conoscenza_riutilizzabile   - quanto il test informa ALTRE strategie/pattern

QUEUE = [
    {
        "candidate": "ORDER_BLOCK", "pattern": "CROSS_TIMEFRAME_STATE_CONTAMINATION",
        "classification": "DEFECT_CONFIRMED", "confidence": "STRUTTURALE (non empirica)",
        "default_enabled": True, "profile_tf": "D1",
        "scores": {
            "gravita_propagazione": "ALTA - macchina a stati con zone di prezzo "
                "persistenti (obLo/obHi); rischio BOTH (falsi positivi E negativi); "
                "PROPAGA a OB_MIT (chiamata diretta, stessa mutazione di stato).",
            "raggiungibilita": "ALTA - InpStrat_ORDER_BLOCK=true di default, selettore 15.",
            "evidenza_storica_in_gioco": "NON QUANTIFICATA nel census (nessun "
                "historical_tests registrato) - non significa assente, mancante nei "
                "dati disponibili.",
            "rilevanza_config_operativa": "ALTA - strategia SMC di riferimento, "
                "abilitata di default in ogni configurazione standard.",
            "isolabilita_misurabilita": "ALTA - stato binario/discreto (zona attiva o "
                "no, invalidata o no) e gia' esiste un Decision/Gate/Execution Trace "
                "riutilizzabile da BREAKOUT_ACC per contare segnali/zone per pass.",
            "costo_test_diagnostico": "BASSO-MEDIO - metodologia diagnostica "
                "DIRETTAMENTE riutilizzabile da Phase 7.9E-G (stesso schema: EA "
                "diagnostico standalone o guardia TF di prova + confronto conteggi).",
            "conoscenza_riutilizzabile": "MASSIMA - valida la sotto-classe "
                "STATE_MACHINE_CONTAMINATION (mai testata empiricamente, distinta dal "
                "COOLDOWN gia' validato su BREAKOUT_ACC) E chiarisce simultaneamente "
                "OB_MIT E informa la famiglia SH_BMS_RTO/SH_BMS_RTO_V2/SILVER_BULLET/"
                "RANGE_FADE (stessa categoria macchina-a-stati).",
        },
        "rank_rationale": "Combinazione di raggiungibilita' alta, propagazione "
            "documentata a una seconda identita' (OB_MIT), costo diagnostico basso "
            "(riuso diretto della metodologia 7.9E-G) e massimo valore di conoscenza "
            "riutilizzabile per l'intera famiglia SMC a macchina a stati - nessun "
            "altro singolo test coprirebbe altrettanto.",
    },
    {
        "candidate": "OB_MIT", "pattern": "CROSS_TIMEFRAME_STATE_CONTAMINATION (ereditato)",
        "classification": "DEFECT_CONFIRMED", "confidence": "DIRETTA (chiamata di funzione, "
            "non analogia)",
        "default_enabled": False, "profile_tf": "D1",
        "scores": {
            "gravita_propagazione": "IDENTICA a ORDER_BLOCK (stessa funzione eseguita).",
            "raggiungibilita": "BASSA di per se' (InpStrat_OB_Mit=false) - ma "
                "irrilevante: la diagnosi di ORDER_BLOCK copre automaticamente OB_MIT.",
            "evidenza_storica_in_gioco": "NON QUANTIFICATA.",
            "rilevanza_config_operativa": "BASSA in isolamento (disabilitata di "
                "default).",
            "isolabilita_misurabilita": "Stessa di ORDER_BLOCK.",
            "costo_test_diagnostico": "ZERO AGGIUNTIVO - risolta dallo stesso test di "
                "ORDER_BLOCK, nessun protocollo separato necessario.",
            "conoscenza_riutilizzabile": "Nessuna aggiuntiva oltre ORDER_BLOCK.",
        },
        "rank_rationale": "Non richiede un protocollo diagnostico proprio - da trattare "
            "come conseguenza diretta della diagnosi di ORDER_BLOCK, non come task "
            "separata in coda.",
        "not_a_separate_task": True,
    },
    {
        "candidate": "TSI", "pattern": "CROSS_TIMEFRAME_STATE_CONTAMINATION",
        "classification": "DEFECT_CONFIRMED", "confidence": "STRUTTURALE (non empirica)",
        "default_enabled": True, "profile_tf": "D1",
        "scores": {
            "gravita_propagazione": "MASSIMA (per valutazione qualitativa di Phase "
                "7.10) - valore ricorsivo a doppio smoothing EMA, un singolo pass "
                "sbagliato corrompe l'intera catena futura, non solo la barra "
                "successiva.",
            "raggiungibilita": "ALTA - InpStrat_TSI=true di default, selettore 5.",
            "evidenza_storica_in_gioco": "L'UNICA fra tutti i 10+ residui con "
                "historical_tests registrato nel census (sweep37, 839 trade eseguiti) "
                "- quantita' di evidenza potenzialmente coinvolta CONFERMATA presente "
                "(la sua qualita'/esito NON e' usata come criterio).",
            "rilevanza_config_operativa": "ALTA - abilitata di default.",
            "isolabilita_misurabilita": "MEDIA-BASSA - lo stato e' un VALORE CONTINUO "
                "ricorsivo (sm1/sm2/sm1Abs/sm2Abs/signal), non uno stato binario - "
                "isolare l'effetto richiede esportare l'intera traiettoria numerica e "
                "confrontarla con una ricostruzione isolata, non un semplice conteggio "
                "di eventi.",
            "costo_test_diagnostico": "MEDIO-ALTO - richiede strumentazione nuova "
                "(esportazione di piu' variabili di stato per barra), non direttamente "
                "riutilizzabile 1:1 dalla metodologia BREAKOUT_ACC (che confrontava "
                "conteggi di segnali, non traiettorie numeriche).",
            "conoscenza_riutilizzabile": "ALTA - valida la sotto-classe "
                "RECURSIVE_VALUE_CONTAMINATION (distinta da COOLDOWN e da "
                "STATE_MACHINE) e informa PMAX (stessa categoria).",
        },
        "rank_rationale": "Priorita' #2, non #1: la severita' teorica e l'evidenza "
            "storica documentata sono le piu' alte del gruppo, ma il costo/complessita' "
            "del test diagnostico (traiettoria continua vs stato discreto) e' "
            "significativamente maggiore, e non chiarisce simultaneamente una seconda "
            "identita' come fa ORDER_BLOCK. Va comunque eseguita a breve per l'entita' "
            "dell'evidenza storica in gioco.",
    },
    {
        "candidate": "SH_BMS_RTO / SH_BMS_RTO_V2 / SILVER_BULLET", "pattern":
            "CROSS_TIMEFRAME_STATE_CONTAMINATION", "classification": "DEFECT_CONFIRMED",
        "confidence": "STRUTTURALE (non empirica)", "default_enabled": True,
        "profile_tf": "D1 / H1 / M15 (sessione-vincolata)",
        "scores": {
            "gravita_propagazione": "ALTA - macchine a stati multi-fase (stesso "
                "meccanismo generale di ORDER_BLOCK).",
            "raggiungibilita": "ALTA - tutte e 3 abilitate di default.",
            "evidenza_storica_in_gioco": "NON QUANTIFICATA.",
            "rilevanza_config_operativa": "ALTA.",
            "isolabilita_misurabilita": "ALTA - stessa natura di ORDER_BLOCK (stati "
                "discreti).",
            "costo_test_diagnostico": "BASSO-MEDIO - stessa metodologia di ORDER_BLOCK, "
                "diagnosticabili in sequenza dopo di esso.",
            "conoscenza_riutilizzabile": "ALTA MA RIDONDANTE con ORDER_BLOCK se testato "
                "per primo - il valore marginale di un test dedicato scende dopo che "
                "ORDER_BLOCK ha gia' validato la sotto-classe STATE_MACHINE.",
        },
        "rank_rationale": "Priorita' #3 (gruppo) - stessa famiglia di ORDER_BLOCK, "
            "da testare DOPO per verificare che il meccanismo generalizzi (non "
            "assumerlo), ma con priorita' minore perche' il primo test (ORDER_BLOCK) "
            "gia' fornisce la validazione di categoria piu' preziosa.",
    },
    {
        "candidate": "BB_SQUEEZE", "pattern": "CROSS_TIMEFRAME_STATE_CONTAMINATION",
        "classification": "DEFECT_CONFIRMED", "confidence": "STRUTTURALE",
        "default_enabled": True, "profile_tf": "D1",
        "scores": {
            "gravita_propagazione": "MEDIA - contatore accumulato (squeezeBars), meno "
                "severo di un valore ricorsivo o di una macchina a stati con zone di "
                "prezzo.",
            "raggiungibilita": "ALTA - abilitata di default.",
            "evidenza_storica_in_gioco": "NON QUANTIFICATA.",
            "isolabilita_misurabilita": "MEDIA - un contatore e' piu' semplice di uno "
                "stato continuo ma piu' complesso di un flag binario.",
            "costo_test_diagnostico": "BASSO-MEDIO.",
            "conoscenza_riutilizzabile": "MEDIA - sotto-classe intermedia, non ancora "
                "rappresentata da un test dedicato.",
        },
        "rank_rationale": "Priorita' #4 - severita' intermedia, nessuna propagazione "
            "a una seconda identita', nessuna evidenza storica documentata.",
    },
    {
        "candidate": "PMAX", "pattern": "CROSS_TIMEFRAME_STATE_CONTAMINATION",
        "classification": "DEFECT_CONFIRMED", "confidence": "STRUTTURALE",
        "default_enabled": False, "profile_tf": "H1",
        "scores": {
            "gravita_propagazione": "ALTA - valore ricorsivo (stop-and-reverse "
                "ATR-adattivo), stessa famiglia di TSI.",
            "raggiungibilita": "BASSA - InpStrat_PMax=false di default.",
            "evidenza_storica_in_gioco": "NON QUANTIFICATA.",
            "rilevanza_config_operativa": "BASSA (disabilitata di default).",
            "isolabilita_misurabilita": "MEDIA-BASSA - stessa complessita' di TSI "
                "(valore ricorsivo).",
            "costo_test_diagnostico": "MEDIO-ALTO.",
            "conoscenza_riutilizzabile": "MEDIA - se TSI viene testato per primo nella "
                "categoria RECURSIVE_VALUE, il valore marginale di un secondo test "
                "nella stessa sotto-classe scende.",
        },
        "rank_rationale": "Priorita' #5 - stessa categoria di TSI ma disabilitata di "
            "default (raggiungibilita' bassa) - da testare dopo TSI per conferma di "
            "generalizzazione, non con urgenza propria.",
    },
    {
        "candidate": "BAR_UPDN", "pattern": "CROSS_TIMEFRAME_STATE_CONTAMINATION",
        "classification": "DEFECT_CONFIRMED", "confidence": "STRUTTURALE (identico a "
            "BREAKOUT_ACC pre-fix, stesso commit)",
        "default_enabled": False, "profile_tf": "M15",
        "scores": {
            "gravita_propagazione": "BASSA-MEDIA - cooldown timedelta, stessa "
                "categoria GIA' VALIDATA empiricamente su BREAKOUT_ACC (rischio quasi "
                "solo falsi negativi).",
            "raggiungibilita": "BASSA - InpStrat_BarUpDn=false di default.",
            "evidenza_storica_in_gioco": "NON QUANTIFICATA.",
            "rilevanza_config_operativa": "BASSA (disabilitata di default).",
            "isolabilita_misurabilita": "ALTA (identica a BREAKOUT_ACC, gia' provata).",
            "costo_test_diagnostico": "BASSISSIMO - il meccanismo E il metodo "
                "diagnostico sono GIA' identici a un caso gia' risolto.",
            "conoscenza_riutilizzabile": "BASSA - la sotto-classe COOLDOWN e' GIA' "
                "validata su BREAKOUT_ACC; un secondo test qui confermerebbe solo "
                "generalizzazione di un meccanismo gia' provato, non aggiunge "
                "conoscenza nuova su ALTRE sotto-classi.",
        },
        "rank_rationale": (
            "ESPLICITAMENTE NON messa al primo posto nonostante il costo diagnostico "
            "piu' basso del gruppo: e' disabilitata di default (bassa "
            "raggiungibilita'/rilevanza operativa) e la sua sotto-classe (cooldown) e' "
            "GIA' validata empiricamente da BREAKOUT_ACC - testarla per prima "
            "produrrebbe conferma a basso costo ma informazione marginale bassa, "
            "rispetto a candidate che validano sotto-classi mai testate o che "
            "chiariscono una seconda identita'."
        ),
    },
    {
        "candidate": "PIVOT_WICK", "pattern": "CROSS_TIMEFRAME_STATE_CONTAMINATION",
        "classification": "DEFECT_CONFIRMED", "confidence": "STRUTTURALE",
        "default_enabled": False, "profile_tf": "M15",
        "scores": {"gravita_propagazione": "BASSA-MEDIA - cooldown timedelta al "
                "livello top; il pool pivot sottostante e' verificato SAFE.",
            "raggiungibilita": "BASSA - default disabilitata.",
            "conoscenza_riutilizzabile": "BASSA - stessa sotto-classe cooldown gia' "
                "validata."},
        "rank_rationale": "Priorita' bassa - stesse ragioni di BAR_UPDN.",
    },
    {
        "candidate": "RANGE_FADE", "pattern": "CROSS_TIMEFRAME_STATE_CONTAMINATION",
        "classification": "DEFECT_CONFIRMED", "confidence": "STRUTTURALE",
        "default_enabled": False, "profile_tf": "D1",
        "scores": {"gravita_propagazione": "MEDIA - valore persistente (range di "
                "riferimento), non un cooldown puro ma non un valore ricorsivo "
                "complesso.",
            "raggiungibilita": "BASSA - InpUseStrat_RangeFade=false di default.",
            "conoscenza_riutilizzabile": "BASSA-MEDIA."},
        "rank_rationale": "Priorita' bassa - disabilitata di default, severita' "
            "intermedia gia' rappresentata da BB_SQUEEZE.",
    },
    {
        "candidate": "FVG_MIT_WINDOW", "pattern": "CROSS_TIMEFRAME_STATE_CONTAMINATION "
            "(nuovo, Phase 7.12)", "classification": "SUSPECT",
        "confidence": "MODERATA (vedi coverage_gaps_and_new_candidates_v1.json)",
        "default_enabled": True, "profile_tf": "D1 (implicito)",
        "scores": {
            "gravita_propagazione": "MEDIA - pool di zone FVG, ne' un cooldown puro "
                "ne' un valore ricorsivo.",
            "raggiungibilita": "BLOCCATA - default enabled MA strutturalmente "
                "impedita dall'UNKNOWN_STRATEGY_REGISTRY_GAP (Phase 7.11): non puo' "
                "aprire trade oggi indipendentemente da questo difetto.",
            "conoscenza_riutilizzabile": "MEDIA - richiederebbe prima un'adjudication "
                "documentale (tipo 7.9F) per passare a DEFECT_CONFIRMED.",
        },
        "rank_rationale": "Priorita' CONDIZIONALE - irrilevante finche' il registry "
            "gap non viene corretto (nessun trade possibile oggi). Se/quando il "
            "registry gap venisse corretto, questo diventerebbe rilevante PRIMA di "
            "abilitare la strategia in pratica - trattato come nota di attenzione "
            "collegata al gap di registry, non come task diagnostica indipendente in "
            "questa coda.",
        "special_category": "REGISTRY_GAP_DEPENDENT",
    },
    {
        "candidate": "MACD_SMA200 / ICHIMOKU_HULL_MACD / 3COMMAS_BOT / RSI_DIV_PINE",
        "pattern": "CROSS_TIMEFRAME_STATE_CONTAMINATION", "classification": "SUSPECT",
        "confidence": "BASSA (rischio pratico, per valutazione Phase 7.10)",
        "default_enabled": False,
        "scores": {
            "gravita_propagazione": "BASSA - solo bare lastBarTime, nessun valore "
                "ricorsivo/contatore/macchina a stati; richiede una coincidenza esatta "
                "di bar-time cross-TF per manifestarsi, evento raro.",
            "raggiungibilita": "BASSA - tutte e 4 disabilitate di default.",
            "conoscenza_riutilizzabile": "BASSA - sotto-classe gia' concettualmente "
                "chiara (bare lastBarTime, rischio quasi nullo).",
        },
        "rank_rationale": "Priorita' minima - basso rischio pratico dichiarato, "
            "disabilitate di default, nessuna urgenza.",
    },
    {
        "candidate": "BOLLINGER", "pattern": "CROSS_TIMEFRAME_STATE_CONTAMINATION",
        "classification": "SUSPECT", "confidence": "BASSA", "default_enabled": True,
        "scores": {
            "gravita_propagazione": "BASSA - bare lastEvalBar, stesso ragionamento "
                "della famiglia 'bare lastBarTime'.",
            "raggiungibilita": "ALTA - InpStrat_BOLLINGER=true di default.",
            "rilevanza_config_operativa": "MEDIA - abilitata di default ma rischio "
                "pratico dichiarato basso.",
            "conoscenza_riutilizzabile": "BASSA.",
        },
        "rank_rationale": "Priorita' bassa-media - unica SUSPECT abilitata di default, "
            "ma il rischio pratico e' dichiarato basso dalla stessa Phase 7.10 "
            "(coincidenza di bar-time richiesta, evento raro) - non giustifica "
            "precedenza sui DEFECT_CONFIRMED ad alta raggiungibilita'.",
    },
]

REGISTRY_GAPS = {
    "description": "Trattati SEPARATAMENTE dalla coda dei difetti di stato - "
        "correggere il riconoscimento in NXS_StrategyKnown() e' un intervento "
        "DIVERSO (rende ESEGUIBILE codice oggi strutturalmente bloccato, non corregge "
        "uno stato contaminato).",
    "candidates": [
        {"strategy": "CRT", "default_enabled": False, "state_issue": "NESSUNO "
            "(verificato stateless in questa fase - vedi coverage_gaps)",
         "action_if_corrected": "Renderebbe eseguibile una strategia SENZA problemi di "
            "stato noti - il rischio principale sarebbe economico/di segnale "
            "(sconosciuto, mai testato), non di contaminazione cross-TF."},
        {"strategy": "FVG_MIT_WINDOW", "default_enabled": True, "state_issue": "SUSPECT "
            "(nuovo, questa fase - vedi sopra)",
         "action_if_corrected": "Renderebbe eseguibile una strategia CON un problema di "
            "stato SUSPECT non ancora confermato - correggere il registry gap PRIMA di "
            "chiarire lo stato di questo secondo difetto rischierebbe di attivare "
            "silenziosamente un meccanismo di contaminazione non testato."},
    ],
    "recommendation": "Se una futura fase decidesse di correggere il registry gap, "
        "FVG_MIT_WINDOW dovrebbe essere accompagnata da un'adjudication del suo stato "
        "SUSPECT (o quantomeno da un flag esplicito di rischio non testato) - CRT non "
        "ha questo vincolo.",
}


def build():
    ordered = [q["candidate"] for q in QUEUE if not q.get("not_a_separate_task")
              and not q.get("special_category")]
    return {
        "phase": "7.12",
        "no_pf_or_contaminated_historical_return_used": True,
        "not_defaulted_to_tsi_or_bar_updn": True,
        "criteria_used": [
            "gravita_propagazione", "raggiungibilita", "evidenza_storica_in_gioco "
            "(quantita', mai qualita'/esito)", "rilevanza_config_operativa",
            "isolabilita_misurabilita", "costo_test_diagnostico",
            "conoscenza_riutilizzabile",
        ],
        "queue": QUEUE,
        "ordered_candidate_ids": ordered,
        "top_priority": "ORDER_BLOCK",
        "second_priority": "TSI",
        "registry_gaps_separate_category": REGISTRY_GAPS,
        "ob_mit_note": "OB_MIT (DEFECT_CONFIRMED, evidenza diretta) NON ha una riga "
            "propria in coda - la sua diagnosi e' automaticamente coperta dal test su "
            "ORDER_BLOCK (stessa funzione eseguita).",
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE712_DIR, "strategy_priority_queue_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print("top_priority:", payload["top_priority"])
    print("ordered:", payload["ordered_candidate_ids"])
    return doc


if __name__ == "__main__":
    main()
