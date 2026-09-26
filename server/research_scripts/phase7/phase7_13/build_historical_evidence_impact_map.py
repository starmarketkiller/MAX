#!/usr/bin/env python3
"""Phase 7.13 punto 5 - mappa (senza cancellare nulla) di quali vecchi
artifact/riferimenti a ORDER_BLOCK/OB_MIT potrebbero essere stati
prodotti dall'implementazione contaminata (CROSS_TIMEFRAME_STATE_
CONTAMINATION, Phase 7.12). Classificazione: UNAFFECTED /
POSSIBLY_CONTAMINATED / CONTAMINATED / CANNOT_DETERMINE.

Principio esplicito applicato ovunque in questo file: un PF/WR NON
viene mai reinterpretato come evidenza della "strategia canonica" se
l'identita' realmente eseguita (single-TF pulito vs multi-TF
contaminato) non e' stabilita per quell'artifact specifico.
"""
import os
import sys

PHASE713_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE713_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

ITEMS = [
    {
        "artifact": "server/backtest.py::sig_order_block / sig_order_block_ext / _ob_series (righe ~1319-1357, ~3605-3660)",
        "kind": "PYTHON_BACKTEST_ENGINE_IMPLEMENTATION",
        "classification": "UNAFFECTED_BUT_NOT_REPRESENTATIVE_OF_LIVE",
        "reasoning": "_ob_series() mantiene uno stato locale (dict st) scoped a UN SOLO ciclo su "
                    "UNA SOLA serie di candele (il TF su cui gira il motore di backtest per questa "
                    "strategia) - strutturalmente equivalente alla ricostruzione diagnostica "
                    "TF-scoped (Stream B) di questa fase, non al multi-TF loop del router live "
                    "(NEXUS_EA_v2.mq5:670-733). Il commento del 04/08 dichiara fedelta' riga-per-riga "
                    "con NXS_OB_UpdateSide MA non riproduce ne' menziona il multi-pass del router - "
                    "conferma indipendente (scritta in una sessione diversa, per un motivo diverso) "
                    "che l'implementazione 'corretta' concettualmente e' quella single-TF.",
        "implication": "Qualunque PF/WR storico calcolato con questo motore Python per ORDER_BLOCK/"
                       "OB_MIT NON E' rappresentativo di cio' che l'EA MQL5 dal vivo esegue oggi "
                       "(dimostrato materialmente diverso in ab_simulation_v1.json) - non e' "
                       "'validato' ne' 'invalidato' dal difetto, e' semplicemente la misura di "
                       "un'IDENTITA' DIVERSA da quella live.",
    },
    {
        "artifact": "results/phase2_baseline_20260705_v2.0.27.csv, riga InpStrat_ORDER_BLOCK "
                   "(8 trade, PF 0.00, 'history_quality: 100% ticks reali')",
        "kind": "MT5_STRATEGY_TESTER_REAL_TICK_RESULT",
        "classification": "POSSIBLY_CONTAMINATED",
        "reasoning": "Esecuzione su tick reali del vero EA MQL5 (non un proxy Python) - se durante "
                    "questo run InpProfileMultiTF=true (default di sistema, vedi NXS_Inputs.mqh:291), "
                    "il difetto era strutturalmente presente ed eseguito. La configurazione ESATTA "
                    "di questo specifico run (multi-TF on/off, altri override) NON e' verificabile "
                    "dal solo CSV - non possiamo affermare con certezza che questo run specifico "
                    "abbia attivato il multi-TF loop, quindi POSSIBLY_ (non CONTAMINATED tout court).",
        "implication": "Il PF 0.00 su 8 trade (campione minuscolo) NON viene reinterpretato ne' come "
                       "prova che ORDER_BLOCK 'canonico' sia debole ne' come prova che il difetto lo "
                       "peggiori - il campione e' troppo piccolo per qualunque conclusione, e "
                       "l'identita' eseguita non e' accertata al 100%.",
    },
    {
        "artifact": "results/phase_partB_silent_diagnostic_20260706.csv, riga ORDER_BLOCK "
                   "(pattern_fired_count=1955, dominant_block_stage=PREFLIGHT(10), "
                   "note='blocked_by_gate:PREFLIGHT(ambiguous)')",
        "kind": "MT5_DIAGNOSTIC_RAW_SIGNAL_COUNT",
        "classification": "POSSIBLY_CONTAMINATED",
        "reasoning": "Conteggio di 'pattern_fired' (piu' vicino concettualmente a un raw trigger "
                    "che a un trade eseguito) su una configurazione non documentata in questo "
                    "artifact. L'ordine di grandezza (1955 su una finestra non nota) e' compatibile "
                    "con un conteggio multi-TF contaminato (questa fase trova 2453 raw trigger "
                    "totali su 2.9 anni nella propria simulazione, ab_simulation_v1.json) ma le "
                    "finestre temporali non sono le stesse - NON trattato come conferma numerica, "
                    "solo come coerenza di ordine di grandezza plausibile.",
        "implication": "Nessuna reinterpretazione quantitativa - il numero resta un dato storico "
                       "non ri-derivabile con la strumentazione di questa fase (manca la "
                       "configurazione esatta del run).",
    },
    {
        "artifact": "MQL5/Include/NEXUS_v1/NXS_StrategyProfiles.mqh righe 426-427 "
                   "(NXS_Profile_Risk: 'ORDER_BLOCK -> 0.5 // PF 0.67', 'OB_MIT -> 0.5 // PF 0.38') "
                   "e righe 490-491 (NXS_Profile_TrailK: 'ORDER_BLOCK 0.94->2.03', 'OB_MIT 0.46->1.52')",
        "kind": "CODE_COMMENT_REFERENCING_UNTRACEABLE_HISTORICAL_PF",
        "classification": "CANNOT_DETERMINE",
        "reasoning": "Questi commenti sono collocati nella sezione 'Fuori dal nucleo attuale, valori "
                    "precedenti invariati' (riga 416: 'nessuna nuova evidenza raccolta su quelle') - "
                    "la fonte (Python OOS vs MT5 reale), la data e la configurazione multi-TF di "
                    "queste misure NON sono ricostruibili da questo commento da solo. Richiederebbe "
                    "git blame per-strategia, dichiarato fuori scope anche dal census di Phase 7.11 "
                    "per lo stesso motivo.",
        "implication": "Non utilizzato per nessuna conclusione in questa fase - ne' come conferma "
                       "ne' come confutazione del difetto o della redditivita'.",
    },
    {
        "artifact": "vault_documentation=PRESENT (census Phase 7.11) - articoli vault non "
                   "singolarmente riletti in questa fase per ORDER_BLOCK/OB_MIT",
        "kind": "VAULT_ARTICLES_UNSPECIFIED",
        "classification": "CANNOT_DETERMINE",
        "reasoning": "Limite dichiarato: questa fase non ha riletto individualmente ogni articolo "
                    "vault storico che menziona ORDER_BLOCK/OB_MIT per classificarne il contenuto "
                    "riga per riga rispetto al difetto - sarebbe un lavoro di audit documentale "
                    "separato (stesso tipo di 'adjudication documentale' usata per BREAKOUT_ACC in "
                    "Phase 7.9F), non nello scope di questo protocollo diagnostico.",
        "implication": "Raccomandato come follow-up SOLO se si decide di procedere verso un fix "
                       "(vedi Decision Card, sezione dipendenze) - non blocca la diagnosi causale "
                       "gia' effettuata in questa fase.",
    },
    {
        "artifact": "census Phase 7.11 (complete_strategy_census_v1.json): historical_tests=null "
                   "per ORDER_BLOCK e OB_MIT",
        "kind": "CENSUS_STRUCTURED_FIELD",
        "classification": "UNAFFECTED",
        "reasoning": "Nessun artifact di sweep strutturato (formato tipo il sweep37 di TSI) e' "
                    "stato trovato per ORDER_BLOCK/OB_MIT nel census - questo campo null non e' "
                    "esso stesso un'evidenza contaminabile, e' l'assenza di un tipo di evidenza.",
        "implication": "Nessuna implicazione oltre quanto gia' noto: non c'e' uno sweep storico "
                       "strutturato da riclassificare per queste due identita'.",
    },
]


def build():
    counts = {}
    for it in ITEMS:
        counts[it["classification"]] = counts.get(it["classification"], 0) + 1
    payload = {
        "principle": "un PF/WR non viene mai reinterpretato come evidenza della strategia canonica "
                    "se l'identita' eseguita (single-TF pulito vs multi-TF contaminato) non e' "
                    "stabilita per quell'artifact specifico - nessun artifact viene cancellato, "
                    "solo classificato",
        "classifications_used": ["UNAFFECTED", "UNAFFECTED_BUT_NOT_REPRESENTATIVE_OF_LIVE",
                                 "POSSIBLY_CONTAMINATED", "CONTAMINATED", "CANNOT_DETERMINE"],
        "items": ITEMS,
        "counts_by_classification": counts,
        "no_artifact_deleted_or_modified": True,
        "no_pf_reinterpreted_as_canonical_evidence": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE713_DIR, "historical_evidence_impact_map_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  classificazioni: {payload['counts_by_classification']}")


if __name__ == "__main__":
    main()
