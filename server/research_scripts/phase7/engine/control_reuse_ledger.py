#!/usr/bin/env python3
"""Phase 7.4A Final Statistical Integrity Patch sec.5 - Control Reuse
Ledger. BaselineEngineV4.match() sceglie i k nearest-neighbour per
OGNI evento indipendentemente - nulla impedisce che lo STESSO control
bar venga scelto come vicino per piu' eventi diversi nella stessa run.
Riuso non vietato per principio (un pool storico finito rende il
riuso spesso necessario), ma va CONGELATO un tetto massimo e
l'incertezza (diagnostica DEPENDENCE_SENSITIVE) deve poterne riflettere
l'effetto - non lasciato illimitato e non tracciato."""


class ControlReuseLimitExceededWarning(Exception):
    """Sollevata solo in modalita' strict (test) - in produzione il
    controllo oltre il tetto viene ESCLUSO dal pool disponibile per il
    prossimo evento, non causa un errore fatale della run."""
    pass


class ControlReuseLedger:
    def __init__(self, max_control_reuse_per_run: int):
        if max_control_reuse_per_run < 1:
            raise ValueError("max_control_reuse_per_run deve essere >=1")
        self.max_control_reuse_per_run = max_control_reuse_per_run
        self._usage_count = {}

    def filter_available_pool(self, control_pool: list) -> list:
        """Da chiamare PRIMA di passare il pool a
        SequenceBaselineAdapter.match_sequence_event() per il prossimo
        evento - esclude i control_id che hanno gia' raggiunto il tetto
        di riuso in questa run."""
        return [cid for cid in control_pool if self._usage_count.get(cid, 0) < self.max_control_reuse_per_run]

    def register_controls_used(self, control_ids_used: list):
        for cid in control_ids_used:
            self._usage_count[cid] = self._usage_count.get(cid, 0) + 1

    def usage_report(self) -> dict:
        if not self._usage_count:
            return {"n_controls_used": 0, "max_reuse_observed": 0, "n_controls_at_cap": 0}
        counts = list(self._usage_count.values())
        return {
            "n_controls_used": len(self._usage_count),
            "max_reuse_observed": max(counts),
            "n_controls_at_cap": sum(1 for c in counts if c >= self.max_control_reuse_per_run),
            "mean_reuse": sum(counts) / len(counts),
        }


if __name__ == "__main__":
    # Caso 1: sotto il tetto, nessuna esclusione.
    ledger = ControlReuseLedger(max_control_reuse_per_run=3)
    ledger.register_controls_used(["C1", "C2"])
    pool = ["C1", "C2", "C3", "C4"]
    filtered = ledger.filter_available_pool(pool)
    assert filtered == pool, "sotto il tetto nessun controllo deve essere escluso"
    print(f"Caso 1 OK: pool invariato sotto il tetto -> {filtered}")

    # Caso 2: un controllo raggiunge il tetto -> escluso dal pool per il prossimo evento.
    for _ in range(3):
        ledger.register_controls_used(["C1"])
    filtered2 = ledger.filter_available_pool(pool)
    assert "C1" not in filtered2 and set(filtered2) == {"C2", "C3", "C4"}
    print(f"Caso 2 OK: C1 al tetto (3 usi) correttamente escluso -> {filtered2}")

    # Caso 3: usage_report riflette correttamente lo stato (C1 usato 1+3=4 volte totali).
    report = ledger.usage_report()
    assert report["max_reuse_observed"] == 4 and report["n_controls_at_cap"] == 1
    print(f"Caso 3 OK: usage_report -> {report}")

    # Caso 4: tetto invalido rifiutato.
    try:
        ControlReuseLedger(max_control_reuse_per_run=0)
        print("ERRORE: tetto invalido non rifiutato!")
    except ValueError:
        print("Caso 4 OK: max_control_reuse_per_run<1 correttamente rifiutato.")

    print("\nSelf-test control_reuse_ledger completato su dati SINTETICI.")
