#!/usr/bin/env python3
"""Phase 7.1 Integrity & Provenance Patch (post-review, 2026-09-19) -
enforcement REALE (non solo policy) della regola:

    PRE-REGISTRATION COMMIT -> RUN -> RESULT COMMIT

Bug/limite trovato nella prima vera discovery run (Phase 7.1): il
frozen spec (phase7_1_frozen_spec_v1.json) e' stato committato NELLO
STESSO commit dei risultati (f9bfd68) - la dichiarazione
"congelato PRIMA di guardare i dati" e' vera (verificabile leggendo il
contenuto del file e la sequenza di esecuzione reale), ma Git da solo
NON puo' provare l'ordine temporale quando frozen spec e risultati
condividono un commit. Questo modulo impedisce che la cosa si ripeta:
una futura discovery run deve rifiutarsi di partire se il proprio
frozen spec non e' GIA' un file tracciato e pulito (nessuna modifica
non committata) al momento dell'avvio - questo forza strutturalmente
il frozen spec in un commit SEPARATO e ANTECEDENTE a qualunque commit
di risultati.

Non e' una prova crittografica di "quando" il file e' stato scritto
(Git non registra quello) - e' un vincolo PROCEDURALE: se il file deve
gia' essere committato e pulito prima che lo script parta, il commit
dei risultati (fatto DOPO l'esecuzione) sara' necessariamente
successivo. Dichiarato esplicitamente come limite, non come garanzia
piu' forte di quella che e'.
"""
import subprocess


class PreRegistrationProvenanceError(Exception):
    pass


def _git(args, cwd):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)


def is_tracked_and_clean(repo_root: str, rel_path: str):
    """Ritorna (ok: bool, reason: str|None). ok=True solo se il file e'
    tracciato da git E non ha modifiche non committate rispetto a HEAD."""
    r = _git(["ls-files", "--error-unmatch", rel_path], repo_root)
    if r.returncode != 0:
        return False, "file non tracciato da git (mai committato)"
    r2 = _git(["diff", "--quiet", "HEAD", "--", rel_path], repo_root)
    if r2.returncode != 0:
        return False, "file tracciato ma con modifiche non committate rispetto a HEAD"
    return True, None


def get_commit_sha_for_file(repo_root: str, rel_path: str):
    r = _git(["log", "-1", "--format=%H", "--", rel_path], repo_root)
    sha = r.stdout.strip()
    return sha or None


def assert_frozen_spec_committed_before_run(repo_root: str, rel_path: str) -> str:
    """Da chiamare all'AVVIO di ogni futura discovery run, prima di
    calcolare qualunque outcome. Solleva PreRegistrationProvenanceError
    se il frozen spec non e' pronto - ritorna il commit SHA del frozen
    spec se la verifica passa (da riportare nel run manifest)."""
    ok, reason = is_tracked_and_clean(repo_root, rel_path)
    if not ok:
        raise PreRegistrationProvenanceError(
            f"Frozen spec '{rel_path}' non e' pronto per una nuova discovery run: {reason}. "
            f"Regola obbligatoria: PRE-REGISTRATION COMMIT -> RUN -> RESULT COMMIT. "
            f"Committa il frozen spec in un commit dedicato PRIMA di eseguire questa run."
        )
    sha = get_commit_sha_for_file(repo_root, rel_path)
    if sha is None:
        raise PreRegistrationProvenanceError(
            f"Frozen spec '{rel_path}' risulta tracciato/pulito ma senza alcun commit SHA associato - stato incoerente, run bloccata."
        )
    return sha


if __name__ == "__main__":
    import os
    import tempfile

    repo_root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()

    # Caso 1 (positivo): un file GIA' committato e pulito nel repo reale
    # deve passare e restituire uno SHA valido. Usiamo un file di Phase 7
    # gia' committato in una fase precedente (baseline_contract_v4.json).
    known_committed_rel = "server/research_scripts/phase7/baseline_contract_v4.json"
    sha = assert_frozen_spec_committed_before_run(repo_root, known_committed_rel)
    print(f"Caso 1 (file committato e pulito): OK, sha={sha[:12]}...")
    assert sha is not None and len(sha) == 40

    # Caso 2 (negativo): un file MAI committato deve bloccare la run.
    with tempfile.NamedTemporaryFile(dir=os.path.join(repo_root, "server", "research_scripts", "phase7"),
                                      suffix=".json", delete=False) as tf:
        tf.write(b'{"fake": "never committed"}')
        tmp_path = tf.name
    rel_tmp = os.path.relpath(tmp_path, repo_root).replace("\\", "/")
    try:
        assert_frozen_spec_committed_before_run(repo_root, rel_tmp)
        print("ERRORE: un file mai committato avrebbe dovuto bloccare la run!")
    except PreRegistrationProvenanceError as e:
        print(f"Caso 2 (file mai committato) correttamente bloccato: {type(e).__name__}")
    finally:
        os.remove(tmp_path)

    # Caso 3 (negativo): un file tracciato ma con modifiche non committate
    # deve bloccare la run - simulato modificando temporaneamente un file
    # gia' committato e ripristinandolo subito dopo (nessuna modifica reale lasciata).
    target = os.path.join(repo_root, known_committed_rel)
    with open(target, "r", encoding="utf-8") as f:
        original_content = f.read()
    try:
        with open(target, "a", encoding="utf-8") as f:
            f.write("\n")  # modifica minima non committata
        try:
            assert_frozen_spec_committed_before_run(repo_root, known_committed_rel)
            print("ERRORE: un file con modifiche non committate avrebbe dovuto bloccare la run!")
        except PreRegistrationProvenanceError as e:
            print(f"Caso 3 (modifiche non committate) correttamente bloccato: {type(e).__name__}")
    finally:
        with open(target, "w", encoding="utf-8") as f:
            f.write(original_content)  # ripristino esatto, nessuna modifica lasciata sul repo

    print("\nTutti i casi verificati.")
