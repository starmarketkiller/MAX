#!/usr/bin/env python3
"""Phase 7.4A Final Statistical Integrity Patch sec.3-4 - Matched-Pair
Block Sign-Flip Permutation Test.

Risponde a due problemi distinti sollevati nell'audit:

sec.1 (bootstrap CI != p-value valido sotto H0): il metodo precedente
(two_sample_block_bootstrap_percentile_p) ricampiona le distribuzioni
OSSERVATE (evento e baseline) e guarda dove cade 0 nella distribuzione
bootstrap della differenza - questo e' un test per INVERSIONE DI CI, non
impone esplicitamente H0: delta=0 nel ricampionamento stesso. Sotto skew
o bias questo puo' essere mal calibrato (motivo per cui esiste BCa come
correzione del percentile bootstrap "ingenuo").

sec.4 (struttura matched non va appiattita): BaselineEngineV4 produce
PER OGNI evento un set di controlli matched (k nearest-neighbour) - non
un pool indipendente condiviso. Appiattire tutto in due pool separati
(evento vs baseline) getta via l'informazione di accoppiamento e puo'
sia sovra- sia sotto-stimare l'incertezza reale a seconda della
struttura di dipendenza fra evento e i propri controlli (che ESISTE per
costruzione: i controlli sono scelti proprio perche' simili allo stato
dell'evento).

Soluzione unificata per outcome BINARI e CONTINUI:

  d_i = outcome(event_i) - mean(outcome(matched_controls_i))

Sotto H0 (nessuna differenza sistematica fra un evento e i propri
controlli comparabili), il segno di ciascun d_i e' scambiabile - si
genera la distribuzione nulla capovolgendo il segno di BLOCCHI
contigui (non singoli d_i, per preservare dipendenza seriale residua
fra osservazioni indipendenti vicine nel tempo - vedi
sequence_episode_engine.build_outcome_independent_view, che rimuove
solo la sovrapposizione diretta delle outcome window, non la
dipendenza di regime piu' ampia) e si calcola il p-value come
frazione di repliche con |media permutata| >= |media osservata|
(test di permutazione standard, ispezionabile passo-passo, nessun
modello nascosto - vedi statistical_methods_policy.json)."""
import math
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_5"))
from block_bootstrap import block_length_default  # noqa: E402,F401 - riuso della stessa formula L=ceil(n^(1/3))


def compute_matched_pair_differences(event_outcomes: list, matched_control_outcomes_by_event: list,
                                      aggregate: str = "mean") -> list:
    """event_outcomes[i]: outcome scalare (0/1 per binario, float per continuo)
    dell'osservazione i della INDEPENDENT_VIEW. matched_control_outcomes_by_event[i]:
    lista degli outcome dei controlli k-NN matched a QUELLA osservazione (mai un
    pool condiviso fra osservazioni diverse). aggregate='mean' e' l'UNICA funzione
    di aggregazione ammessa qui (dichiarata esplicitamente, non parametrizzabile
    silenziosamente in una run reale)."""
    if aggregate != "mean":
        raise ValueError("Solo aggregate='mean' e' congelato per questa family - nessun'altra aggregazione ammessa senza pre-registrazione esplicita.")
    d = []
    for outcome_i, controls_i in zip(event_outcomes, matched_control_outcomes_by_event):
        if not controls_i:
            continue  # evento senza controlli validi - escluso, mai imputato
        d.append(float(outcome_i) - float(np.mean(controls_i)))
    return d


def block_sign_flip_permutation_p(d_values, n_boot=2000, block_length=None, seed=42):
    """d_values: sequenza ORDINATA per tempo delle differenze accoppiate
    (evento - aggregato controlli matched). Genera la distribuzione nulla
    capovolgendo il segno di blocchi contigui - impone ESPLICITAMENTE
    H0: E[d]=0 per costruzione (l'operazione di sign-flip e' simmetrica
    attorno a 0, a differenza del bootstrap dei dati osservati)."""
    d = np.asarray([v for v in d_values if v is not None and not (isinstance(v, float) and np.isnan(v))], dtype=float)
    n = len(d)
    if n < 5:
        return {"n": n, "note": "campione troppo piccolo per il test di permutazione"}
    L = block_length or block_length_default(n)
    n_blocks = math.ceil(n / L)
    rng = np.random.default_rng(seed)

    t_obs = float(d.mean())
    t_boot = np.empty(n_boot)
    for b in range(n_boot):
        signs_per_block = rng.choice([-1.0, 1.0], size=n_blocks)
        signs = np.repeat(signs_per_block, L)[:n]
        t_boot[b] = (d * signs).mean()

    # p-value di permutazione standard (correzione +1/+1 per evitare p=0 - Davison & Hinkley 1997).
    p_value = float((1 + np.sum(np.abs(t_boot) >= abs(t_obs))) / (n_boot + 1))

    return {
        "n": n, "block_length": L, "n_blocks": n_blocks, "n_boot": n_boot,
        "t_observed": t_obs, "t_null_std": float(t_boot.std()),
        "p_value": p_value, "method": "block_sign_flip_permutation",
    }


if __name__ == "__main__":
    rng = np.random.default_rng(11)

    # Caso 1: d_i sotto H0 vera (media 0) -> p-value NON deve rifiutare sistematicamente.
    d_h0 = rng.normal(0.0, 1.0, 60)
    r1 = block_sign_flip_permutation_p(d_h0)
    print(f"Caso 1 (H0 vera, media~0): t_obs={r1['t_observed']:.4f}, p={r1['p_value']:.4f}")
    assert r1["p_value"] > 0.05, "con H0 vera il p-value non dovrebbe risultare falsamente significativo in questo seed"

    # Caso 2: differenza chiara -> p-value deve rifiutare H0.
    d_effect = rng.normal(0.8, 1.0, 60)
    r2 = block_sign_flip_permutation_p(d_effect)
    print(f"Caso 2 (differenza reale e ampia): t_obs={r2['t_observed']:.4f}, p={r2['p_value']:.4f}")
    assert r2["p_value"] < 0.05, "con una differenza ampia e reale il p-value dovrebbe risultare significativo"

    # Caso 3: campione troppo piccolo -> nessun p-value, nota esplicita.
    r3 = block_sign_flip_permutation_p([0.1, 0.2, -0.1])
    assert "p_value" not in r3 and "note" in r3
    print(f"Caso 3 (campione insufficiente): {r3['note']}")

    # Caso 4: compute_matched_pair_differences - esclude eventi senza controlli, aggregate!='mean' rifiutato.
    d4 = compute_matched_pair_differences([1.0, 0.5, 0.0], [[0.2, 0.3], [], [0.1, 0.1, 0.1]])
    assert len(d4) == 2, "l'evento senza controlli deve essere escluso, non imputato"
    try:
        compute_matched_pair_differences([1.0], [[0.5]], aggregate="median")
        print("ERRORE: aggregate!='mean' avrebbe dovuto essere rifiutato!")
    except ValueError:
        print("Caso 4 OK: evento senza controlli escluso; aggregate diverso da 'mean' rifiutato.")

    print("\nSelf-test matched_pair_permutation_test completato su dati SINTETICI.")
