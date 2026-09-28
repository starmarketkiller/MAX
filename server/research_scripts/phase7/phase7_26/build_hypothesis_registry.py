#!/usr/bin/env python3
"""Phase 7.26.C - HYPOTHESIS_REGISTRY_V1. Regola obbligatoria: una
hypothesis scoperta su un dataset non puo' essere considerata validata
usando quello stesso dataset - verify() (e verify_leakage.py) la
applicano staticamente confrontando discovery_dataset_id contro
validation_dataset_ids."""
import os
import sys

PHASE726_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE726_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE726_DIR)
from nxs_schemas import (HYPOTHESIS_REQUIRED_FIELDS, HYPOTHESIS_LIFECYCLE_STATES,  # noqa: E402
                         missing_required)


def _h(**kw):
    for f in HYPOTHESIS_REQUIRED_FIELDS:
        kw.setdefault(f, None)
    kw.setdefault("mechanical_verification_exception", False)
    assert kw["lifecycle_state"] in HYPOTHESIS_LIFECYCLE_STATES, kw["lifecycle_state"]
    return kw


def build():
    hypotheses = [
        _h(
            hypothesis_id="H1_BREAKOUT_ACC_NET_EXPECTANCY_POSITIVE",
            statement="BREAKOUT_ACC (ALL, BUY+SELL aggregato) possiede expectancy netta "
                     "positiva dopo costi realistici.",
            lifecycle_state="INCONCLUSIVE",
            discovery_dataset_id="BREAKOUT_ACC::2019.02.21_2026.06.09",
            validation_dataset_ids=["BREAKOUT_ACC::2026.08.15_2026.09.27"],
            originating_strategies=["BREAKOUT_ACC"],
            evidence_level="CI95 include lo zero sul dataset di discovery; OOS n=1 "
                          "(INSUFFICIENT_OOS_SAMPLE, perdente) - nessuna validazione indipendente "
                          "sufficiente ancora ottenuta.",
        ),
        _h(
            hypothesis_id="H2_BREAKOUT_ACC_BUY_MORE_ROBUST_THAN_SELL",
            statement="Il lato BUY di BREAKOUT_ACC possiede expectancy positiva piu' robusta "
                     "del lato SELL.",
            lifecycle_state="HYPOTHESIS",
            discovery_dataset_id="BREAKOUT_ACC::2019.02.21_2026.06.09",
            validation_dataset_ids=[],
            originating_strategies=["BREAKOUT_ACC"],
            evidence_level="POST-HOC per costruzione (scoperta guardando l'intero campione, "
                          "Phase 7.9I/J/K) - MAI testata su un dataset indipendente. Non puo' "
                          "salire a SUPPORTED/REJECTED finche' non esiste un validation_dataset "
                          "diverso dal discovery_dataset (regola obbligatoria di questo registry).",
        ),
        _h(
            hypothesis_id="H_ORDER_BLOCK_EDGE_EXISTS",
            statement="ORDER_BLOCK V2 (TF-guarded) possiede un edge economico reale.",
            lifecycle_state="INCONCLUSIVE",
            discovery_dataset_id="ORDER_BLOCK::2023.10.02_2026.08.24",
            validation_dataset_ids=["ORDER_BLOCK::2026.08.25_2026.09.27"],
            originating_strategies=["ORDER_BLOCK"],
            evidence_level="Expectancy nominale positiva ma CI95 include zero, concentrazione "
                          "estrema (196.8% top-5), OOS n=0 (INSUFFICIENT_OOS_SAMPLE).",
        ),
        _h(
            hypothesis_id="H_TSI_TF_GUARD_FIX_EFFECTIVE",
            mechanical_verification_exception=True,
            statement="La guardia TF-scoped aggiunta a NXS_Strat_TSI() elimina la contaminazione "
                     "cross-TF (100% delle barre D1 alterate pre-fix).",
            lifecycle_state="SUPPORTED",
            discovery_dataset_id="TSI::2026.01.01_2026.08.25_short_diag",
            validation_dataset_ids=["TSI::2026.01.01_2026.08.25_short_diag"],
            originating_strategies=["TSI"],
            evidence_level="A/B pre/post-fix sugli STESSI tick reali (0 righe non-D1 post-fix, "
                          "atteso 0) - questa e' un'ipotesi MECCANICA (verificabile per "
                          "costruzione/conteggio esatto), non economica: la regola "
                          "discovery!=validation si applica a hypothesis ECONOMICHE/di pattern, "
                          "non a verifiche deterministiche di un fix di codice sullo stesso "
                          "sistema che lo implementa.",
        ),
        _h(
            hypothesis_id="H_LIQ_SWEEP_HTF_MISMATCH",
            mechanical_verification_exception=True,
            statement="Il filtro HTF (px200 vs g_ema200) di LIQ_SWEEP soffre di un mismatch "
                     "cross-TF dovuto a g_ema200 stantio durante il pass multi-TF.",
            lifecycle_state="REJECTED",
            discovery_dataset_id="LIQ_SWEEP::2023.10.02_2026.06.30",
            validation_dataset_ids=["LIQ_SWEEP::2023.10.02_2026.06.30"],
            originating_strategies=["LIQ_SWEEP"],
            evidence_level="Verifica per COSTRUZIONE (trace statico del codice sorgente, non "
                          "statistica) - NXS_ActivateTF chiama NXS_UpdateIndicators PRIMA di "
                          "NXS_CollectRaw nello stesso pass, sempre. Come H_TSI sopra, e' una "
                          "verifica meccanica/deterministica, non soggetta alla regola "
                          "discovery!=validation (nessun campionamento statistico coinvolto).",
        ),
        _h(
            hypothesis_id="H_LIQ_SWEEP_EXIT_MISMATCH_MQL5_PYTHON",
            mechanical_verification_exception=True,
            statement="L'uscita SL/TP di LIQ_SWEEP diverge strutturalmente fra MQL5 (ATR fisso) "
                     "e il proxy storico Python (target dinamico su liquidita').",
            lifecycle_state="SUPPORTED",
            discovery_dataset_id="LIQ_SWEEP::2023.10.02_2026.06.30",
            validation_dataset_ids=["LIQ_SWEEP::2023.10.02_2026.06.30"],
            originating_strategies=["LIQ_SWEEP"],
            evidence_level="Lettura diretta del codice sorgente di entrambe le implementazioni "
                          "(non statistica) - il commento Python stesso dichiara la sostituzione "
                          "di 'un multiplo fisso di ATR'.",
        ),
        _h(
            hypothesis_id="H_LIQ_SWEEP_EDGE_EXISTS",
            statement="LIQ_SWEEP (post-fix detector) possiede un edge economico reale.",
            lifecycle_state="INCONCLUSIVE",
            discovery_dataset_id="LIQ_SWEEP::2023.10.02_2026.06.30",
            validation_dataset_ids=["LIQ_SWEEP::2026.07.01_2026.09.27"],
            originating_strategies=["LIQ_SWEEP"],
            evidence_level="Storico nominalmente positivo (PF 1.48) ma CI95 include zero, 99% "
                          "del netto concentrato in un solo anno (2025), OOS genuino n=6 "
                          "NEGATIVO (-$539.30/-89.88 per trade, WR 17%) - il segnale contrario "
                          "piu' forte del corpus finora, ma n troppo piccolo per REJECTED.",
        ),
        _h(
            hypothesis_id="H_CROSS_STRATEGY_PROFIT_CONCENTRATION",
            statement="Le strategie D1 di questo corpus (BREAKOUT_ACC/ORDER_BLOCK/LIQ_SWEEP) "
                     "tendono a mostrare P&L storico concentrato in pochi trade/periodi, non "
                     "distribuito uniformemente - possibile pattern trasversale, non ancora "
                     "spiegato meccanicamente.",
            lifecycle_state="HYPOTHESIS",
            discovery_dataset_id="CROSS_STRATEGY_SYNTHESIS_V1_BACKFILL",
            validation_dataset_ids=[],
            originating_strategies=["BREAKOUT_ACC", "ORDER_BLOCK", "LIQ_SWEEP"],
            evidence_level="OBSERVATION aggregata in questa fase (Phase 7.26) - richiede "
                          "validazione su strategie/dataset FUTURI, non ancora testati, prima di "
                          "poter salire di stato.",
        ),
        _h(
            hypothesis_id="H_BUY_DOMINANCE_MARKET_REGIME_ARTIFACT",
            statement="La dominanza BUY condivisa da BREAKOUT_ACC/ORDER_BLOCK/LIQ_SWEEP riflette "
                     "principalmente il regime di mercato (trend/volatilita' di GOLD nel periodo "
                     "studiato), non una capacita' di selezione temporale specifica di ciascuna "
                     "strategia.",
            lifecycle_state="TESTING",
            discovery_dataset_id="CROSS_STRATEGY_SYNTHESIS_V1_BACKFILL",
            validation_dataset_ids=["BREAKOUT_ACC::2019.02.21_2026.06.09",
                                   "ORDER_BLOCK::2023.10.02_2026.08.24",
                                   "LIQ_SWEEP::2023.10.02_2026.06.30"],
            originating_strategies=["BREAKOUT_ACC", "ORDER_BLOCK", "LIQ_SWEEP"],
            evidence_level="Phase 7.27: benchmark preregistrato (random/periodic/regime-matched/"
                          "unconditional) su tutti i BUY reali delle 3 strategie, orizzonte "
                          "primario h10 - NESSUNA strategia batte significativamente il "
                          "benchmark long regime-matched (CI95 include sempre zero); su 21 "
                          "confronti orizzonte/strategia regime-matched solo 1 e' 'significativo' "
                          "(ORDER_BLOCK h1, n=12, si inverte di segno agli orizzonti piu' lunghi, "
                          "non sopravvive a una correzione multiple-testing anche minima) - "
                          "decisione: BUY_DOMINANCE_LARGELY_EXPLAINED_BY_MARKET_REGIME. RESTA "
                          "'TESTING' non 'SUPPORTED': i dataset usati sono di discovery (gia' "
                          "esposti), non un holdout indipendente (dichiarato esplicitamente dal "
                          "task stesso, punto 7) - qualunque promozione a SUPPORTED richiede "
                          "prima una validazione indipendente su dati non ancora esposti.",
        ),
    ]
    for h in hypotheses:
        missing = missing_required(h, HYPOTHESIS_REQUIRED_FIELDS)
        if missing:
            raise AssertionError(f"{h.get('hypothesis_id')} manca campi: {missing}")

    payload = {
        "schema_version": "HYPOTHESIS_REGISTRY_V1",
        "lifecycle_states": HYPOTHESIS_LIFECYCLE_STATES,
        "mandatory_rule": "Una hypothesis scoperta su un dataset non puo' essere considerata "
                        "SUPPORTED/REJECTED usando quello stesso dataset come unica "
                        "validation - eccezione dichiarata SOLO per verifiche deterministiche/"
                        "meccaniche di codice (non statistiche, nessun campionamento) come i fix "
                        "TSI/HTF di questa fase.",
        "hypotheses": hypotheses, "n_hypotheses": len(hypotheses),
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE726_DIR, "hypothesis_registry_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  n_hypotheses={payload['n_hypotheses']}")


if __name__ == "__main__":
    main()
